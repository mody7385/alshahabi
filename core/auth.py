from functools import wraps
from django.shortcuts import redirect
from .models import Employee


def get_current_employee(request):
    employee_id = request.session.get('employee_id')
    if not employee_id:
        return None
    try:
        return Employee.objects.get(id=employee_id, is_active=True)
    except Employee.DoesNotExist:
        return None


def login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not get_current_employee(request):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def permission_required(permission_key):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            employee = get_current_employee(request)
            if not employee:
                return redirect('login')
            if employee.role == 'admin' or employee.permissions.get(permission_key, False):
                request.current_employee = employee
                return view_func(request, *args, **kwargs)
            return redirect('dashboard')
        return _wrapped
    return decorator
