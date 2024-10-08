# po_manager/models.py
from django.db import models
# from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=120)
    price = models.FloatField()
    description = models.TextField()

    def __str__(self):
        return self.name