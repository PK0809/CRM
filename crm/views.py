from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from django.db import IntegrityError
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .models import UserProfile
from .forms import UserForm

User = get_user_model()


# ---------- LOGIN ----------
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


# ---------- CREATE USER ----------
@login_required
def create_user(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        role = request.POST.get('role', 'User')
        phone_number = request.POST.get('phone_number', '').strip()
        selected_permissions = request.POST.getlist('permissions')  # ['app_label.codename', ...]

        # --- Validation ---
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
            # --- Create User ---
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            user.is_staff = True
            user.is_superuser = (role == 'Admin')
            user.role = role
            user.save()

            # --- Create Profile ---
            user_profile = UserProfile.objects.create(
                user=user,
                name=username,
                email=email,
                phone_number=phone_number,
                role=role
            )

            # --- Assign Permissions ---
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

    # GET request
    permissions = Permission.objects.filter(content_type__app_label='crm').order_by('name')
    return render(request, 'users/add_user.html', {'permissions': permissions})


# ---------- USER LIST ----------
@login_required
def user_list(request):
    users = UserProfile.objects.select_related('user').all()
    return render(request, "users/user_list.html", {'users': users})


# ---------- EDIT USER ----------
@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    # Filter permissions
    if user.role == 'Admin':
        permissions = Permission.objects.all()
    else:
        permissions = Permission.objects.exclude(
            codename__in=['admin_access', 'purchase_access']
        )

    if request.method == 'POST':
        selected_permissions = request.POST.getlist('permissions')  # ['app_label.codename', ...]
        perms_to_set = []
        for perm_str in selected_permissions:
            try:
                app_label, codename = perm_str.split('.')
                perm = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                perms_to_set.append(perm)
            except Permission.DoesNotExist:
                messages.warning(request, f"Permission '{perm_str}' not found.")

        user.user_permissions.set(perms_to_set)
        # Update profile permissions too
        if hasattr(user, 'userprofile'):
            user.userprofile.permissions.set(perms_to_set)

        user.save()
        messages.success(request, 'User updated successfully.')
        return redirect('user_list')

    return render(request, 'users/edit_user.html', {
        'user_obj': user,
        'permissions': permissions
    })


# ---------- DELETE USER ----------
@login_required
def delete_user(request, user_id):
    user_profile = get_object_or_404(UserProfile, id=user_id)
    user_profile.user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('user_list')


# ---------- GET PERMISSIONS BY ROLE ----------
@login_required
def get_permissions_by_role(request):
    role = request.GET.get('role')

    if role == 'Admin':
        permissions = Permission.objects.all()
    elif role == 'User':
        permissions = Permission.objects.filter(
            codename__in=[
                'view_client', 'view_lead', 'view_estimation', 'view_invoice', 'view_report'
            ]
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

from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from .forms import UserForm

User = get_user_model()

class UserUpdateView(UpdateView):
    model = User
    form_class = UserForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('user_list')

from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.db.models import Sum, Q
from .models import Invoice, PaymentLog
from django.shortcuts import render
from crm.models import Client, Invoice, Lead, Estimation, UserPermission, PaymentLog


@login_required
def dashboard(request):
    user = request.user

    # --- Permissions (supports multiple) ---
    user_perms = UserPermission.objects.filter(userprofile__user=user)
    user_perm_names = set(user_perms.values_list("name", flat=True))

    context = {
        "can_view_client": "can_view_client" in user_perm_names,
        "can_view_lead": "can_view_lead" in user_perm_names,
        "can_view_estimation": "can_view_estimation" in user_perm_names,
        "can_view_invoice": "can_view_invoice" in user_perm_names,
        "can_view_reports": "can_view_reports" in user_perm_names,
    }

    context["grouped_modules"] = {
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
    }

    # --- Financials ---
    total_invoiced = Invoice.objects.aggregate(total=Sum('total_value'))['total'] or 0

    # ✅ Paid = Paid + Partial Paid together
    total_paid = PaymentLog.objects.filter(
        Q(status="Paid") | Q(status="Partial Paid")
    ).aggregate(total=Sum("amount_paid"))["total"] or 0

    total_balance_due = Invoice.objects.aggregate(total=Sum("balance_due"))["total"] or 0

    # --- Stats ---
    total_leads = Lead.objects.count()
    total_quotations = Estimation.objects.count()
    total_invoices = Invoice.objects.count()
    conversion_rate = (
        round((total_invoices / total_leads) * 100, 2) if total_leads > 0 else 0
    )

    # --- Quotation Status Chart ---
    quotation_status = (
        Estimation.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    # Invoice status counts
    invoice_status = (
        Invoice.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    # --- Top Clients ---
    top_clients = (
        Client.objects.annotate(total_leads=Count("lead"))
        .order_by("-total_leads")[:4]
    )

    # --- Filters ---
    filter_options = [
        ("This Month", "this_month"),
        ("This Quarter", "this_quarter"),
        ("This Year", "this_year"),
        ("Previous Month", "previous_month"),
        ("Previous Quarter", "previous_quarter"),
        ("Previous Year", "previous_year"),
        ("Custom", "custom"),
    ]
    selected_filter = request.GET.get("date_filter", "this_month")

    # --- Add to context ---
    context.update(
        {
            "filter_options": filter_options,
            "selected_filter": selected_filter,
            "user_name": user.first_name or user.username,
            "total_invoiced": total_invoiced,
            "paid": total_paid,  # ✅ Paid + Partial Paid combined
            "balance_due": total_balance_due,
            "total_leads": total_leads,
            "total_quotations": total_quotations,
            "total_invoices": total_invoices,
            "conversion_rate": conversion_rate,
            "quotation_status": quotation_status,
            "invoice_status": invoice_status,
            "top_clients": top_clients,
        }
    )

    return render(request, "dashboard.html", context)



@login_required
def confirm_payment(request, payment_id):
    payment = get_object_or_404(PaymentLog, id=payment_id)
    invoice = payment.invoice

    # ✅ Always include Paid + Partial Paid when calculating invoice totals
    total_paid = (
        PaymentLog.objects.filter(
            invoice=invoice, status__in=["Paid", "Partial Paid"]
        ).aggregate(total=Sum("amount_paid"))["total"]
        or 0
    )

    # --- Update invoice status ---
    if total_paid >= invoice.total_value:
        invoice.status = "Paid"
    elif total_paid > 0:
        invoice.status = "Partial Paid"
    else:
        invoice.status = "Unpaid"

    invoice.paid_amount = total_paid
    invoice.balance_due = invoice.total_value - total_paid
    invoice.save()

    # --- Sync payment log with invoice status ---
    payment.status = invoice.status
    payment.save()

    return redirect("payment_list")





# --- CLIENT VIEWS ---
@login_required
def client_list(request):
    clients = Client.objects.all()
    return render(request, 'create_quotation.html', {'clients': clients})


from django.core.paginator import Paginator

@login_required
def client_list(request):
    query = request.GET.get('q', '')
    clients = Client.objects.all()

    if query:
        clients = clients.filter(
            company_name__icontains=query
        )

    paginator = Paginator(clients, 10)  # Show 8 clients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'client.html', {
        'clients': page_obj,
        'query': query,
        'page_obj': page_obj
    })


from django.shortcuts import render, get_object_or_404, redirect
from .models import Client

def edit_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    if request.method == 'POST':
        client.company_name = request.POST.get('company_name')
        client.type_of_company = request.POST.get('type_of_company')
        client.gst_no = request.POST.get('gst_no')
        client.save()
        return redirect('client')  # or whatever name you gave the client list view

    return render(request, 'edit_client.html', {'client': client})



# --- OTHER MODULE PLACEHOLDER VIEWS ---
@login_required
def lead_list(request):
    return render(request, 'lead.html')

@login_required
def estimation_list(request):
    estimations = Estimation.objects.all().order_by('-quote_date', '-id')
    return render(request, 'estimation_list.html', {'estimations': estimations})

@login_required
def invoice_view(request):
    return render(request, 'invoice.html')

@login_required
def vendor_view(request):
    return render(request, 'vendor.html')

@login_required
def purchase_order_view(request):
    return render(request, 'purchase_order.html')

@login_required
def bill_view(request):
    return render(request, 'bill.html')

@login_required
def profile_view(request):
    return render(request, 'profile.html')

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect

@login_required
@csrf_exempt
def client_entry(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        type_of_company = request.POST.get('type_of_company')
        gst_no = request.POST.get('gst_no')

        Client.objects.create(
            company_name=company_name,
            type_of_company=type_of_company,
            gst_no=gst_no
        )
        return redirect('client')

from django.shortcuts import render

def client_view(request):
    return render(request, 'crm/client_form.html')  # Adjust template name as needed


    
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Lead
from .forms import LeadForm
from . import models
from django.db.models import Sum


def generate_lead_no():
    last_lead = Lead.objects.order_by('id').last()
    if last_lead and last_lead.lead_no:
        number = int(last_lead.lead_no.split('-')[-1]) + 1
    else:
        number = 1
    return f"LEAD-{number:04d}"



from django.shortcuts import redirect
from .models import Lead, Client

def lead_create(request):
    if request.method == 'POST':
        company_id = request.POST.get('company_name')
        contact_person = request.POST.get('contact_person')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        address = request.POST.get('address')
        requirement = request.POST.get('requirement')
        status = request.POST.get('status', 'Pending')

        try:
            client = Client.objects.get(id=company_id)
        except Client.DoesNotExist:
            return redirect('lead_list')

        Lead.objects.create(
            company_name=client,
            contact_person=contact_person,
            email=email,
            mobile=mobile,
            address=address,
            requirement=requirement,
        )

        return redirect('lead_list')  # make sure URL name is correct

    return redirect('lead_list')

from django.shortcuts import render

from django.shortcuts import render, redirect
from .forms import ClientForm   # assuming you already have a form for Client
from .models import Client

def add_client(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("client_list")  # update with your correct URL name
    else:
        form = ClientForm()
    return render(request, "crm/client_form.html", {"form": form})


def lead_view(request):
    return render(request, 'leads/lead_view.html')

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from .models import Lead, Estimation, Client

@login_required
def lead_edit(request, pk):
    lead = get_object_or_404(Lead, pk=pk)

    if lead.status == "Won" and request.method == "POST":
        return HttpResponseForbidden("Cannot edit a lead with status 'Won'.")

    if request.method == "POST":
        # Do NOT update company_name — it's read-only and a ForeignKey
        lead.contact_person = request.POST.get("contact_person")
        lead.email = request.POST.get("email")
        lead.mobile = request.POST.get("mobile")
        lead.requirement = request.POST.get("requirement")
        lead.save()
        return redirect('lead_list')  # Ensure this matches your urls.py name

    return render(request, 'edit_lead.html', {'lead': lead})


from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Lead, Estimation, Client

def lead_list(request):
    search_query = request.GET.get('q', '')
    leads = Lead.objects.all().order_by('-id')

    if search_query:
        leads = leads.filter(company_name__company_name__icontains=search_query)

    # Recalculate computed_status for all leads
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
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'leads': page_obj,
        'page_obj': page_obj,
        'clients': Client.objects.all(),
        'query': search_query,
    }

    return render(request, 'lead.html', context)

def create_estimation(request):
    if request.method == "POST":
        lead_id = request.POST.get('lead_no')

        if lead_id:
            try:
                lead = Lead.objects.get(id=lead_id)
                estimation = Estimation(lead_no=lead)
                # Add other estimation field initializations here if required
                estimation.save()
                messages.success(request, "Quotation created successfully.")
                return redirect('estimation_list')
            except Lead.DoesNotExist:
                messages.error(request, "Invalid Lead selected.")
        else:
            messages.error(request, "Please select a Lead No.")
        
        return redirect('estimation_create')

    return redirect('estimation_create')



from django.http import JsonResponse
from .models import Lead

def get_pending_lead(request):
    client_id = request.GET.get('client_id')
    lead = Lead.objects.filter(company_name_id=client_id, status="Pending").order_by('-date').first()

    if client_id:
        lead = Lead.objects.filter(company_name__id=client_id, status='Pending').first()

    if lead:
        return JsonResponse({'lead_no': lead.lead_no})
    return JsonResponse({'lead_no': ''})

from django.http import JsonResponse
from .models import Lead

def get_pending_leads(request):
    client_id = request.GET.get('client_id')
    leads = Lead.objects.filter(company_name_id=client_id, status='Pending')
    data = {
        'leads': [{'id': lead.id, 'lead_no': lead.lead_no} for lead in leads]
    }
    return JsonResponse(data)




def get_gst_no(request):
    client_id = request.GET.get('client_id')
    try:
        client = Client.objects.get(id=client_id)
        return JsonResponse({'gst_no': client.gst_no})
    except Client.DoesNotExist:
        return JsonResponse({'gst_no': ''})

    lead_id = request.POST.get('lead_no')
    lead_obj = Lead.objects.get(id=lead_id)
    estimation.lead_no = lead_obj
    print("lead_id received:", lead_id)

    try:
        lead_id = int(lead_id)
    except (ValueError, TypeError):
        return render(request, 'quotation_form.html', {
            'error': "Invalid Lead ID received.",
        })


    lead_id_raw = request.POST.get('lead_no')

    try:
        lead_id = int(lead_id_raw)
        lead = Lead.objects.get(id=lead_id)
    except (ValueError, TypeError, Lead.DoesNotExist):
        return render(request, 'create_quotation.html', {
            'clients': Client.objects.all(),
            'gst_percentage': 18,
            'error': f"Something went wrong: Field 'id' expected a number but got '{lead_id_raw}'"
        })






from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Client, Lead, Estimation, EstimationItem, GSTSettings
from .utils import generate_and_reserve_quote_no, safe_decimal
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.template.loader import render_to_string, get_template
from django.conf import settings
from weasyprint import HTML
from num2words import num2words
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
import pandas as pd
import os


from .models import (
    Client, Lead, Estimation, EstimationItem, Invoice, PaymentLog,
    EstimationSettings, GSTSettings, QuotationItem
)
from .forms import (
    ClientForm, EstimationForm, ApprovalForm
)
from .utils import inr_currency_words, generate_invoice_number


# 🔢 Generate Unique Quote No
def generate_and_reserve_quote_no():
    setting = EstimationSettings.objects.first()
    if not setting:
        setting = EstimationSettings.objects.create(prefix="EST", next_number=1)

    while True:
        quote_no = f"{setting.prefix}-{setting.next_number:04d}"
        if not Estimation.objects.filter(quote_no=quote_no).exists():
            setting.next_number += 1
            setting.save()
            return quote_no
        setting.next_number += 1
        setting.save()

# 🔒 Safe Decimal Conversion
def safe_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0.00')


# 📝 Create Quotation View
def create_quotation(request):
    clients = Client.objects.all()
    gst_setting = GSTSettings.objects.first()
    pending_leads = Lead.objects.filter(status='Pending')

    default_terms = """1) This is a system generated Quotation. Hence, signature is not needed.<br>
    2) Payment Terms: 100% Advance Payment or As Per Agreed Terms<br>
    3) Service Warranty 30 to 90 Days Depending upon the Availed Service<br>
    4) All Products and Accessories Carries Standard OEM Warranty"""

    if request.method == 'POST':
        company_id = request.POST.get('company_name')
        lead_id = request.POST.get('lead_no')

        try:
            quote_no = generate_and_reserve_quote_no()
            quote_date = now().date()
            client = Client.objects.get(id=company_id)
            lead_instance = Lead.objects.get(id=lead_id) if lead_id else None

            # 🧾 Create Estimation
            estimation = Estimation.objects.create(
                quote_no=quote_no,
                quote_date=quote_date,
                company_name=client,
                lead_no=lead_instance,
                validity_days=request.POST.get('validity_days'),
                gst_no=request.POST.get('gst_no'),
                billing_address=request.POST.get('billing_address'),
                shipping_address=request.POST.get('shipping_address'),
                terms_conditions=request.POST.get('terms_conditions'),
                bank_details=request.POST.get('bank_details'),
                sub_total=safe_decimal(request.POST.get('sub_total')),
                discount=safe_decimal(request.POST.get('discount')),
                gst_amount=safe_decimal(request.POST.get('gst_amount')),
                total=safe_decimal(request.POST.get('total')),
            )

            # 🧾 Add Quotation Items
            items = zip(
                request.POST.getlist('item_details[]'),
                request.POST.getlist('hsn_sac[]'),
                request.POST.getlist('quantity[]'),
                request.POST.getlist('rate[]'),
                request.POST.getlist('tax[]'),
                request.POST.getlist('amount[]')
            )

            for detail, hsn, qty, rate, tax, amt in items: 
                EstimationItem.objects.create(
                    estimation=estimation,
                    item_details=detail,
                    hsn_sac=hsn.strip() if hsn else "—",
                    quantity=int(qty or 0),
                    rate=safe_decimal(rate),
                    tax=safe_decimal(tax),
                    amount=safe_decimal(amt)
                )

            # ✅ Update Lead Status Immediately
            if lead_instance:
                if estimation.status in ['Approved', 'Invoiced']:
                    lead_instance.computed_status = 'Won'
                elif estimation.status == 'Pending':
                    lead_instance.computed_status = 'Quoted'
                elif estimation.status == 'Lost':
                    lead_instance.computed_status = 'Lost'
                else:
                    lead_instance.computed_status = 'Pending'
                lead_instance.save()

            return redirect('estimation')

        except Exception as e:
            return render(request, 'create_quotation.html', {
                'clients': clients,
                'pending_leads': pending_leads,
                'gst_percentage': gst_setting.percentage if gst_setting else 18.0,
                'error': f"Something went wrong: {e}"
            })

    return render(request, 'create_quotation.html', {
        'clients': clients,
        'pending_leads': pending_leads,
        'gst_percentage': gst_setting.percentage if gst_setting else 18.0,
        'terms': default_terms
    })

   



from django.http import JsonResponse
from .models import Client

@csrf_exempt
def client_entry_ajax(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        type_of_company = request.POST.get('type_of_company')
        gst_no = request.POST.get('gst_no')

        client = Client.objects.create(
            company_name=company_name,
            type_of_company=type_of_company,
            gst_no=gst_no
        )
        return JsonResponse({'success': True, 'client': {'company_name': client.company_name}})
    return JsonResponse({'success': False})


from .models import TermsAndConditions
from crm.models import TermsAndConditions

def quotation_pdf(request, pk):
    quotation = get_object_or_404(Estimation, pk=pk)
    terms = TermsAndConditions.objects.last()  # Get latest one

    html_string = render_to_string("quotation_pdf.html", {
        'quotation': quotation,
        'items': items,
        'terms': terms,
    })



from django.views import View
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from datetime import timedelta
from .models import Estimation, EstimationItem, DefaultTerms
from .utils import inr_currency_words
from django.conf import settings
from pathlib import Path

class QuotationPDFView(View):  # ✅ Inherit from View
    def get(self, request, pk):
        estimation = get_object_or_404(Estimation, pk=pk)

        items = [
            {
                'item_details': item.item_details,
                'hsn_sac': item.hsn_sac or "",
                'quantity': item.quantity,
                'rate': item.rate,
                'tax': item.tax,
                'amount': item.amount,
            }
            for item in estimation.items.all()
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

        default_terms = DefaultTerms.objects.order_by('-id').first() or DefaultTerms(content="")
        expiry_date = estimation.quote_date + timedelta(days=estimation.validity_days)
        amount_in_words = inr_currency_words(estimation.total)

        # Logo
        logo_path = Path(settings.STATIC_ROOT) / "images/logo.png"
        logo_uri = logo_path.as_uri()

        html_string = render_to_string('quotation_pdf_template.html', {
            'estimation': estimation,
            'items': items,
            'amount_in_words': amount_in_words,
            'logo_uri': logo_uri,
            'expiry_date': expiry_date,
            'same_state': same_state,
            'cgst': cgst,
            'sgst': sgst,
            'igst': igst,
            'cgst_rate': cgst_rate,
            'sgst_rate': sgst_rate,
            'igst_rate': igst_rate,
            'terms': default_terms,
        })

        pdf = HTML(string=html_string, base_url=settings.STATIC_ROOT.as_uri()).write_pdf()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=Quotation_{estimation.quote_no}.pdf'
        return response


import os
from django.conf import settings

logo_path = str(os.path.join(settings.STATIC_ROOT, "images/logo.png"))


# 📋 Estimation List View
def estimation_view(request):
    sort = request.GET.get('sort', 'quote_date')
    estimations = Estimation.objects.all().order_by('company_name' if sort == 'company' else '-quote_date')
    query = request.GET.get('q')
    if query:
        estimations = estimations.filter(quote_no__icontains=query)

    return render(request, 'estimation.html', {
        'estimations': estimations,
        'query': query,
        'current_sort': sort,
    })

from django.shortcuts import render, get_object_or_404, redirect
from decimal import Decimal
from .models import Estimation, EstimationItem, DefaultTerms, Client, Lead
from .forms import EstimationForm
from .utils import generate_estimation_pdf


def edit_estimation(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)

    # Fetch supporting data
    clients = Client.objects.all()
    items = EstimationItem.objects.filter(estimation=estimation)
    default_terms = DefaultTerms.objects.first()
    all_leads = Lead.objects.filter(company_name=estimation.company_name)

    if request.method == 'POST':
        print(">>> METHOD:", request.method)
        print(">>> POST DATA:", request.POST.dict())

        form = EstimationForm(request.POST, instance=estimation)

        if form.is_valid():
            print(">>> FORM VALID ✅")
            updated_estimation = form.save(commit=False)

            # Update numeric fields
            updated_estimation.sub_total = Decimal(request.POST.get('sub_total') or 0)
            updated_estimation.discount = Decimal(request.POST.get('discount') or 0)
            updated_estimation.gst_amount = Decimal(request.POST.get('gst_amount') or 0)
            updated_estimation.total = Decimal(request.POST.get('total') or 0)

            # Update other fields
            updated_estimation.terms_conditions = request.POST.get('terms_conditions', '')
            updated_estimation.quote_date = request.POST.get('quote_date')
            updated_estimation.validity_days = request.POST.get('validity_days')
            updated_estimation.lead_no_id = request.POST.get('lead_no') or None
            updated_estimation.company_name_id = request.POST.get('company_name') or estimation.company_name_id

            updated_estimation.save()
            print(">>> Estimation saved with ID:", updated_estimation.id)

            # Replace old items
            EstimationItem.objects.filter(estimation=updated_estimation).delete()

            # Save new/edited items
            item_details = request.POST.getlist('item_details[]')
            hsn_sacs = request.POST.getlist('hsn_sac[]')
            quantities = request.POST.getlist('quantity[]')
            rates = request.POST.getlist('rate[]')
            taxes = request.POST.getlist('tax[]')
            amounts = request.POST.getlist('amount[]')

            for detail, hsn, qty, rate, tax, amount in zip(
                item_details, hsn_sacs, quantities, rates, taxes, amounts
            ):
                if detail.strip():  # only save non-empty rows
                    EstimationItem.objects.create(
                        estimation=updated_estimation,
                        item_details=detail.strip(),
                        hsn_sac=hsn.strip() if hsn else None,
                        quantity=int(qty or 0),
                        rate=Decimal(rate or 0),
                        tax=Decimal(tax or 0),
                        amount=Decimal(amount or 0),
                    )

            print(">>> Items saved:", EstimationItem.objects.filter(estimation=updated_estimation).count())

            # Regenerate PDF
            generate_estimation_pdf(updated_estimation)
            print(">>> PDF generated successfully")

            print(">>> Redirecting to estimation_list 🚀")
            return redirect('estimation_list')

        else:
            print(">>> FORM INVALID ❌")
            print(">>> ERRORS:", form.errors)

    else:
        form = EstimationForm(instance=estimation)

    return render(request, 'edit_estimation.html', {
        'form': form,
        'estimation': estimation,
        'clients': clients,
        'items': items,
        'terms': default_terms,
        'all_leads': all_leads,
    })


from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Estimation
from django.utils.timezone import localdate
from django.db.models import Q

def estimation_list(request):
    today = localdate()
    follow_up_filter = request.GET.get("follow_up", "")

    if follow_up_filter == "today":
        estimations = Estimation.objects.filter(follow_up_date=today).order_by('-id')
    else:
        estimations = Estimation.objects.all().order_by('-id')

    paginator = Paginator(estimations, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "follow_up": follow_up_filter,
        "today": today,
    }
    return render(request, "estimation_list.html", context)



# ✅ Approve Estimation + Create Invoice
from django.shortcuts import get_object_or_404, redirect, render
from .models import Estimation, Invoice

from .forms import ApprovalForm

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

        # ❌ DO NOT create invoice here
        # ✅ Just mark Estimation as Approved

        return redirect('invoice_approval_list')

    # Add form context (required to avoid template error)
    from .forms import ApprovalForm
    form = ApprovalForm(instance=estimation)
    return render(request, 'crm/approve_estimation.html', {
        'estimation': estimation,
        'form': form,
    })

from django.views.decorators.http import require_POST
from django.shortcuts import redirect, get_object_or_404
from .models import Estimation

@require_POST
def reject_estimation(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    estimation.status = "Rejected"
    estimation.remarks = request.POST.get("reason", "")
    estimation.save()
    return redirect("estimation")  # Make sure this name exists in your urls



# 📊 Invoice Approval Table View
def invoice_approval_table(request):
    estimations = Estimation.objects.filter(status='Approved', invoice__isnull=True)
    invoices = Invoice.objects.all().order_by('-created_at')
    return render(request, 'invoice_approval_list.html', {
        'estimations': estimations,
        'invoices': invoices,
    })


@require_POST
def reject_invoice(request, pk):
    # Try fetching invoice, if not found, fallback to estimation
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

from django.views.decorators.csrf import csrf_exempt

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

from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from .models import Estimation

@require_http_methods(["POST"])
def mark_lost(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    reason = request.POST.get('reason', '').strip()

    if reason:
        estimation.status = "Lost"
        estimation.lost_reason = reason
        estimation.save()
    return redirect('estimation_list')



# 🧾 Placeholder Create Invoice View
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

from django.shortcuts import get_object_or_404, render
from .models import Estimation, QuotationItem

def invoice_detail_view(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    items = EstimationItem.objects.filter(estimation=estimation)
    invoice = Invoice.objects.filter(estimation=estimation).first()  # may be None

    context = {
        'estimation': estimation,
        'items': items,
        'invoice': invoice,
        'amount_in_words': inr_currency_words(estimation.total),    
    }
    return render(request, 'crm/invoice_detail.html', context)

from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST
from crm.models import Estimation, Invoice
from .utils import generate_invoice_number

@require_POST
def approve_invoice(request, est_id):
    estimation = get_object_or_404(Estimation, id=est_id)

    if Invoice.objects.filter(estimation=estimation).exists():
        return redirect('invoice_list')  # already invoiced

    estimation.status = 'Approved'
    estimation.save()

    credit_days = estimation.credit_days or 0
    due_date = timezone.now().date() + timedelta(days=credit_days)

    invoice = Invoice.objects.create(
        estimation=estimation,
        invoice_no=generate_invoice_number(),
        created_at=timezone.now(),
        total_value=estimation.total,
        balance_due=estimation.total,
        due_date=due_date,
        credit_days=credit_days,
        remarks=estimation.remarks,
        is_approved=True,
        status='Pending'
    )

    estimation.status = 'Invoiced'
    estimation.save()

    return redirect('invoice_list')  # this must match your invoice table view name



from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from .models import Estimation, Invoice

@require_POST
def generate_invoice_from_estimation(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)

    # Only generate if not already generated
    if not Invoice.objects.filter(estimation=estimation).exists():
        Invoice.objects.create(
            estimation=estimation,
            invoice_no=generate_invoice_number(),
            is_approved=False
        )
    return redirect('invoice_approval_list')



from django.shortcuts import render, get_object_or_404
from .models import Estimation, EstimationItem

def estimation_detail_view(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    items = estimation.items.all()

    total = 0  # ✅ initialize total to avoid UnboundLocalError

    for item in items:
        total += item.amount

    context = {
        'estimation': estimation,
        'items': items,
        'total': total,
    }

    return render(request, 'crm/estimation_detail_view.html', context)




from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from .models import Estimation

@csrf_exempt
def mark_under_review(request, id):
    if request.method == 'POST':
        estimation = Estimation.objects.get(id=id)
        estimation.status = 'Under Review'
        estimation.follow_up_date = request.POST.get('follow_up_date')
        estimation.follow_up_remarks = request.POST.get('follow_up_remarks')
        estimation.save()
        return redirect('estimation_list')


from .models import Estimation

def invoices_view(request):
    estimations_without_invoice = Estimation.objects.filter(generated_invoice__isnull=True)
    ...
from django.shortcuts import get_object_or_404, redirect
from .models import Estimation, Invoice


from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from datetime import timedelta
from .models import Invoice, EstimationItem
from num2words import num2words
from django.conf import settings
from pathlib import Path

def invoice_pdf_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    estimation = invoice.estimation
    items = EstimationItem.objects.filter(estimation=estimation)

    # Due date
    due_date = invoice.created_at + timedelta(days=invoice.credit_days or 0)

    # Amount in words
    total = estimation.total
    rupees = int(total)
    paise = int(round((total - rupees) * 100))
    amount_in_words = f"Rupees {num2words(rupees, lang='en_IN').title()}"
    if paise > 0:
        amount_in_words += f" and {num2words(paise, lang='en_IN').title()} Paise"
    amount_in_words += " Only"

    # GST
    company_gst_state_code = estimation.gst_no[:2] if estimation.gst_no else ''
    our_gst_state_code = "29"  # Karnataka
    same_state = (company_gst_state_code == our_gst_state_code)

    if same_state:
        sgst = cgst = estimation.gst_amount / 2
        igst = 0
    else:
        sgst = cgst = 0
        igst = estimation.gst_amount

    # Logo
    logo_path = Path(settings.STATIC_ROOT) / "images/logo.png"
    logo_uri = logo_path.as_uri()

    # Render HTML
    html_string = render_to_string("invoice_pdf_weasy.html", {
        'invoice': invoice,
        'estimation': estimation,
        'items': items,
        'due_date': due_date,
        'amount_in_words': amount_in_words,
        'same_state': same_state,
        'sgst': sgst,
        'cgst': cgst,
        'igst': igst,
        'logo_uri': logo_uri,
    })

    pdf_file = HTML(string=html_string, base_url=settings.STATIC_ROOT.as_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="{invoice.invoice_no}.pdf"'
    return response




from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from .models import Invoice

@require_POST
def update_payment_status(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    new_status = request.POST.get("payment_status")

    if new_status in dict(Invoice.PAYMENT_STATUS_CHOICES):
        invoice.payment_status = new_status
        invoice.save()

    return redirect('invoice_approval_table')  # Change to your actual redirect target



from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from decimal import Decimal
from .models import Invoice, PaymentLog  # Adjust to your model names
from decimal import Decimal, InvalidOperation
from django.shortcuts import render

@require_POST
def confirm_payment(request, invoice_id):
    from decimal import Decimal
    from .models import Invoice, PaymentLog

    invoice = get_object_or_404(Invoice, pk=invoice_id)

    try:
        amount_paid = Decimal(request.POST.get('amount_paid', 0))
        utr_number = request.POST.get('utr_number')
        payment_date = request.POST.get('payment_date')

        PaymentLog.objects.create(
            invoice=invoice,
            amount_paid=amount_paid,
            utr_number=utr_number,
            payment_date=payment_date
        )

        invoice.balance_due -= amount_paid

        if invoice.balance_due <= 0:
            invoice.status = "Paid"
            invoice.balance_due = Decimal('0.00')
        else:
            invoice.status = "Partial Paid"

        invoice.save()

    except Exception as e:
        return HttpResponse(f"Something went wrong: {e}")

    return redirect('invoice_list')  # update to your correct name




from django.http import JsonResponse
from .models import Invoice, PaymentLog

def get_payment_logs(request, invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    logs = invoice.logs.all().order_by('-payment_date')  # Related name used: `logs` in PaymentLog model

    logs_data = [
        {
            "amount_paid": str(log.amount_paid),
            "utr_number": log.utr_number,
            "payment_date": log.payment_date.strftime('%Y-%m-%d')
        }
        for log in logs
    ]
    
    return JsonResponse({"logs": logs_data})

from django.shortcuts import render, get_object_or_404
from .models import Invoice, PaymentLog

def view_payment_logs(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    logs = PaymentLog.objects.filter(invoice=invoice).order_by('-payment_date')
    return render(request, 'payment_logs.html', {'invoice': invoice, 'logs': logs})

from django.shortcuts import render
from crm.models import Invoice
from crm.models import Estimation

def invoice_list_view(request):
    estimations = Estimation.objects.filter(status='Approved')  # This must match
    invoices = Invoice.objects.all().order_by('-created_at')

    return render(request, 'invoice_approval_list.html', {
        'estimations': estimations,
        'invoices': invoices,
    })



from django.http import JsonResponse
from .models import PaymentLog

def invoice_logs_api(request, invoice_id):
    logs = PaymentLog.objects.filter(invoice_id=invoice_id).order_by('-payment_date')
    data = {
        'logs': [
            {
                'amount_paid': str(log.amount_paid),
                'payment_date': log.payment_date.strftime('%d-%m-%Y'),
                'utr_number': log.utr_number
            }
            for log in logs
        ]
    }
    return JsonResponse(data)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from crm.models import Lead, Estimation, Invoice, PaymentLog
from django.core.paginator import Paginator

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
        payment = PaymentLog.objects.filter(invoice=invoice).first() if invoice else None

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

    paginator = Paginator(report_data, 20)  # 20 rows per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'crm/report_list.html', {
        'report_data': page_obj,
        'page_obj': page_obj,
    })




import pandas as pd
from django.http import HttpResponse
from crm.models import Invoice


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
        payment = PaymentLog.objects.filter(invoice=invoice).first() if invoice else None

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



from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse


def export_report_pdf(request):
    invoices = get_filtered_invoices(request)

    html_string = render_to_string('report_pdf_template.html', {
        'invoices': invoices,
    })

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Filtered_CRM_Report.pdf"'
    return response

from .models import Invoice

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


