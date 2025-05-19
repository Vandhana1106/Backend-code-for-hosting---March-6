from datetime import datetime, timedelta, date
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.db.models import (
    F, Sum, Count, Case, When, Value, FloatField, ExpressionWrapper,
    Avg, IntegerField, Q, DurationField
)
from django.db.models.functions import (
    ExtractHour, ExtractMinute, ExtractSecond, Cast
)
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import UserMachineLog, OperatorAFL
from .serializers import UserMachineLogSerializer

# Dictionary to map mode numbers to descriptions
MODES = {
    1: "Sewing",
    2: "Idle",
    3: "Rework",
    4: "Needle Break",
    5: "Maintenance",
}

@api_view(['GET'])
def get_consolidated_user_AFL_logs(request):
    """
    View to retrieve user machine logs with summary calculations.
    Handles multiple filter values for machine_id, line_number, and operator_name.
    Uses UserMachineLog and OperatorAFL models.
    """
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    
    # Get all filter values
    machine_ids = request.query_params.getlist('machine_id', [])
    line_numbers = request.query_params.getlist('line_number', [])
    operator_names = request.query_params.getlist('operator_name', [])

    logs = UserMachineLog.objects.all()
    
    # Apply date filters
    if from_date:
        logs = logs.filter(DATE__gte=from_date)
    if to_date:
        logs = logs.filter(DATE__lte=to_date)
    
    # Apply machine ID filters
    if machine_ids:
        logs = logs.filter(MACHINE_ID__in=machine_ids)
    
    # Apply line number filters
    if line_numbers:
        logs = logs.filter(LINE_NUMB__in=line_numbers)
    
    # Apply operator filters - using OperatorAFL instead of Operator
    if operator_names:
        operator_afl = OperatorAFL.objects.filter(
            rfid_card_no__in=operator_names
        ).distinct()
        operator_ids = operator_afl.values_list('rfid_card_no', flat=True)
        logs = logs.filter(OPERATOR_ID__in=operator_ids)
    
    # Calculate duration in hours for each log entry
    logs = logs.annotate(
        start_seconds=ExpressionWrapper(
            ExtractHour('START_TIME') * 3600 + 
            ExtractMinute('START_TIME') * 60 + 
            ExtractSecond('START_TIME'),
            output_field=FloatField()
        ),
        end_seconds=ExpressionWrapper(
            ExtractHour('END_TIME') * 3600 + 
            ExtractMinute('END_TIME') * 60 + 
            ExtractSecond('END_TIME'),
            output_field=FloatField()
        ),
        duration_hours=ExpressionWrapper(
            (F('end_seconds') - F('start_seconds')) / 3600,
            output_field=FloatField()
        )
    )
    
    # Filter for working hours (8:25 AM to 7:30 PM)
    logs = logs.filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:30 PM (19.5 * 3600)
    )
    
    # Exclude specific break periods
    logs = logs.exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )
    
    # Calculate summary data
    summary = {
        'total_logs': logs.count(),
        'sewing_hours': logs.filter(MODE=1).aggregate(
            total=Sum('duration_hours')
        )['total'] or 0,
        'idle_hours': logs.filter(MODE=2).aggregate(
            total=Sum('duration_hours')
        )['total'] or 0,
        'meeting_hours': logs.filter(MODE=3).aggregate(
            total=Sum('duration_hours')
        )['total'] or 0,
        'no_feeding_hours': logs.filter(MODE=4).aggregate(
            total=Sum('duration_hours')
        )['total'] or 0,
        'maintenance_hours': logs.filter(MODE=5).aggregate(
            total=Sum('duration_hours')
        )['total'] or 0,
        'total_hours': logs.aggregate(
            total=Sum('duration_hours')
        )['total'] or 0,
        'total_stitch_count': logs.aggregate(
            total=Sum('STITCH_COUNT')
        )['total'] or 0,
        'total_needle_runtime': logs.aggregate(
            total=Sum('NEEDLE_RUNTIME')
        )['total'] or 0,
    }
    
    # Calculate percentages
    if summary['total_hours'] > 0:
        summary['productive_percent'] = round(
            (summary['sewing_hours'] / summary['total_hours']) * 100, 2
        )
        summary['npt_percent'] = round(
            ((summary['idle_hours'] + summary['meeting_hours'] + 
             summary['no_feeding_hours'] + summary['maintenance_hours']) / 
            summary['total_hours']) * 100, 2
        )
    else:
        summary['productive_percent'] = 0
        summary['npt_percent'] = 0
    
    # Calculate average sewing speed if there are sewing logs
    sewing_logs = logs.filter(MODE=1)
    if sewing_logs.exists():
        summary['sewing_speed'] = round(
            sewing_logs.aggregate(
                avg=Sum('STITCH_COUNT') / Sum('NEEDLE_RUNTIME')
            )['avg'] or 0, 2
        )
    else:
        summary['sewing_speed'] = 0
    
    # Serialize logs using UserMachineLogSerializer
    serialized_logs = UserMachineLogSerializer(logs, many=True).data
    
    response_data = {
        'summary': summary,
        'logs': serialized_logs,
        'filters': {
            'from_date': from_date,
            'to_date': to_date,
            'machine_ids': machine_ids,
            'line_numbers': line_numbers,
            'operator_names': operator_names
        }
    }

    return Response(response_data)
