from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_view, name='client'),
    path('add/', views.add_client, name='add-client'),
    path('edit/<int:client_id>/', views.edit_client, name='edit-client'),
]
