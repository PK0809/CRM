from django.contrib import admin
from .models import Client

admin.site.register(Client)

from django.contrib import admin
from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['lead_no', 'company_name', 'status', 'date']



from django.contrib import admin
from .models import (
    Estimation,
    EstimationItem,
    EstimationSettings,
    GSTSettings
)

# Estimation inline for EstimationItem
class EstimationItemInline(admin.TabularInline):
    model = EstimationItem
    extra = 1

@admin.register(Estimation)
class EstimationAdmin(admin.ModelAdmin):
    list_display = ('quote_no', 'company_name', 'quote_date', 'total', 'status')
    list_filter = ('status',)


from .models import TermsAndConditions
admin.site.register(TermsAndConditions)


# Settings
admin.site.register(EstimationSettings)
admin.site.register(GSTSettings)
   
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'estimation', 'created_at', 'payment_status')
    list_editable = ('payment_status',)


from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'created_by', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('report_type', 'created_at')



from django.contrib import admin
from .models import UserProfile, UserPermission

admin.site.register(UserProfile)
admin.site.register(UserPermission)
