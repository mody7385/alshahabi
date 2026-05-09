from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('inventory/', views.inventory, name='inventory'),
    path('sales/', views.sales, name='sales'),
    path('sales/create/', views.create_sale, name='create_sale'),
    path('sales/<int:sale_id>/', views.sale_detail, name='sale_detail'),
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/my/', views.my_account, name='my_account'),
    path('accounts/my/settlement/add/', views.add_employee_settlement, name='add_employee_settlement'),
    path('accounts/my/settlement/<int:tx_id>/edit/', views.edit_employee_settlement, name='edit_employee_settlement'),
    path('accounts/my/settlement/<int:tx_id>/delete/', views.delete_employee_settlement, name='delete_employee_settlement'),
    path('operations/', views.operations, name='operations'),
    path('operations/sale/<int:sale_id>/delete/', views.delete_sale_operation, name='delete_sale_operation'),
    path('suppliers/', views.suppliers, name='suppliers'),
    path('offers/', views.offers, name='offers'),
    path('currency/', views.currency, name='currency'),
    path('discounts/', views.discounts, name='discounts'),
    path('capital/', views.capital, name='capital'),
]
