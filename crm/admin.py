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
    # Use actual fields present on Client: company_name, type_of_company, gst_no
    list_display = ("id", "company_name", "type_of_company", "gst_no")
    search_fields = ("company_name", "gst_no")
    list_filter = ("type_of_company",)
    ordering = ("-id",)

# =====================================
# Lead
# =====================================
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    # Lead typically has: lead_no, company_name (FK), status, date
    list_display = ("lead_no", "company_name", "status", "date")
    search_fields = ("lead_no", "company_name__company_name")
    list_filter = ("status", "date")
    ordering = ("-date",)

# =====================================
# Estimation and Items
# =====================================
class EstimationItemInline(admin.TabularInline):
    model = EstimationItem
    extra = 1
    # EstimationItem fields seen in code: item_details, hsn_sac, quantity, rate, tax, amount
    fields = ("item_details", "hsn_sac", "quantity", "rate", "tax", "amount")
    readonly_fields = ()

@admin.register(Estimation)
class EstimationAdmin(admin.ModelAdmin):
    # Estimation fields in code: quote_no, company_name, quote_date, total, status
    list_display = ("quote_no", "company_name", "quote_date", "total", "status")
    list_filter = ("status", "quote_date")
    search_fields = ("quote_no", "company_name__company_name")
    inlines = [EstimationItemInline]
    readonly_fields = ("quote_no", "quote_date")
    ordering = ("-quote_date",)

# =====================================
# Terms & Settings
# =====================================
@admin.register(TermsAndConditions)
class TermsAdmin(admin.ModelAdmin):
    # TermsAndConditions is used with .content; title/created_at may not exist
    # Show id and a trimmed preview of content safely
    list_display = ("id", "content_preview")
    search_fields = ("content",)
    ordering = ("-id",)

    def content_preview(self, obj):
        return (obj.content or "")[:60] + ("..." if obj.content and len(obj.content) > 60 else "")
    content_preview.short_description = "Content"

@admin.register(EstimationSettings)
class EstimationSettingsAdmin(admin.ModelAdmin):
    # Fields used in code: prefix, next_number
    list_display = ("id", "prefix", "next_number")
    ordering = ("-id",)

@admin.register(GSTSettings)
class GSTSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "percentage")
    ordering = ("-id",)

    def percentage(self, obj):
        return obj.gst_percentage
    percentage.short_description = "GST %"

# =====================================
# Report
# =====================================
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    # Keep generic, only use likely-safe fields; adjust if your Report model differs
    list_display = ("id", "title", "report_type", "created_at")
    search_fields = ("title", "description")
    list_filter = ("report_type", "created_at")
    ordering = ("-created_at",)

# =====================================
# User Management
# =====================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # Fields used in code: user (FK), role; created_at may or may not exist
    list_display = ("user", "role")
    search_fields = ("user__username", "user__email", "role")
    list_filter = ("role",)
    ordering = ("-id",)

@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    # Your model exposes 'name' (permission name) and relation to UserProfile via userprofile?
    # Use callables to show related user; avoid non-existent fields like can_edit/can_delete
    list_display = ("id", "get_user", "name")
    search_fields = ("name", "userprofile__user__username", "userprofile__user__email")
    list_filter = ("name",)
    ordering = ("-id",)

    def get_user(self, obj):
        # Adjust relation if different; this matches usage in views where UserPermission
        # is linked to UserProfile, which links to auth User
        up = getattr(obj, "userprofile", None)
        if up and getattr(up, "user", None):
            return up.user.username
        return ""
    get_user.short_description = "User"
