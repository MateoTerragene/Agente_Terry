# Generated by Django 5.0.7 on 2024-09-09 18:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Module_Manager", "0006_alter_userinteraction_phone_number_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userinteraction",
            name="message_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
