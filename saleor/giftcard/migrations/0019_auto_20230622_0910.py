# Generated by Django 3.2.18 on 2023-06-22 09:10

import django.contrib.postgres.search
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("giftcard", "0018_metadata_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="giftcard",
            name="search_index_dirty",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="giftcard",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(
                blank=True, null=True
            ),
        ),
    ]
