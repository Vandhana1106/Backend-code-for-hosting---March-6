# Generated by Django 5.1.6 on 2025-02-19 12:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0003_alter_machinelog_unique_together'),
    ]

    operations = [
        migrations.RenameField(
            model_name='machinelog',
            old_name='date',
            new_name='DATE',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='device_id',
            new_name='DEVICE_ID',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='end_time',
            new_name='END_TIME',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='line_numb',
            new_name='LINE_NUMB',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='machine_id',
            new_name='MACHINE_ID',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='mode',
            new_name='MODE',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='needle_runtime',
            new_name='NEEDLE_RUNTIME',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='needle_stoptime',
            new_name='NEEDLE_STOPTIME',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='operator_id',
            new_name='OPERATOR_ID',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='reserve',
            new_name='RESERVE',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='login_time',
            new_name='START_TIME',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='stitch_count',
            new_name='STITCH_COUNT',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='str_logid',
            new_name='Str_LOGID',
        ),
        migrations.RenameField(
            model_name='machinelog',
            old_name='tx_logid',
            new_name='Tx_LOGID',
        ),
        migrations.AlterUniqueTogether(
            name='machinelog',
            unique_together={('MACHINE_ID', 'OPERATOR_ID', 'START_TIME', 'END_TIME')},
        ),
        migrations.RemoveField(
            model_name='machinelog',
            name='start_time',
        ),
    ]
