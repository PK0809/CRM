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
    path('leads/', views.lead_view, name='lead'),
    path('client/add', views.client_list, name='client'),        # Shows the client list
    path('client/add/', views.client_view, name='client'),   # Shows the "New Client" form,
    path('client/add/', views.add_client, name='client_entry'),
    path('client/', views.client_view, name='client'),
    path('estimation/', views.estimation_view, name='estimation'),
    path('invoice/', views.invoice_view, name='invoice'),
    path('vendor/', views.vendor_view, name='vendor'),
    path('purchase-order/', views.purchase_order_view   , name='purchase_order'),
    path('bill/', views.bill_view, name='bill'),
]

class ClientView(View):  # or something similar
    def get(self, request):
        # your logic
        return render(request, 'client.html')

   
