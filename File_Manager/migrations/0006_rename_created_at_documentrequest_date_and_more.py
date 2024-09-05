# Generated by Django 5.0.7 on 2024-08-27 13:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("File_Manager", "0005_rename_date_documentrequest_created_at_and_more"),
        ("Module_Manager", "0003_userinteraction_task_type"),
    ]

    operations = [
        migrations.RenameField(
            model_name="documentrequest",
            old_name="created_at",
            new_name="date",
        ),
        migrations.AlterField(
            model_name="documentrequest",
            name="link",
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name="documentrequest",
            name="phone_number",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="documentrequest",
            name="user_interaction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="Module_Manager.userinteraction",
            ),
        ),
        migrations.AlterModelTable(
            name="documentrequest",
            table=None,
        ),
    ]