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
# Global Admin Settings
# =====================================
admin.site.site_header = "CRM Administration"
admin.site.site_title = "CRM Admin Portal"
admin.site.index_title = "Database Management"

# =====================================
# Client
# =====================================
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "phone", "created_at"]
    search_fields = ["name", "email", "phone"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]

# =====================================
# Lead
# =====================================
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["lead_no", "company_name", "status", "date"]
    search_fields = ["lead_no", "company_name"]
    list_filter = ["status", "date"]
    ordering = ["-date"]

# =====================================
# Estimation and Items
# =====================================
class EstimationItemInline(admin.TabularInline):
    model = EstimationItem
    extra = 1
    fields = ["item_name", "quantity", "price", "total"]

@admin.register(Estimation)
class EstimationAdmin(admin.ModelAdmin):
    list_display = ("quote_no", "company_name", "quote_date", "total", "status")
    list_filter = ("status", "quote_date")
    search_fields = ("quote_no", "company_name")
    inlines = [EstimationItemInline]
    readonly_fields = ["quote_no", "quote_date"]
    ordering = ["-quote_date"]

# =====================================
# Terms & Settings
# =====================================
@admin.register(TermsAndConditions)
class TermsAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "created_at"]
    search_fields = ["title"]
    ordering = ["-created_at"]

@admin.register(EstimationSettings)
class EstimationSettingsAdmin(admin.ModelAdmin):
    list_display = ["id", "prefix", "next_number", "created_at"]
    ordering = ["-created_at"]

@admin.register(GSTSettings)
class GSTSettingsAdmin(admin.ModelAdmin):
    list_display = ["id", "gst_percentage", "created_at"]
    ordering = ["-created_at"]

# =====================================
# Report
# =====================================
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "report_type", "created_by", "created_at")
    search_fields = ("title", "description")
    list_filter = ("report_type", "created_at")
    ordering = ["-created_at"]

# =====================================
# User Management
# =====================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "created_at"]
    search_fields = ["user__username", "role"]
    list_filter = ["role", "created_at"]
    ordering = ["-created_at"]

@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ["user", "permission_name", "can_edit", "can_delete"]
    search_fields = ["user__username", "permission_name"]
    list_filter = ["can_edit", "can_delete"]
