from django.db import models

class FormDetails(models.Model):
    id = models.CharField(max_length=255, primary_key=True)  # Cambiar 'id' a un CharField
    first_name = models.CharField(max_length=100, blank=True, default="")
    surname = models.CharField(max_length=100, blank=True, default="")
    company = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    how_did_you_know_about_us = models.TextField(blank=True, default="")
    level_of_knowledge_of_products = models.TextField(blank=True, default="")
    additional_comments = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.first_name} {self.surname} ({self.email})"
