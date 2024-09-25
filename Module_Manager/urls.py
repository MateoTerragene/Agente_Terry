from django.urls import path
from .views import ClassifyQueryView, WhatsAppQueryView, UserView

urlpatterns = [
    path('', UserView.as_view(), name='home'),  # Si el usuario está autenticado
    path('whatsapp_query/', WhatsAppQueryView.as_view(), name='whatsapp_query'),
    path('web-service/', ClassifyQueryView.as_view(), name='web_service'),
]
