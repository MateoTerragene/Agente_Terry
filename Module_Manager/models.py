from django.db import models
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Thread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255) 
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    thread_id = models.CharField(max_length=255, default=uuid.uuid4)
    language = models.CharField(max_length=50, default="Unknown")

    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.save()



class ExternalUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_login = models.CharField(max_length=255)
    user_email = models.EmailField()
    display_name = models.CharField(max_length=255)

    class Meta:
        managed = False  # No permitir que Django gestione la tabla
        db_table = 'wp_users'  
        # app_label = 'Module_Manager'

class WhatsAppUser(models.Model):
    phone_number = models.CharField(max_length=50, unique=True) 
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.phone_number
    

class UserInteraction(models.Model):
    id = models.BigAutoField(primary_key=True)
    thread_id = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)
    endpoint = models.CharField(max_length=50)  # Puede ser 'ClassifyQueryView' o 'WhatsAppQueryView'
    user_id = models.CharField(max_length=255, blank=True, null=True)  # Puede ser None para WhatsApp
    user_login = models.CharField(max_length=255, blank=True, null=True)
    user_email = models.EmailField(blank=True, null=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)  # Puede ser None para usuarios registrados
    query = models.TextField()
    response = models.TextField()
    task_type = models.CharField(max_length=50, blank=True, null=True)
    message_id = models.CharField(max_length=255, blank=True, null=True, unique=True) 
    class Meta:
        db_table = 'Module_Manager_userinteraction' 