# Generated by Django 5.2.4 on 2025-07-11 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_testedor'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreAvaliacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('texto', models.TextField()),
            ],
        ),
    ]
