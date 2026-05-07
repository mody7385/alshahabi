from django.db import models


class Employee(models.Model):
    ROLE_CHOICES = [('admin', 'مدير'), ('worker', 'عامل'), ('owner', 'صاحب')]

    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker')
    permissions = models.JSONField(default=dict, blank=True)
    balance_sar = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def has_access(self, key: str) -> bool:
        if self.role == 'admin':
            return True
        return bool(self.permissions.get(key, False))

    def __str__(self):
        return self.full_name


class EmployeePreference(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='preference')
    last_branch = models.CharField(max_length=100, blank=True, default='')
    last_currency = models.CharField(max_length=20, blank=True, default='SAR')
    last_account_type = models.CharField(max_length=30, blank=True, default='cash')
    last_manager_account = models.CharField(max_length=100, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"تفضيلات {self.employee.full_name}"
