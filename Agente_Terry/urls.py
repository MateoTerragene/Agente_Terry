from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('module_manager/', include('Module_Manager.urls')),
]