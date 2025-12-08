from django import template

register = template.Library()


@register.simple_tag
def get_object_fields(obj):
    """
    Returns a list of tuples containing (field_name, field_value) for all fields.
    Excludes the 'id' field.
    
    Usage in template:
        {% get_object_fields object as fields %}
        {% for field_name, field_value in fields %}
            <td>{{ field_value }}</td>
        {% endfor %}
    """
    fields = []
    for field in obj._meta.fields:
        if field.name != 'id':
            field_name = field.verbose_name
            field_value = getattr(obj, field.name, '')
            fields.append((field_name, field_value))
    return fields


@register.simple_tag
def get_field_options(obj, field_name):
    model = obj.model
    distinct_values = model.objects.values_list(field_name, flat=True).distinct().order_by(field_name)
    return [v for v in distinct_values if v not in (None, '')]


@register.simple_tag
def is_selected(option, request, field):
    current = request.GET.get(field, '')
    return 'selected' if str(option) == str(current) else ''
