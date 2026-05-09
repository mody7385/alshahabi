from django import template

register = template.Library()


@register.filter
def money_sar(value):
    try:
        return f"{float(value):,.2f} ر.س"
    except Exception:
        return "0.00 ر.س"
