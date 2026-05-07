from django.shortcuts import render

MODULES = [
    {'name': 'المخزون', 'icon': '📦', 'url': 'inventory', 'perm': 'inventory'},
    {'name': 'المبيعات', 'icon': '🛒', 'url': 'sales', 'perm': 'sales'},
    {'name': 'الحسابات', 'icon': '💰', 'url': 'accounts', 'perm': 'accounts'},
    {'name': 'العمليات', 'icon': '🧾', 'url': 'operations', 'perm': 'operations'},
    {'name': 'الموردون', 'icon': '🚚', 'url': 'suppliers', 'perm': 'suppliers'},
    {'name': 'العروض', 'icon': '🎁', 'url': 'offers', 'perm': 'offers'},
    {'name': 'المصارفة', 'icon': '💱', 'url': 'currency', 'perm': 'currency'},
    {'name': 'الخصومات', 'icon': '🏷️', 'url': 'discounts', 'perm': 'discounts'},
    {'name': 'رأس المال', 'icon': '📊', 'url': 'capital', 'perm': 'capital', 'admin_only': True},
]


def dashboard(request):
    role = request.GET.get('role', 'admin')
    visible = []
    for item in MODULES:
        if item.get('admin_only') and role != 'admin':
            continue
        visible.append(item)
    return render(request, 'core/dashboard.html', {'modules': visible, 'role': role})


def module_page(request, title):
    role = request.GET.get('role', 'admin')
    return render(request, 'core/module_page.html', {'title': title, 'role': role})
