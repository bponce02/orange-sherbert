from django import template

register = template.Library()


@register.simple_tag
def get_field_options(obj, field_name):
    model = obj.model
    field = model._meta.get_field(field_name)
    
    # Check if it's a ForeignKey - return (id, str) tuples
    if field.is_relation:
        related_model = field.related_model
        related_ids = model.objects.values_list(field_name, flat=True).distinct()
        related_ids = [v for v in related_ids if v is not None]
        related_objects = related_model.objects.filter(pk__in=related_ids)
        return [(obj.pk, str(obj)) for obj in related_objects]
    
    # Regular field - return simple values
    distinct_values = model.objects.values_list(field_name, flat=True).distinct().order_by(field_name)
    return [(v, v) for v in distinct_values if v not in (None, '')]


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


