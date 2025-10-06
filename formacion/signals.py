# formacion/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Participacion, Curso

# Modificar el signals.py para manejar cursos bajo demanda
@receiver(post_save, sender=Participacion)
def actualizar_plazas_disponibles(sender, instance, created, **kwargs):
    """
    Señal que actualiza automáticamente las plazas disponibles
    Solo para cursos con plazas limitadas (plazas_totales > 0)
    """
    curso = instance.curso
    
    # Solo actualizar cursos con plazas limitadas
    if curso.plazas_totales > 0:
        estados_que_ocupan_plaza = ['confirmado', 'asistido', 'completado', 'abandonado']
        plazas_ocupadas = Participacion.objects.filter(
            curso=curso,
            estado__in=estados_que_ocupan_plaza
        ).count()
        
        plazas_disponibles = curso.plazas_totales - plazas_ocupadas
        
        if curso.plazas_disponibles != plazas_disponibles:
            curso.plazas_disponibles = plazas_disponibles
            curso.save(update_fields=['plazas_disponibles'])
            print(f"Plazas actualizadas para curso '{curso.nombre}': {curso.plazas_disponibles}")

