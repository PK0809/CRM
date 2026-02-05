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

# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, UserPermission


# ====================================================
# Inline: UserProfile within User
# ====================================================
class UserProfileInline(admin.StackedInline):
    """
    Display and edit user profile inline under the User model.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"
    fields = ("name", "phone_number", "role", "permissions", "created_at")
    readonly_fields = ("created_at",)
    filter_horizontal = ("permissions",)


# ====================================================
# User Admin
# ====================================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User with inline profile.
    """
    inlines = [UserProfileInline]

    list_display = ("username", "email", "role", "is_staff", "is_superuser", "last_login")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email", "mobile")}),
        ("Role & Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "role", "is_staff", "is_superuser"),
        }),
    )

    def get_inline_instances(self, request, obj=None):
        """
        Only show inline when editing an existing user.
        """
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


# ====================================================
# User Profile Admin
# ====================================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin for direct access to User Profiles (optional).
    """
    list_display = ("user", "name", "role", "phone_number", "created_at")
    search_fields = ("user__username", "user__email", "name")
    list_filter = ("role", "created_at")
    ordering = ("-created_at",)
    filter_horizontal = ("permissions",)
    readonly_fields = ("created_at",)


# ====================================================
# User Permission Admin
# ====================================================
@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    """
    Simple list of CRM-level permissions.
    """
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)