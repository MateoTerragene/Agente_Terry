# Generated by Django 5.0.7 on 2024-08-27 15:05

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Module_Manager", "0005_alter_userinteraction_phone_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userinteraction",
            name="phone_number",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="whatsappuser",
            name="phone_number",
            field=models.CharField(max_length=50, unique=True),
        ),
    ]
