from django.contrib import admin
from django.urls import path, include
from Module_Manager.views import WhatsAppQueryView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('module_manager/', include('Module_Manager.urls')),
    path('whatsapp/', WhatsAppQueryView.as_view(), name='whatsapp_query')
]