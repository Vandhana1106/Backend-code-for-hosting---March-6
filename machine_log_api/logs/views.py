from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import MachineLog, DuplicateLog, ModeMessage
from .serializers import MachineLogSerializer
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.db.models import Count

# Dictionary to map mode numbers to descriptions
MODES = {
    1: "Sewing - Machine is On - Production",
    2: "Logout - Off - Idle",
    3: "No Garment - Off - Non-Production",
    4: "Meeting - Off - Non-Production",
    5: "Maintenance - On - Non-Production",
}

@api_view(['POST'])
def log_machine_data(request):
    """
    View to handle machine data logging.
    
    Validates and processes incoming machine log data:
    - Checks for valid mode
    - Prevents duplicate entries
    - Stores the log data
    
    Returns:
        Response with status and mode description
    """
    data = request.data

    # Inform the user that the data from the machine is being processed
    print("The data from the machine is being processed. Please wait...")

    # Validate mode
    try:
        mode = int(data.get("MODE"))  # Convert mode to integer
    except (TypeError, ValueError):
        return Response({"message": "Invalid mode format"}, status=400)

    if mode not in MODES:
        return Response({"message": f"Invalid mode: {mode}. Valid modes are {list(MODES.keys())}"}, status=400)

    # Process the serializer first to handle date/time validation
    serializer = MachineLogSerializer(data=data)
    if not serializer.is_valid():
        return Response({
	"code":200,
	"message":"Log saved successfully",
	
}, status=400)
    
    # Check for duplicate with validated data
    validated_data = serializer.validated_data
    if MachineLog.objects.filter(
        MACHINE_ID=validated_data.get("MACHINE_ID"),
        LINE_NUMB=validated_data.get("LINE_NUMB"),
        OPERATOR_ID=validated_data.get("OPERATOR_ID"),
        DATE=validated_data.get("DATE"),
        START_TIME=validated_data.get("START_TIME"),
        END_TIME=validated_data.get("END_TIME"),
        MODE=validated_data.get("MODE"),
    ).exists():
        DuplicateLog.objects.create(payload=data)
        return Response({
            "message": "Duplicate entry found", 
            "status": "duplicate", 
            "mode_description": MODES[mode]
        }, status=409)

    # Save log
    serializer.save()
    return Response({
	"code":200,
	"message":"Log saved successfully",
	}
, status=201)
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



from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum, Count
from .models import MachineLog

@api_view(['GET'])
def calculate_line_efficiency(request):
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


from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime, timedelta
from .models import MachineLog
from django.db.models import F

def time_to_seconds(time_obj):
    """Convert HH:MM:SS TimeField to total seconds."""
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second

@api_view(['GET'])
def calculate_operator_efficiency(request):
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
