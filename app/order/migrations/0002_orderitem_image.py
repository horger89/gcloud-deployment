# Generated by Django 4.2.11 on 2024-05-08 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="image",
            field=models.CharField(default="", max_length=500),
        ),
    ]
