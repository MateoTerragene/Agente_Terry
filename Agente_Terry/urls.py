from django.contrib import admin
from django.urls import path, include
from Module_Manager.views import WhatsAppQueryView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('module_manager/', include('Module_Manager.urls')),
    path('whatsapp/', WhatsAppQueryView.as_view(), name='whatsapp_query'),
    path('dbviewer/', include('dbviewer.urls')),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
