# Generated by Django 5.1.6 on 2025-03-20 06:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0009_alter_machinelog_operator_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Operator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rfid_card_no', models.CharField(max_length=20, unique=True)),
                ('operator_name', models.CharField(max_length=50)),
                ('remarks', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
    ]
