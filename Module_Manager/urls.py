from django.urls import path
from .views import ClassifyQueryView, QueryView, ChatView

urlpatterns = [
    path('', ClassifyQueryView.as_view(), name='classify_query'),
    path('query/', QueryView.as_view(), name='query'),
    path('chat/', ChatView.as_view(), name='chat'),
]