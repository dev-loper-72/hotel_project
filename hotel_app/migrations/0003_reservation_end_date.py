# Generated by Django 5.1.6 on 2025-02-25 19:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_app', '0002_alter_reservation_guest_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
