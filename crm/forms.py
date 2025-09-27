from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['company_name', 'type_of_company', 'gst_no',]

from django import forms
from .models import Lead

class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['company_name', 'requirement', 'status']  # include required fields
        widgets = {
            'requirement': forms.Textarea(attrs={'rows': 3}),
        }


from django import forms
from .models import Estimation, Lead

class EstimationForm(forms.ModelForm):
    class Meta:
        model = Estimation
        fields = [
            "quote_no", "quote_date", "lead_no", "company_name",
            "validity_days", "gst_no", "billing_address",
            "shipping_address", "terms_conditions", "bank_details",
            "sub_total", "discount", "gst_amount", "total",
            "status", "credit_days", "po_number", "po_date",
            "po_received_date", "po_attachment", "remarks",
            "follow_up_date", "follow_up_remarks"
        ]




from django import forms
from .models import Estimation

class ApprovalForm(forms.ModelForm):
    class Meta:
        model = Estimation
        fields = ['credit_days', 'po_number', 'po_date', 'po_received_date', 'po_attachment', 'remarks']


from django import forms
from .models import Estimation

class ApproveEstimationForm(forms.ModelForm):
    class Meta:
        model = Estimation
        fields = ['credit_days', 'po_number', 'po_date', 'po_received_date', 'po_attachment', 'remarks']
        widgets = {
            'po_date': forms.DateInput(attrs={'type': 'date'}),
            'po_received_date': forms.DateInput(attrs={'type': 'date'}),
        }


from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile, UserPermission

User = get_user_model()

class UserForm(forms.ModelForm):
    name = forms.CharField(max_length=100, required=False)
    phone_number = forms.CharField(max_length=15, required=False)
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)
    permissions = forms.ModelMultipleChoiceField(
        queryset=UserPermission.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'role',
            'password', 'confirm_password',
            'name', 'phone_number', 'permissions'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ensure permissions list loads
        self.fields['permissions'].queryset = UserPermission.objects.all()

        # If editing an existing user
        if self.instance.pk:
            try:
                profile = self.instance.userprofile
                self.fields['name'].initial = profile.name
                self.fields['phone_number'].initial = profile.phone_number
                self.fields['permissions'].initial = profile.permissions.values_list('pk', flat=True)
            except UserProfile.DoesNotExist:
                pass

        # Hide permissions if role is not "User"
        if self.initial.get('role') != 'User':
            self.fields['permissions'].widget.attrs['style'] = 'display:none;'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password or confirm:
            if password != confirm:
                self.add_error('confirm_password', "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

            profile, created = UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'name': self.cleaned_data.get('name', ''),
                    'phone_number': self.cleaned_data.get('phone_number', '')
                }
            )

            profile.permissions.set(self.cleaned_data.get('permissions', []))

        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['name', 'phone_number', 'permissions']


