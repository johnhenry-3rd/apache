# File: /home/john/Apache/apache_db/artist_logs/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies value by arg and divides by 100 (for percentage calculations)"""
    try:
        return float(value) * float(arg) / 100
    except (ValueError, TypeError):
        return 0  