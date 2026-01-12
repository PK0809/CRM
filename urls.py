from django.urls import path
from django.shortcuts import redirect
from . import views

def redirect_to_login(request):
    return redirect('login')

urlpatterns = [
    path('', redirect_to_login),  # 👈 root URL redirects to /login/
    path('login/', views.user_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('lead/', views.lead_list, name='lead_list'),
    
    # CLIENT MANAGEMENT
    path('client/', views.client_list, name='client_list'),
    path('client/add/', views.client_entry, name='client_entry'),
    path('client/add/ajax/', views.client_entry_ajax, name='client_entry_ajax'),
    path('client/edit/<int:client_id>/', views.edit_client, name='edit_client'),
    path('clients/delete/<int:client_id>/', views.delete_client, name='delete_client'),
    path('client/<int:client_id>/branches/', views.branch_list, name='branch_list'),
    path('client/<int:client_id>/branches/delete/<int:branch_id>/', views.delete_branch, name='delete_branch'),
    path('get-gst-no/', views.get_gst_no, name='get_gst_no'),

    path('estimation/', views.estimation_view, name='estimation'),
    path('invoices/', views.invoice_list_view, name='invoice_list'),
    path('vendor/', views.vendor_view, name='vendor'),
    path('purchase-order/', views.purchase_order_view   , name='purchase_order'),
    path('bill/', views.bill_view, name='bill'),
]

from django.views import View
from django.shortcuts import render

class ClientView(View):  # or something similar
    def get(self, request):
        # your logic
        return render(request, 'client.html')

   