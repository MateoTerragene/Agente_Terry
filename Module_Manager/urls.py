from django.urls import path
from .views import ClassifyQueryView, WhatsAppQueryView, UserView

urlpatterns = [
    path('', UserView.as_view(), name='home'),  # Ruta para la vista principal
    # path('whatsapp_query/', WhatsAppQueryView.as_view(), name='whatsapp_query'),
    path('web-service/', ClassifyQueryView.as_view(), name='web_service'),
    path('create-thread/', UserView.as_view(), name='create_thread'),  # Ruta para crear un nuevo thread
    path('set_avatar/', UserView.as_view(), name='set_avatar'),  # Ruta para configurar el avatar
]
