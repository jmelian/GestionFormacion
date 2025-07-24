# tu_proyecto/urls.py (o como se llame la carpeta principal de tu proyecto)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('formacion/', include('formacion.urls', namespace='formacion')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)