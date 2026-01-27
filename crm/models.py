from django.db import models
from django.contrib.auth.models import AbstractUser, Permission
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from decimal import Decimal
from num2words import num2words


# ====================================================
#  CUSTOM USER MODEL
# ====================================================
class User(AbstractUser):
    """
    Extends Django's default User with role and mobile fields.
    """
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('User', 'User'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='User')
    mobile = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


# ====================================================
#  USER PERMISSION MODEL
# ====================================================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=50, default='User')
    permissions = models.ManyToManyField('UserPermission', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Prevent infinite recursion by disabling signals during sync
        from django.db.models.signals import post_save
        from django.contrib.auth import get_user_model
        from .signals import create_or_update_user_profile

        post_save.disconnect(create_or_update_user_profile, sender=get_user_model())

        super().save(*args, **kwargs)
        self.sync_user_permissions()

        # Reconnect signal after sync
        post_save.connect(create_or_update_user_profile, sender=get_user_model())

    def sync_user_permissions(self):
        """Sync custom permissions with Django built-in system."""
        self.user.user_permissions.clear()
        if self.role == "User":
            for perm in self.permissions.all():
                # Optional: Only sync if codename exists
                try:
                    from django.contrib.auth.models import Permission
                    django_perm = Permission.objects.filter(codename=perm.codename).first()
                    if django_perm:
                        self.user.user_permissions.add(django_perm)
                except Exception:
                    pass
        # Don't call self.user.save() — it re-triggers the signal!
        
# ====================================================
#  User Permission
# ====================================================
class UserPermission(models.Model):
    """
    Custom permission names for CRM features.
    Example: 'can_add_client', 'can_view_invoice'
    """
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)

    class Meta:
        verbose_name = "User Permission"
        verbose_name_plural = "User Permissions"

    def __str__(self):
        return self.name


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

class Branch(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='branches')
    branch_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    mobile = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True) 
    gst_no = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.branch_name} - {self.client.company_name}"

# ====================================================
#  Lead
# ====================================================
from django.db import transaction

def generate_lead_no():
    with transaction.atomic():
        last = Lead.objects.select_for_update().order_by('-id').first()
        number = int(last.lead_no.replace('#', '')) + 1 if last and last.lead_no else 1
        return f"#{number:04d}"



class Lead(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Quoted', 'Quoted'),
        ('Won', 'Won'),
        ('Lost', 'Lost'),
        ('Rejected', 'Rejected'),
    ]

    LEAD_TYPE_CHOICES = [
        ('Referrals', 'Referrals'),
        ('E-mail', 'E-mail'),
        ('Advertisements', 'Advertisements'),
        ('Website', 'Website'),
        ('JD', 'JD'),
        ('Social media', 'Social media'),
    ]

    lead_no = models.CharField(max_length=50, unique=True, blank=True)
    date = models.DateField(auto_now_add=True)
    company_name = models.ForeignKey(Client, on_delete=models.CASCADE)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    mobile = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    requirement = models.TextField(blank=True)
    lead_type = models.CharField(max_length=50, choices=LEAD_TYPE_CHOICES, default='Referrals')  # 👈 new field
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

    quote_no = models.CharField(max_length=100, unique=True, blank=True)
    quote_date = models.DateField(default=timezone.now)
    lead_no = models.ForeignKey('Lead', on_delete=models.CASCADE, null=True, blank=True)
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


from django.db import transaction
from django.db.models import F

def generate_estimation_no():
    with transaction.atomic():
        setting, _ = EstimationSettings.objects.select_for_update().get_or_create(
            id=1,
            defaults={'prefix': 'EST', 'next_number': 1}
        )

        quote_no = f"{setting.prefix}-{setting.next_number:04d}"
        setting.next_number = F('next_number') + 1
        setting.save(update_fields=['next_number'])
        setting.refresh_from_db()
        return quote_no


class EstimationItem(models.Model):
    estimation = models.ForeignKey(Estimation, on_delete=models.CASCADE, related_name='items')
    item_details = models.TextField()
    hsn_sac = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    UOM_CHOICES = [
        ("Nos", "Nos"),
        ("Box", "Box"),
        ("Meter", "Meter"),
    ]

    uom = models.CharField(
        max_length=10,
        choices=UOM_CHOICES,
        default="Nos"
    )
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def delivered_qty(self):
        return sum(
            item.quantity
            for item in DeliveryChallanItem.objects.filter(
                estimation_item=self
            )
        )

    def remaining_qty(self):
        return self.quantity - self.delivered_qty()


    def __str__(self):
        return f"{self.item_details} (Qty: {self.quantity})"
    
def is_open(self):
    return self.status in ["Pending", "Under Review"]

def can_create_dc(self):
    return self.status in ["Pending", "Under Review", "Approved", "Invoiced"]
    
# ============================
# Delivery Challan
# ============================
# models.py
class DeliveryChallan(models.Model):
    estimation = models.ForeignKey(
        Estimation,
        on_delete=models.CASCADE,
        related_name="delivery_challans"
    )

    dc_no = models.CharField(max_length=50, unique=True)
    dc_date = models.DateField()

    delivery_address = models.TextField()
    contact_person = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)

    # ✅ REQUIRED FOR YOUR CREATE_DC VIEW
    po_no = models.CharField(max_length=100, blank=True, null=True)
    po_date = models.DateField(blank=True, null=True)

    terms = models.TextField(
        default="Received the above mentioned goods in good condition, complaints (if any) contact within 24 hours"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.dc_no

class DeliveryChallanItem(models.Model):
    dc = models.ForeignKey(
        DeliveryChallan,
        on_delete=models.CASCADE,
        related_name="items"
    )

    estimation_item = models.ForeignKey(
        EstimationItem,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    UOM_CHOICES = [
        ("Nos", "Nos"),
        ("Box", "Box"),
        ("Meter", "Meter"),
    ]
    uom = models.CharField(
        max_length=10,
        choices=UOM_CHOICES,
        default="Nos"
    )

    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # ✅ Fallback to estimation item description
        if not self.description and self.estimation_item:
            self.description = self.estimation_item.item_details
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description[:40]} ({self.quantity} {self.uom})"


from django.db import transaction
from django.db.models import F

def generate_dc_no():
    with transaction.atomic():
        last = DeliveryChallan.objects.select_for_update().order_by('-id').first()
        number = last.id + 1 if last else 1
        return f"DC-{number:04d}"




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
    invoice_no = models.CharField(max_length=50, unique=True)
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
