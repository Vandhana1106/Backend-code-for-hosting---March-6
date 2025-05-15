@api_view(['GET'])
def get_consolidated_logs(request):
    """
    View to retrieve machine logs with summary calculations.
    Each machine contributes 10.17 hours per day (8:25 AM to 7:30 PM minus breaks).
    """
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    machine_id = request.query_params.get('machine_id')
    line_number = request.query_params.get('line_number')
    operator_name = request.query_params.get('operator_name')

    logs = MachineLog.objects.all()
    
    # Apply filters
    if from_date:
        logs = logs.filter(DATE__gte=from_date)
    if to_date:
        logs = logs.filter(DATE__lte=to_date)
    if machine_id:
        logs = logs.filter(MACHINE_ID=machine_id)
    if line_number:
        logs = logs.filter(LINE_NUMB=line_number)
    if operator_name:
        logs = logs.filter(operator_name=operator_name)
        
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

    # Constants
    WORKING_HOURS_PER_MACHINE_PER_DAY = 10.17  # 8:25 AM to 7:30 PM minus breaks (10h10m)
    
    # Get unique dates and machines in the filtered data
    unique_dates = logs.dates('DATE', 'day').distinct()
    unique_machines = logs.values('MACHINE_ID').distinct()
    
    # Calculate total possible working hours
    total_machines = len(unique_machines)
    total_days = len(unique_dates)
    total_hours = total_machines * total_days * WORKING_HOURS_PER_MACHINE_PER_DAY

    # Calculate summary data
    summary = {
        'total_hours': total_hours,
        'sewing_hours': 0,
        'idle_hours': 0,
        'meeting_hours': 0,
        'no_feeding_hours': 0,
        'maintenance_hours': 0,
        'total_stitch_count': 0,
        'total_needle_runtime': 0,
        'unique_machines': total_machines,
        'unique_dates': total_days,
        'hours_per_machine': WORKING_HOURS_PER_MACHINE_PER_DAY,
        'logs': []
    }

    # Process each log to calculate actual activity hours
    for log in logs:
        # Calculate duration in hours (already adjusted for breaks in query)
        duration = (log.end_seconds - log.start_seconds) / 3600
        
        # Categorize by mode
        mode = str(log.MODE).lower()
        if mode == '1' or mode == 'sewing':
            summary['sewing_hours'] += duration
            summary['total_needle_runtime'] += duration * 3600  # convert to seconds
        elif mode == '2' or mode == 'idle':
            summary['idle_hours'] += duration
        elif mode == '3' or mode == 'no feeding':
            summary['no_feeding_hours'] += duration
        elif mode == '4' or mode == 'meeting':
            summary['meeting_hours'] += duration
        elif mode == '5' or mode == 'maintenance':
            summary['maintenance_hours'] += duration
        
        # Add stitch count
        summary['total_stitch_count'] += log.STITCH_COUNT if log.STITCH_COUNT else 0

    # Calculate percentages
    if summary['total_hours'] > 0:
        summary['productive_percent'] = (summary['sewing_hours'] / summary['total_hours']) * 100
        summary['npt_percent'] = 100 - summary['productive_percent']
    else:
        summary['productive_percent'] = 0
        summary['npt_percent'] = 0
    
    # Calculate sewing speed (stitches per hour)
    if summary['sewing_hours'] > 0:
        summary['sewing_speed'] = summary['total_stitch_count'] / summary['sewing_hours']
    else:
        summary['sewing_speed'] = 0

    # Serialize the logs
    serialized_logs = MachineLogSerializer(logs, many=True).data
    for idx, log in enumerate(serialized_logs, start=1):
        log['index'] = idx

    response_data = {
        'summary': summary,
        'logs': serialized_logs,
        'filters': {
            'from_date': from_date,
            'to_date': to_date,
            'machine_id': machine_id,
            'line_number': line_number,
            'operator_name': operator_name
        }
    }

    return Response(response_data)
