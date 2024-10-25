from django.contrib import admin
from django.urls import path, include
from Module_Manager.views import WhatsAppQueryView,UserView, logout_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('module_manager/', include('Module_Manager.urls')),
    path('', UserView.as_view(), name='home'),  # URL raíz para login y chat
    path('login/', UserView.as_view(), name='login'),  # Ruta para login
    path('logout/', logout_view, name='logout'),
    path('whatsapp/', WhatsAppQueryView.as_view(), name='whatsapp_query'),
    path('dbviewer/', include('dbviewer.urls')),  # Incluye las URLs de dbviewer
]
