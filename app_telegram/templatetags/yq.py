from django import template

from app_telegram.i18n import trn

register = template.Library()


@register.simple_tag
def yq(key, **kwargs):
    """{% yq "dash_users" %} — перевод из app_telegram/i18n.py на языке запроса."""
    return trn(key, **kwargs)
