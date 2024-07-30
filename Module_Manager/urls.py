from django.urls import path
from .views import ClassifyQueryView

urlpatterns = [
    path('', ClassifyQueryView.as_view(), name='classify_query'),
]