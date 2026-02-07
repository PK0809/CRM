from django import template
import locale

register = template.Library()

@register.filter
def indian_currency(value):
    try:
        value = float(value)
        return "₹{:,.2f}".format(value)
    except:
        return value

from django import template

register = template.Library()

@register.filter
def indian_format(value):
    return value
