

# Standard library imports
from datetime import datetime, timedelta, date

# Django imports
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

# Django REST framework imports
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework import status

# Local application imports
from .models import MachineLog, DuplicateLog, ModeMessage, Operator
from .serializers import MachineLogSerializer

# Dictionary to map mode numbers to descriptions
MODES = {
    1: "Sewing",
    2: "Idle",
    3: "No feeding",
    4: "Meeting",
    5: "Maintenance",
}

@api_view(['POST'])
def log_machine_data(request):
    """
    View to handle machine data logging with updated Tx Log ID and Str Log ID conditions.
    
    - Tx_LOGID: Now only saves the data without any condition.
    - Str_LOGID:
      - If > 1000, subtracts 1000 and stores only the adjusted value.
      - Checks if the adjusted Log ID exists for the same Machine ID before saving.
    """
    data = request.data
    print("Processing machine log data...")

    # Validate mode
    try:
        mode = int(data.get("MODE"))
    except (TypeError, ValueError):
        return Response({"message": "Invalid mode format"}, status=400)

    if mode not in MODES:
        return Response({"message": f"Invalid mode: {mode}. Valid modes are {list(MODES.keys())}"}, status=400)

    # Validate serializer
    serializer = MachineLogSerializer(data=data)
    if not serializer.is_valid():
        return Response({"message": "Validation failed", "errors": serializer.errors}, status=400)

    validated_data = serializer.validated_data

    # Extract Log IDs and Machine ID
    tx_log_id = validated_data.get("Tx_LOGID")
    str_log_id = validated_data.get("Str_LOGID")
    machine_id = validated_data.get("MACHINE_ID")

    if machine_id is None:
        return Response({"message": "MACHINE_ID is required"}, status=400)

    # Str_LOGID Handling
    if str_log_id is not None:
        try:
            str_log_id = int(str_log_id)  # Convert to integer
        except ValueError:
            return Response({"message": "Invalid Str_LOGID format"}, status=400)

        if str_log_id > 1000:
            adjusted_str_log_id = str_log_id - 1000  # Subtract 1000

            # Check if the adjusted STR Log ID exists for the same MACHINE_ID
            if MachineLog.objects.filter(Str_LOGID=adjusted_str_log_id, MACHINE_ID=machine_id).exists():
                return Response({
                    "code": 200,
                    "message": "STR Log ID already exists, data not saved"
                }, status=200)

            # Update validated data with adjusted Str_LOGID
            validated_data["Str_LOGID"] = adjusted_str_log_id

    # Save the log data
    MachineLog.objects.create(**validated_data)

    return Response({
        "code": 201,
        "message": "Log saved successfully",
    }, status=201)

@api_view(['GET'])
def get_machine_logs(request):
    """
    View to retrieve all machine logs.
    
    Fetches all machine logs from the database and enriches them
    with mode descriptions from the MODES dictionary.
    
    Returns:
        Response containing serialized logs with mode descriptions
    """
    logs = MachineLog.objects.all()
    serialized_logs = MachineLogSerializer(logs, many=True).data

    # Add mode descriptions to the serialized logs
    for log in serialized_logs:
        log['mode_description'] = MODES.get(log.get('MODE'), 'Unknown mode')

    return Response(serialized_logs)

@api_view(['POST'])
def user_login(request):
    """
    View to handle user login and authenticate using Django's built-in authentication system.
    
    Validates and processes incoming user login data:
    - Authenticates the user
    - Returns a token if authentication is successful
    
    Returns:
        Response with status and message
    """
    data = request.data
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return Response({"message": "Username and password are required"}, status=400)

    user = authenticate(username=username, password=password)
    if user is not None:
        # Authentication successful, generate token
        token, created = Token.objects.get_or_create(user=user)
        return Response({"message": "Login successful", "token": token.key}, status=200)
    else:
        return Response({"message": "Invalid credentials"}, status=400)

@api_view(['GET'])
def get_underperforming_operators(request):
    """
    Fetches the count of underperforming operators.
    
    Criteria:
    - Operators in non-production modes (mode 3, 4, 5)
    - Counts the number of unique `operator_id` values

    Returns:
        JSON response with count
    """
    underperforming_modes = [3, 4, 5]  # Non-production modes
    underperforming_count = (
        MachineLog.objects.filter(mode__in=underperforming_modes)
        .values("operator_id")  # Group by operator
        .distinct()
        .count()
    )

    return Response({"underperforming_operator_count": underperforming_count}, status=200)

@api_view(['GET'])
def get_machine_id_count(request):
    """
    Fetch total number of unique Machine IDs.
    """
    machine_count = MachineLog.objects.values("MACHINE_ID").distinct().count()
    return Response({"machine_id_count": machine_count}, status=200)

@api_view(['GET'])
def get_line_number_count(request):
    """
    Fetch total number of unique Line Numbers.
    """
    line_count = MachineLog.objects.values("LINE_NUMB").distinct().count()
    return Response({"line_number_count": line_count}, status=200)

@api_view(['GET'])
def calculate_line_efficiency(request):
    """
    Calculate efficiency metrics for each production line.
    
    Returns:
        Response with efficiency data for each line including:
        - Total machines
        - Runtime efficiency percentage
    """
    line_stats = (
        MachineLog.objects.values("LINE_NUMB")
        .annotate(
            total_machines=Count("MACHINE_ID", distinct=True),
            total_runtime=Sum("NEEDLE_RUNTIME"),
            total_stoptime=Sum("NEEDLE_STOPTIME")
        )
    )

    response = {}
    for stat in line_stats:
        line_number = stat["LINE_NUMB"]
        total_machines = stat["total_machines"]
        total_runtime = stat["total_runtime"]
        total_stoptime = stat["total_stoptime"]

        efficiency = (total_runtime / (total_runtime + total_stoptime)) * 100 if (total_runtime + total_stoptime) > 0 else 0

        response[f"Line {line_number}"] = {
            "Total_Machines": total_machines,
            "Efficiency": f"{efficiency:.2f}%"
        }

    return Response(response)

def time_to_seconds(time_obj):
    """Helper function to convert HH:MM:SS TimeField to total seconds."""
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second

@api_view(['GET'])
def calculate_operator_efficiency(request):
    """
    Calculate efficiency metrics for operators based on their working hours.
    
    Returns:
        Response with efficiency percentage for each operator
    """
    logs = MachineLog.objects.values("OPERATOR_ID", "START_TIME", "END_TIME")

    response = []
    standard_work_time = 8 * 3600  # 8 hours in seconds

    for log in logs:
        operator_id = log["OPERATOR_ID"]
        start_time = log["START_TIME"]
        end_time = log["END_TIME"]

        start_seconds = time_to_seconds(start_time)
        end_seconds = time_to_seconds(end_time)

        # Handle cases where END_TIME is on the next day
        if end_seconds < start_seconds:
            end_seconds += 24 * 3600  # Add 24 hours in seconds

        actual_work_time = end_seconds - start_seconds
        efficiency = (actual_work_time / standard_work_time) * 100 if standard_work_time > 0 else 0

        response.append({
            "operator": f"Operator {operator_id}",
            "efficiency": round(efficiency, 2)
        })

    return Response(response)

class MachineLogListView(APIView):
    """
    API View to list all machine logs.
    """
    def get(self, request, format=None):
        machine_logs = MachineLog.objects.all()
        serializer = MachineLogSerializer(machine_logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def operator_reports_by_name(request, operator_name):
    """
    Generate detailed performance report for a specific operator.
    
    Parameters:
        operator_name: Name of the operator to generate report for
        from_date (optional): Start date filter (YYYY-MM-DD)
        to_date (optional): End date filter (YYYY-MM-DD)
        
    Returns:
        Comprehensive operator performance metrics including:
        - Production vs non-production time
        - Sewing speed
        - Stitch count
        - Needle runtime
        - Daily breakdown in table format
    """
    try:
        operator = Operator.objects.get(operator_name=operator_name)
        logs = MachineLog.objects.filter(OPERATOR_ID=operator.rfid_card_no)
    except Operator.DoesNotExist:
        return Response({"error": "Operator not found"}, status=404)

    # Get date filters from query parameters
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')

    # Apply date filtering if dates are provided
    if from_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        logs = logs.filter(DATE__gte=from_date)

    if to_date_str:
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        logs = logs.filter(DATE__lte=to_date)

    # Exclude records where OPERATOR_ID is 0 AND MODE is 2
    logs = logs.exclude(Q(OPERATOR_ID=0) & Q(MODE=2))

    # Calculate duration in hours for each log entry with time constraints (8:30 AM to 7:30 PM)
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
        # Calculate adjusted start and end times within working hours (8:30 AM to 7:30 PM)
        adjusted_start_seconds=Case(
            When(start_seconds__lt=8.5*3600, then=Value(8.5*3600)),  # 8:30 AM
            When(start_seconds__gt=19.5*3600, then=Value(19.5*3600)),  # 7:30 PM
            default=F('start_seconds'),
            output_field=FloatField()
        ),
        adjusted_end_seconds=Case(
            When(end_seconds__lt=8.5*3600, then=Value(8.5*3600)),  # 8:30 AM
            When(end_seconds__gt=19.5*3600, then=Value(19.5*3600)),  # 7:30 PM
            default=F('end_seconds'),
            output_field=FloatField()
        ),
        # Calculate duration only for the time within working hours
        duration_hours=Case(
            # Case when both start and end are outside working hours
            When(
                Q(end_seconds__lte=8.5*3600) | Q(start_seconds__gte=19.5*3600),
                then=Value(0)
            ),
            # Case when log spans working hours
            default=ExpressionWrapper(
                (F('adjusted_end_seconds') - F('adjusted_start_seconds')) / 3600,
                output_field=FloatField()
            ),
            output_field=FloatField()
        ),
        reserve_numeric=Cast('RESERVE', output_field=IntegerField())
    ).filter(duration_hours__gt=0)  # Only include logs with positive duration within working hours

    # Filter out break times
    logs = logs.exclude(
        Q(start_seconds__gte=10.5*3600, end_seconds__lte=10.6667*3600) |  # 10:30-10:40
        Q(start_seconds__gte=13.3333*3600, end_seconds__lte=14*3600) |    # 13:20-14:00
        Q(start_seconds__gte=16.3333*3600, end_seconds__lte=16.5*3600)    # 16:20-16:30
    )

    # Calculate total working days and available hours (10 hours per day accounting for breaks)
    total_working_days = logs.values('DATE').distinct().count()
    total_available_hours = total_working_days * 10  # 10 hours per working day

    # Calculate total hours for each mode
    mode_hours = logs.values('MODE').annotate(
        total_hours=Sum('duration_hours')
    )

    # Initialize hour counters
    total_production_hours = 0
    total_meeting_hours = 0
    total_no_feeding_hours = 0
    total_maintenance_hours = 0

    # Sum hours for each mode
    for mode in mode_hours:
        if mode['MODE'] == 1:  # Sewing (Production)
            total_production_hours = mode['total_hours'] or 0
        elif mode['MODE'] == 4:  # Meeting
            total_meeting_hours = mode['total_hours'] or 0
        elif mode['MODE'] == 3:  # No Feeding
            total_no_feeding_hours = mode['total_hours'] or 0
        elif mode['MODE'] == 5:  # Maintenance
            total_maintenance_hours = mode['total_hours'] or 0

    # Calculate total idle hours
    total_idle_hours = max(total_available_hours - (
        total_production_hours + 
        total_no_feeding_hours + 
        total_meeting_hours + 
        total_maintenance_hours
    ), 0)

    # Calculate non-productive time components
    total_non_production_hours = (
        total_no_feeding_hours + 
        total_meeting_hours + 
        total_maintenance_hours + 
        total_idle_hours
    )

    # Calculate percentages
    production_percentage = (total_production_hours / total_available_hours * 100) if total_available_hours > 0 else 0
    npt_percentage = (total_non_production_hours / total_available_hours * 100) if total_available_hours > 0 else 0

    # Calculate Average Sewing Speed
    valid_speed_logs = logs.filter(reserve_numeric__gt=0)
    average_sewing_speed = valid_speed_logs.aggregate(
        avg_speed=Avg('reserve_numeric')
    )['avg_speed'] or 0

    # Calculate total stitch count
    total_stitch_count = logs.aggregate(
        total=Sum('STITCH_COUNT', default=0)
    )['total'] or 0

    # Calculate Needle Runtime metrics
    sewing_logs = logs.filter(MODE=1)  # Only sewing mode logs
    total_needle_runtime = sewing_logs.aggregate(
        total_runtime=Sum('NEEDLE_RUNTIME', default=0)
    )['total_runtime'] or 0
    
    needle_runtime_instances = sewing_logs.count()
    average_needle_runtime = total_needle_runtime / needle_runtime_instances if needle_runtime_instances > 0 else 0
    
    # Convert needle runtime from seconds to hours for percentage calculation
    total_needle_runtime_hours = total_needle_runtime / 3600
    needle_runtime_percentage = (total_needle_runtime_hours / total_production_hours * 100) if total_production_hours > 0 else 0

    # Fetch Table Data (daily breakdown)
    table_data = logs.values('DATE').annotate(
        sewing_hours=Sum(Case(
            When(MODE=1, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        meeting_hours=Sum(Case(
            When(MODE=4, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        no_feeding_hours=Sum(Case(
            When(MODE=3, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        maintenance_hours=Sum(Case(
            When(MODE=5, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        total_stitch_count=Sum('STITCH_COUNT'),
        sewing_speed=Avg(Case(
            When(reserve_numeric__gt=0, then=F('reserve_numeric')),
            default=Value(0),
            output_field=FloatField()
        )),
        needle_runtime=Sum('NEEDLE_RUNTIME')
    ).annotate(
        total_hours=Value(10, output_field=FloatField()),
        idle_hours=Value(10, output_field=FloatField()) - 
                 (F('sewing_hours') + F('meeting_hours') + 
                  F('no_feeding_hours') + F('maintenance_hours')),
        productive_time_percentage=(F('sewing_hours') / 10) * 100,
        npt_percentage=100 - (F('sewing_hours') / 10) * 100
    ).order_by('DATE')

    formatted_table_data = [
        {
            'Date': str(data['DATE']),
            'Operator ID': operator.rfid_card_no,
            'Operator Name': operator_name,
            'Total Hours': round(data['total_hours'], 2),
            'Sewing Hours': round(data['sewing_hours'], 2),
            'Idle Hours': round(max(data['idle_hours'], 0), 2),
            'Meeting Hours': round(data['meeting_hours'], 2),
            'No Feeding Hours': round(data['no_feeding_hours'], 2),
            'Maintenance Hours': round(data['maintenance_hours'], 2),
            'Productive Time in %': round(data['productive_time_percentage'], 2),
            'NPT in %': round(data['npt_percentage'], 2),
            'Sewing Speed': round(data['sewing_speed'], 2),
            'Stitch Count': data['total_stitch_count'],
            'Needle Runtime': data['needle_runtime']
        }
        for data in table_data
    ]

    return Response({
        "totalProductionHours": round(total_production_hours, 2),
        "totalNonProductionHours": round(total_non_production_hours, 2),
        "totalIdleHours": round(total_idle_hours, 2),
        "productionPercentage": round(production_percentage, 2),
        "nptPercentage": round(npt_percentage, 2),
        "averageSewingSpeed": round(average_sewing_speed, 2),
        "totalStitchCount": total_stitch_count,
        "totalNeedleRuntime": round(average_needle_runtime, 2),
        "needleRuntimePercentage": round(needle_runtime_percentage, 2),
        "tableData": formatted_table_data,
        "totalHours": round(total_available_hours, 2),
        "totalPT": round(total_production_hours, 2),
        "totalNPT": round(total_non_production_hours, 2)
    })

from django.db.models import Sum, Case, When, Value, FloatField, F, ExpressionWrapper, Q, IntegerField, Avg, Count
from django.db.models.functions import ExtractHour, ExtractMinute, ExtractSecond, Cast
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
from .models import MachineLog

def process_line_data(logs, line_number):
    """Helper function to process data for a single line"""
    # Calculate total ideal hours (sum of all Mode 2 durations)
    ideal_hours_data = logs.filter(MODE=2).aggregate(
        total_ideal=Sum('duration_hours')
    )
    total_ideal_hours = ideal_hours_data['total_ideal'] or 0

    # Get machine counts per day
    daily_machine_counts = logs.values('DATE').annotate(
        machine_count=Count('MACHINE_ID', distinct=True)
    ).order_by('DATE')

    # Calculate total working days and average machines per day
    total_working_days = len(daily_machine_counts)
    average_machines = sum(item['machine_count'] for item in daily_machine_counts) / total_working_days if total_working_days > 0 else 0

    # Create a dictionary of date to machine count
    date_machine_counts = {item['DATE']: item['machine_count'] for item in daily_machine_counts}

    # Get aggregated data by date
    daily_data = logs.values('DATE').annotate(
        sewing_hours=Sum(Case(
            When(MODE=1, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        no_feeding_hours=Sum(Case(
            When(MODE=3, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        meeting_hours=Sum(Case(
            When(MODE=4, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        maintenance_hours=Sum(Case(
            When(MODE=5, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        idle_hours=Sum(Case(
            When(MODE=2, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        total_stitch_count=Sum('STITCH_COUNT'),
        sewing_speed=Avg(Case(
            When(reserve_numeric__gt=0, then=F('reserve_numeric')),
            default=Value(0),
            output_field=FloatField()
        )),
        needle_runtime=Sum('NEEDLE_RUNTIME')
    ).order_by('DATE')

    # Calculate totals
    total_sewing_hours = 0
    total_no_feeding_hours = 0
    total_meeting_hours = 0
    total_maintenance_hours = 0
    total_idle_hours = 0
    total_stitch_count = 0
    total_needle_runtime = 0
    total_hours = 0  # Sum of all actual hours (PT + NPT)

    formatted_table_data = []
    for data in daily_data:
        date = data['DATE']
        machine_count = date_machine_counts.get(date, 1)
        
        sewing_hours = data['sewing_hours'] or 0
        no_feeding_hours = data['no_feeding_hours'] or 0
        meeting_hours = data['meeting_hours'] or 0
        maintenance_hours = data['maintenance_hours'] or 0
        idle_hours = data['idle_hours'] or 0
        
        # Calculate PT and NPT
        productive_time = sewing_hours
        non_productive_time = no_feeding_hours + meeting_hours + maintenance_hours + idle_hours
        daily_total_hours = productive_time + non_productive_time
        
        # Accumulate to total hours
        total_hours += daily_total_hours
        
        # Calculate percentages
        productive_time_percentage = (productive_time / daily_total_hours * 100) if daily_total_hours > 0 else 0
        non_productive_time_percentage = (non_productive_time / daily_total_hours * 100) if daily_total_hours > 0 else 0
        
        formatted_table_data.append({
            'Date': str(date),
            'Sewing Hours (PT)': round(sewing_hours, 2),
            'No Feeding Hours': round(no_feeding_hours, 2),
            'Meeting Hours': round(meeting_hours, 2),
            'Maintenance Hours': round(maintenance_hours, 2),
            'Idle Hours': round(idle_hours, 2),
            'Total Hours': round(daily_total_hours, 2),
            'Productive Time (PT) %': round(productive_time_percentage, 2),
            'Non-Productive Time (NPT) %': round(non_productive_time_percentage, 2),
            'Sewing Speed': round(data['sewing_speed'], 2),
            'Stitch Count': data['total_stitch_count'],
            'Needle Runtime': data['needle_runtime'],
            'Machine Count': machine_count
        })

        # Accumulate totals
        total_sewing_hours += sewing_hours
        total_no_feeding_hours += no_feeding_hours
        total_meeting_hours += meeting_hours
        total_maintenance_hours += maintenance_hours
        total_idle_hours += idle_hours
        total_stitch_count += data['total_stitch_count'] or 0
        total_needle_runtime += data['needle_runtime'] or 0

    # Calculate overall PT and NPT
    total_productive_time = total_sewing_hours
    total_non_productive_time = (
        total_no_feeding_hours + 
        total_meeting_hours + 
        total_maintenance_hours + 
        total_idle_hours
    )
    
    # Calculate overall percentages
    total_productive_percentage = (total_productive_time / total_hours * 100) if total_hours > 0 else 0
    total_non_productive_percentage = (total_non_productive_time / total_hours * 100) if total_hours > 0 else 0
    utilization_percentage = (total_hours / total_ideal_hours * 100) if total_ideal_hours > 0 else 0

    # Calculate average sewing speed
    valid_speed_logs = logs.filter(reserve_numeric__gt=0)
    average_sewing_speed = valid_speed_logs.aggregate(
        avg_speed=Avg('reserve_numeric')
    )['avg_speed'] or 0

    # Calculate needle runtime percentage
    sewing_logs = logs.filter(MODE=1)
    needle_runtime_instances = sewing_logs.count()
    average_needle_runtime = total_needle_runtime / needle_runtime_instances if needle_runtime_instances > 0 else 0
    total_needle_runtime_hours = total_needle_runtime / 3600
    needle_runtime_percentage = (total_needle_runtime_hours / total_productive_time * 100) if total_productive_time > 0 else 0

    return {
        "lineNumber": line_number,
        "totalIdealHours": round(total_ideal_hours, 2),
        "utilizationPercentage": round(utilization_percentage, 2),
        "totalWorkingDays": total_working_days,
        "averageMachines": round(average_machines, 2),
        "totalHours": round(total_hours, 2),
        "totalProductiveTime": {
            "hours": round(total_productive_time, 2),
            "percentage": round(total_productive_percentage, 2)
        },
        "totalNonProductiveTime": {
            "hours": round(total_non_productive_time, 2),
            "percentage": round(total_non_productive_percentage, 2),
            "breakdown": {
                "noFeedingHours": round(total_no_feeding_hours, 2),
                "meetingHours": round(total_meeting_hours, 2),
                "maintenanceHours": round(total_maintenance_hours, 2),
                "idleHours": round(total_idle_hours, 2)
            }
        },
        "totalStitchCount": total_stitch_count,
        "averageSewingSpeed": round(average_sewing_speed, 2),
        "totalNeedleRuntime": round(average_needle_runtime, 2),
        "needleRuntimePercentage": round(needle_runtime_percentage, 2),
        "tableData": formatted_table_data
    }

@api_view(['GET'])
def line_reports(request, line_number):
    try:
        # Handle "all" case - convert line_number to string first
        line_number_str = str(line_number)
        if line_number_str.lower() == 'all':
            logs = MachineLog.objects.all()
            all_lines = True
        else:
            # Convert back to integer if it's a numeric line number
            line_number = int(line_number_str)
            logs = MachineLog.objects.filter(LINE_NUMB=line_number)
            all_lines = False
    except MachineLog.DoesNotExist:
        return Response({"error": "Data not found"}, status=404)
    except ValueError:
        return Response({"error": "Invalid line number"}, status=400)

    # Get date filters from query parameters
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')

    # Apply date filtering if dates are provided
    if from_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        logs = logs.filter(DATE__gte=from_date)

    if to_date_str:
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        logs = logs.filter(DATE__lte=to_date)

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
        ),
        reserve_numeric=Cast('RESERVE', output_field=IntegerField())
    )

    # Filter for working hours (8:30 AM to 7:30 PM)
    logs = logs.filter(
        start_seconds__gte=30600,  # 8:30 AM (8.5 * 3600)
        end_seconds__lte=70200     # 7:30 PM (19.5 * 3600)
    )

    # Exclude specific break periods (entirely within these ranges)
    logs = logs.exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )

    # For "all" case, we'll group by line number
    if all_lines:
        # Get distinct line numbers
        line_numbers = logs.order_by('LINE_NUMB').values_list('LINE_NUMB', flat=True).distinct()
        
        all_line_reports = []
        summary_data = {
            "totalIdealHours": 0,
            "totalHours": 0,
            "totalProductiveTime": 0,
            "totalNonProductiveTime": 0,
            "totalStitchCount": 0,
            "totalNeedleRuntime": 0,
            "averageSewingSpeed": 0,
            "totalWorkingDays": 0,
            "averageMachines": 0
        }
        
        speed_sum = 0
        speed_count = 0
        needle_runtime_count = 0
        
        for line_num in line_numbers:
            line_logs = logs.filter(LINE_NUMB=line_num)
            
            # Process data for this line (similar to single line processing)
            line_report = process_line_data(line_logs, str(line_num))
            all_line_reports.append(line_report)
            
            # Accumulate summary data
            summary_data["totalIdealHours"] += line_report["totalIdealHours"]
            summary_data["totalHours"] += line_report["totalHours"]
            summary_data["totalProductiveTime"] += line_report["totalProductiveTime"]["hours"]
            summary_data["totalNonProductiveTime"] += line_report["totalNonProductiveTime"]["hours"]
            summary_data["totalStitchCount"] += line_report["totalStitchCount"]
            summary_data["totalNeedleRuntime"] += line_report["totalNeedleRuntime"]
            summary_data["totalWorkingDays"] = max(summary_data["totalWorkingDays"], line_report["totalWorkingDays"])
            summary_data["averageMachines"] += line_report["averageMachines"]
            
            # For averages
            speed_sum += line_report["averageSewingSpeed"] * line_report["totalHours"]
            speed_count += line_report["totalHours"]
            needle_runtime_count += line_report["totalProductiveTime"]["hours"] if line_report["totalProductiveTime"]["hours"] > 0 else 0
        
        # Calculate weighted averages
        if speed_count > 0:
            summary_data["averageSewingSpeed"] = speed_sum / speed_count
        if len(all_line_reports) > 0:
            summary_data["averageMachines"] = summary_data["averageMachines"] / len(all_line_reports)
        if summary_data["totalProductiveTime"] > 0:
            summary_data["needleRuntimePercentage"] = (summary_data["totalNeedleRuntime"] / summary_data["totalProductiveTime"]) * 100
        
        return Response({
            "allLinesReport": all_line_reports,
            "summary": {
                "totalLines": len(all_line_reports),
                "totalIdealHours": round(summary_data["totalIdealHours"], 2),
                "utilizationPercentage": round((summary_data["totalHours"] / summary_data["totalIdealHours"] * 100) if summary_data["totalIdealHours"] > 0 else 0, 2),
                "totalWorkingDays": summary_data["totalWorkingDays"],
                "averageMachines": round(summary_data["averageMachines"], 2),
                "totalHours": round(summary_data["totalHours"], 2),
                "totalProductiveTime": {
                    "hours": round(summary_data["totalProductiveTime"], 2),
                    "percentage": round((summary_data["totalProductiveTime"] / summary_data["totalHours"] * 100) if summary_data["totalHours"] > 0 else 0, 2)
                },
                "totalNonProductiveTime": {
                    "hours": round(summary_data["totalNonProductiveTime"], 2),
                    "percentage": round((summary_data["totalNonProductiveTime"] / summary_data["totalHours"] * 100) if summary_data["totalHours"] > 0 else 0, 2)
                },
                "totalStitchCount": summary_data["totalStitchCount"],
                "averageSewingSpeed": round(summary_data["averageSewingSpeed"], 2),
                "totalNeedleRuntime": round(summary_data["totalNeedleRuntime"], 2),
                "needleRuntimePercentage": round(summary_data.get("needleRuntimePercentage", 0), 2)
            }
        })
    else:
        # Process single line data
        line_report = process_line_data(logs, str(line_number))
        return Response(line_report)

@api_view(['GET'])
def machine_reports(request, machine_id):
    """
    Generate detailed performance report for a specific machine.
    
    Parameters:
        machine_id: Machine ID to generate report for
        from_date (optional): Start date filter (YYYY-MM-DD)
        to_date (optional): End date filter (YYYY-MM-DD)
        
    Returns:
        Comprehensive machine performance metrics including:
        - Available vs utilized hours
        - Productive vs non-productive time
        - Stitch count
        - Needle runtime
        - Daily breakdown in table format
    """
    try:
        logs = MachineLog.objects.filter(MACHINE_ID=machine_id)
    except MachineLog.DoesNotExist:
        return Response({"error": "Machine not found"}, status=404)

    # Get date filters from query parameters
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')

    # Apply date filtering if dates are provided
    if from_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        logs = logs.filter(DATE__gte=from_date)

    if to_date_str:
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        logs = logs.filter(DATE__lte=to_date)

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
        ),
        reserve_numeric=Cast('RESERVE', output_field=IntegerField())
    )

    # Filter for working hours (8:30 AM to 7:30 PM)
    logs = logs.filter(
        start_seconds__gte=30600,  # 8:30 AM (8.5 * 3600)
        end_seconds__lte=70200     # 7:30 PM (19.5 * 3600)
    )

    # Exclude specific break periods (entirely within these ranges)
    logs = logs.exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )

    # Calculate total working days and available hours (11 hours per day)
    distinct_dates = logs.dates('DATE', 'day')
    total_working_days = distinct_dates.count()
    total_available_hours = total_working_days * 11

    # Get aggregated data by date
    daily_data = logs.values('DATE').annotate(
        sewing_hours=Sum(Case(
            When(MODE=1, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        no_feeding_hours=Sum(Case(
            When(MODE=3, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        meeting_hours=Sum(Case(
            When(MODE=4, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        maintenance_hours=Sum(Case(
            When(MODE=5, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        idle_hours=Sum(Case(
            When(MODE=2, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        total_stitch_count=Sum('STITCH_COUNT'),
        sewing_speed=Avg(Case(
            When(reserve_numeric__gt=0, then=F('reserve_numeric')),
            default=Value(0),
            output_field=FloatField()
        )),
        needle_runtime=Sum('NEEDLE_RUNTIME')
    ).order_by('DATE')

    # Calculate totals
    total_sewing_hours = 0
    total_no_feeding_hours = 0
    total_meeting_hours = 0
    total_maintenance_hours = 0
    total_idle_hours = 0
    total_stitch_count = 0
    total_needle_runtime = 0

    formatted_table_data = []
    for data in daily_data:
        sewing_hours = data['sewing_hours'] or 0
        no_feeding_hours = data['no_feeding_hours'] or 0
        meeting_hours = data['meeting_hours'] or 0
        maintenance_hours = data['maintenance_hours'] or 0
        idle_hours = data['idle_hours'] or 0
        
        # Calculate PT and NPT according to new requirements
        productive_time = sewing_hours
        non_productive_time = no_feeding_hours + meeting_hours + maintenance_hours + idle_hours
        total_hours = productive_time + non_productive_time
        
        # Calculate percentages
        productive_time_percentage = (productive_time / total_hours * 100) if total_hours > 0 else 0
        non_productive_time_percentage = (non_productive_time / total_hours * 100) if total_hours > 0 else 0
        
        formatted_table_data.append({
            'Date': str(data['DATE']),
            'Sewing Hours (PT)': round(sewing_hours, 2),
            'No Feeding Hours': round(no_feeding_hours, 2),
            'Meeting Hours': round(meeting_hours, 2),
            'Maintenance Hours': round(maintenance_hours, 2),
            'Idle Hours': round(idle_hours, 2),
            'Total Hours': round(total_hours, 2),
            'Productive Time (PT) %': round(productive_time_percentage, 2),
            'Non-Productive Time (NPT) %': round(non_productive_time_percentage, 2),
            'Sewing Speed': round(data['sewing_speed'], 2),
            'Stitch Count': data['total_stitch_count'],
            'Needle Runtime': data['needle_runtime'],
            'Machine ID': machine_id
        })

        # Accumulate totals
        total_sewing_hours += sewing_hours
        total_no_feeding_hours += no_feeding_hours
        total_meeting_hours += meeting_hours
        total_maintenance_hours += maintenance_hours
        total_idle_hours += idle_hours
        total_stitch_count += data['total_stitch_count'] or 0
        total_needle_runtime += data['needle_runtime'] or 0

    # Calculate overall PT and NPT
    total_productive_time = total_sewing_hours
    total_non_productive_time = (
        total_no_feeding_hours + 
        total_meeting_hours + 
        total_maintenance_hours + 
        total_idle_hours
    )
    total_hours = total_productive_time + total_non_productive_time
    
    # Calculate overall percentages
    total_productive_percentage = (total_productive_time / total_hours * 100) if total_hours > 0 else 0
    total_non_productive_percentage = (total_non_productive_time / total_hours * 100) if total_hours > 0 else 0

    return Response({
        "machineId": machine_id,
        "totalAvailableHours": total_available_hours,
        "totalWorkingDays": total_working_days,
        "totalHours": round(total_hours, 2),
        "totalProductiveTime": {
            "hours": round(total_productive_time, 2),
            "percentage": round(total_productive_percentage, 2)
        },
        "totalNonProductiveTime": {
            "hours": round(total_non_productive_time, 2),
            "percentage": round(total_non_productive_percentage, 2),
            "breakdown": {
                "noFeedingHours": round(total_no_feeding_hours, 2),
                "meetingHours": round(total_meeting_hours, 2),
                "maintenanceHours": round(total_maintenance_hours, 2),
                "idleHours": round(total_idle_hours, 2)
            }
        },
        "totalStitchCount": total_stitch_count,
        "totalNeedleRuntime": round(total_needle_runtime, 2),
        "tableData": formatted_table_data
    })

@api_view(['GET'])
def operator_reports_all(request):
    """
    Generate summary performance reports for all operators.
    
    Parameters:
        from_date (optional): Start date filter (YYYY-MM-DD)
        to_date (optional): End date filter (YYYY-MM-DD)
        
    Returns:
        List of operator performance summaries including:
        - Operator ID and name
        - Production vs non-production hours
        - Efficiency percentages
    """
    operators = Operator.objects.all()
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')

    all_operators_data = []

    for operator in operators:
        logs = MachineLog.objects.filter(OPERATOR_ID=operator.rfid_card_no)

        # Apply date filtering if dates are provided
        if from_date_str:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            logs = logs.filter(DATE__gte=from_date)

        if to_date_str:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            logs = logs.filter(DATE__lte=to_date)

        # Exclude records where OPERATOR_ID is 0 AND MODE is 2
        logs = logs.exclude(Q(OPERATOR_ID=0) & Q(MODE=2))

        # Calculate duration in hours
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
            adjusted_start_seconds=Case(
                When(start_seconds__lt=8.5 * 3600, then=Value(8.5 * 3600)),
                When(start_seconds__gt=19.5 * 3600, then=Value(19.5 * 3600)),
                default=F('start_seconds'),
                output_field=FloatField()
            ),
            adjusted_end_seconds=Case(
                When(end_seconds__lt=8.5 * 3600, then=Value(8.5 * 3600)),
                When(end_seconds__gt=19.5 * 3600, then=Value(19.5 * 3600)),
                default=F('end_seconds'),
                output_field=FloatField()
            ),
            duration_hours=Case(
                When(
                    Q(end_seconds__lte=8.5 * 3600) | Q(start_seconds__gte=19.5 * 3600),
                    then=Value(0)
                ),
                default=ExpressionWrapper(
                    (F('adjusted_end_seconds') - F('adjusted_start_seconds')) / 3600,
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        ).filter(duration_hours__gt=0)

        # Filter out break times
        logs = logs.exclude(
            Q(start_seconds__gte=10.5 * 3600, end_seconds__lte=10.6667 * 3600) |
            Q(start_seconds__gte=13.3333 * 3600, end_seconds__lte=14 * 3600) |
            Q(start_seconds__gte=16.3333 * 3600, end_seconds__lte=16.5 * 3600)
        )

        # Calculate metrics
        total_working_days = logs.values('DATE').distinct().count()
        total_available_hours = total_working_days * 10

        mode_hours = logs.values('MODE').annotate(
            total_hours=Sum('duration_hours')
        )

        total_production_hours = sum(
            mode['total_hours'] for mode in mode_hours if mode['MODE'] == 1
        )
        total_non_production_hours = total_available_hours - total_production_hours

        production_percentage = (total_production_hours / total_available_hours * 100) if total_available_hours > 0 else 0
        npt_percentage = 100 - production_percentage

        all_operators_data.append({
            "operatorId": operator.rfid_card_no,
            "operatorName": operator.operator_name,
            "totalProductionHours": round(total_production_hours, 2),
            "totalNonProductionHours": round(total_non_production_hours, 2),
            "productionPercentage": round(production_percentage, 2),
            "nptPercentage": round(npt_percentage, 2),
        })

    return Response(all_operators_data)