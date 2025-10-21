from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.db import IntegrityError, transaction
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.utils.timezone import now, localdate
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.template.loader import render_to_string
from django.conf import settings

from decimal import Decimal, InvalidOperation
from datetime import timedelta
from pathlib import Path

from .models import (
    UserProfile, Client, Invoice, Lead, Estimation, EstimationItem,
    UserPermission, PaymentLog, GSTSettings, EstimationSettings,
    TermsAndConditions
)
from .forms import UserForm, ClientForm, EstimationForm, ApprovalForm
from .utils import inr_currency_words, generate_invoice_number

User = get_user_model()

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def create_user(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        role = request.POST.get('role', 'User')
        phone_number = request.POST.get('phone_number', '').strip()
        selected_permissions = request.POST.getlist('permissions')

        if not username or not password or not confirm_password or not role:
            messages.error(request, "All required fields must be filled.")
            return redirect('create_user')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('create_user')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('create_user')

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_staff = True
            user.is_superuser = (role == 'Admin')
            user.role = role
            user.save()

            user_profile = UserProfile.objects.create(
                user=user, name=username, email=email, phone_number=phone_number, role=role
            )

            if role != 'Admin' and selected_permissions:
                perms_to_add = []
                for perm_str in selected_permissions:
                    try:
                        app_label, codename = perm_str.split('.')
                        perm = Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=codename
                        )
                        perms_to_add.append(perm)
                    except Permission.DoesNotExist:
                        messages.warning(request, f"Permission '{perm_str}' not found.")
                user.user_permissions.set(perms_to_add)
                user_profile.permissions.set(perms_to_add)

            messages.success(request, f"{role} '{username}' created successfully.")
            return redirect('user_list')
        except IntegrityError:
            messages.error(request, "Database error. Try again.")
            return redirect('create_user')

    permissions = Permission.objects.filter(content_type__app_label='crm').order_by('name')
    return render(request, 'users/add_user.html', {'permissions': permissions})

@login_required
def user_list(request):
    users = UserProfile.objects.select_related('user').all()
    return render(request, "users/user_list.html", {'users': users})

@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if user.role == 'Admin':
        permissions = Permission.objects.all()
    else:
        permissions = Permission.objects.exclude(codename__in=['admin_access', 'purchase_access'])

    if request.method == 'POST':
        selected_permissions = request.POST.getlist('permissions')
        perms_to_set = []
        for perm_str in selected_permissions:
            try:
                app_label, codename = perm_str.split('.')
                perm = Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
                perms_to_set.append(perm)
            except Permission.DoesNotExist:
                messages.warning(request, f"Permission '{perm_str}' not found.")
        user.user_permissions.set(perms_to_set)
        if hasattr(user, 'userprofile'):
            user.userprofile.permissions.set(perms_to_set)
        user.save()
        messages.success(request, 'User updated successfully.')
        return redirect('user_list')

    return render(request, 'users/edit_user.html', {'user_obj': user, 'permissions': permissions})

@login_required
def delete_user(request, user_id):
    user_profile = get_object_or_404(UserProfile, id=user_id)
    user_profile.user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('user_list')

@login_required
def get_permissions_by_role(request):
    role = request.GET.get('role')
    if role == 'Admin':
        permissions = Permission.objects.all()
    elif role == 'User':
        permissions = Permission.objects.filter(
            codename__in=['view_client', 'view_lead', 'view_estimation', 'view_invoice', 'view_report']
        )
    else:
        permissions = Permission.objects.none()
    permission_list = [
        {
            'id': p.id,
            'name': f"{p.content_type.app_label} | {p.name}",
            'code': f"{p.content_type.app_label}.{p.codename}"
        } for p in permissions
    ]
    return JsonResponse({'permissions': permission_list})

class UserUpdateView(UpdateView):
    model = User
    form_class = UserForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('user_list')

@login_required
def dashboard(request):
    user = request.user
    user_perm_names = set(
        UserPermission.objects.filter(userprofile__user=user).values_list("name", flat=True)
    )
    context = {
        "can_view_client": "can_view_client" in user_perm_names,
        "can_view_lead": "can_view_lead" in user_perm_names,
        "can_view_estimation": "can_view_estimation" in user_perm_names,
        "can_view_invoice": "can_view_invoice" in user_perm_names,
        "can_view_reports": "can_view_reports" in user_perm_names,
        "grouped_modules": {
            "Sales": [
                {"name": "Client", "url": "/client/"},
                {"name": "Lead", "url": "/lead/"},
                {"name": "Estimation", "url": "/estimation/"},
                {"name": "Invoice", "url": "/invoices/"},
                {"name": "Reports", "url": "/reports/"},
            ],
            "Purchase": [
                {"name": "Vendor", "url": "/vendor/"},
                {"name": "PO", "url": "/purchase-order/"},
                {"name": "Bill", "url": "/bill/"},
            ],
        },
    }
    context["total_invoiced"] = Invoice.objects.aggregate(total=Sum('total_value'))['total'] or 0
    context["paid"] = PaymentLog.objects.filter(
        Q(status="Paid") | Q(status="Partial Paid")
    ).aggregate(total=Sum("amount_paid"))["total"] or 0
    context["balance_due"] = Invoice.objects.aggregate(total=Sum("balance_due"))["total"] or 0
    total_leads = Lead.objects.count()
    total_invoices = Invoice.objects.count()
    context["total_leads"] = total_leads
    context["total_quotations"] = Estimation.objects.count()
    context["total_invoices"] = total_invoices
    context["conversion_rate"] = round((total_invoices / total_leads) * 100, 2) if total_leads else 0
    context["quotation_status"] = Estimation.objects.values("status").annotate(count=Count("id")).order_by("status")
    context["invoice_status"] = Invoice.objects.values("status").annotate(count=Count("id")).order_by("status")
    context["top_clients"] = Client.objects.annotate(total_leads=Count("lead")).order_by("-total_leads")[:4]
    context["filter_options"] = [
        ("This Month", "this_month"), ("This Quarter", "this_quarter"), ("This Year", "this_year"),
        ("Previous Month", "previous_month"), ("Previous Quarter", "previous_quarter"),
        ("Previous Year", "previous_year"), ("Custom", "custom"),
    ]
    context["selected_filter"] = request.GET.get("date_filter", "this_month")
    context["user_name"] = user.first_name or user.username
    return render(request, "dashboard.html", context)

@login_required
def confirm_payment(request, payment_id):
    payment = get_object_or_404(PaymentLog, id=payment_id)
    invoice = payment.invoice
    total_paid = PaymentLog.objects.filter(
        invoice=invoice, status__in=["Paid", "Partial Paid"]
    ).aggregate(total=Sum("amount_paid"))["total"] or 0
    if total_paid >= invoice.total_value:
        invoice.status = "Paid"
    elif total_paid > 0:
        invoice.status = "Partial Paid"
    else:
        invoice.status = "Unpaid"
    invoice.paid_amount = total_paid
    invoice.balance_due = invoice.total_value - total_paid
    invoice.save()
    payment.status = invoice.status
    payment.save()
    return redirect("payment_list")

@login_required
def client_list(request):
    query = request.GET.get('q', '')
    clients = Client.objects.all()
    if query:
        clients = clients.filter(company_name__icontains=query)
    paginator = Paginator(clients, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'client.html', {'clients': page_obj, 'query': query, 'page_obj': page_obj})

def edit_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    if request.method == 'POST':
        client.company_name = request.POST.get('company_name')
        client.type_of_company = request.POST.get('type_of_company')
        client.gst_no = request.POST.get('gst_no')
        client.save()
        return redirect('client')
    return render(request, 'edit_client.html', {'client': client})

@login_required
@csrf_exempt
def client_entry(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name', '').strip()
        type_of_company = request.POST.get('type_of_company', '').strip()
        gst_no = request.POST.get('gst_no', '').strip()
        if not company_name:
            messages.error(request, "Company name is required.")
            return render(request, 'crm/client_form.html', {
                'company_name': company_name, 'type_of_company': type_of_company, 'gst_no': gst_no
            })
        Client.objects.create(company_name=company_name, type_of_company=type_of_company, gst_no=gst_no)
        messages.success(request, "Client added successfully.")
        return redirect('client')
    return render(request, 'crm/client_form.html')

@csrf_exempt
def client_entry_ajax(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        type_of_company = request.POST.get('type_of_company')
        gst_no = request.POST.get('gst_no')
        client = Client.objects.create(company_name=company_name, type_of_company=type_of_company, gst_no=gst_no)
        return JsonResponse({'success': True, 'client': {'company_name': client.company_name}})
    return JsonResponse({'success': False})

@login_required
def lead_list(request):
    search_query = request.GET.get('q', '')
    leads = Lead.objects.all().order_by('-id')
    if search_query:
        leads = leads.filter(company_name__company_name__icontains=search_query)
    for lead in leads:
        latest_estimation = Estimation.objects.filter(lead_no=lead).order_by('-id').first()
        if latest_estimation:
            if latest_estimation.status in ['Invoiced', 'Approved']:
                lead.computed_status = 'Won'
            elif latest_estimation.status == 'Pending':
                lead.computed_status = 'Quoted'
            elif latest_estimation.status == 'Lost':
                lead.computed_status = 'Lost'
            else:
                lead.computed_status = 'Pending'
        else:
            lead.computed_status = 'Pending'
        lead.save(update_fields=['computed_status'])
    paginator = Paginator(leads, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'lead.html', {'leads': page_obj, 'page_obj': page_obj, 'clients': Client.objects.all(), 'query': search_query})

@login_required
@csrf_exempt
def lead_create(request):
    clients = Client.objects.all()
    if request.method == "POST":
        try:
            client_id = request.POST.get("company_name")
            contact_person = request.POST.get("contact_person", "").strip()
            email = request.POST.get("email", "").strip()
            mobile = request.POST.get("mobile", "").strip()
            requirement = request.POST.get("requirement", "").strip()
            company = get_object_or_404(Client, id=client_id)
            Lead.objects.create(
                company_name=company, contact_person=contact_person, email=email, mobile=mobile,
                requirement=requirement, status="Pending", date=now().date(),
            )
            messages.success(request, "Lead created successfully.")
            return redirect("lead_list")
        except Exception as e:
            messages.error(request, f"Error creating lead: {e}")
    return render(request, "leads/lead_create.html", {"clients": clients})

@login_required
def lead_edit(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if lead.status == "Won" and request.method == "POST":
        return HttpResponseForbidden("Cannot edit a lead with status 'Won'.")
    if request.method == "POST":
        lead.contact_person = request.POST.get("contact_person")
        lead.email = request.POST.get("email")
        lead.mobile = request.POST.get("mobile")
        lead.requirement = request.POST.get("requirement")
        lead.save()
        return redirect('lead_list')
    return render(request, 'edit_lead.html', {'lead': lead})

def get_pending_lead(request):
    client_id = request.GET.get('client_id')
    lead = Lead.objects.filter(company_name_id=client_id, status="Pending").order_by('-date').first()
    if lead:
        return JsonResponse({'lead_no': lead.lead_no})
    return JsonResponse({'lead_no': ''})

def get_pending_leads(request):
    client_id = request.GET.get('client_id')
    leads = Lead.objects.filter(company_name_id=client_id, status='Pending')
    return JsonResponse({'leads': [{'id': lead.id, 'lead_no': lead.lead_no} for lead in leads]})

def get_gst_no(request):
    client_id = request.GET.get('client_id')
    try:
        client = Client.objects.get(id=client_id)
        return JsonResponse({'gst_no': client.gst_no})
    except Client.DoesNotExist:
        return JsonResponse({'gst_no': ''})

from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import F
from django.utils.timezone import now
from django.shortcuts import render, redirect, get_object_or_404

from decimal import Decimal, InvalidOperation
import re

from .models import (
    Client, Lead, Estimation, EstimationItem,
    TermsAndConditions, GSTSettings, EstimationSettings
)

# Plain-text defaults (one item per line, no bullets here)
DEFAULT_TERMS = """This is a system generated Quotation. Hence, signature is not needed.
Payment Terms: 100% Advance Payment or As Per Agreed Terms
Service Warranty 30 to 90 Days Depending upon the Availed Service
All Products and Accessories Carries Standard OEM Warranty"""

def safe_decimal(value, default='0.00'):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)

_BULLET_PREFIX = re.compile(r'^\s*[-•]\s*')  # strip leading '-' or '•'

def _split_lines(text: str):
    """
    Split on newlines, strip whitespace, drop empties, and remove leading bullets.
    """
    lines = []
    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        ln = _BULLET_PREFIX.sub("", raw.strip())
        if ln:
            lines.append(ln)
    return lines

def merge_terms_to_html(default_terms_text: str, user_terms_text: str) -> str:
    """
    Merge default and user-entered terms into a single HTML <ul> list, de-duplicated,
    left-aligned with consistent indentation and tight line spacing.
    The resulting HTML is safe to render with |safe in templates and PDFs.
    """
    base = _split_lines(default_terms_text)
    extra = _split_lines(user_terms_text)

    seen = set()
    merged = []
    for ln in base + extra:
        key = ln.lower()
        if key not in seen:
            seen.add(key)
            merged.append(ln)

    # Tailwind-friendly and PDF-safe left alignment + spacing
    # If you do not use Tailwind, these inline styles still align correctly.
    return (
        '<ul class="list-disc ml-5 leading-snug text-left" '
        'style="list-style:disc; margin:0 0 0 1.25rem; padding:0; line-height:1.35; text-align:left;">'
        + "".join(f"<li style='margin:0.2rem 0;'>{ln}</li>" for ln in merged)
        + "</ul>"
    )

@transaction.atomic
def generate_and_reserve_quote_no():
    """
    Atomically generate and reserve the next quote number.
    """
    setting = (
        EstimationSettings.objects.select_for_update().first()
        or EstimationSettings.objects.create(prefix="EST", next_number=1)
    )
    while True:
        quote_no = f"{setting.prefix}-{setting.next_number:04d}"
        if not Estimation.objects.filter(quote_no=quote_no).exists():
            setting.next_number = F('next_number') + 1
            setting.save(update_fields=['next_number'])
            setting.refresh_from_db(fields=['next_number'])
            return quote_no
        setting.next_number = F('next_number') + 1
        setting.save(update_fields=['next_number'])
        setting.refresh_from_db(fields=['next_number'])

def create_quotation(request):
    clients = Client.objects.all().order_by('company_name')
    pending_leads = Lead.objects.filter(status='Pending').order_by('-id')

    gst_setting = GSTSettings.objects.order_by('-id').first()
    gst_percentage = float(getattr(gst_setting, 'gst_percentage', 18.0))

    # Prefer DB terms; fallback to DEFAULT_TERMS literal (plain text)
    terms_obj = TermsAndConditions.objects.order_by('-id').first()
    default_terms_text = (terms_obj.content.strip() if terms_obj and terms_obj.content else DEFAULT_TERMS)

    if request.method == 'POST':
        company_id = request.POST.get('company_name')
        lead_id = request.POST.get('lead_no') or None

        try:
            with transaction.atomic():
                quote_no = generate_and_reserve_quote_no()
                quote_date = now().date()

                client = get_object_or_404(Client, id=company_id)
                lead_instance = Lead.objects.filter(id=lead_id).first() if lead_id else None

                # Merge default and user-entered lines into HTML list
                user_terms_text = request.POST.get('terms_conditions') or ""
                final_terms_html = merge_terms_to_html(default_terms_text, user_terms_text)

                estimation = Estimation.objects.create(
                    quote_no=quote_no,
                    quote_date=quote_date,
                    company_name=client,
                    lead_no=lead_instance,
                    validity_days=int(request.POST.get('validity_days') or 0),
                    gst_no=(request.POST.get('gst_no') or "").strip(),
                    billing_address=(request.POST.get('billing_address') or "").strip(),
                    shipping_address=(request.POST.get('shipping_address') or "").strip(),
                    terms_conditions=final_terms_html,  # Store aligned HTML list
                    bank_details=(request.POST.get('bank_details') or "").strip(),
                    sub_total=safe_decimal(request.POST.get('sub_total')),
                    discount=safe_decimal(request.POST.get('discount')),
                    gst_amount=safe_decimal(request.POST.get('gst_amount')),
                    total=safe_decimal(request.POST.get('total')),
                    status='Pending',
                )

                items = zip(
                    request.POST.getlist('item_details[]'),
                    request.POST.getlist('hsn_sac[]'),
                    request.POST.getlist('quantity[]'),
                    request.POST.getlist('rate[]'),
                    request.POST.getlist('tax[]'),
                    request.POST.getlist('amount[]'),
                )

                for detail, hsn, qty, rate, tax, amt in items:
                    detail_clean = (detail or "").strip()
                    if not detail_clean:
                        continue
                    EstimationItem.objects.create(
                        estimation=estimation,
                        item_details=detail_clean,
                        hsn_sac=((hsn or "").strip() or None),
                        quantity=int(qty or 0),
                        rate=safe_decimal(rate),
                        tax=safe_decimal(tax),
                        amount=safe_decimal(amt),
                    )

                # Optional: update derived lead status
                if lead_instance:
                    lead_instance.computed_status = 'Quoted'
                    lead_instance.save(update_fields=['computed_status'])

            return redirect('estimation_list')

        except Exception as e:
            return render(request, 'create_quotation.html', {
                'clients': clients,
                'pending_leads': pending_leads,
                'gst_percentage': gst_percentage,
                'terms': default_terms_text,  # keep default visible
                'error': f"Something went wrong: {e}",
            })

    # GET
    return render(request, 'create_quotation.html', {
        'clients': clients,
        'pending_leads': pending_leads,
        'gst_percentage': gst_percentage,
        'terms': default_terms_text,
    })


def quotation_pdf(request, pk):
    quotation = get_object_or_404(Estimation, pk=pk)
    terms_obj = TermsAndConditions.objects.last()
    terms = terms_obj.content if terms_obj else (quotation.terms_conditions or "")
    try:
        items = quotation.items.all()
    except Exception:
        items = EstimationItem.objects.filter(estimation=quotation)
    return render(request, "quotation_pdf.html", {'quotation': quotation, 'items': items, 'terms': terms})

from django.views import View
from weasyprint import HTML

class QuotationPDFView(View):
    def get(self, request, pk):
        estimation = get_object_or_404(Estimation, pk=pk)
        items = [
            {
                'item_details': item.item_details, 'hsn_sac': item.hsn_sac or "",
                'quantity': item.quantity, 'rate': item.rate, 'tax': item.tax, 'amount': item.amount
            } for item in estimation.items.all()
        ]
        company_gst_state = (estimation.gst_no or "").strip()[:2]
        our_gst_state = "29"
        same_state = company_gst_state == our_gst_state
        gst_rate = 18
        if same_state:
            cgst = sgst = estimation.gst_amount / 2
            igst = 0
            cgst_rate = sgst_rate = gst_rate / 2
            igst_rate = 0
        else:
            cgst = sgst = 0
            igst = estimation.gst_amount
            igst_rate = gst_rate
            cgst_rate = sgst_rate = 0
        terms_obj = TermsAndConditions.objects.order_by('-id').first()
        terms_content = terms_obj.content if terms_obj else (estimation.terms_conditions or "")
        expiry_date = estimation.quote_date + timedelta(days=estimation.validity_days or 0)
        amount_in_words = inr_currency_words(estimation.total)
        logo_path = Path(settings.STATIC_ROOT) / "images/logo.png"
        logo_uri = logo_path.as_uri()
        html_string = render_to_string('quotation_pdf_template.html', {
            'estimation': estimation, 'items': items, 'amount_in_words': amount_in_words,
            'logo_uri': logo_uri, 'expiry_date': expiry_date, 'same_state': same_state,
            'cgst': cgst, 'sgst': sgst, 'igst': igst, 'cgst_rate': cgst_rate,
            'sgst_rate': sgst_rate, 'igst_rate': igst_rate, 'terms': terms_content,
        })
        pdf = HTML(string=html_string, base_url=settings.STATIC_ROOT.as_uri()).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=Quotation_{estimation.quote_no}.pdf'
        return response

def estimation_view(request):
    sort = request.GET.get('sort', 'quote_date')
    estimations = Estimation.objects.all().order_by('company_name' if sort == 'company' else '-quote_date')
    query = request.GET.get('q')
    if query:
        estimations = estimations.filter(quote_no__icontains=query)
    return render(request, 'estimation.html', {'estimations': estimations, 'query': query, 'current_sort': sort})

import logging
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import localdate
from django.core.paginator import Paginator

from .models import Estimation, EstimationItem, Client, Lead, TermsAndConditions
from .forms import EstimationForm

logger = logging.getLogger(__name__)

def _d(val, default='0.00'):
    try:
        return Decimal(val or default)
    except Exception:
        return Decimal(default)

def edit_estimation(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    clients = Client.objects.all()
    items = EstimationItem.objects.filter(estimation=estimation).order_by('id')

    terms_obj = TermsAndConditions.objects.order_by('-id').first()
    default_terms = terms_obj.content if terms_obj else (estimation.terms_conditions or "")

    # Load leads for the current company
    all_leads = Lead.objects.filter(company_name=estimation.company_name)

    form = EstimationForm(request.POST or None, instance=estimation)

    if request.method == 'POST':
        try:
            if not form.is_valid():
                return render(request, 'edit_estimation.html', {
                    'form': form,
                    'estimation': estimation,
                    'clients': clients,
                    'items': items,
                    'terms': default_terms,
                    'all_leads': all_leads,
                    'error': "Please fix the highlighted errors.",
                })

            with transaction.atomic():
                updated = form.save(commit=False)

                # Company and Lead (allow change if provided)
                company_id = request.POST.get('company_name') or estimation.company_name_id
                updated.company_name_id = company_id

                updated.lead_no_id = request.POST.get('lead_no') or None

                # Numeric fields
                updated.sub_total = _d(request.POST.get('sub_total'))
                updated.discount = _d(request.POST.get('discount'))
                updated.gst_amount = _d(request.POST.get('gst_amount'))
                updated.total = _d(request.POST.get('total'))

                # Dates/text
                updated.quote_date = request.POST.get('quote_date') or updated.quote_date
                updated.validity_days = request.POST.get('validity_days') or updated.validity_days
                updated.terms_conditions = request.POST.get('terms_conditions', updated.terms_conditions or "")

                updated.save()

                # Replace items with submitted rows
                EstimationItem.objects.filter(estimation=updated).delete()

                details = request.POST.getlist('item_details[]')
                hsns = request.POST.getlist('hsn_sac[]')
                qtys = request.POST.getlist('quantity[]')
                rates = request.POST.getlist('rate[]')
                taxes = request.POST.getlist('tax[]')
                amts = request.POST.getlist('amount[]')

                for detail, hsn, qty, rate, tax, amt in zip(details, hsns, qtys, rates, taxes, amts):
                    if str(detail).strip():
                        EstimationItem.objects.create(
                            estimation=updated,
                            item_details=str(detail).strip(),
                            hsn_sac=(hsn or "").strip() or None,
                            quantity=int(qty or 0),
                            rate=_d(rate),
                            tax=_d(tax),
                            amount=_d(amt),
                        )

                return redirect('estimation_list')

        except Exception as e:
            logger.exception("Error saving estimation %s", estimation.pk)
            form.add_error(None, f"Error saving quotation: {e}")

    return render(request, 'edit_estimation.html', {
        'form': form,
        'estimation': estimation,
        'clients': clients,
        'items': items,
        'terms': default_terms,
        'all_leads': all_leads,
    })


def estimation_list(request):
    today = localdate()
    follow_up_filter = request.GET.get("follow_up", "")
    if follow_up_filter == "today":
        estimations = Estimation.objects.filter(follow_up_date=today).order_by('-id')
    else:
        estimations = Estimation.objects.all().order_by('-id')

    paginator = Paginator(estimations, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "estimation_list.html", {
        "page_obj": page_obj,
        "follow_up": follow_up_filter,
        "today": today
    })


def estimation_list(request):
    today = localdate()
    follow_up_filter = request.GET.get("follow_up", "")
    if follow_up_filter == "today":
        estimations = Estimation.objects.filter(follow_up_date=today).order_by('-id')
    else:
        estimations = Estimation.objects.all().order_by('-id')
    paginator = Paginator(estimations, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "estimation_list.html", {
        "page_obj": page_obj,
        "follow_up": follow_up_filter,
        "today": today
    })

def approve_estimation(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    if request.method == 'POST':
        estimation.status = 'Approved'
        estimation.credit_days = request.POST.get('credit_days')
        estimation.remarks = request.POST.get('remarks')
        estimation.po_number = request.POST.get('po_number')
        estimation.po_date = request.POST.get('po_date') or None
        estimation.po_received_date = request.POST.get('po_received_date') or None
        if 'po_attachment' in request.FILES:
            estimation.po_attachment = request.FILES['po_attachment']
        estimation.save()
        return redirect('invoice_approval_list')
    form = ApprovalForm(instance=estimation)
    return render(request, 'crm/approve_estimation.html', {'estimation': estimation, 'form': form})

@require_POST
def reject_estimation(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    estimation.status = "Rejected"
    estimation.remarks = request.POST.get("reason", "")
    estimation.save()
    return redirect("estimation")

def invoice_approval_table(request):
    estimations = Estimation.objects.filter(status='Approved', invoice__isnull=True)
    invoices = Invoice.objects.all().order_by('-created_at')
    return render(request, 'invoice_approval_list.html', {'estimations': estimations, 'invoices': invoices})

@require_POST
def reject_invoice(request, pk):
    try:
        invoice = Invoice.objects.get(pk=pk)
        estimation = invoice.estimation
        invoice.delete()
    except Invoice.DoesNotExist:
        estimation = get_object_or_404(Estimation, pk=pk)
    estimation.status = 'Rejected'
    estimation.remarks = request.POST.get('reason', '')
    estimation.save()
    return redirect('invoice_approval_list')

@csrf_exempt
def mark_as_lost(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    if request.method == "POST":
        reason = request.POST.get("reason", "")
        estimation.status = "Lost"
        estimation.lost_reason = reason
        estimation.save()
        return JsonResponse({"status": "success"})
    if estimation.status == "Lost":
        return JsonResponse({"reason": estimation.lost_reason})
    return JsonResponse({"status": "need_reason"})

@require_http_methods(["POST"])
def mark_lost(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    reason = request.POST.get('reason', '').strip()
    if reason:
        estimation.status = "Lost"
        estimation.lost_reason = reason
        estimation.save()
    return redirect('estimation_list')

def create_invoice(request):
    return render(request, 'create_invoice.html')

def update_estimation_status(request, pk, new_status):
    estimation = get_object_or_404(Estimation, pk=pk)
    if new_status == "rejected" and request.method == "POST":
        estimation.status = "Rejected"
        estimation.remarks = request.POST.get("reason", "")
    else:
        estimation.status = new_status
    estimation.save()
    return redirect("invoice_approval_list")

def generate_invoice_number():
    last = Invoice.objects.order_by('-id').first()
    number = int(last.invoice_no.split('-')[-1]) + 1 if last else 1
    return f"INV-{number:04d}"

def invoice_detail_view(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    items = EstimationItem.objects.filter(estimation=estimation)
    invoice = Invoice.objects.filter(estimation=estimation).first()
    return render(request, 'crm/invoice_detail.html', {
        'estimation': estimation, 'items': items, 'invoice': invoice, 'amount_in_words': inr_currency_words(estimation.total),
    })

from django.utils.timezone import now
from datetime import timedelta

@require_POST
def approve_invoice(request, est_id):
    estimation = get_object_or_404(Estimation, id=est_id)
    if Invoice.objects.filter(estimation=estimation).exists():
        return redirect('invoice_list')

    estimation.status = 'Approved'
    estimation.save()

    credit_days = estimation.credit_days or 0
    # due date will be computed by Invoice.due_date property from created_at + credit_days
    Invoice.objects.create(
        estimation=estimation,
        invoice_no=generate_invoice_number(),
        created_at=now(),
        total_value=estimation.total,
        balance_due=estimation.total,
        credit_days=credit_days,
        remarks=estimation.remarks,
        is_approved=True,
        status='Pending',
    )

    estimation.status = 'Invoiced'
    estimation.save()
    return redirect('invoice_list')


@require_POST
def generate_invoice_from_estimation(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    if not Invoice.objects.filter(estimation=estimation).exists():
        Invoice.objects.create(estimation=estimation, invoice_no=generate_invoice_number(), is_approved=False)
    return redirect('invoice_approval_list')

def estimation_detail_view(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    items = estimation.items.all()
    total = sum((item.amount for item in items), Decimal('0.00'))
    return render(request, 'crm/estimation_detail_view.html', {'estimation': estimation, 'items': items, 'total': total})

@csrf_exempt
def mark_under_review(request, id):
    if request.method == 'POST':
        estimation = Estimation.objects.get(id=id)
        estimation.status = 'Under Review'
        estimation.follow_up_date = request.POST.get('follow_up_date')
        estimation.follow_up_remarks = request.POST.get('follow_up_remarks')
        estimation.save()
        return redirect('estimation_list')

def invoices_view(request):
    estimations_without_invoice = Estimation.objects.filter(generated_invoice__isnull=True)
    return render(request, 'invoices.html', {'estimations_without_invoice': estimations_without_invoice})

def invoice_pdf_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    estimation = invoice.estimation
    items = EstimationItem.objects.filter(estimation=estimation)
    due_date = invoice.created_at + timedelta(days=invoice.credit_days or 0)
    total = estimation.total
    rupees = int(total)
    paise = int(round((total - rupees) * 100))
    from num2words import num2words
    amount_in_words = f"Rupees {num2words(rupees, lang='en_IN').title()}"
    if paise > 0:
        amount_in_words += f" and {num2words(paise, lang='en_IN').title()} Paise"
    amount_in_words += " Only"
    company_gst_state_code = estimation.gst_no[:2] if estimation.gst_no else ''
    our_gst_state_code = "29"
    same_state = (company_gst_state_code == our_gst_state_code)
    if same_state:
        sgst = cgst = estimation.gst_amount / 2
        igst = 0
    else:
        sgst = cgst = 0
        igst = estimation.gst_amount
    logo_path = Path(settings.STATIC_ROOT) / "images/logo.png"
    logo_uri = logo_path.as_uri()
    html_string = render_to_string("invoice_pdf_weasy.html", {
        'invoice': invoice, 'estimation': estimation, 'items': items, 'due_date': due_date,
        'amount_in_words': amount_in_words, 'same_state': same_state,
        'sgst': sgst, 'cgst': cgst, 'igst': igst, 'logo_uri': logo_uri,
    })
    from weasyprint import HTML
    pdf_file = HTML(string=html_string, base_url=settings.STATIC_ROOT.as_uri()).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="{invoice.invoice_no}.pdf"'
    return response

@require_POST
def update_payment_status(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    new_status = request.POST.get("payment_status")
    if new_status in dict(Invoice.PAYMENT_STATUS_CHOICES):
        invoice.payment_status = new_status
        invoice.save()
    return redirect('invoice_approval_table')

@require_POST
def confirm_payment_post(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    try:
        amount_paid = Decimal(request.POST.get('amount_paid', 0))
        utr_number = request.POST.get('utr_number')
        payment_date = request.POST.get('payment_date')
        PaymentLog.objects.create(invoice=invoice, amount_paid=amount_paid, utr_number=utr_number, payment_date=payment_date)
        invoice.balance_due -= amount_paid
        if invoice.balance_due <= 0:
            invoice.status = "Paid"
            invoice.balance_due = Decimal('0.00')
        else:
            invoice.status = "Partial Paid"
        invoice.save()
    except Exception as e:
        return HttpResponse(f"Something went wrong: {e}")
    return redirect('invoice_list')

def get_payment_logs(request, invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    logs = invoice.logs.all().order_by('-payment_date')
    logs_data = [
        {"amount_paid": str(log.amount_paid), "utr_number": log.utr_number, "payment_date": log.payment_date.strftime('%Y-%m-%d')}
        for log in logs
    ]
    return JsonResponse({"logs": logs_data})

def view_payment_logs(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    logs = PaymentLog.objects.filter(invoice=invoice).order_by('-payment_date')
    return render(request, 'payment_logs.html', {'invoice': invoice, 'logs': logs})

def invoice_list_view(request):
    estimations = Estimation.objects.filter(status='Approved')
    invoices = Invoice.objects.all().order_by('-created_at')
    return render(request, 'invoice_approval_list.html', {'estimations': estimations, 'invoices': invoices})

def invoice_logs_api(request, invoice_id):
    logs = PaymentLog.objects.filter(invoice_id=invoice_id).order_by('-payment_date')
    data = [{
        'amount_paid': str(log.amount_paid),
        'payment_date': log.payment_date.strftime('%d-%m-%Y'),
        'utr_number': log.utr_number
    } for log in logs]
    return JsonResponse(data, safe=False)

@login_required
def purchase_order_view(request):
    return render(request, 'purchase_order.html')

@login_required
def vendor_view(request):
    return render(request, 'vendor.html')

@login_required
def bill_view(request):
    return render(request, 'bill.html')

@login_required
def profile_view(request):
    return render(request, 'profile.html')

@login_required
def report_list(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    leads = Lead.objects.all()
    if from_date and to_date:
        leads = leads.filter(date__range=[from_date, to_date])
    else:
        leads = leads.order_by('-date')
    report_data = []
    for lead in leads:
        estimation = Estimation.objects.filter(lead_no=lead).first()
        invoice = Invoice.objects.filter(estimation__lead_no=lead).first()
        report_data.append({
            'lead_no': lead.lead_no,
            'lead_date': lead.date.strftime('%d-%m-%Y') if lead.date else '',
            'client': lead.company_name.company_name if lead.company_name else '',
            'requirement': lead.requirement,
            'estimation_no': estimation.quote_no if estimation else '',
            'estimation_status': estimation.status if estimation else '',
            'lost_reason': estimation.lost_reason if estimation else '',
            'po_number': estimation.po_number if estimation else '',
            'po_date': estimation.po_date.strftime('%d-%m-%Y') if estimation and estimation.po_date else '',
            'po_attachment': estimation.po_attachment.url if estimation and estimation.po_attachment else '',
            'invoice_no': invoice.invoice_no if invoice else '',
            'invoice_amount': invoice.total_value if invoice else '',
            'payment_status': invoice.status if invoice else '',
        })
    paginator = Paginator(report_data, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'crm/report_list.html', {'report_data': page_obj, 'page_obj': page_obj})

def export_report_excel(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    leads = Lead.objects.all()
    if from_date and to_date:
        leads = leads.filter(date__range=[from_date, to_date])
    data = []
    for lead in leads:
        estimation = Estimation.objects.filter(lead_no=lead.lead_no).first()
        invoice = Invoice.objects.filter(estimation__lead_no=lead.lead_no).first()
        data.append({
            "Lead No": lead.lead_no,
            "Lead Date": lead.date.strftime('%d-%m-%Y') if lead.date else '',
            "Client": lead.company_name.company_name,
            "Requirement": lead.requirement,
            "Estimation No": estimation.quote_no if estimation else '',
            "Estimation Status": estimation.status if estimation else 'Pending',
            "Lost Reason": estimation.lost_reason if estimation else '',
            "Client PO Number": estimation.po_number if estimation else '',
            "PO Date": estimation.po_date.strftime("%d-%m-%Y") if estimation and estimation.po_date else '',
            "Invoice No": invoice.invoice_no if invoice else '',
            "Amount": float(invoice.total_value) if invoice else '',
            "Paid": float(invoice.total_value) - float(invoice.balance_due) if invoice else '',
            "Balance": float(invoice.balance_due) if invoice else '',
            "Payment Status": invoice.status if invoice else '',
        })
    import pandas as pd
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=CRM_Complete_Report.xlsx'
    df.to_excel(response, index=False)
    return response

def export_report_pdf(request):
    invoices = get_filtered_invoices(request)
    html_string = render_to_string('report_pdf_template.html', {'invoices': invoices})
    from weasyprint import HTML
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Filtered_CRM_Report.pdf"'
    return response

def get_filtered_invoices(request):
    invoices = Invoice.objects.select_related('estimation', 'estimation__company_name').all()


    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    company = request.GET.get('company')
    lead_no = request.GET.get('lead_no')

    if from_date and to_date:
        invoices = invoices.filter(created_at__date__range=[from_date, to_date])
    elif from_date:
        invoices = invoices.filter(created_at__date__gte=from_date)
    elif to_date:
        invoices = invoices.filter(created_at__date__lte=to_date)

    if company:
        invoices = invoices.filter(estimation__company_name__id=company)
    if lead_no:
        invoices = invoices.filter(estimation__lead_no=lead_no)

    return invoices
