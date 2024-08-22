from django.urls import path
from .views import ClassifyQueryView, ChatView, WhatsAppQueryView

urlpatterns = [
    path('', ClassifyQueryView.as_view(), name='classify_query'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('whatsapp_query/', WhatsAppQueryView.as_view(), name='whatsapp_query'),
]
