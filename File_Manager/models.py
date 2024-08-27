from django.db import models

class DocumentRequest(models.Model):
    user_id = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    thread_id = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)
    documento = models.CharField(max_length=255)
    producto = models.CharField(max_length=255, null=True, blank=True)
    lote = models.CharField(max_length=255, null=True, blank=True)
    link = models.URLField(max_length=2000, null=True, blank=True)

    class Meta:
        db_table = 'file_manager_documentrequest'
