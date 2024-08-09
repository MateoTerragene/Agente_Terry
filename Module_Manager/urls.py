from django.urls import path
from .views import ClassifyQueryView, ChatView

urlpatterns = [
    path('', ClassifyQueryView.as_view(), name='classify_query'),
    path('chat/', ChatView.as_view(), name='chat'),
]
