from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .admin import custom_admin_site

urlpatterns = [
    path('admin/', custom_admin_site.urls),
    path('api/', include('auth_app.urls')),
    path('api/', include('speech.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
