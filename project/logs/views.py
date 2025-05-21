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
from .models import MachineLog, DuplicateLog, ModeMessage, Operator, OperatorAFL
from .serializers import MachineLogSerializer
from .constants import MODES

# ======================================
# Machine Data Management Endpoints
# ======================================

@api_view(['POST'])
def log_machine_data(request):
    """
    View to handle machine data logging with updated Tx Log ID and Str Log ID conditions.
    
    - Tx_LOGID:
      - If > 1000, subtracts 1000 and stores only the adjusted value.
      - Checks if the adjusted Log ID exists for the same Machine ID, Date, Start Time, and End Time before saving.
    - Str_LOGID:
      - If > 1000, subtracts 1000 and stores only the adjusted value.
      - Checks if the adjusted Log ID exists for the same Machine ID, Date, Start Time, and End Time before saving.
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

    # Extract Log IDs, Machine ID, Date, Start Time and End Time
    tx_log_id = validated_data.get("Tx_LOGID")
    str_log_id = validated_data.get("Str_LOGID")
    machine_id = validated_data.get("MACHINE_ID")
    log_date = validated_data.get("DATE")  # Assumes DATE is provided and validated in serializer
    start_time = validated_data.get("START_TIME")
    end_time = validated_data.get("END_TIME")

    if machine_id is None:
        return Response({"message": "MACHINE_ID is required"}, status=400)

    if log_date is None:
        return Response({"message": "DATE is required"}, status=400)
        
    if start_time is None:
        return Response({"message": "START_TIME is required"}, status=400)
        
    if end_time is None:
        return Response({"message": "END_TIME is required"}, status=400)
    
    # Tx_LOGID Handling
    if tx_log_id is not None:
        try:
            tx_log_id = int(tx_log_id)  # Convert to integer
        except ValueError:
            return Response({"message": "Invalid Tx_LOGID format"}, status=400)
        
        if tx_log_id > 1000:
            adjusted_tx_log_id = tx_log_id - 1000  # Subtract 1000
            
            # Check if the adjusted TX Log ID exists for the same MACHINE_ID, DATE, START_TIME, and END_TIME
            if MachineLog.objects.filter(
                Tx_LOGID=adjusted_tx_log_id,
                MACHINE_ID=machine_id,
                DATE=log_date,
                START_TIME=start_time,
                END_TIME=end_time
            ).exists():
                return Response({
                    "code": 200,
                    "message": "Log saved successfully"
                }, status=200)
            
            # Keep the original Tx_LOGID value (do not subtract 1000)

    # Str_LOGID Handling
    if str_log_id is not None:
        try:
            str_log_id = int(str_log_id)  # Convert to integer
        except ValueError:
            return Response({"message": "Invalid Str_LOGID format"}, status=400)

        if str_log_id > 1000:
            adjusted_str_log_id = str_log_id - 1000  # Subtract 1000

            # Check if the adjusted STR Log ID exists for the same MACHINE_ID, DATE, START_TIME, and END_TIME
            if MachineLog.objects.filter(
                Str_LOGID=adjusted_str_log_id,
                MACHINE_ID=machine_id,
                DATE=log_date,
                START_TIME=start_time,
                END_TIME=end_time
            ).exists():
                return Response({
                    "code": 200,
                    "message": "Log saved successfully"
                }, status=200)

            # Update validated data with adjusted Str_LOGID
            validated_data["Str_LOGID"] = adjusted_str_log_id

    # Save the log data
    MachineLog.objects.create(**validated_data)

    return Response({
        "code": 200,
        "message": "Log saved successfully",
    }, status=200)


# ======================================
# Logs Retrieval Endpoints
# ======================================

@api_view(['GET'])
def get_machine_logs(request):
    """
    View to retrieve machine logs with optional date filtering.
    
    Parameters:
        - from_date (query param): Optional. Filter logs created on or after this date
        - to_date (query param): Optional. Filter logs created on or before this date
    
    Returns:
        JSON response with indexed list of machine logs
    """
    # Get date filter parameters from the request
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    
    # Query all logs, ordered by creation date (newest first)
    logs = MachineLog.objects.all().order_by('-created_at')
    
    # Apply date filters if provided
    if from_date:
        logs = logs.filter(DATE__gte=from_date)
    if to_date:
        logs = logs.filter(DATE__lte=to_date)
    
    # Serialize the logs to JSON
    serialized_logs = MachineLogSerializer(logs, many=True).data

    # Add indexing (starting from 1) for easier reference
    for idx, log in enumerate(serialized_logs, start=1):
        log['index'] = idx

    return Response(serialized_logs)


@api_view(['POST'])
def user_login(request):
    """
    View to handle user login and authenticate using Django's built-in authentication system.
    
    Validates and processes incoming user login data:
    - Authenticates the user
    - Returns a token if authentication is successful
    
    Parameters:
        - username: User's username
        - password: User's password
    
    Returns:
        Response with status and message, and token if authentication successful
    """
    data = request.data
    username = data.get('username')
    password = data.get('password')

    # Validate required fields
    if not username or not password:
        return Response({"message": "Username and password are required"}, status=400)

    # Authenticate user
    user = authenticate(username=username, password=password)
    if user is not None:
        # Authentication successful, generate token
        token, created = Token.objects.get_or_create(user=user)
        return Response({"message": "Login successful", "token": token.key}, status=200)
    else:
        # Authentication failed
        return Response({"message": "Invalid credentials"}, status=400)


# ======================================
# Analytics and Reporting Endpoints
# ======================================

@api_view(['GET'])
def get_underperforming_operators(request):
    """
    Fetches the count of underperforming operators.
    
    Criteria:
    - Operators in non-production modes (mode 3, 4, 5)
    - Counts the number of unique operator_id values

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


# ======================================
# Helper Functions
# ======================================

def time_to_seconds(time_obj):
    """
    Helper function to convert HH:MM:SS TimeField to total seconds.
    
    Parameters:
        time_obj: A time object with hour, minute, and second attributes
        
    Returns:
        Total seconds as an integer
    """
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


# ======================================
# Machine Log List View
# ======================================

# ======================================
# Machine Log List View
# ======================================

class MachineLogListView(APIView):
    """
    API View to list all machine logs with optional filters.
    
    This class-based view provides a RESTful endpoint for retrieving
    machine logs with pagination and sorting capabilities.
    """
    def get(self, request, format=None):
        """
        GET method to retrieve all machine logs.
        
        The method supports query parameters for pagination:
        - page: Page number to retrieve
        - page_size: Number of records per page
        
        Returns:
            Serialized JSON response of machine logs with pagination metadata
        """
        machine_logs = MachineLog.objects.all()
        serializer = MachineLogSerializer(machine_logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ======================================
# Operator Report Endpoints
# ======================================

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
        if operator_name == "All":
            operator = Operator.objects.all()
            logs = MachineLog.objects.all()
        else:
            # Fetch operator by name
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

    # Calculate duration in hours for each log entry with time constraints (8:25 AM to 7:35 PM)
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
        # Calculate adjusted start and end times within working hours (8:25 AM to 7:35 PM)
        adjusted_start_seconds=Case(
            When(start_seconds__lt=30300, then=Value(30300)),  # 8:25 AM (8.416667 * 3600)
            When(start_seconds__gt=70500, then=Value(70500)),  # 7:35 PM (19.583333 * 3600)
            default=F('start_seconds'),
            output_field=FloatField()
        ),
        adjusted_end_seconds=Case(
            When(end_seconds__lt=30300, then=Value(30300)),  # 8:25 AM (8.416667 * 3600)
            When(end_seconds__gt=70500, then=Value(70500)),  # 7:35 PM (19.583333 * 3600)
            default=F('end_seconds'),
            output_field=FloatField()
        ),
        # Calculate duration only for the time within working hours
        duration_hours=Case(
            # Case when both start and end are outside working hours
            When(
                Q(end_seconds__lte=30300) | Q(start_seconds__gte=70500),
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

    # Filter for working hours (8:25 AM to 7:35 PM)
    logs = logs.filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
    )

    # Exclude specific break periods (entirely within these ranges)
    logs = logs.exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )

    # Calculate total working days
    distinct_dates = logs.values('DATE').distinct()
    total_working_days = distinct_dates.count()
    
    # Get today's date
    today = datetime.now().date()
    
    # Calculate the total available hours dynamically
    total_available_hours = 0
    
    for entry in distinct_dates:
        date_entry = entry['DATE']
        
        # Check if this date is today
        if date_entry == today:
            # For today, calculate hours from 8:25 AM to current time
            current_time = datetime.now().time()
            current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
            
            # Start time is 8:25 AM (30300 seconds)
            start_seconds = 30300
            
            # End time is the minimum of current time or end of workday (7:35 PM)
            end_seconds = min(current_seconds, 70500)
            
            # If current time is before workday start, set hours to 0
            if current_seconds < start_seconds:
                day_hours = 0
            else:
                # Calculate hours for today
                day_hours = (end_seconds - start_seconds) / 3600
                
                # Subtract break times if they've already passed
                if current_seconds > 38400:  # After 10:40 AM
                    day_hours -= 10/60  # Subtract 10 minutes for first break
                
                if current_seconds > 50400:  # After 2:00 PM
                    day_hours -= 40/60  # Subtract 40 minutes for second break
                
                if current_seconds > 59400:  # After 4:30 PM
                    day_hours -= 10/60  # Subtract 10 minutes for third break
        else:
            # For past dates, use the full day hours (8:25 AM to 7:35 PM minus breaks)
            day_hours = (70500 - 30300) / 3600 - 1  # 10.17 hours
        
        total_available_hours += day_hours

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

    # Fetch Table Data (daily breakdown) - only group by DATE and OPERATOR_ID
    table_data = logs.values('DATE', 'OPERATOR_ID').annotate(
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
    ).order_by('DATE', 'OPERATOR_ID')
    
    mode_description_mapping = MODES

    # Now format the data, fetching operator name from the Operator model
    formatted_table_data = []
    for data in table_data:
        # Get operator details from the Operator model
        try:
            operator = Operator.objects.get(rfid_card_no=data['OPERATOR_ID'])
            operator_name = operator.operator_name
            rfid_card_no = operator.rfid_card_no
        except Operator.DoesNotExist:
            operator_name = "Unknown"
            rfid_card_no = "Unknown"
        
        # Get the date from the data
        entry_date = data['DATE']
        
        # Calculate total available hours for this day
        day_total_hours = 0
        
        # Check if this date is today
        if entry_date == today:
            # For today, calculate hours from 8:25 AM to current time
            current_time = datetime.now().time()
            current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
            
            # Start time is 8:25 AM (30300 seconds)
            start_seconds = 30300
            
            # End time is the minimum of current time or end of workday (7:35 PM)
            end_seconds = min(current_seconds, 70500)
            
            # If current time is before workday start, set hours to 0
            if current_seconds < start_seconds:
                day_total_hours = 0
            else:
                # Calculate hours for today
                day_total_hours = (end_seconds - start_seconds) / 3600
                
                # Subtract break times if they've already passed
                if current_seconds > 38400:  # After 10:40 AM
                    day_total_hours -= 10/60  # Subtract 10 minutes for first break
                
                if current_seconds > 50400:  # After 2:00 PM
                    day_total_hours -= 40/60  # Subtract 40 minutes for second break
                
                if current_seconds > 59400:  # After 4:30 PM
                    day_total_hours -= 10/60  # Subtract 10 minutes for third break
        else:
            # For past dates, use the full day hours (8:25 AM to 7:35 PM minus breaks)
            day_total_hours = (70500 - 30300) / 3600 - 1  # 10.17 hours
        
        # Calculate sewing and non-sewing hours
        sewing_hours = data['sewing_hours'] or 0
        meeting_hours = data['meeting_hours'] or 0
        no_feeding_hours = data['no_feeding_hours'] or 0
        maintenance_hours = data['maintenance_hours'] or 0
        
        # Calculate idle hours as the remainder
        idle_hours = max(day_total_hours - (sewing_hours + meeting_hours + no_feeding_hours + maintenance_hours), 0)
        
        # Calculate percentages
        productive_time_percentage = (sewing_hours / day_total_hours * 100) if day_total_hours > 0 else 0
        npt_percentage = 100 - productive_time_percentage
        
        formatted_table_data.append({
            'Date': str(entry_date),
            'Operator ID': data['OPERATOR_ID'],
            'Operator Name': operator_name,
            'Total Hours': round(day_total_hours, 2),
            'Sewing Hours': round(sewing_hours, 2),
            'Idle Hours': round(idle_hours, 2),
            'Meeting Hours': round(meeting_hours, 2),
            'No Feeding Hours': round(no_feeding_hours, 2),
            'Maintenance Hours': round(maintenance_hours, 2),
            'Productive Time in %': round(productive_time_percentage, 2),
            'NPT in %': round(npt_percentage, 2),
            'Sewing Speed': round(data['sewing_speed'] or 0, 2),
            'Stitch Count': data['total_stitch_count'] or 0,
            'Needle Runtime': data['needle_runtime'] or 0
        })

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


# ======================================
# Line Reports and Processing Functions
# ======================================

def process_line_data(logs, line_number):
    """
    Helper function to process and analyze data for a single production line.
    
    This function performs complex calculations on machine logs to generate
    comprehensive metrics for production line performance analysis including:
    - Work hours and utilization rates
    - Productive vs non-productive time
    - Sewing speeds and efficiency metrics
    - Machine counts and operational statistics
    
    Parameters:
        logs: QuerySet of MachineLog objects filtered for a specific line
        line_number: The line number being processed (string or int)
        
    Returns:
        dict: Dictionary containing processed analytics data with the following keys:
            - lineNumber: The line identifier
            - totalIdealHours: Maximum possible working hours
            - utilizationPercentage: Percentage of ideal hours actually utilized
            - totalWorkingDays: Number of days with activity
            - averageMachines: Average number of machines in use
            - totalHours: Actual working hours
            - totalProductiveTime: Dict with hours and percentage
            - totalNonProductiveTime: Dict with hours, percentage and breakdown
            - totalStitchCount: Total stitches made
            - averageSewingSpeed: Average sewing speed
            - totalNeedleRuntime: Total needle runtime
            - needleRuntimePercentage: Percentage of productive time with needle running
            - tableData: Daily breakdown of all metrics
        Dictionary containing processed metrics and table data for the line
    """
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

# ======================================
# Line Reports and Processing Functions
# ======================================

@api_view(['GET'])
def line_reports(request, line_number):
    """
    Generate a comprehensive report for a specific production line or all lines.
    
    This endpoint provides detailed metrics for production lines including:
    - Working hours and utilization
    - Productive vs. non-productive time
    - Stitch counts and sewing speeds
    - Machine usage and efficiency
    
    Parameters:
        line_number (str/int): The line number to report on, or 'all' for all lines
        from_date (query param): Start date for the report (YYYY-MM-DD)
        to_date (query param): End date for the report (YYYY-MM-DD)
    
    Returns:
        Response: JSON containing line performance data or appropriate error
    """
    try:
        # Get valid operator IDs from Operator model
        valid_operators = Operator.objects.values_list('rfid_card_no', flat=True)
        
        # Handle "all" case - convert line_number to string first
        line_number_str = str(line_number)
        if line_number_str.lower() == 'all':
            logs = MachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
            all_lines = True
        else:
            # Convert back to integer if it's a numeric line number
            line_number = int(line_number_str)
            logs = MachineLog.objects.filter(LINE_NUMB=line_number, OPERATOR_ID__in=valid_operators)
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

    # Filter for working hours (8:25 AM to 7:35 PM)
    logs = logs.filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
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


# ======================================
# Machine Reports and Processing Functions
# ======================================

def process_machine_data(logs, machine_id):
    """
    Helper function to process and analyze data for a single machine.
    
    This function performs complex calculations on machine logs to generate
    comprehensive metrics for machine performance analysis including:
    - Working hours and efficiency metrics
    - Productive vs non-productive time
    - Sewing speeds and stitch counts
    - Operator usage statistics
    
    Parameters:
        logs: QuerySet of MachineLog objects filtered for a specific machine
        machine_id: The machine ID being processed (string or int)
        
    Returns:
        dict: Dictionary containing processed analytics data with the following keys:
            - machineId: The machine identifier
            - totalWorkingDays: Number of days the machine was active
            - totalHours: Total recorded working hours
            - totalProductiveTime: Dict with hours and percentage
            - totalNonProductiveTime: Dict with hours, percentage and breakdown
            - totalStitchCount: Total stitches made
            - averageSewingSpeed: Average sewing speed
            - totalNeedleRuntime: Total needle runtime hours
            - tableData: Daily breakdown of all metrics
    """
    # Calculate total working days and available hours (11 hours per day)
    distinct_dates = logs.dates('DATE', 'day')
    total_working_days = distinct_dates.count()
    total_available_hours = total_working_days * 11

    # Get aggregated data by date with operation counts
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
        sewing_operation_count=Sum(Case(
            When(MODE=1, then=F('STITCH_COUNT')),
            default=Value(0),
            output_field=IntegerField()
        )),
        sewing_skip_count=Sum(Case(
            When(MODE=1, then=F('NEEDLE_RUNTIME')),
            default=Value(0),
            output_field=IntegerField()
        )),
        rework_operation_count=Sum(Case(
            When(MODE=3, then=F('STITCH_COUNT')),
            default=Value(0),
            output_field=IntegerField()
        )),
        rework_stitch_count=Sum(Case(
            When(MODE=3, then=F('NEEDLE_RUNTIME')),
            default=Value(0),
            output_field=IntegerField()
        )),
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
    total_sewing_operation_count = 0
    total_sewing_skip_count = 0
    total_rework_operation_count = 0
    total_rework_stitch_count = 0
    total_hours = 0

    formatted_table_data = []
    for data in daily_data:
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
            'Date': str(data['DATE']),
            'Sewing Hours (PT)': round(sewing_hours, 2),
            'Sewing Operation Count': data['sewing_operation_count'] or 0,
            'Sewing Skip Count': data['sewing_skip_count'] or 0,
            'Rework Operation Count': data['rework_operation_count'] or 0,
            'Rework Stitch Count': data['rework_stitch_count'] or 0,
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
        total_sewing_operation_count += data['sewing_operation_count'] or 0
        total_sewing_skip_count += data['sewing_skip_count'] or 0
        total_rework_operation_count += data['rework_operation_count'] or 0
        total_rework_stitch_count += data['rework_stitch_count'] or 0

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

    # Calculate average sewing speed
    valid_speed_logs = logs.filter(reserve_numeric__gt=0)
    average_sewing_speed = valid_speed_logs.aggregate(
        avg_speed=Avg('reserve_numeric')
    )['avg_speed'] or 0

    return {
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
        "totalSewingOperationCount": total_sewing_operation_count,
        "totalSewingSkipCount": total_sewing_skip_count,
        "totalReworkOperationCount": total_rework_operation_count,
        "totalReworkStitchCount": total_rework_stitch_count,
        "averageSewingSpeed": round(average_sewing_speed, 2),
        "totalNeedleRuntime": round(total_needle_runtime, 2),
        "tableData": formatted_table_data
    }

# ======================================
# Machine Reports and Processing Functions
# ======================================

@api_view(['GET'])
def machine_reports(request, machine_id):
    """
    Generate a comprehensive report for a specific machine or all machines.
    
    This endpoint analyzes machine performance data including:
    - Working hours and efficiency
    - Productive vs. non-productive time breakdown
    - Stitch counts and sewing speeds
    - Operator utilization of the machine
    
    Parameters:
        machine_id (str/int): The machine ID to report on, or 'all' for all machines
        from_date (query param): Start date for the report (YYYY-MM-DD)
        to_date (query param): End date for the report (YYYY-MM-DD)
    
    Returns:
        Response: JSON containing machine performance data or appropriate error
    """
    try:
        # Get valid operator IDs from Operator model
        valid_operators = Operator.objects.values_list('rfid_card_no', flat=True)
        
        # Handle "all" case - convert machine_id to string first
        machine_id_str = str(machine_id)
        if machine_id_str.lower() == 'all':
            logs = MachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
            all_machines = True
        else:
            logs = MachineLog.objects.filter(MACHINE_ID=machine_id, OPERATOR_ID__in=valid_operators)
            all_machines = False
    except MachineLog.DoesNotExist:
        return Response({"error": "Data not found"}, status=404)
    except ValueError:
        return Response({"error": "Invalid machine ID"}, status=400)

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

    # Filter for working hours (8:25 AM to 7:35 PM)
    logs = logs.filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
    )

    # Exclude specific break periods (entirely within these ranges)
    logs = logs.exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )

    # For "all" case, we'll group by machine ID
    if all_machines:
        # Get distinct machine IDs
        machine_ids = logs.order_by('MACHINE_ID').values_list('MACHINE_ID', flat=True).distinct()
        
        all_machine_reports = []
        
        for machine_id in machine_ids:
            machine_logs = logs.filter(MACHINE_ID=machine_id)
            
            # Process data for this machine
            machine_report = process_machine_data(machine_logs, machine_id)
            all_machine_reports.append(machine_report)
        
        return Response({
            "allMachinesReport": all_machine_reports,
            "totalMachines": len(all_machine_reports)
        })
    else:
        # Process single machine data
        machine_report = process_machine_data(logs, machine_id)
        return Response(machine_report)


@api_view(['GET'])
def all_machines_report(request):
    try:
        # Get valid operator IDs from Operator model
        valid_operators = Operator.objects.values_list('rfid_card_no', flat=True)
        logs = MachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

    # Get date filters from query parameters
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')

    # Apply date filtering if dates are provided
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            logs = logs.filter(DATE__gte=from_date)
        except ValueError:
            return Response({"error": "Invalid from_date format. Use YYYY-MM-DD"}, status=400)

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            logs = logs.filter(DATE__lte=to_date)
        except ValueError:
            return Response({"error": "Invalid to_date format. Use YYYY-MM-DD"}, status=400)

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
    ).filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
    ).exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )

    # Get distinct machine IDs
    machine_ids = logs.order_by('MACHINE_ID').values_list('MACHINE_ID', flat=True).distinct()
    
    all_machine_reports = []
    
    for machine_id in machine_ids:
        machine_logs = logs.filter(MACHINE_ID=machine_id)
        
        # Process data for this machine
        try:
            machine_report = process_machine_data(machine_logs, machine_id)
            all_machine_reports.append(machine_report)
        except Exception as e:
            print(f"Error processing machine {machine_id}: {str(e)}")
            continue
    
    return Response({
        "allMachinesReport": all_machine_reports,
        "totalMachines": len(all_machine_reports),
        "from_date": from_date_str,
        "to_date": to_date_str
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

# Use imports and MODES constant from the top of the file


# ======================================
# Filtering and Lookup Endpoints
# ======================================

@api_view(['GET'])
def filter_logs(request):
    line_number = request.GET.get('line_number')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    queryset = MachineLog.objects.all()
    
    if line_number and line_number.lower() != 'all':
        queryset = queryset.filter(LINE_NUMB=line_number)
    
    if from_date:
        queryset = queryset.filter(DATE__gte=from_date)
    
    if to_date:
        queryset = queryset.filter(DATE__lte=to_date)
    
    # Prefetch operator data to optimize queries
    logs = list(queryset)
    operator_ids = set(log.OPERATOR_ID for log in logs if log.OPERATOR_ID != "0")
    operators = Operator.objects.filter(rfid_card_no__in=operator_ids)
    operator_map = {op.rfid_card_no: op.operator_name for op in operators}
    
    data = []
    for log in logs:
        log_data = {
            **log.__dict__,
            'mode_description': MODES.get(log.MODE, 'Unknown mode'),
            'operator_name': operator_map.get(log.OPERATOR_ID, "") if log.OPERATOR_ID != "0" else ""
        }
        # Remove Django internal fields
        log_data.pop('_state', None)
        data.append(log_data)
    
    return Response(data)


@api_view(['GET'])
def filter_logs_by_machine_id(request):
    machine_id = request.GET.get('machine_id')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    queryset = MachineLog.objects.all()
    
    if machine_id and machine_id.lower() != 'all':
        queryset = queryset.filter(MACHINE_ID=machine_id)
    
    if from_date:
        queryset = queryset.filter(DATE__gte=from_date)
    
    if to_date:
        queryset = queryset.filter(DATE__lte=to_date)
    
    # Prefetch operator data to optimize queries
    logs = list(queryset)
    operator_ids = set(log.OPERATOR_ID for log in logs if log.OPERATOR_ID != "0")
    operators = Operator.objects.filter(rfid_card_no__in=operator_ids)
    operator_map = {op.rfid_card_no: op.operator_name for op in operators}
    
    data = []
    for log in logs:
        log_data = {
            **log.__dict__,
            'mode_description': MODES.get(log.MODE, 'Unknown mode'),
            'operator_name': operator_map.get(log.OPERATOR_ID, "") if log.OPERATOR_ID != "0" else ""
        }
        # Remove Django internal fields
        log_data.pop('_state', None)
        data.append(log_data)
    
    return Response(data)

@api_view(['GET'])
def get_line_numbers(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if not from_date or not to_date:
        return Response({"error": "Both from_date and to_date are required"}, status=400)
    
    queryset = MachineLog.objects.filter(
        DATE__gte=from_date,
        DATE__lte=to_date
    ).values_list('LINE_NUMB', flat=True).distinct()
    
    line_numbers = sorted(list(queryset))
    return Response({"line_numbers": line_numbers})

@api_view(['GET'])
def get_machine_ids(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if not from_date or not to_date:
        return Response({"error": "Both from_date and to_date are required"}, status=400)
    
    queryset = MachineLog.objects.filter(
        DATE__gte=from_date,
        DATE__lte=to_date
    ).values_list('MACHINE_ID', flat=True).distinct()
    
    machine_ids = sorted(list(queryset))
    return Response({"machine_ids": machine_ids})







# views.py
# Use imports and MODES constant from the top of the file

@api_view(['GET'])
def get_operator_ids(request):
    """
    Retrieve a list of all unique operator IDs within the specified date range.
    
    This endpoint is typically used to populate dropdown lists in the frontend or
    to validate operator selection in other API calls.
    
    Parameters:
        from_date (str): Start date for filtering operators (YYYY-MM-DD)
        to_date (str): End date for filtering operators (YYYY-MM-DD)
    
    Returns:
        Response: JSON containing a sorted list of operator IDs
                 or an error if date parameters are missing
    """
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if not from_date or not to_date:
        return Response({"error": "Both from_date and to_date are required"}, status=400)
    
    queryset = MachineLog.objects.filter(
        DATE__gte=from_date,
        DATE__lte=to_date
    ).exclude(OPERATOR_ID="0").values_list('OPERATOR_ID', flat=True).distinct()
    
    operator_ids = sorted(list(queryset))
    return Response({"operator_ids": operator_ids})

# ======================================
# Operator Report Endpoints
# ======================================

@api_view(['GET'])
def operator_report(request, operator_id):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    queryset = MachineLog.objects.filter(OPERATOR_ID=operator_id)
    
    if from_date:
        queryset = queryset.filter(DATE__gte=from_date)
    if to_date:
        queryset = queryset.filter(DATE__lte=to_date)
    
    # Get operator name
    operator_name = ""
    try:
        operator = Operator.objects.get(rfid_card_no=operator_id)
        operator_name = operator.operator_name
    except Operator.DoesNotExist:
        pass
    
    # Calculate totals
    total_hours = queryset.aggregate(
        total_hours=Sum('NEEDLE_RUNTIME')
    )['total_hours'] or 0
    
    productive_hours = queryset.filter(MODE=1).aggregate(
        total=Sum('NEEDLE_RUNTIME')
    )['total'] or 0
    
    no_feeding_hours = queryset.filter(MODE=3).aggregate(
        total=Sum('NEEDLE_RUNTIME')
    )['total'] or 0
    
    meeting_hours = queryset.filter(MODE=4).aggregate(
        total=Sum('NEEDLE_RUNTIME')
    )['total'] or 0
    
    maintenance_hours = queryset.filter(MODE=5).aggregate(
        total=Sum('NEEDLE_RUNTIME')
    )['total'] or 0
    
    idle_hours = queryset.filter(MODE=2).aggregate(
        total=Sum('NEEDLE_RUNTIME')
    )['total'] or 0
    
    total_stitch_count = queryset.aggregate(
        total=Sum('STITCH_COUNT')
    )['total'] or 0
    
    # Prepare daily data
    daily_data = queryset.values('DATE').annotate(
        sewing_hours=Sum('NEEDLE_RUNTIME', filter=operator.Q(MODE=1)),
        no_feeding_hours=Sum('NEEDLE_RUNTIME', filter=operator.Q(MODE=3)),
        meeting_hours=Sum('NEEDLE_RUNTIME', filter=operator.Q(MODE=4)),
        maintenance_hours=Sum('NEEDLE_RUNTIME', filter=operator.Q(MODE=5)),
        idle_hours=Sum('NEEDLE_RUNTIME', filter=operator.Q(MODE=2)),
        total_hours=Sum('NEEDLE_RUNTIME'),
        stitch_count=Sum('STITCH_COUNT'),
        machine_count=Count('MACHINE_ID', distinct=True),
        avg_sewing_speed=Avg('RESERVE')
    ).order_by('DATE')
    
    # Format daily data for table
    table_data = []
    for day in daily_data:
        day_total = day['total_hours'] or 0
        pt_percentage = (day['sewing_hours'] / day_total * 100) if day_total > 0 else 0
        npt_percentage = 100 - pt_percentage
        
        table_data.append({
            "Date": day['DATE'],
            "Sewing Hours (PT)": day['sewing_hours'] or 0,
            "No Feeding Hours": day['no_feeding_hours'] or 0,
            "Meeting Hours": day['meeting_hours'] or 0,
            "Maintenance Hours": day['maintenance_hours'] or 0,
            "Idle Hours": day['idle_hours'] or 0,
            "Total Hours": day_total,
            "Productive Time (PT) %": round(pt_percentage, 2),
            "Non-Productive Time (NPT) %": round(npt_percentage, 2),
            "Sewing Speed": round(day['avg_sewing_speed'] or 0, 2),
            "Stitch Count": day['stitch_count'] or 0,
            "Machine Count": day['machine_count'] or 0
        })
    
    # Calculate percentages
    pt_percentage = (productive_hours / total_hours * 100) if total_hours > 0 else 0
    npt_percentage = 100 - pt_percentage
    
    response_data = {
        "operator_id": operator_id,
        "operator_name": operator_name,
        "total_hours": round(total_hours, 2),
        "total_productive_time": {
            "hours": round(productive_hours, 2),
            "percentage": round(pt_percentage, 2)
        },
        "total_non_productive_time": {
            "hours": round(no_feeding_hours + meeting_hours + maintenance_hours + idle_hours, 2),
            "percentage": round(npt_percentage, 2),
            "breakdown": {
                "no_feeding_hours": round(no_feeding_hours, 2),
                "meeting_hours": round(meeting_hours, 2),
                "maintenance_hours": round(maintenance_hours, 2),
                "idle_hours": round(idle_hours, 2)
            }
        },
        "total_stitch_count": total_stitch_count,
        "table_data": table_data,
        "all_table_data": table_data  # For filtering
    }
    
    return Response(response_data)

@api_view(['GET'])
def all_operators_report(request):
    """
    Generate a summary report for all operators within a specified date range.
    
    This endpoint provides an aggregated view of operator performance metrics including:
    - Total working hours
    - Productive hours and percentage
    - Stitch count
    - Machine utilization
    
    Parameters:
        from_date (str): Start date for the report (YYYY-MM-DD) 
        to_date (str): End date for the report (YYYY-MM-DD)
    
    Returns:
        Response: JSON containing performance data for all operators
                 or an error if date parameters are missing
    """
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if not from_date or not to_date:
        return Response({"error": "Both from_date and to_date are required"}, status=400)
    
    # Get all operator data
    operators = MachineLog.objects.filter(
        DATE__gte=from_date,
        DATE__lte=to_date
    ).exclude(OPERATOR_ID="0").values('OPERATOR_ID').distinct()
    
    all_operators_report = []
    
    for operator in operators:
        operator_id = operator['OPERATOR_ID']
        operator_data = MachineLog.objects.filter(
            OPERATOR_ID=operator_id,
            DATE__gte=from_date,
            DATE__lte=to_date
        )
        
        # Get operator name
        operator_name = ""
        try:
            operator_obj = Operator.objects.get(rfid_card_no=operator_id)
            operator_name = operator_obj.operator_name
        except Operator.DoesNotExist:
            pass
        
        # Calculate totals
        total_hours = operator_data.aggregate(
            total_hours=Sum('NEEDLE_RUNTIME')
        )['total_hours'] or 0
        
        productive_hours = operator_data.filter(MODE=1).aggregate(
            total=Sum('NEEDLE_RUNTIME')
        )['total'] or 0
        
        pt_percentage = (productive_hours / total_hours * 100) if total_hours > 0 else 0
        
        all_operators_report.append({
            "operator_id": operator_id,
            "operator_name": operator_name,
            "total_hours": round(total_hours, 2),
            "productive_hours": round(productive_hours, 2),
            "productive_percentage": round(pt_percentage, 2),
            "stitch_count": operator_data.aggregate(
                total=Sum('STITCH_COUNT')
            )['total'] or 0,
            "machine_count": operator_data.values('MACHINE_ID').distinct().count()
        })
    
    return Response({"allOperatorsReport": all_operators_report})


# Use imports and MODES constant from the top of the file

@api_view(['GET'])
def get_consolidated_logs(request):
    """
    Retrieve machine logs with summary calculations and filtering capabilities.
    
    This view provides a comprehensive way to query and analyze machine logs with filters
    for multiple machine IDs, line numbers, and operator names. It also calculates 
    aggregated metrics like total hours, productive time, non-productive time, and more.
    
    Parameters:
        from_date (str): Start date for filtering logs (YYYY-MM-DD)
        to_date (str): End date for filtering logs (YYYY-MM-DD)
        machine_id (list): List of machine IDs to filter by
        line_number (list): List of line numbers to filter by
        operator_name (list): List of operator names or IDs to filter by
    
    Returns:
        Response: JSON containing summary data and serialized logs with applied filters
    """
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    
    # Get all filter values
    machine_ids = request.query_params.getlist('machine_id', [])
    line_numbers = request.query_params.getlist('line_number', [])
    operator_names = request.query_params.getlist('operator_name', [])

    logs = MachineLog.objects.all()
    
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
    
    # Apply operator filters
    if operator_names:
        operators = Operator.objects.filter(
            Q(operator_name__in=operator_names) | 
            Q(rfid_card_no__in=operator_names)
        ).distinct()
        operator_ids = operators.values_list('rfid_card_no', flat=True)
        logs = logs.filter(OPERATOR_ID__in=operator_ids)
    
    # Calculate duration in hours for each log entry
    # This complex query converts time fields to seconds for accurate duration calculations
    # and enables proper filtering of work hours and breaks
    logs = logs.annotate(
        # Convert START_TIME to seconds (hours*3600 + minutes*60 + seconds)
        start_seconds=ExpressionWrapper(
            ExtractHour('START_TIME') * 3600 + 
            ExtractMinute('START_TIME') * 60 + 
            ExtractSecond('START_TIME'),
            output_field=FloatField()
        ),
        # Convert END_TIME to seconds (hours*3600 + minutes*60 + seconds)
        end_seconds=ExpressionWrapper(
            ExtractHour('END_TIME') * 3600 + 
            ExtractMinute('END_TIME') * 60 + 
            ExtractSecond('END_TIME'),
            output_field=FloatField()
        ),
        # Calculate duration in hours by subtracting seconds and dividing by 3600
        duration_hours=ExpressionWrapper(
            (F('end_seconds') - F('start_seconds')) / 3600,
            output_field=FloatField()
        )
    )
    
    # Filter for standard working hours (8:25 AM to 7:30 PM)
    logs = logs.filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:30 PM (19.5 * 3600)
    )
    
    # Exclude specific break periods
    logs = logs.exclude(
        # Morning break: 10:30-10:40 AM
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  
        # Lunch break: 13:20-14:00
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  
        # Afternoon break: 16:20-16:30
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    
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
    
    # Serialize logs
    serialized_logs = MachineLogSerializer(logs, many=True).data
    
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





# views.py

from .models import UserMachineLog, Operator, OperatorAFL, ModeMessage
from .serializers import UserMachineLogSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view

# Updated MODES for UserMachineLog
MODES = {
    1: "Sewing",
    2: "Idle",
    3: "Rework",
    4: "Needle Break",
    5: "Maintenance"
}

@api_view(['POST'])
def log_user_machine_data(request):
    data = request.data
    print("Processing user machine log data...")

    # Validate mode
    try:
        mode = int(data.get("MODE"))
    except (TypeError, ValueError):
        return Response({"message": "Invalid mode format"}, status=400)

    if mode not in MODES:
        return Response({"message": f"Invalid mode: {mode}. Valid modes are {list(MODES.keys())}"}, status=400)

    # Validate serializer
    serializer = UserMachineLogSerializer(data=data)
    if not serializer.is_valid():
        return Response({"message": "Validation failed", "errors": serializer.errors}, status=400)

    validated_data = serializer.validated_data

    # Extract Log IDs, Machine ID, Date, Start Time and End Time
    tx_log_id = validated_data.get("Tx_LOGID")
    str_log_id = validated_data.get("Str_LOGID")
    machine_id = validated_data.get("MACHINE_ID")
    log_date = validated_data.get("DATE")
    start_time = validated_data.get("START_TIME")
    end_time = validated_data.get("END_TIME")

    if machine_id is None:
        return Response({"message": "MACHINE_ID is required"}, status=400)

    if log_date is None:
        return Response({"message": "DATE is required"}, status=400)

    if start_time is None:
        return Response({"message": "START_TIME is required"}, status=400)

    if end_time is None:
        return Response({"message": "END_TIME is required"}, status=400)

    # Tx_LOGID Handling
    if tx_log_id is not None:
        try:
            tx_log_id = int(tx_log_id)
        except ValueError:
            return Response({"message": "Invalid Tx_LOGID format"}, status=400)

        if tx_log_id > 1000:
            adjusted_tx_log_id = tx_log_id - 1000
            if UserMachineLog.objects.filter(
                Tx_LOGID=adjusted_tx_log_id,
                MACHINE_ID=machine_id,
                DATE=log_date,
                START_TIME=start_time,
                END_TIME=end_time
            ).exists():
                return Response({
                    "code": 200,
                    "message": "Log saved successfully"
                }, status=200)
            # Continue with original tx_log_id (don't save adjusted value)

    # Str_LOGID Handling
    if str_log_id is not None:
        try:
            str_log_id = int(str_log_id)
        except ValueError:
            return Response({"message": "Invalid Str_LOGID format"}, status=400)

        if str_log_id > 1000:
            adjusted_str_log_id = str_log_id - 1000
            if UserMachineLog.objects.filter(
                Str_LOGID=adjusted_str_log_id,
                MACHINE_ID=machine_id,
                DATE=log_date,
                START_TIME=start_time,
                END_TIME=end_time
            ).exists():
                return Response({
                    "code": 200,
                    "message": "Log saved successfully"
                }, status=200)
            
            # Replace with adjusted value for saving
            validated_data["Str_LOGID"] = adjusted_str_log_id

    # Save the log data with original Tx_LOGID (if >1000) and adjusted Str_LOGID (if >1000)
    UserMachineLog.objects.create(**validated_data)

    return Response({
        "code": 200,
        "message": "Log saved successfully"
    }, status=200)

@api_view(['GET'])
def get_user_machine_logs(request):
    """
    View to fetch user machine logs with pagination and filtering
    """
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    
    print(f"Fetching user machine logs from {from_date} to {to_date}")
    
    logs = UserMachineLog.objects.all().order_by('-created_at')
    
    if from_date:
        logs = logs.filter(DATE__gte=from_date)
    if to_date:
        logs = logs.filter(DATE__lte=to_date)

    # Prefetch operator data to optimize queries and prevent N+1 queries
    operator_ids = set(log.OPERATOR_ID for log in logs if log.OPERATOR_ID)
    
    # Check both Operator and OperatorAFL models for operator names
    regular_operators = {op.rfid_card_no: op.operator_name for op in Operator.objects.filter(rfid_card_no__in=operator_ids)}
    afl_operators = {op.rfid_card_no: op.operatorAFL_name for op in OperatorAFL.objects.filter(rfid_card_no__in=operator_ids)}
    
    # Combine both operator dictionaries, with AFL operators taking precedence
    operators = {**regular_operators, **afl_operators}
    
    print(f"Found {logs.count()} logs with {len(operators)} operators ({len(regular_operators)} regular, {len(afl_operators)} AFL)")
    
    serialized_logs = UserMachineLogSerializer(logs, many=True).data
    
    # Add index to each log
    for idx, log in enumerate(serialized_logs, start=1):
        log['index'] = idx
        
        # Double-check operator_name and mode_description
        if not log.get('operator_name') and log.get('OPERATOR_ID') and log['OPERATOR_ID'] != '0':
            operator_name = operators.get(log['OPERATOR_ID'])
            if operator_name:
                log['operator_name'] = operator_name
        
        # Ensure mode_description is set
        if not log.get('mode_description') and log.get('MODE') is not None:
            log['mode_description'] = MODES.get(log['MODE'], f"Mode {log['MODE']}")

    print(f"Returning {len(serialized_logs)} serialized logs")
    return Response(serialized_logs)
















def process_machine_data(logs, machine_id):
    """Helper function to process data for a single machine"""
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
        needle_runtime=Sum('NEEDLE_RUNTIME'),
        sewing_operation_count=Sum(Case(
            When(MODE=1, then=F('STITCH_COUNT')),
            default=Value(0),
            output_field=IntegerField()
        )),
        sewing_skip_count=Sum(Case(
            When(MODE=1, then=F('NEEDLE_RUNTIME')),
            default=Value(0),
            output_field=IntegerField()
        )),
        rework_operation_count=Sum(Case(
            When(MODE=3, then=F('STITCH_COUNT')),
            default=Value(0),
            output_field=IntegerField()
        )),
        rework_skip_count=Sum(Case(
            When(MODE=3, then=F('NEEDLE_RUNTIME')),
            default=Value(0),
            output_field=IntegerField()
        ))
    ).order_by('DATE')

    # Calculate totals
    total_sewing_hours = 0
    total_no_feeding_hours = 0
    total_meeting_hours = 0
    total_maintenance_hours = 0
    total_idle_hours = 0
    total_stitch_count = 0
    total_needle_runtime = 0
    total_hours = 0

    formatted_table_data = []
    for data in daily_data:
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
            'Date': str(data['DATE']),
            'Sewing Hours (PT)': round(sewing_hours, 2),
            'Sewing Operation count': data['sewing_operation_count'] or 0,
            'Sewing Skip count': data['sewing_skip_count'] or 0,
            'Rework Operation count': data['rework_operation_count'] or 0,
            'Rework Skip count': data['rework_skip_count'] or 0,
            'No Feeding Hours': round(no_feeding_hours, 2),
            'Meeting Hours': round(meeting_hours, 2),
            'Maintenance Hours': round(maintenance_hours, 2),
            'Idle Hours': round(idle_hours, 2),
            'Total Hours': round(daily_total_hours, 2),
            'Productive Time (PT) %': round(productive_time_percentage, 2),
            'Non-Productive Time (NPT) %': round(non_productive_time_percentage, 2),
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
    
    # Calculate overall percentages
    total_productive_percentage = (total_productive_time / total_hours * 100) if total_hours > 0 else 0
    total_non_productive_percentage = (total_non_productive_time / total_hours * 100) if total_hours > 0 else 0

    # Calculate average sewing speed
    valid_speed_logs = logs.filter(reserve_numeric__gt=0)
    average_sewing_speed = valid_speed_logs.aggregate(
        avg_speed=Avg('reserve_numeric')
    )['avg_speed'] or 0

    return {
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
        "averageSewingSpeed": round(average_sewing_speed, 2),
        "totalNeedleRuntime": round(total_needle_runtime, 2),
        "tableData": formatted_table_data
    }

@api_view(['GET'])
def afl_machine_reports(request, machine_id):
    try:
        # Get valid operator IDs from OperatorAFL model
        valid_operators = OperatorAFL.objects.values_list('rfid_card_no', flat=True)
        
        # Handle "all" case - convert machine_id to string first
        machine_id_str = str(machine_id)
        if machine_id_str.lower() == 'all':
            logs = UserMachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
            all_machines = True
        else:
            logs = UserMachineLog.objects.filter(MACHINE_ID=machine_id, OPERATOR_ID__in=valid_operators)
            all_machines = False
    except UserMachineLog.DoesNotExist:
        return Response({"error": "Data not found"}, status=404)
    except ValueError:
        return Response({"error": "Invalid machine ID"}, status=400)

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

    # Filter for working hours (8:25 AM to 7:35 PM)
    logs = logs.filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
    )

    # Exclude specific break periods (entirely within these ranges)
    logs = logs.exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )

    # For "all" case, we'll group by machine ID
    if all_machines:
        # Get distinct machine IDs
        machine_ids = logs.order_by('MACHINE_ID').values_list('MACHINE_ID', flat=True).distinct()
        
        all_machine_reports = []
        
        for machine_id in machine_ids:
            machine_logs = logs.filter(MACHINE_ID=machine_id)
            
            # Process data for this machine
            machine_report = process_machine_data(machine_logs, machine_id)
            all_machine_reports.append(machine_report)
        
        return Response({
            "allMachinesReport": all_machine_reports,
            "totalMachines": len(all_machine_reports)
        })
    else:
        # Process single machine data
        machine_report = process_machine_data(logs, machine_id)
        return Response(machine_report)


@api_view(['GET'])
def afl_all_machines_report(request):
    try:
        # Get valid operator IDs from OperatorAFL model
        valid_operators = OperatorAFL.objects.values_list('rfid_card_no', flat=True)
        logs = UserMachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

    # Get date filters from query parameters
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')

    # Apply date filtering if dates are provided
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            logs = logs.filter(DATE__gte=from_date)
        except ValueError:
            return Response({"error": "Invalid from_date format. Use YYYY-MM-DD"}, status=400)

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            logs = logs.filter(DATE__lte=to_date)
        except ValueError:
            return Response({"error": "Invalid to_date format. Use YYYY-MM-DD"}, status=400)

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
    ).filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
    ).exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )

    # Get distinct machine IDs
    machine_ids = logs.order_by('MACHINE_ID').values_list('MACHINE_ID', flat=True).distinct()
    
    all_machine_reports = []
    
    for machine_id in machine_ids:
        machine_logs = logs.filter(MACHINE_ID=machine_id)
        
        # Process data for this machine
        try:
            machine_report = process_machine_data(machine_logs, machine_id)
            all_machine_reports.append(machine_report)
        except Exception as e:
            print(f"Error processing machine {machine_id}: {str(e)}")
            continue
    
    return Response({
        "allMachinesReport": all_machine_reports,
        "totalMachines": len(all_machine_reports),
        "from_date": from_date_str,
        "to_date": to_date_str
    })












@api_view(['GET'])
def operator_afl_reports_by_name(request, operator_name):
    """
    Generate detailed performance report for a specific AFL operator.
    
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
        if operator_name == "All":
            operator = OperatorAFL.objects.all()
            logs = UserMachineLog.objects.all()
        else:
            # Fetch operator by name
            operator = OperatorAFL.objects.get(operatorAFL_name=operator_name)
            logs = UserMachineLog.objects.filter(OPERATOR_ID=operator.rfid_card_no)    
       
    except OperatorAFL.DoesNotExist:
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

    # Calculate duration in hours for each log entry with time constraints (8:25 AM to 7:35 PM)
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
        # Calculate adjusted start and end times within working hours (8:25 AM to 7:35 PM)
        adjusted_start_seconds=Case(
            When(start_seconds__lt=30300, then=Value(30300)),  # 8:25 AM (8.416667 * 3600)
            When(start_seconds__gt=70500, then=Value(70500)),  # 7:35 PM (19.583333 * 3600)
            default=F('start_seconds'),
            output_field=FloatField()
        ),
        adjusted_end_seconds=Case(
            When(end_seconds__lt=30300, then=Value(30300)),  # 8:25 AM (8.416667 * 3600)
            When(end_seconds__gt=70500, then=Value(70500)),  # 7:35 PM (19.583333 * 3600)
            default=F('end_seconds'),
            output_field=FloatField()
        ),
        # Calculate duration only for the time within working hours
        duration_hours=Case(
            # Case when both start and end are outside working hours
            When(
                Q(end_seconds__lte=30300) | Q(start_seconds__gte=70500),
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

    # Filter for working hours (8:25 AM to 7:35 PM)
    logs = logs.filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
    )

    # Exclude specific break periods (entirely within these ranges)
    logs = logs.exclude(
        Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
        Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
        Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
    )

    # Calculate total working days
    distinct_dates = logs.values('DATE').distinct()
    total_working_days = distinct_dates.count()
    
    # Get today's date
    today = datetime.now().date()
    
    # Calculate the total available hours dynamically
    total_available_hours = 0
    
    for entry in distinct_dates:
        date_entry = entry['DATE']
        
        # Check if this date is today
        if date_entry == today:
            # For today, calculate hours from 8:25 AM to current time
            current_time = datetime.now().time()
            current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
            
            # Start time is 8:25 AM (30300 seconds)
            start_seconds = 30300
            
            # End time is the minimum of current time or end of workday (7:35 PM)
            end_seconds = min(current_seconds, 70500)
            
            # If current time is before workday start, set hours to 0
            if current_seconds < start_seconds:
                day_hours = 0
            else:
                # Calculate hours for today
                day_hours = (end_seconds - start_seconds) / 3600
                
                # Subtract break times if they've already passed
                if current_seconds > 38400:  # After 10:40 AM
                    day_hours -= 10/60  # Subtract 10 minutes for first break
                
                if current_seconds > 50400:  # After 2:00 PM
                    day_hours -= 40/60  # Subtract 40 minutes for second break
                
                if current_seconds > 59400:  # After 4:30 PM
                    day_hours -= 10/60  # Subtract 10 minutes for third break
        else:
            # For past dates, use the full day hours (8:25 AM to 7:35 PM minus breaks)
            day_hours = (70500 - 30300) / 3600 - 1  # 10.17 hours
        
        total_available_hours += day_hours

    # Define the updated MODES dictionary
    MODES = {
        1: "Sewing",
        2: "Idle",
        3: "Rework",
        4: "Needle Break",
        5: "Maintenance"
    }

    # Calculate total hours for each mode
    mode_hours = logs.values('MODE').annotate(
        total_hours=Sum('duration_hours')
    )

    # Initialize hour counters
    total_production_hours = 0  # Mode 1: Sewing
    total_idle_hours_tracked = 0  # Mode 2: Idle (tracked)
    total_rework_hours = 0  # Mode 3: Rework
    total_needle_break_hours = 0  # Mode 4: Needle Break
    total_maintenance_hours = 0  # Mode 5: Maintenance

    # Sum hours for each mode
    for mode in mode_hours:
        if mode['MODE'] == 1:  # Sewing
            total_production_hours = mode['total_hours'] or 0
        elif mode['MODE'] == 2:  # Idle
            total_idle_hours_tracked = mode['total_hours'] or 0
        elif mode['MODE'] == 3:  # Rework
            total_rework_hours = mode['total_hours'] or 0
        elif mode['MODE'] == 4:  # Needle Break
            total_needle_break_hours = mode['total_hours'] or 0
        elif mode['MODE'] == 5:  # Maintenance
            total_maintenance_hours = mode['total_hours'] or 0

    # Calculate total tracked hours
    total_tracked_hours = (
        total_production_hours + 
        total_idle_hours_tracked + 
        total_rework_hours + 
        total_needle_break_hours + 
        total_maintenance_hours
    )

    # Calculate untracked idle hours
    untracked_idle_hours = max(total_available_hours - total_tracked_hours, 0)
    
    # Total idle is tracked idle plus untracked idle
    total_idle_hours = total_idle_hours_tracked + untracked_idle_hours

    # Calculate non-productive time components
    total_non_production_hours = (
        total_idle_hours + 
        total_rework_hours + 
        total_needle_break_hours + 
        total_maintenance_hours
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

    # Fetch Table Data (daily breakdown) - only group by DATE and OPERATOR_ID
    table_data = logs.values('DATE', 'OPERATOR_ID').annotate(
        sewing_hours=Sum(Case(
            When(MODE=1, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        idle_hours_tracked=Sum(Case(
            When(MODE=2, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        rework_hours=Sum(Case(
            When(MODE=3, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        needle_break_hours=Sum(Case(
            When(MODE=4, then=F('duration_hours')),
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
    ).order_by('DATE', 'OPERATOR_ID')
    
    # Now format the data, fetching operator name from the OperatorAFL model
    formatted_table_data = []
    for data in table_data:
        # Get operator details from the OperatorAFL model
        try:
            operator = OperatorAFL.objects.get(rfid_card_no=data['OPERATOR_ID'])
            operator_name = operator.operatorAFL_name
            rfid_card_no = operator.rfid_card_no
        except OperatorAFL.DoesNotExist:
            operator_name = "Unknown"
            rfid_card_no = "Unknown"
        
        # Get the date from the data
        entry_date = data['DATE']
        
        # Calculate total available hours for this day
        day_total_hours = 0
        
        # Check if this date is today
        if entry_date == today:
            # For today, calculate hours from 8:25 AM to current time
            current_time = datetime.now().time()
            current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
            
            # Start time is 8:25 AM (30300 seconds)
            start_seconds = 30300
            
            # End time is the minimum of current time or end of workday (7:35 PM)
            end_seconds = min(current_seconds, 70500)
            
            # If current time is before workday start, set hours to 0
            if current_seconds < start_seconds:
                day_total_hours = 0
            else:
                # Calculate hours for today
                day_total_hours = (end_seconds - start_seconds) / 3600
                
                # Subtract break times if they've already passed
                if current_seconds > 38400:  # After 10:40 AM
                    day_total_hours -= 10/60  # Subtract 10 minutes for first break
                
                if current_seconds > 50400:  # After 2:00 PM
                    day_total_hours -= 40/60  # Subtract 40 minutes for second break
                
                if current_seconds > 59400:  # After 4:30 PM
                    day_total_hours -= 10/60  # Subtract 10 minutes for third break
        else:
            # For past dates, use the full day hours (8:25 AM to 7:35 PM minus breaks)
            day_total_hours = (70500 - 30300) / 3600 - 1  # 10.17 hours
        
        # Calculate sewing and non-sewing hours
        sewing_hours = data['sewing_hours'] or 0
        idle_hours_tracked = data['idle_hours_tracked'] or 0
        rework_hours = data['rework_hours'] or 0
        needle_break_hours = data['needle_break_hours'] or 0
        maintenance_hours = data['maintenance_hours'] or 0
        
        # Calculate untracked idle hours as the remainder
        total_tracked_hours_for_day = sewing_hours + idle_hours_tracked + rework_hours + needle_break_hours + maintenance_hours
        untracked_idle_hours_for_day = max(day_total_hours - total_tracked_hours_for_day, 0)
        
        # Total idle is tracked idle plus untracked idle
        total_idle_hours_for_day = idle_hours_tracked + untracked_idle_hours_for_day
        
        # Calculate percentages
        productive_time_percentage = (sewing_hours / day_total_hours * 100) if day_total_hours > 0 else 0
        npt_percentage = 100 - productive_time_percentage
        
        formatted_table_data.append({
            'Date': str(entry_date),
            'Operator ID': data['OPERATOR_ID'],
            'Operator Name': operator_name,
            'Total Hours': round(day_total_hours, 2),
            'Sewing Hours': round(sewing_hours, 2),
            'Idle Hours': round(total_idle_hours_for_day, 2),
            'Rework Hours': round(rework_hours, 2),
            'Needle Break Hours': round(needle_break_hours, 2),
            'Maintenance Hours': round(maintenance_hours, 2),
            'Productive Time in %': round(productive_time_percentage, 2),
            'NPT in %': round(npt_percentage, 2),
            'Sewing Speed': round(data['sewing_speed'] or 0, 2),
            'Stitch Count': data['total_stitch_count'] or 0,
            'Needle Runtime': data['needle_runtime'] or 0
        })

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
        "totalNPT": round(total_non_production_hours, 2),
        "reworkHours": round(total_rework_hours, 2),
        "needleBreakHours": round(total_needle_break_hours, 2),
        "maintenanceHours": round(total_maintenance_hours, 2)
    })





def process_user_line_data(logs, line_number):
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
        rework_hours=Sum(Case(
            When(MODE=3, then=F('duration_hours')),
            default=Value(0),
            output_field=FloatField()
        )),
        needle_break_hours=Sum(Case(
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
    total_rework_hours = 0
    total_needle_break_hours = 0
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
        rework_hours = data['rework_hours'] or 0
        needle_break_hours = data['needle_break_hours'] or 0
        maintenance_hours = data['maintenance_hours'] or 0
        idle_hours = data['idle_hours'] or 0
        
        # Calculate PT and NPT
        productive_time = sewing_hours
        non_productive_time = rework_hours + needle_break_hours + maintenance_hours + idle_hours
        daily_total_hours = productive_time + non_productive_time
        
        # Accumulate to total hours
        total_hours += daily_total_hours
        
        # Calculate percentages
        productive_time_percentage = (productive_time / daily_total_hours * 100) if daily_total_hours > 0 else 0
        non_productive_time_percentage = (non_productive_time / daily_total_hours * 100) if daily_total_hours > 0 else 0
        
        formatted_table_data.append({
            'Date': str(date),
            'Sewing Hours (PT)': round(sewing_hours, 2),
            'Rework Hours': round(rework_hours, 2),
            'Needle Break Hours': round(needle_break_hours, 2),
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
        total_rework_hours += rework_hours
        total_needle_break_hours += needle_break_hours
        total_maintenance_hours += maintenance_hours
        total_idle_hours += idle_hours
        total_stitch_count += data['total_stitch_count'] or 0
        total_needle_runtime += data['needle_runtime'] or 0

    # Calculate overall PT and NPT
    total_productive_time = total_sewing_hours
    total_non_productive_time = (
        total_rework_hours + 
        total_needle_break_hours + 
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
                "reworkHours": round(total_rework_hours, 2),
                "needleBreakHours": round(total_needle_break_hours, 2),
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
def user_line_reports(request, line_number):
    try:
        # Get valid operator IDs from OperatorAFL model
        valid_operators = OperatorAFL.objects.values_list('rfid_card_no', flat=True)
        
        # Handle "all" case - convert line_number to string first
        line_number_str = str(line_number)
        if line_number_str.lower() == 'all':
            logs = UserMachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
            all_lines = True
        else:
            # Convert back to integer if it's a numeric line number
            line_number = int(line_number_str)
            logs = UserMachineLog.objects.filter(LINE_NUMB=line_number, OPERATOR_ID__in=valid_operators)
            all_lines = False
    except UserMachineLog.DoesNotExist:
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

    # Filter for working hours (8:25 AM to 7:35 PM)
    logs = logs.filter(
        start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
        end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
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
            line_report = process_user_line_data(line_logs, str(line_num))
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
        line_report = process_user_line_data(logs, str(line_number))
        return Response(line_report)




# ======================================
# User Logs Filtering Endpoints
# ======================================

@api_view(['GET'])
def filter_user_logs(request):
    line_number = request.GET.get('line_number')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    queryset = UserMachineLog.objects.all()
    
    if line_number and line_number.lower() != 'all':
        queryset = queryset.filter(LINE_NUMB=line_number)
    
    if from_date:
        queryset = queryset.filter(DATE__gte=from_date)
    
    if to_date:
        queryset = queryset.filter(DATE__lte=to_date)
    
    # Prefetch operator data to optimize queries
    logs = list(queryset)
    operator_ids = set(log.OPERATOR_ID for log in logs if log.OPERATOR_ID != "0")
    operators = OperatorAFL.objects.filter(rfid_card_no__in=operator_ids)
    operator_map = {op.rfid_card_no: op.operator_name for op in operators}
    
    data = []
    for log in logs:
        log_data = {
            **log.__dict__,
            'mode_description': MODES.get(log.MODE, 'Unknown mode'),
            'operator_name': operator_map.get(log.OPERATOR_ID, "") if log.OPERATOR_ID != "0" else ""
        }
        # Remove Django internal fields
        log_data.pop('_state', None)
        data.append(log_data)
    
    return Response(data)


# ======================================
# User Line Number Endpoints
# ======================================

@api_view(['GET'])
def get_user_line_numbers(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if not from_date or not to_date:
        return Response({"error": "Both from_date and to_date are required"}, status=400)
    
    queryset = UserMachineLog.objects.filter(
        DATE__gte=from_date,
        DATE__lte=to_date
    ).values_list('LINE_NUMB', flat=True).distinct()
    
    line_numbers = sorted(list(queryset))
    return Response({"line_numbers": line_numbers})

# End of file