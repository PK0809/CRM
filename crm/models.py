from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# --------- Custom User Model ----------
class User(AbstractUser):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('User', 'User'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='User')
    mobile = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username


# --------- Permission Model ----------
class UserPermission(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=15, blank=True, null=True)


# --------- User Profile Model ----------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default='User')
    permissions = models.ManyToManyField(UserPermission, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"



# ---------- Client ----------
class Client(models.Model):
    company_name = models.CharField(max_length=255)
    type_of_company = models.CharField(max_length=100)
    gst_no = models.CharField(max_length=50, blank=True, null=True)
    
    # Optional fields
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)


    def __str__(self):
        return self.company_name


from django.db import models
from .models import Client  # If in same file, you can skip this

def generate_lead_no():
    last_lead = Lead.objects.order_by('id').last()
    if last_lead and last_lead.lead_no:
        try:
            number = int(last_lead.lead_no.split('-')[-1])
        except ValueError:
            number = last_lead.id
        number += 1
    else:
        number = 1
    return f"#{number:04d}"


class Lead(models.Model):
    lead_no = models.CharField(max_length=50, unique=True, blank=True)
    date = models.DateField(auto_now_add=True, editable=False)
    company_name = models.ForeignKey(Client, on_delete=models.CASCADE)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    mobile = models.CharField(max_length=20)
    address = models.TextField()
    requirement = models.TextField()
    computed_status = models.CharField(max_length=20, default='Pending')

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Partial Paid', 'Partial Paid'),
        ('Paid', 'Paid'),
        ('Converted', 'Converted'),
        ('Rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.lead_no} - {self.company_name}"

    def save(self, *args, **kwargs):
        if not self.lead_no:
            self.lead_no = generate_lead_no()
        super().save(*args, **kwargs)

@property
def computed_status(self):
    if self.estimation_set.filter(status__in=["Approved", "Invoiced"]).exists():
        return "Won"
    return self.status



# ---------- Quotation ----------
from django.db import models
from django.utils import timezone
from num2words import num2words
from datetime import timedelta
from decimal import Decimal


# ----- Estimation Related -----
class Estimation(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Lost', 'Lost'),
    ]
   
    quote_no = models.CharField(max_length=100, unique=True)
    quote_date = models.DateField(default=timezone.now)
    lead_no = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True)
    company_name = models.ForeignKey('Client', on_delete=models.CASCADE)
    validity_days = models.PositiveIntegerField()
    gst_no = models.CharField(max_length=30, blank=True, null=True)
    billing_address = models.TextField()
    shipping_address = models.TextField()
    terms_conditions = models.TextField(blank=True, null=True)
    bank_details = models.TextField(blank=True, null=True)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    credit_days = models.PositiveIntegerField(blank=True, null=True)
    po_number = models.CharField(max_length=100, blank=True, null=True)
    po_date = models.DateField(blank=True, null=True)
    po_received_date = models.DateField(blank=True, null=True)
    po_attachment = models.FileField(upload_to="po_attachments/", blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_remarks = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, default='Pending')
    lost_reason = models.TextField(blank=True, null=True)

    def amount_in_words(self):
        return num2words(self.total, to='currency', lang='en_IN').title() + ' Only'

    def __str__(self):
        return self.quote_no

class TermsAndConditions(models.Model):
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Terms & Conditions"


class Invoice(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Partial Paid', 'Partial Paid'),
        ('Payment Received', 'Payment Received'),
    ]
    status = models.CharField(
        max_length=20,
        choices=[('Unpaid', 'Unpaid'), ('Partial Paid', 'Partial Paid'), ('Paid', 'Paid')],
        default='Unpaid'
    )

    estimation = models.ForeignKey('Estimation', on_delete=models.CASCADE)
    invoice_no = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    credit_days = models.PositiveIntegerField(default=0)
    remarks = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    due_date = models.DateField(null=True, blank=True)

@property
def due_date(self):
    return self.created_at + timedelta(days=30)

@property
def balance(self):
    return self.total_amount - self.paid_amount




    # 🆕 New Field
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateField(null=True, blank=True)
    utr_number = models.CharField(max_length=100, blank=True, null=True)


    def __str__(self):
        return self.invoice_no

class EstimationItem(models.Model):
    estimation = models.ForeignKey('Estimation', on_delete=models.CASCADE, related_name='items')
    item_details = models.TextField()
    hsn_sac = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.item_details} (Qty: {self.quantity})"

from django.db import models

class DefaultTerms(models.Model):
    content = models.TextField()

    def __str__(self):
        return "Default Terms & Conditions"


class QuotationItem(models.Model):
    estimation = models.ForeignKey(Estimation, on_delete=models.CASCADE)
    item_details = models.TextField()
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.item_details} (Qty: {self.quantity})"

# ----- Estimation Settings -----
class EstimationSettings(models.Model):
    prefix = models.CharField(max_length=10, default='EST')
    next_number = models.PositiveIntegerField(default=1)
    frequency = models.CharField(
        max_length=10,
        choices=[('daily', 'Daily'), ('monthly', 'Monthly'), ('yearly', 'Yearly')],
        default='monthly'
    )

    def __str__(self):
        return f"{self.prefix} Settings"

class GSTSettings(models.Model):
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)

    def __str__(self):
        return f"{self.percentage}%"

# ---------- PDF View ----------
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import Estimation, EstimationItem

def quotation_pdf_view(request, pk):
    estimation = get_object_or_404(Estimation, pk=pk)
    items = EstimationItem.objects.filter(estimation=estimation)

    template_path = 'quotation_pdf.html'
    context = {
        'estimation': estimation,
        'items': items,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="{estimation.quote_no}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF generation failed', status=500)
    return response
    
 
from django.db import models
from .models import Invoice  # or import it correctly if elsewhere

class PaymentLog(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='logs')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    utr_number = models.CharField(max_length=100)
    payment_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[("Paid", "Paid"), ("Partial Paid", "Partial Paid"), ("Pending", "Pending")],
        default="Pending"   # ✅ default set
    )
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.invoice.invoice_no} - ₹{self.amount_paid}"




from django.db import models
from django.contrib.auth.models import User

class Report(models.Model):
    REPORT_TYPES = (
        ('summary', 'Summary'),
        ('detailed', 'Detailed'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title



 








