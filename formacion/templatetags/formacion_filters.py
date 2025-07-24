from django import template

register = template.Library()

@register.filter
def has_participation(user, course):
    """
    Checks if a given user has any active participation in a specific course.
    """
    if not user.is_authenticated:
        return False
    
    # Assuming your Participation model has a foreign key to User (e.g., 'empleado')
    # and a foreign key to Curso (e.g., 'curso').
    # Also, consider if you want to check for 'active' states like 'aceptado' or 'pendiente'
    # or just any participation record. For simplicity, we check for any record here.
    
    # You might need to adjust 'empleado' and 'curso' based on your actual model field names
    # Example: if your Participation model has 'user' and 'course' fields:
    # return course.participacion_set.filter(user=user).exists()

    # Based on previous contexts, let's assume Participacion model has fields:
    # empleado (ForeignKey to User) and curso (ForeignKey to Curso)
    # And we're looking for participations that are not 'cancelado' or 'rechazado'

    from formacion.models import Participacion # Import your Participation model

    return Participacion.objects.filter(
        empleado=user,
        curso=course
    ).exclude(estado__in=['cancelado', 'rechazado']).exists()