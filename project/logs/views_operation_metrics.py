# Django imports
from django.db.models import Sum, Q, F, Case, When, Value, FloatField, IntegerField
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import ExtractHour, ExtractMinute, ExtractSecond, Cast

# Django REST framework imports
from rest_framework.response import Response
from rest_framework.decorators import api_view

# Local application imports
from .models import MachineLog, Operator, UserMachineLog, OperatorAFL

@api_view(['GET'])
def machine_operation_metrics(request, machine_id=None):
    """
    Calculate operation metrics for machines:
    - Sewing Operation Count
    - Sewing Skip Count
    - Rework Operation Count
    - Rework Stitch Count

    Parameters:
        machine_id (optional): Specific machine ID to get metrics for
        from_date (optional): Start date filter (YYYY-MM-DD)
        to_date (optional): End date filter (YYYY-MM-DD)
        
    Returns:
        Metrics for machines including operation and skip counts for both sewing and rework modes
    """
    try:
        # Get valid operator IDs from Operator model
        valid_operators = Operator.objects.values_list('rfid_card_no', flat=True)
        
        # Handle machine_id filter
        if machine_id and machine_id.lower() != 'all':
            logs = MachineLog.objects.filter(MACHINE_ID=machine_id, OPERATOR_ID__in=valid_operators)
        else:
            logs = MachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
            
    except MachineLog.DoesNotExist:
        return Response({"error": "Data not found"}, status=404)
    except ValueError:
        return Response({"error": "Invalid machine ID"}, status=400)

    # Get date filters from query parameters
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')

    # Apply date filtering if dates are provided
    if from_date_str:
        from datetime import datetime
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            logs = logs.filter(DATE__gte=from_date)
        except ValueError:
            return Response({"error": "Invalid from_date format. Use YYYY-MM-DD"}, status=400)

    if to_date_str:
        from datetime import datetime
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

    # Get metrics by machine
    if machine_id and machine_id.lower() != 'all':
        # For single machine
        machine_metrics = calculate_machine_operation_metrics(logs, machine_id)
        return Response(machine_metrics)
    else:
        # For all machines
        machine_ids = logs.order_by('MACHINE_ID').values_list('MACHINE_ID', flat=True).distinct()
        all_machine_metrics = []
        
        for m_id in machine_ids:
            machine_logs = logs.filter(MACHINE_ID=m_id)
            try:
                metrics = calculate_machine_operation_metrics(machine_logs, m_id)
                all_machine_metrics.append(metrics)
            except Exception as e:
                print(f"Error processing machine {m_id}: {str(e)}")
                continue
        
        return Response({
            "allMachinesMetrics": all_machine_metrics,
            "totalMachines": len(all_machine_metrics),
            "from_date": from_date_str,
            "to_date": to_date_str
        })

def calculate_machine_operation_metrics(logs, machine_id):
    """
    Helper function to calculate operation metrics for a single machine
    
    Metrics calculated:
    - Sewing Operation Count (STITCH_COUNT for MODE=1)
    - Sewing Skip Count (NEEDLE_RUNTIME for MODE=1)
    - Rework Operation Count (STITCH_COUNT for MODE=3)
    - Rework Skip Count (NEEDLE_RUNTIME for MODE=3)
    """
    # For Mode 1 (Sewing)
    sewing_logs = logs.filter(MODE=1)
    sewing_operation_count = sewing_logs.aggregate(total=Sum('STITCH_COUNT'))['total'] or 0
    sewing_skip_count = sewing_logs.aggregate(total=Sum('NEEDLE_RUNTIME'))['total'] or 0
    
    # For Mode 3 (Rework)
    rework_logs = logs.filter(MODE=3)
    rework_operation_count = rework_logs.aggregate(total=Sum('STITCH_COUNT'))['total'] or 0
    rework_skip_count = rework_logs.aggregate(total=Sum('NEEDLE_RUNTIME'))['total'] or 0
    
    # Get daily metrics breakdown
    daily_data = logs.values('DATE').annotate(
        sewing_operation_count=Sum(Case(
            When(MODE=1, then=F('STITCH_COUNT')),
            default=Value(0),
            output_field=IntegerField()
        )),
        sewing_skip_count=Sum(Case(
            When(MODE=1, then=F('NEEDLE_RUNTIME')),
            default=Value(0),
            output_field=FloatField()
        )),
        rework_operation_count=Sum(Case(
            When(MODE=3, then=F('STITCH_COUNT')),
            default=Value(0),
            output_field=IntegerField()
        )),
        rework_skip_count=Sum(Case(
            When(MODE=3, then=F('NEEDLE_RUNTIME')),
            default=Value(0),
            output_field=FloatField()
        ))
    ).order_by('DATE')
    
    # Format daily data for table
    formatted_table_data = []
    for data in daily_data:
        formatted_table_data.append({
            'Date': str(data['DATE']),
            'Sewing Operation Count': data['sewing_operation_count'] or 0,
            'Sewing Skip Count': round(data['sewing_skip_count'] or 0, 2),
            'Rework Operation Count': data['rework_operation_count'] or 0,
            'Rework Skip Count': round(data['rework_skip_count'] or 0, 2),
            'Machine ID': machine_id
        })
    
    return {
        "machineId": machine_id,
        "sewingMetrics": {
            "operationCount": sewing_operation_count,
            "skipCount": round(sewing_skip_count, 2)
        },
        "reworkMetrics": {
            "operationCount": rework_operation_count,
            "skipCount": round(rework_skip_count, 2)
        },
        "totalOperationCount": sewing_operation_count + rework_operation_count,
        "totalSkipCount": round(sewing_skip_count + rework_skip_count, 2),
        "tableData": formatted_table_data
    }

@api_view(['GET'])
def user_machine_operation_metrics(request, machine_id=None):
    """
    Calculate operation metrics for user machines (AFL):
    - Sewing Operation Count
    - Sewing Skip Count
    - Rework Operation Count
    - Rework Stitch Count

    Parameters:
        machine_id (optional): Specific machine ID to get metrics for
        from_date (optional): Start date filter (YYYY-MM-DD)
        to_date (optional): End date filter (YYYY-MM-DD)
        
    Returns:
        Metrics for user machines including operation and skip counts for both sewing and rework modes
    """
    try:
        # Get valid operator IDs from OperatorAFL model
        valid_operators = OperatorAFL.objects.values_list('rfid_card_no', flat=True)
        
        # Handle machine_id filter
        if machine_id and machine_id.lower() != 'all':
            logs = UserMachineLog.objects.filter(MACHINE_ID=machine_id, OPERATOR_ID__in=valid_operators)
        else:
            logs = UserMachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
            
    except UserMachineLog.DoesNotExist:
        return Response({"error": "Data not found"}, status=404)
    except ValueError:
        return Response({"error": "Invalid machine ID"}, status=400)

    # Get date filters from query parameters
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')

    # Apply date filtering if dates are provided
    if from_date_str:
        from datetime import datetime
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            logs = logs.filter(DATE__gte=from_date)
        except ValueError:
            return Response({"error": "Invalid from_date format. Use YYYY-MM-DD"}, status=400)

    if to_date_str:
        from datetime import datetime
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

    # IMPORTANT: For UserMachineLog, Mode 3 is "Rework" instead of "No feeding"
    # Get metrics by machine
    if machine_id and machine_id.lower() != 'all':
        # For single machine
        machine_metrics = calculate_user_machine_operation_metrics(logs, machine_id)
        return Response(machine_metrics)
    else:
        # For all machines
        machine_ids = logs.order_by('MACHINE_ID').values_list('MACHINE_ID', flat=True).distinct()
        all_machine_metrics = []
        
        for m_id in machine_ids:
            machine_logs = logs.filter(MACHINE_ID=m_id)
            try:
                metrics = calculate_user_machine_operation_metrics(machine_logs, m_id)
                all_machine_metrics.append(metrics)
            except Exception as e:
                print(f"Error processing machine {m_id}: {str(e)}")
                continue
        
        return Response({
            "allMachinesMetrics": all_machine_metrics,
            "totalMachines": len(all_machine_metrics),
            "from_date": from_date_str,
            "to_date": to_date_str
        })

def calculate_user_machine_operation_metrics(logs, machine_id):
    """
    Helper function to calculate operation metrics for a single user machine (AFL)
    
    Metrics calculated:
    - Sewing Operation Count (STITCH_COUNT for MODE=1)
    - Sewing Skip Count (NEEDLE_RUNTIME for MODE=1)
    - Rework Operation Count (STITCH_COUNT for MODE=3)
    - Rework Skip Count (NEEDLE_RUNTIME for MODE=3)
    
    Note: For UserMachineLog, Mode 3 is "Rework" instead of "No feeding"
    """
    # For Mode 1 (Sewing)
    sewing_logs = logs.filter(MODE=1)
    sewing_operation_count = sewing_logs.aggregate(total=Sum('STITCH_COUNT'))['total'] or 0
    sewing_skip_count = sewing_logs.aggregate(total=Sum('NEEDLE_RUNTIME'))['total'] or 0
    
    # For Mode 3 (Rework)
    rework_logs = logs.filter(MODE=3)
    rework_operation_count = rework_logs.aggregate(total=Sum('STITCH_COUNT'))['total'] or 0
    rework_skip_count = rework_logs.aggregate(total=Sum('NEEDLE_RUNTIME'))['total'] or 0
    
    # Get daily metrics breakdown
    daily_data = logs.values('DATE').annotate(
        sewing_operation_count=Sum(Case(
            When(MODE=1, then=F('STITCH_COUNT')),
            default=Value(0),
            output_field=IntegerField()
        )),
        sewing_skip_count=Sum(Case(
            When(MODE=1, then=F('NEEDLE_RUNTIME')),
            default=Value(0),
            output_field=FloatField()
        )),
        rework_operation_count=Sum(Case(
            When(MODE=3, then=F('STITCH_COUNT')),
            default=Value(0),
            output_field=IntegerField()
        )),
        rework_skip_count=Sum(Case(
            When(MODE=3, then=F('NEEDLE_RUNTIME')),
            default=Value(0),
            output_field=FloatField()
        ))
    ).order_by('DATE')
    
    # Format daily data for table
    formatted_table_data = []
    for data in daily_data:
        formatted_table_data.append({
            'Date': str(data['DATE']),
            'Sewing Operation Count': data['sewing_operation_count'] or 0,
            'Sewing Skip Count': round(data['sewing_skip_count'] or 0, 2),
            'Rework Operation Count': data['rework_operation_count'] or 0,
            'Rework Skip Count': round(data['rework_skip_count'] or 0, 2),
            'Machine ID': machine_id
        })
    
    return {
        "machineId": machine_id,
        "sewingMetrics": {
            "operationCount": sewing_operation_count,
            "skipCount": round(sewing_skip_count, 2)
        },
        "reworkMetrics": {
            "operationCount": rework_operation_count,
            "skipCount": round(rework_skip_count, 2)
        },
        "totalOperationCount": sewing_operation_count + rework_operation_count,
        "totalSkipCount": round(sewing_skip_count + rework_skip_count, 2),
        "tableData": formatted_table_data
    }
