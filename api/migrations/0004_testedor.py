# Generated by Django 5.2.4 on 2025-07-10 15:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_categoriateste_todostestes_testefuncao'),
    ]

    operations = [
        migrations.CreateModel(
            name='TesteDor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_avaliacao', models.DateField(verbose_name='Data')),
                ('resultado', models.CharField(max_length=100, verbose_name='Resultado')),
                ('observacao', models.TextField(blank=True, verbose_name='Observações')),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dadosdeteste_dor', to='api.usuário')),
                ('teste', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.todostestes')),
            ],
            options={
                'verbose_name': 'Teste de Dor',
                'verbose_name_plural': 'Testes de Dor',
                'ordering': ['-data_avaliacao'],
            },
        ),
    ]
