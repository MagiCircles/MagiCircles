import datetime
from django import template
from django.forms.fields import NullBooleanField, BooleanField, DateTimeField
register = template.Library()

@register.filter
def is_boolean(field):
    if isinstance(field.field, NullBooleanField):
        return False
    elif isinstance(field.field, BooleanField):
        return True
    return False

@register.filter
def is_date_time_field(field):
    if isinstance(field.field, DateTimeField):
        return True
    return False

def _parse_date(field):
    val = field.value()
    if not val:
        return None
    elif isinstance(val, basestring):
        try:
            val = datetime.datetime.strptime(val, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            val = datetime.datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
    return val


@register.filter
def hours_for_field(field):
    val = _parse_date(field)
    hours = None if val is None else val.hour
    # Default min to 8am.
    nums = [8, 9, 10, 11, 0, 1, 2, 3, 4, 5, 6, 7]
    for i in nums:
        selected = hours is not None and i == (hours % 12)
        if i == 0:
            yield "12".format(i), selected
        else:
            yield str(i), selected

@register.filter
def minutes_for_field(field):
    val = _parse_date(field)
    minutes = None if val is None else val.minute
    for i in range(0, 60, 5):
        yield "{:02}".format(i), i == minutes

@register.filter
def ampm_for_field(field):
    val = _parse_date(field)
    yield "am", val is not None and val.hour < 12
    yield "pm", val is not None and val.hour >= 12

@register.filter
def bootstrap_control_field(field):
    """
    Add 'form-control' class and placeholder='field.label' to the field.
    """
    return field.as_widget(attrs={
        'class': field.css_classes() or u' '.join([
            'form-control', field.field.widget.attrs.get('class', ''),
        ]),
        "placeholder": getattr(field.field, 'placeholder', None) or field.label,
    });
