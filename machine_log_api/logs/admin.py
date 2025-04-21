from django.contrib import admin
from import_export.admin import ExportMixin, ImportExportModelAdmin
from import_export import resources
from .models import MachineLog

# Define resource for import/export
class MachineLogResource(resources.ModelResource):
    class Meta:
        model = MachineLog
        fields = ('MACHINE_ID', 'LINE_NUMB', 'OPERATOR_ID', 'DATE', 'START_TIME', 'END_TIME',
                  'MODE', 'STITCH_COUNT', 'NEEDLE_RUNTIME', 'NEEDLE_STOPTIME', 'Tx_LOGID',
                  'Str_LOGID', 'DEVICE_ID', 'RESERVE', 'created_at')

# Admin Configuration
class MachineLogAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = MachineLogResource
    list_display = ('MACHINE_ID', 'OPERATOR_ID', 'DATE', 'START_TIME', 'END_TIME', 'MODE')
    search_fields = ('MACHINE_ID', 'OPERATOR_ID', 'DATE')
    list_filter = ('DATE', 'MODE')

# Register the model with custom admin
admin.site.register(MachineLog, MachineLogAdmin)
