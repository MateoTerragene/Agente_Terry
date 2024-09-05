from django.urls import path
from .views import ShowTablesView, CustomSQLQueryView, IntelligentQueryView, ShowTableContentView

urlpatterns = [
    path('tables/', ShowTablesView.as_view(), name='show_tables'),
    path('tables/<str:table_name>/', ShowTableContentView.as_view(), name='show_table_content'),
    path('custom_sql_query/', CustomSQLQueryView.as_view(), name='custom_sql_query'),
    path('intelligent_query/', IntelligentQueryView.as_view(), name='intelligent_query'),
]
