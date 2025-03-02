# Generated by Django 5.1.6 on 2025-02-25 20:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hotel_app", "0004_alter_guest_phone_number_alter_guest_postcode_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="reservation",
            name="number_of_guests",
            field=models.PositiveSmallIntegerField(
                help_text="Number of guests staying in the room"
            ),
        ),
    ]
