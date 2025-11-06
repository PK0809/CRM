from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from .models import (
    UserProfile,
    UserPermission,
    Client,
    Lead,
    Estimation,
)

User = get_user_model()

# ====================================================
#  USER FORM (CREATE / EDIT)
# ====================================================
class UserForm(forms.ModelForm):
    """Handles both user creation and editing, with linked profile and permissions."""

    # Custom extra fields
    name = forms.CharField(max_length=100, required=False, label="Full Name")
    phone_number = forms.CharField(max_length=15, required=False, label="Phone Number")
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Leave blank to keep current password'}),
        required=False,
        label="Password",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password (optional)'}),
        required=False,
        label="Confirm Password",
    )
    permissions = forms.ModelMultipleChoiceField(
        queryset=UserPermission.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Permissions",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "role",
            "password",
            "confirm_password",
            "name",
            "phone_number",
            "permissions",
        ]

    # -------------------
    # Initialization
    # -------------------
    def __init__(self, *args, **kwargs):
        """Pre-fill existing user data and apply consistent styling."""
        super().__init__(*args, **kwargs)

        # Add Tailwind-compatible styling
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({
                    "class": "form-control w-full rounded-md border-gray-300 p-2 focus:ring-2 focus:ring-blue-400"
                })

        # Prefill existing user data from UserProfile
        if self.instance and self.instance.pk:
            try:
                profile = self.instance.userprofile
                self.fields["name"].initial = profile.name
                self.fields["phone_number"].initial = profile.phone_number
                self.fields["permissions"].initial = profile.permissions.values_list("pk", flat=True)
            except UserProfile.DoesNotExist:
                pass

    # -------------------
    # Validation
    # -------------------
    def clean(self):
        """Validate password match and length."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password or confirm:
            if password != confirm:
                self.add_error("confirm_password", "Passwords do not match.")
            elif len(password) < 6:
                self.add_error("password", "Password must be at least 6 characters long.")
        return cleaned_data

    # -------------------
    # Save Logic
    # -------------------
    def save(self, commit=True):
        """Create or update user and linked profile safely."""
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")

        # ✅ If a new password is entered, hash and save it
        if password:
            user.set_password(password)

        if commit:
            user.save()

            # ✅ Create or update user profile
            profile, _ = UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "name": self.cleaned_data.get("name", ""),
                    "phone_number": self.cleaned_data.get("phone_number", ""),
                    "role": self.cleaned_data.get("role", user.role),
                    "email": self.cleaned_data.get("email", ""),
                },
            )

            # ✅ Assign permissions (only for role = "User")
            if getattr(user, "role", "User") == "User":
                selected_permissions = self.cleaned_data.get("permissions", [])
                profile.permissions.set(selected_permissions)
            else:
                profile.permissions.clear()

        return user


# ====================================================
#  CLIENT FORM
# ====================================================
class ClientForm(forms.ModelForm):
    """Form for adding/editing client information."""

    class Meta:
        model = Client
        fields = [
            "company_name",
            "type_of_company",
            "gst_no",
            "contact_person",
            "mobile",
            "email",
            "address",
        ]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "w-full border p-2 rounded"}),
            "type_of_company": forms.Select(attrs={"class": "w-full border p-2 rounded", "id": "id_type_of_company"}),
            "gst_no": forms.TextInput(attrs={"class": "w-full border p-2 rounded", "id": "id_gst_no"}),
            "contact_person": forms.TextInput(attrs={"class": "w-full border p-2 rounded", "id": "id_contact_person"}),
            "mobile": forms.TextInput(attrs={"class": "w-full border p-2 rounded", "id": "id_mobile"}),
            "email": forms.EmailInput(attrs={"class": "w-full border p-2 rounded", "id": "id_email"}),
            "address": forms.Textarea(attrs={"class": "w-full border p-2 rounded", "rows": 3}),
        }


# ====================================================
#  LEAD FORM
# ====================================================
class LeadForm(forms.ModelForm):
    """Form for creating or editing leads."""

    class Meta:
        model = Lead
        fields = ["company_name", "requirement", "status"]
        widgets = {
            "requirement": forms.Textarea(attrs={"rows": 3, "class": "w-full border p-2 rounded"}),
            "status": forms.Select(attrs={"class": "w-full border p-2 rounded"}),
            "company_name": forms.TextInput(attrs={"class": "w-full border p-2 rounded"}),
        }


# ====================================================
#  ESTIMATION FORM
# ====================================================
class EstimationForm(forms.ModelForm):
    """Form for creating or editing estimations."""

    class Meta:
        model = Estimation
        fields = [
            "company_name",
            "lead_no",
            "quote_date",
            "validity_days",
            "gst_no",
            "billing_address",
            "shipping_address",
            "terms_conditions",
            "bank_details",
        ]
        widgets = {
            "company_name": forms.Select(attrs={"class": "w-full border p-2 rounded"}),
            "lead_no": forms.TextInput(attrs={"class": "w-full border p-2 rounded"}),
            "quote_date": forms.DateInput(attrs={"type": "date", "class": "w-full border p-2 rounded"}),
            "validity_days": forms.NumberInput(attrs={"class": "w-full border p-2 rounded"}),
            "gst_no": forms.TextInput(attrs={"class": "w-full border p-2 rounded"}),
            "billing_address": forms.Textarea(attrs={"rows": 3, "class": "w-full border p-2 rounded"}),
            "shipping_address": forms.Textarea(attrs={"rows": 3, "class": "w-full border p-2 rounded"}),
            "terms_conditions": forms.Textarea(attrs={"rows": 6, "class": "w-full border p-2 rounded"}),
            "bank_details": forms.Textarea(attrs={"rows": 4, "class": "w-full border p-2 rounded"}),
        }


# ====================================================
#  APPROVAL FORM (MANAGER / ADMIN)
# ====================================================
class ApprovalForm(forms.ModelForm):
    """Used when approving or reviewing estimations."""

    class Meta:
        model = Estimation
        fields = [
            "credit_days",
            "po_number",
            "po_date",
            "po_received_date",
            "po_attachment",
            "remarks",
        ]
        widgets = {
            "po_date": forms.DateInput(attrs={"type": "date", "class": "w-full border p-2 rounded"}),
            "po_received_date": forms.DateInput(attrs={"type": "date", "class": "w-full border p-2 rounded"}),
            "remarks": forms.Textarea(attrs={"rows": 3, "class": "w-full border p-2 rounded"}),
        }


# ====================================================
#  APPROVE ESTIMATION FORM
# ====================================================
class ApproveEstimationForm(forms.ModelForm):
    """Form specifically used when finalizing approved estimations."""

    class Meta:
        model = Estimation
        fields = [
            "credit_days",
            "po_number",
            "po_date",
            "po_received_date",
            "po_attachment",
            "remarks",
        ]
        widgets = {
            "po_date": forms.DateInput(attrs={"type": "date", "class": "w-full border p-2 rounded"}),
            "po_received_date": forms.DateInput(attrs={"type": "date", "class": "w-full border p-2 rounded"}),
            "remarks": forms.Textarea(attrs={"rows": 3, "class": "w-full border p-2 rounded"}),
        }
