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
