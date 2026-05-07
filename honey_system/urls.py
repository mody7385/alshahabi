from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('inventory/', lambda request: views.module_page(request, 'المخزون'), name='inventory'),
    path('sales/', lambda request: views.module_page(request, 'المبيعات'), name='sales'),
    path('accounts/', lambda request: views.module_page(request, 'الحسابات'), name='accounts'),
    path('operations/', lambda request: views.module_page(request, 'العمليات'), name='operations'),
    path('suppliers/', lambda request: views.module_page(request, 'الموردون'), name='suppliers'),
    path('offers/', lambda request: views.module_page(request, 'العروض'), name='offers'),
    path('currency/', lambda request: views.module_page(request, 'المصارفة'), name='currency'),
    path('discounts/', lambda request: views.module_page(request, 'الخصومات'), name='discounts'),
    path('capital/', lambda request: views.module_page(request, 'رأس المال'), name='capital'),
]
