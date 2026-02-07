from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.views.static import serve
from crm.views import invoices_view

from importlib import import_module
_crm_views = import_module('crm.views')
views = _crm_views
QuotationPDFView = _crm_views.QuotationPDFView
report_list = _crm_views.report_list
export_report_excel = _crm_views.export_report_excel
export_report_pdf = _crm_views.export_report_pdf
UserUpdateView = _crm_views.UserUpdateView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    path('', include('crm.urls')),


    # Auth
    path('', views.user_login, name='login_redirect'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Users
    path("users/", views.user_list, name="user_list"),
    path("users/create/", views.create_user, name="create_user"),
    path('users/<int:pk>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path("get-permissions/", views.get_permissions_by_role, name="get_permissions"),

    # Clients
    path('client/', views.client_list, name='client'),
    path('client/add/', views.client_entry, name='client_entry'),
    path('client/add/ajax/', views.client_entry_ajax, name='client_entry_ajax'),
    path('client/edit/<int:client_id>/', views.edit_client, name='edit_client'),
    path('clients/delete/<int:client_id>/', views.delete_client, name='delete_client'),
    path("add-branch/", views.add_branch, name="add_branch"),
    path('client/<int:client_id>/branches/', views.branch_list, name='branch_list'),
    path('client/<int:client_id>/branches/delete/<int:branch_id>/', views.delete_branch, name='delete_branch'),
    path('edit-branch/<int:branch_id>/', views.edit_branch, name='edit_branch'),
    path('get-gst-no/', views.get_gst_no, name='get_gst_no'),
    path('get-client-contacts/', views.get_client_contacts, name='get_client_contacts'),

    # Leads
    path('lead/', views.lead_list, name='lead_list'),
    path('lead/create/', views.lead_create, name='lead_create'),
    path('lead/edit/<int:pk>/', views.lead_edit, name='lead_edit'),
    path('get-pending-lead/', views.get_pending_lead, name='get_pending_lead'),
    path('get-pending-leads/', views.get_pending_leads, name='get_pending_leads'),

    # Estimations
    path('estimations/', views.estimation_list, name='estimation_list'),
    path('estimation/<int:pk>/edit/', views.edit_estimation, name='estimation_edit'),
    path('estimation/<int:pk>/approve/', views.approve_estimation, name='approve_estimation'),
    path('estimation/<int:pk>/reject/', views.reject_estimation, name='reject_estimation'),
    path('estimation/<int:pk>/status/<str:new_status>/', views.update_estimation_status, name='estimation_status'),
    path('estimation/<int:pk>/lost/', views.mark_lost, name='mark_lost'),
    path('estimation/<int:pk>/review/',views.mark_under_review,name="mark_under_review",),
    path('estimation/view/<int:pk>/', views.estimation_detail_view, name='estimation_detail'),
    path('create-quotation/', views.create_quotation, name='create_quotation'),
    path('quotation/<int:pk>/pdf/', QuotationPDFView.as_view(), name='quotation_pdf'),
    path('estimation/view/<int:pk>/', views.estimation_detail_view, name='estimation_detail'),

    path("dc/create/<int:pk>/", views.create_dc, name="create_dc"),
    path('dc/', views.dc_list, name='dc_list'),
    path("dc/<int:pk>/edit/", views.edit_dc, name="edit_dc"),
    path("dc/<int:pk>/delete/", views.delete_dc, name="delete_dc"),
    path("dc/<int:pk>/pdf/", views.dc_pdf, name="dc_pdf"),



    
    # Invoices
    path("invoices/", views.invoices_view, name="invoices"),
    path("invoices/", invoice_list_view, name="invoices"),
    path('invoice/generate/<int:pk>/', views.generate_invoice_from_estimation, name='generate_invoice'),
    path('invoice/create/', views.create_invoice, name='create_invoice'),
    path('invoice/<int:pk>/update-payment-status/', views.update_payment_status, name='update_payment_status'),
    path('invoice/<int:invoice_id>/logs/', views.view_payment_logs, name='view_payment_logs'),
    path('invoices/pdf/<int:invoice_id>/', views.invoice_pdf_view, name='invoice_pdf'),
    path('invoices/approve/<int:est_id>/', views.approve_invoice, name='approve_invoice'),
    path('invoices/reject/<int:pk>/', views.reject_invoice, name='reject_invoice'),
    path('api/invoice/<int:invoice_id>/logs/', views.get_payment_logs, name='invoice_logs'),
    path('confirm-payment/<int:invoice_id>/', views.confirm_payment_post, name='confirm_payment'),
    path("invoice/<int:invoice_id>/edit/", views.edit_invoice, name="edit_invoice"),
    path("invoices/export/", views.export_invoice_summary, name="export_invoice_summary"),
    path("invoices/export-gst/", views.export_gst_excel, name="export_gst_excel"),
    path("approve-invoice/<int:est_id>/", views.approve_invoice, name="approve_invoice"),
   



    # Reports
    path("reports/", report_list, name="report_list"),
    path("reports/export/excel/", views.export_report_excel, name="export_report_excel"),
    path("reports/export/pdf/", views.export_report_pdf, name="export_report_pdf"),

    # Other simple pages
    path('purchase-order/', views.purchase_order_view, name='purchase_order'),
    path('bill/', views.bill_view, name='bill'),
    path('vendor/', views.vendor_view, name='vendor'),
    path('profile/', views.profile_view, name='profile'),

    # Media (development convenience)
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# Redirect legacy single invoice list URL to plural
urlpatterns += [
    path('invoice/', RedirectView.as_view(url='/invoices/', permanent=True)),
]

# Static/Media in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
