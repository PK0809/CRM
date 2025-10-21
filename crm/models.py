﻿from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from num2words import num2words


# ====================================================
#  Custom User Model
# ====================================================
class User(AbstractUser):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('User', 'User'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='User')
    mobile = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username


# ====================================================
#  User Permission
# ====================================================
class UserPermission(models.Model):
    # Permission name used across the app
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# ====================================================
#  User Profile
# ====================================================
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default='User')
    permissions = models.ManyToManyField(UserPermission, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


# ====================================================
#  Client
# ====================================================
class Client(models.Model):
    company_name = models.CharField(max_length=255)
    type_of_company = models.CharField(max_length=100)
    gst_no = models.CharField(max_length=50, blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.company_name


# ====================================================
#  Lead
# ====================================================
def generate_lead_no():
    last_lead = Lead.objects.order_by('id').last()
    number = 1
    if last_lead and last_lead.lead_no:
        try:
            number = int(last_lead.lead_no.replace('#', '')) + 1
        except ValueError:
            number = last_lead.id + 1
    return f"#{number:04d}"


class Lead(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Quoted', 'Quoted'),
        ('Won', 'Won'),
        ('Lost', 'Lost'),
        ('Rejected', 'Rejected'),
    ]

    lead_no = models.CharField(max_length=50, unique=True, blank=True)
    date = models.DateField(auto_now_add=True)
    company_name = models.ForeignKey(Client, on_delete=models.CASCADE)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    mobile = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    requirement = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    computed_status = models.CharField(max_length=20, blank=True, default='')

    def save(self, *args, **kwargs):
        if not self.lead_no:
            self.lead_no = generate_lead_no()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.lead_no} - {self.company_name}"


# ====================================================
#  Estimation and Items
# ====================================================
class Estimation(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Lost', 'Lost'),
        ('Invoiced', 'Invoiced'),
    ]

    quote_no = models.CharField(max_length=100, unique=True)
    quote_date = models.DateField(default=timezone.now)
    lead_no = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True)
    company_name = models.ForeignKey(Client, on_delete=models.CASCADE)
    validity_days = models.PositiveIntegerField(default=0)
    gst_no = models.CharField(max_length=30, blank=True, null=True)
    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True, null=True)
    bank_details = models.TextField(blank=True, null=True)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    credit_days = models.PositiveIntegerField(blank=True, null=True)
    po_number = models.CharField(max_length=100, blank=True, null=True)
    po_date = models.DateField(blank=True, null=True)
    po_received_date = models.DateField(blank=True, null=True)
    po_attachment = models.FileField(upload_to="po_attachments/", blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_remarks = models.TextField(null=True, blank=True)
    lost_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def amount_in_words(self):
        return num2words(self.total, to='currency', lang='en_IN').title() + ' Only'

    def __str__(self):
        return self.quote_no


class EstimationItem(models.Model):
    estimation = models.ForeignKey(Estimation, on_delete=models.CASCADE, related_name='items')
    item_details = models.TextField()
    hsn_sac = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.item_details} (Qty: {self.quantity})"


# ====================================================
#  Invoice
# ====================================================
class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Partial Paid', 'Partial Paid'),
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
    ]

    estimation = models.ForeignKey(Estimation, on_delete=models.CASCADE)
    invoice_no = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    credit_days = models.PositiveIntegerField(default=0)
    remarks = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payment_date = models.DateField(null=True, blank=True)
    utr_number = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')

    @property
    def due_date(self):
        return self.created_at + timedelta(days=self.credit_days or 30)

    def __str__(self):
        return self.invoice_no


# ====================================================
#  Settings
# ====================================================
class EstimationSettings(models.Model):
    prefix = models.CharField(max_length=10, default='EST')
    next_number = models.PositiveIntegerField(default=1)
    frequency = models.CharField(
        max_length=10,
        choices=[('daily', 'Daily'), ('monthly', 'Monthly'), ('yearly', 'Yearly')],
        default='monthly'
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.prefix} Settings"


class GSTSettings(models.Model):
    # Align with admin and views; this field is displayed in admin and used in templates
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("18.00"))
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.gst_percentage}%"


class TermsAndConditions(models.Model):
    # Title used in admin; content is used in PDFs/views
    title = models.CharField(max_length=255, default="Default Terms")
    content = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


# ====================================================
#  Payment Log
# ====================================================
class PaymentLog(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='logs')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    utr_number = models.CharField(max_length=100)
    payment_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=50,
        choices=[("Paid", "Paid"), ("Partial Paid", "Partial Paid"), ("Pending", "Pending")],
        default="Pending"
    )
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.invoice.invoice_no} - ₹{self.amount_paid}"


# ====================================================
#  Report
# ====================================================
class Report(models.Model):
    REPORT_TYPES = (
        ('summary', 'Summary'),
        ('detailed', 'Detailed'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
