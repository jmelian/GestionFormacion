# formacion/templatetags/formacion_tags.py

from django import template
from django.http import QueryDict
from django.contrib.auth.models import Group
# Import your models here
from formacion.models import Participacion, Curso # Make sure these paths are correct

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace_param(context, **kwargs):
    """
    Replaces or adds GET parameters in the current URL's query string.
    Example: {% url_replace_param page=1 sort_by='name' %}
    """
    # request.GET is an immutable QueryDict, so make a mutable copy
    d = context['request'].GET.copy()

    for k, v in kwargs.items():
        d[k] = v
    
    # Optional: remove params if value is None or empty string to clean up URL
    # for k in [k for k, v in d.items() if v is None or v == '']:
    #     del d[k]

    return d.urlencode()

# --- NEW: has_participation filter ---
@register.filter
def has_participation(user, course_obj):
    """
    Checks if a given user has any active participation in a specific course.
    """
    if not user.is_authenticated:
        return False
    
    # Ensure course_obj is actually a Curso instance
    if not isinstance(course_obj, Curso):
        # This can happen if the 'course' variable in the template is not a Curso object
        # You might want to log this error for debugging in a real application
        return False

    # Check for participations that are not 'cancelado' or 'rechazado'
    # Adjust 'empleado' and 'curso' field names based on your Participacion model
    return Participacion.objects.filter(
        empleado=user,
        curso=course_obj
    ).exclude(estado__in=['cancelado', 'rechazado']).exists()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Verifica si el usuario pertenece a un grupo específico.
    Uso en template: {% if request.user|has_group:"RRHH" %}
    """
    if not user.is_authenticated:
        return False
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return False
    return group in user.groups.all()