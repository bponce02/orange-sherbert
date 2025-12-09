from django import template

register = template.Library()


@register.simple_tag
def get_object_fields(obj):
    """
    Returns a list of tuples containing (field_name, verbose_name, field_value) for all fields.
    Excludes the 'id' field.
    
    Usage in template:
        {% get_object_fields object as fields %}
        {% for name, label, value in fields %}
            <td>{{ value }}</td>
        {% endfor %}
    """
    fields = []
    for field in obj._meta.fields:
        if field.name != 'id':
            field_value = getattr(obj, field.name, '')
            fields.append((field.name, field.verbose_name, field_value))
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


@register.simple_tag
def get_verbose_name(obj, field_name):
    """
    Get the verbose name for a field from a model instance.
    
    Usage: {% get_verbose_name object 'author' %}
    Returns: The field's verbose_name exactly as defined in the model
    """
    model = obj._meta.model
    try:
        field = model._meta.get_field(field_name)
        return field.verbose_name
    except:
        return field_name.replace('_', ' ').title()


@register.simple_tag(takes_context=True)
def sort_url(context, field_name):
    request = context['request']
    query_params = request.GET.copy()
    
    current_sort_by = query_params.get('sort_by', '')
    current_sort_dir = query_params.get('sort_dir', 'asc')
    
    query_params['sort_by'] = field_name
    
    if current_sort_by == field_name and current_sort_dir == 'asc':
        query_params['sort_dir'] = 'desc'
    else:
        query_params['sort_dir'] = 'asc'
        
    return f"?{query_params.urlencode()}"
