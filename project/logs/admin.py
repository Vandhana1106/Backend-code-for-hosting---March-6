from django.contrib import admin
from import_export.admin import ExportMixin, ImportExportModelAdmin
from import_export import resources
from .models import MachineLog, UserMachineLog, ModeMessage, Operator, OperatorAFL

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
    list_display = ('MACHINE_ID', 'OPERATOR_ID', 'DATE', 'START_TIME', 'END_TIME', 'MODE','created_at')
    search_fields = ('MACHINE_ID', 'OPERATOR_ID', 'DATE')
    list_filter = ('DATE', 'MODE')

# Register the model with custom admin
admin.site.register(MachineLog, MachineLogAdmin)

# admin.py

from django.contrib import admin
from .models import UserMachineLog

@admin.register(UserMachineLog)
class UserMachineLogAdmin(admin.ModelAdmin):
    list_display = ['MACHINE_ID', 'OPERATOR_ID', 'DATE', 'START_TIME', 'END_TIME']
    search_fields = ['MACHINE_ID', 'OPERATOR_ID']
    list_filter = ['DATE', 'MODE']

# Register ModeMessage model
@admin.register(ModeMessage)
class ModeMessageAdmin(admin.ModelAdmin):
    list_display = ['mode', 'message']
    search_fields = ['mode', 'message']

# Register Operator model
@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ['rfid_card_no', 'operator_name', 'remarks']
    search_fields = ['rfid_card_no', 'operator_name', 'remarks']

# Register OperatorAFL model
@admin.register(OperatorAFL)
class OperatorAFLAdmin(admin.ModelAdmin):
    list_display = ['rfid_card_no', 'operatorAFL_name', 'is_active', 'created_at']
    search_fields = ['rfid_card_no', 'operatorAFL_name']
    list_filter = ['is_active', 'created_at']
