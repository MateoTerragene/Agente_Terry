# Generated by Django 5.0.7 on 2024-08-27 11:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("File_Manager", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documentrequest",
            name="link",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
