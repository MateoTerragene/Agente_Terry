# Generated by Django 5.0.7 on 2024-08-27 10:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Module_Manager", "0002_alter_thread_user_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="userinteraction",
            name="task_type",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]