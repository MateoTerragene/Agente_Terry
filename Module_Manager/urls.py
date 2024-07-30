from django.urls import path
from .views import ClassifyQueryView, QueryView

urlpatterns = [
    path('', ClassifyQueryView.as_view(), name='classify_query'),
    path('query/', QueryView.as_view(), name='query')
]
