from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from .auth import get_current_employee, login_required, permission_required
from .models import Account, AccountTransaction, Branch, CurrencyRate, Customer, Employee, EmployeePreference, Inventory, InventoryOperation, Sale, SaleItem

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


def log_system_change(title, target_url='', extra=None):
    details = {'target_url': target_url}
    if extra:
        details.update(extra)
    return InventoryOperation.objects.create(operation_type='adjustment', title=title, details=details)


def refresh_financial_balances():
    for account in Account.objects.all():
        total = Decimal('0')
        for tx in AccountTransaction.objects.filter(account=account):
            if tx.direction in ('add', 'settlement'):
                total += tx.amount_sar
            elif tx.direction in ('purchase', 'subtract'):
                total -= tx.amount_sar
        account.balance_sar = total
        account.save(update_fields=['balance_sar'])
    return True




def _reverse_sale_effects(sale):
    for item in SaleItem.objects.filter(sale=sale).select_related('inventory'):
        inv = item.inventory
        if inv:
            inv.sold_dabba_count = max(Decimal('0'), inv.sold_dabba_count - item.dabba_qty)
            inv.sold_kg_amount = max(Decimal('0'), inv.sold_kg_amount - item.kg_qty)
            inv.dabba_count = inv.dabba_count + item.dabba_qty
            inv.kg_amount = inv.kg_amount + item.kg_qty
            inv.save(update_fields=['sold_dabba_count', 'sold_kg_amount', 'dabba_count', 'kg_amount'])

    AccountTransaction.objects.filter(source='sale', details__sale_id=sale.id).delete()

    if sale.account_type == 'debt' and sale.customer_id:
        customer = Customer.objects.filter(id=sale.customer_id).first()
        if customer:
            customer.debt_sar = max(Decimal('0'), customer.debt_sar - sale.total_amount_sar)
            customer.save(update_fields=['debt_sar'])



def _to_sar(amount_input, currency):
    if currency == 'SAR':
        return amount_input
    rate = CurrencyRate.objects.order_by('-created_at').first()
    if not rate:
        return Decimal('0')
    if currency == 'YER_BIG' and rate.yer_big_per_sar:
        return amount_input / rate.yer_big_per_sar
    if currency == 'YER_SMALL' and rate.yer_small_per_sar:
        return amount_input / rate.yer_small_per_sar
    return Decimal('0')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        try:
            employee = Employee.objects.get(username=username, password=password, is_active=True)
            request.session['employee_id'] = employee.id
            log_system_change(f'تسجيل دخول: {employee.full_name}', target_url='/')
            return redirect('dashboard')
        except Employee.DoesNotExist:
            messages.error(request, 'بيانات الدخول غير صحيحة')
    return render(request, 'core/login.html')


@login_required
def logout_view(request):
    employee = get_current_employee(request)
    if employee:
        log_system_change(f'تسجيل خروج: {employee.full_name}', target_url='/login/')
    request.session.pop('employee_id', None)
    return redirect('login')


@login_required
def dashboard(request):
    employee = get_current_employee(request)
    visible = []
    for item in MODULES:
        if item.get('admin_only') and employee.role != 'admin':
            continue
        if employee.role != 'admin' and not employee.permissions.get(item['perm'], False):
            continue
        visible.append(item)
    return render(request, 'core/dashboard.html', {'modules': visible, 'employee': employee})


@permission_required('inventory')
def inventory(request):
    return module_page(request, 'المخزون')


@permission_required('sales')
def sales(request):
    return redirect('create_sale')


@permission_required('accounts')
def accounts(request):
    employee = get_current_employee(request)
    if employee.role in ('worker', 'owner'):
        return redirect('my_account')

    refresh_financial_balances()
    all_accounts = Account.objects.select_related('employee').order_by('name')
    manager_accounts = all_accounts.filter(kind='manager')
    return render(request, 'core/accounts_overview.html', {'employee': employee, 'accounts': all_accounts, 'manager_accounts': manager_accounts})


@login_required
def my_account(request):
    employee = get_current_employee(request)
    if employee.role == 'admin':
        messages.info(request, 'أنت مدير، هذه واجهة الحسابات العامة متاحة لك.')
        return redirect('accounts')

    refresh_financial_balances()
    account = get_object_or_404(Account, employee=employee)
    transactions = account.transactions.order_by('-created_at')
    manager_accounts = Account.objects.filter(kind='manager').order_by('name')
    return render(request, 'core/my_account.html', {
        'employee': employee,
        'account': account,
        'transactions': transactions,
        'manager_accounts': manager_accounts,
    })


@login_required
def add_employee_settlement(request):
    employee = get_current_employee(request)
    if employee.role not in ('worker', 'owner'):
        return redirect('accounts')
    if request.method != 'POST':
        return redirect('my_account')

    employee_account = get_object_or_404(Account, employee=employee)
    manager_account = get_object_or_404(Account, id=request.POST.get('manager_account_id'), kind='manager')

    try:
        amount = Decimal(request.POST.get('amount_sar', '0'))
    except InvalidOperation:
        amount = Decimal('0')

    if amount <= 0:
        messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر.')
        return redirect('my_account')

    note = request.POST.get('note', '').strip()
    with transaction.atomic():
        tx_employee = AccountTransaction.objects.create(
            account=employee_account,
            direction='settlement',
            source='employee_settlement',
            amount_sar=amount,
            details={'note': note, 'manager_account_id': manager_account.id, 'manager_account_name': manager_account.name},
        )
        tx_manager = AccountTransaction.objects.create(
            account=manager_account,
            direction='add',
            source='employee_settlement',
            amount_sar=amount,
            details={'note': f'تسديد من {employee.full_name}', 'employee_account_id': employee_account.id},
            related_transaction=tx_employee,
        )
        tx_employee.related_transaction = tx_manager
        tx_employee.save(update_fields=['related_transaction'])

    refresh_financial_balances()
    log_system_change(
        title=f'تسديد عامل/صاحب: {employee.full_name} - {amount} ر.س',
        target_url='/accounts/my/',
        extra={'employee_id': employee.id, 'manager_account_id': manager_account.id},
    )
    messages.success(request, 'تم حفظ التسديد بنجاح.')
    return redirect('my_account')


@login_required
def delete_employee_settlement(request, tx_id):
    employee = get_current_employee(request)
    if employee.role not in ('worker', 'owner'):
        return redirect('accounts')
    if request.method != 'POST':
        return redirect('my_account')

    employee_account = get_object_or_404(Account, employee=employee)
    tx_employee = get_object_or_404(
        AccountTransaction,
        id=tx_id,
        account=employee_account,
        source='employee_settlement',
        direction='settlement',
    )
    with transaction.atomic():
        related = tx_employee.related_transaction
        tx_employee.delete()
        if related:
            related.delete()

    refresh_financial_balances()
    log_system_change(
        title=f'حذف تسديد عامل/صاحب: {employee.full_name}',
        target_url='/accounts/my/',
        extra={'employee_id': employee.id},
    )
    messages.success(request, 'تم حذف التسديد وربطه المقابل بنجاح.')
    return redirect('my_account')




@login_required
def edit_employee_settlement(request, tx_id):
    employee = get_current_employee(request)
    if employee.role not in ('worker', 'owner'):
        return redirect('accounts')
    if request.method != 'POST':
        return redirect('my_account')

    employee_account = get_object_or_404(Account, employee=employee)
    tx_employee = get_object_or_404(
        AccountTransaction,
        id=tx_id,
        account=employee_account,
        source='employee_settlement',
        direction='settlement',
    )
    related = tx_employee.related_transaction
    if not related:
        messages.error(request, 'لا يمكن تعديل الحركة لأن الطرف المقابل غير موجود.')
        return redirect('my_account')

    manager_account = get_object_or_404(Account, id=request.POST.get('manager_account_id'), kind='manager')
    try:
        amount = Decimal(request.POST.get('amount_sar', '0'))
    except InvalidOperation:
        amount = Decimal('0')

    if amount <= 0:
        messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر.')
        return redirect('my_account')

    note = request.POST.get('note', '').strip()
    with transaction.atomic():
        tx_employee.amount_sar = amount
        tx_employee.details = {'note': note, 'manager_account_id': manager_account.id, 'manager_account_name': manager_account.name}
        tx_employee.save(update_fields=['amount_sar', 'details'])

        related.account = manager_account
        related.amount_sar = amount
        related.details = {'note': f'تسديد من {employee.full_name}', 'employee_account_id': employee_account.id}
        related.save(update_fields=['account', 'amount_sar', 'details'])

    refresh_financial_balances()
    log_system_change(
        title=f'تعديل تسديد عامل/صاحب: {employee.full_name} - {amount} ر.س',
        target_url='/accounts/my/',
        extra={'employee_id': employee.id, 'manager_account_id': manager_account.id},
    )
    messages.success(request, 'تم تعديل التسديد بنجاح.')
    return redirect('my_account')





@permission_required('sales')
def create_sale(request):
    employee = get_current_employee(request)
    pref, _ = EmployeePreference.objects.get_or_create(employee=employee)
    branches = Branch.objects.order_by('name')
    selected_branch_id = request.GET.get('branch_id') or pref.last_branch
    inventories = Inventory.objects.select_related('product', 'branch').order_by('-created_at')
    if selected_branch_id:
        inventories = inventories.filter(branch_id=selected_branch_id)
    manager_accounts = Account.objects.filter(kind='manager').order_by('name')

    if request.method == 'POST':
        inventory_ids = request.POST.getlist('inventory_id')
        dabba_qtys = request.POST.getlist('dabba_qty')
        kg_qtys = request.POST.getlist('kg_qty')
        unit_prices = request.POST.getlist('unit_price_input')

        account_type = request.POST.get('account_type', 'cash')
        currency = request.POST.get('currency', 'SAR')
        customer = Customer.objects.filter(id=request.POST.get('customer_id')).first()
        branch = get_object_or_404(Branch, id=request.POST.get('branch_id'))
        if employee.role == 'owner':
            currency = 'SAR'

        sale_items_payload = []
        total_input = Decimal('0')
        for idx, inv_id in enumerate(inventory_ids):
            if not inv_id:
                continue
            inventory = get_object_or_404(Inventory, id=inv_id)
            if inventory.branch_id != branch.id:
                messages.error(request, 'كل الأصناف يجب أن تكون من نفس الفرع المختار.')
                return redirect('create_sale')
            try:
                dabba_qty = Decimal(dabba_qtys[idx] or '0')
                kg_qty = Decimal(kg_qtys[idx] or '0')
                unit_price_input = Decimal(unit_prices[idx] or '0')
            except (InvalidOperation, IndexError):
                messages.error(request, 'أحد صفوف البيع يحتوي بيانات غير صالحة.')
                return redirect('create_sale')

            if dabba_qty < 0 or kg_qty < 0 or unit_price_input <= 0:
                messages.error(request, 'تحقق من القيم في كل صف بيع.')
                return redirect('create_sale')
            if dabba_qty == 0 and kg_qty == 0:
                continue
            if dabba_qty > inventory.dabba_count or kg_qty > inventory.kg_amount:
                messages.error(request, f'الكمية المطلوبة أكبر من المخزون في {inventory.product.name}.')
                return redirect('create_sale')

            line_total = (dabba_qty + kg_qty) * unit_price_input
            total_input += line_total
            sale_items_payload.append((inventory, dabba_qty, kg_qty, unit_price_input))

        if not sale_items_payload:
            messages.error(request, 'أضف صنفًا واحدًا على الأقل بكمية صحيحة.')
            return redirect('create_sale')

        total_sar = _to_sar(total_input, currency)
        if total_sar <= 0:
            messages.error(request, 'فشل تحويل العملة إلى سعودي. راجع سعر المصارفة.')
            return redirect('create_sale')

        manager_account = None
        if account_type == 'cash':
            manager_account_id = request.POST.get('manager_account_id')
            if not manager_account_id:
                messages.error(request, 'البيع النقدي يتطلب اختيار حساب مدير.')
                return redirect('create_sale')
            manager_account = get_object_or_404(Account, id=manager_account_id, kind='manager')

        with transaction.atomic():
            sale = Sale.objects.create(
                created_by=employee,
                customer=customer,
                branch=branch,
                currency=currency,
                account_type=account_type,
                total_amount_input=total_input,
                total_amount_sar=total_sar,
            )
            for inventory, dabba_qty, kg_qty, unit_price_input in sale_items_payload:
                SaleItem.objects.create(
                    sale=sale,
                    inventory=inventory,
                    product_name_snapshot=inventory.product.name,
                    dabba_qty=dabba_qty,
                    kg_qty=kg_qty,
                    unit_price_input=unit_price_input,
                )
                inventory.dabba_count = max(Decimal('0'), inventory.dabba_count - dabba_qty)
                inventory.kg_amount = max(Decimal('0'), inventory.kg_amount - kg_qty)
                inventory.sold_dabba_count += dabba_qty
                inventory.sold_kg_amount += kg_qty
                inventory.save(update_fields=['dabba_count', 'kg_amount', 'sold_dabba_count', 'sold_kg_amount'])

            if account_type == 'cash':
                AccountTransaction.objects.create(account=manager_account, direction='add', source='sale', amount_sar=total_sar, details={'sale_id': sale.id})
            elif account_type == 'employee':
                emp_account = Account.objects.filter(employee=employee).first()
                if emp_account:
                    AccountTransaction.objects.create(account=emp_account, direction='add', source='sale', amount_sar=total_sar, details={'sale_id': sale.id})
            elif account_type == 'debt' and customer:
                customer.debt_sar += total_sar
                customer.save(update_fields=['debt_sar'])

        pref.last_branch = str(branch.id)
        pref.last_currency = currency
        pref.last_account_type = account_type
        if request.POST.get('manager_account_id'):
            pref.last_manager_account = request.POST.get('manager_account_id')
        pref.save()

        log_system_change(
            title=f'بيع جديد #{sale.id} - {total_sar} ر.س',
            target_url=f'/sales/{sale.id}/',
            extra={'sale_id': sale.id, 'currency': currency, 'account_type': account_type, 'items_count': len(sale_items_payload)},
        )
        refresh_financial_balances()
        messages.success(request, 'تم حفظ البيع بنجاح.')
        return redirect('sale_detail', sale_id=sale.id)

    customers = Customer.objects.order_by('name')
    return render(request, 'core/create_sale.html', {
        'employee': employee,
        'branches': branches,
        'selected_branch_id': str(selected_branch_id) if selected_branch_id else '',
        'inventories': inventories,
        'customers': customers,
        'manager_accounts': manager_accounts,
        'pref': pref,
    })

@permission_required('sales')
def sale_detail(request, sale_id):
    employee = get_current_employee(request)
    sale = get_object_or_404(Sale, id=sale_id)
    items = SaleItem.objects.filter(sale=sale)
    return render(request, 'core/sale_detail.html', {'employee': employee, 'sale': sale, 'items': items})


@permission_required('operations')
def delete_sale_operation(request, sale_id):
    if request.method != 'POST':
        return redirect('operations')

    sale = get_object_or_404(Sale, id=sale_id)
    _reverse_sale_effects(sale)
    SaleItem.objects.filter(sale=sale).delete()
    sale.delete()

    log_system_change(
        title=f'حذف عملية بيع #{sale_id}',
        target_url='/operations/',
        extra={'sale_id': sale_id},
    )
    refresh_financial_balances()
    messages.success(request, 'تم حذف البيع وعكس أثره بنجاح.')
    return redirect('operations')

@permission_required('operations')
def operations(request):
    employee = get_current_employee(request)
    op_filter = request.GET.get('filter', 'all')
    operations_qs = InventoryOperation.objects.order_by('-created_at')

    filter_map = {
        'sale': 'بيع',
        'stock': 'بضاعة',
        'add': 'إضافة',
        'purchase': 'مشتريات',
        'settlement': 'تسديد',
        'edit': 'تعديل',
        'supplier_discount': 'خصم مورد',
    }
    if op_filter in filter_map:
        operations_qs = operations_qs.filter(title__icontains=filter_map[op_filter])

    return render(request, 'core/operations.html', {
        'employee': employee,
        'operations': operations_qs[:300],
        'op_filter': op_filter,
    })


@permission_required('suppliers')
def suppliers(request):
    return module_page(request, 'الموردون')


@permission_required('offers')
def offers(request):
    return module_page(request, 'العروض')


@permission_required('currency')
def currency(request):
    return module_page(request, 'المصارفة')


@permission_required('discounts')
def discounts(request):
    return module_page(request, 'الخصومات')


@permission_required('capital')
def capital(request):
    employee = get_current_employee(request)
    if employee.role != 'admin':
        return redirect('dashboard')
    return module_page(request, 'رأس المال')


def module_page(request, title):
    employee = get_current_employee(request)
    return render(request, 'core/module_page.html', {'title': title, 'employee': employee})
