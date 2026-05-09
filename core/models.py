from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Employee(TimeStampedModel):
    ROLE_CHOICES = [('admin', 'مدير'), ('worker', 'عامل'), ('owner', 'صاحب')]
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker')
    permissions = models.JSONField(default=dict, blank=True)
    balance_sar = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)


class Branch(TimeStampedModel):
    name = models.CharField(max_length=100)


class Product(TimeStampedModel):
    name = models.CharField(max_length=100)


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default='')
    balance_sar = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class Customer(TimeStampedModel):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True, default='')
    debt_sar = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class Inventory(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL)
    dabba_count = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    kg_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    original_dabba_count = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    original_kg_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sold_dabba_count = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sold_kg_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost_per_dabba = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    owner_sale_price_per_dabba = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    visible_to_workers = models.BooleanField(default=True)
    visible_to_owner = models.BooleanField(default=True)


class Sale(TimeStampedModel):
    CURRENCY_CHOICES = [('SAR', 'ريال سعودي'), ('YER_BIG', 'يمني كبير'), ('YER_SMALL', 'يمني صغير')]
    ACCOUNT_TYPE_CHOICES = [('cash', 'نقدي'), ('employee', 'على عامل/صاحب'), ('debt', 'دين عميل')]
    created_by = models.ForeignKey(Employee, on_delete=models.PROTECT)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    currency = models.CharField(max_length=20, choices=CURRENCY_CHOICES, default='SAR')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='cash')
    total_amount_input = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount_sar = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    inventory = models.ForeignKey(Inventory, null=True, blank=True, on_delete=models.SET_NULL)
    product_name_snapshot = models.CharField(max_length=100)
    dabba_qty = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    kg_qty = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    unit_price_input = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class Account(TimeStampedModel):
    ACCOUNT_KIND = [('manager', 'مدير'), ('employee', 'عامل/صاحب')]
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=ACCOUNT_KIND, default='manager')
    employee = models.OneToOneField(Employee, null=True, blank=True, on_delete=models.SET_NULL)
    balance_sar = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class AccountTransaction(TimeStampedModel):
    DIRECTION = [('add', 'إضافة'), ('settlement', 'تسديد'), ('purchase', 'مشتريات'), ('subtract', 'خصم')]
    SOURCE = [('manual', 'يدوي'), ('sale', 'بيع'), ('debt_settlement', 'تسديد دين'), ('employee_settlement', 'تسديد عامل')]
    account = models.ForeignKey(Account, related_name='transactions', on_delete=models.CASCADE)
    direction = models.CharField(max_length=20, choices=DIRECTION)
    source = models.CharField(max_length=30, choices=SOURCE, default='manual')
    amount_sar = models.DecimalField(max_digits=14, decimal_places=2)
    details = models.JSONField(default=dict, blank=True)
    related_transaction = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)


class SupplierTransaction(TimeStampedModel):
    TX_TYPES = [('stock_in', 'بضاعة'), ('settlement', 'تسديد'), ('discount', 'خصم')]
    supplier = models.ForeignKey(Supplier, related_name='transactions', on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TX_TYPES)
    amount_sar = models.DecimalField(max_digits=14, decimal_places=2)
    details = models.JSONField(default=dict, blank=True)
    account_transaction = models.ForeignKey(AccountTransaction, null=True, blank=True, on_delete=models.SET_NULL)


class CapitalAdjustment(TimeStampedModel):
    TYPES = [('receivable', 'مستحقات لي'), ('liability', 'خصومات علي')]
    adjustment_type = models.CharField(max_length=20, choices=TYPES)
    amount_sar = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default='')


class CurrencyRate(TimeStampedModel):
    yer_big_per_sar = models.DecimalField(max_digits=14, decimal_places=4)
    yer_small_per_sar = models.DecimalField(max_digits=14, decimal_places=4)


class ReadyOffer(TimeStampedModel):
    currency = models.CharField(max_length=20, choices=Sale.CURRENCY_CHOICES, default='SAR')
    name = models.CharField(max_length=120)


class ReadyOfferItem(models.Model):
    offer = models.ForeignKey(ReadyOffer, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=0)


class InventoryOperation(TimeStampedModel):
    operation_type = models.CharField(max_length=40, default='adjustment')
    title = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)


class EmployeePreference(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='preference')
    last_branch = models.CharField(max_length=100, blank=True, default='')
    last_currency = models.CharField(max_length=20, blank=True, default='SAR')
    last_account_type = models.CharField(max_length=30, blank=True, default='cash')
    last_manager_account = models.CharField(max_length=100, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)
