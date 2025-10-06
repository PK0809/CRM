# =====================================
# Django Admin Configuration
# =====================================
from django.contrib import admin
from .models import (
    Client,
    Lead,
    Estimation,
    EstimationItem,
    EstimationSettings,
    GSTSettings,
    TermsAndConditions,
    Report,
    UserProfile,
    UserPermission,
)

# =====================================
# Client
# =====================================
admin.site.register(Client)

# =====================================
# Lead
# =====================================
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['lead_no', 'company_name', 'status', 'date']
    search_fields = ['lead_no', 'company_name']
    list_filter = ['status', 'date']

# =====================================
# Estimation and Items
# =====================================
class EstimationItemInline(admin.TabularInline):
    model = EstimationItem
    extra = 1

@admin.register(Estimation)
class EstimationAdmin(admin.ModelAdmin):
    list_display = ('quote_no', 'company_name', 'quote_date', 'total', 'status')
    list_filter = ('status', 'quote_date')
    search_fields = ('quote_no', 'company_name')
    inlines = [EstimationItemInline]

# =====================================
# Terms & Settings
# =====================================
admin.site.register(TermsAndConditions)
admin.site.register(EstimationSettings)
admin.site.register(GSTSettings)

# =====================================
# Report
# =====================================
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'created_by', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('report_type', 'created_at')

# =====================================
# User Management
# =====================================
admin.site.register(UserProfile)
admin.site.register(UserPermission)
