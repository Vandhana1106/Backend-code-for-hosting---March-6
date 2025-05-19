# from django.db.models import Sum, Case, When, Value, FloatField, F, ExpressionWrapper, Q, IntegerField, Avg, Count
# from django.db.models.functions import ExtractHour, ExtractMinute, ExtractSecond, Cast
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from datetime import datetime
# from .models import UserMachineLog, OperatorAFL

# def process_machine_data_afl(logs, machine_id):
#     """Helper function to process data for a single machine for AFL operators"""
#     # Calculate total working days and available hours (11 hours per day)
#     distinct_dates = logs.dates('DATE', 'day')
#     total_working_days = distinct_dates.count()
#     total_available_hours = total_working_days * 11

#     # Get aggregated data by date
#     daily_data = logs.values('DATE').annotate(
#         sewing_hours=Sum(Case(
#             When(MODE=1, then=F('duration_hours')),
#             default=Value(0),
#             output_field=FloatField()
#         )),
#         no_feeding_hours=Sum(Case(
#             When(MODE=3, then=F('duration_hours')),
#             default=Value(0),
#             output_field=FloatField()
#         )),
#         meeting_hours=Sum(Case(
#             When(MODE=4, then=F('duration_hours')),
#             default=Value(0),
#             output_field=FloatField()
#         )),
#         maintenance_hours=Sum(Case(
#             When(MODE=5, then=F('duration_hours')),
#             default=Value(0),
#             output_field=FloatField()
#         )),
#         idle_hours=Sum(Case(
#             When(MODE=2, then=F('duration_hours')),
#             default=Value(0),
#             output_field=FloatField()
#         )),
#         total_stitch_count=Sum('STITCH_COUNT'),
#         sewing_speed=Avg(Case(
#             When(reserve_numeric__gt=0, then=F('reserve_numeric')),
#             default=Value(0),
#             output_field=FloatField()
#         )),
#         needle_runtime=Sum('NEEDLE_RUNTIME')
#     ).order_by('DATE')

#     # Calculate totals
#     total_sewing_hours = 0
#     total_no_feeding_hours = 0
#     total_meeting_hours = 0
#     total_maintenance_hours = 0
#     total_idle_hours = 0
#     total_stitch_count = 0
#     total_needle_runtime = 0
#     total_hours = 0

#     formatted_table_data = []
#     for data in daily_data:
#         sewing_hours = data['sewing_hours'] or 0
#         no_feeding_hours = data['no_feeding_hours'] or 0
#         meeting_hours = data['meeting_hours'] or 0
#         maintenance_hours = data['maintenance_hours'] or 0
#         idle_hours = data['idle_hours'] or 0
        
#         # Calculate PT and NPT
#         productive_time = sewing_hours
#         non_productive_time = no_feeding_hours + meeting_hours + maintenance_hours + idle_hours
#         daily_total_hours = productive_time + non_productive_time
        
#         # Accumulate to total hours
#         total_hours += daily_total_hours
        
#         # Calculate percentages
#         productive_time_percentage = (productive_time / daily_total_hours * 100) if daily_total_hours > 0 else 0
#         non_productive_time_percentage = (non_productive_time / daily_total_hours * 100) if daily_total_hours > 0 else 0
        
#         formatted_table_data.append({
#             'Date': str(data['DATE']),
#             'Sewing Hours (PT)': round(sewing_hours, 2),
#             'No Feeding Hours': round(no_feeding_hours, 2),
#             'Meeting Hours': round(meeting_hours, 2),
#             'Maintenance Hours': round(maintenance_hours, 2),
#             'Idle Hours': round(idle_hours, 2),
#             'Total Hours': round(daily_total_hours, 2),
#             'Productive Time (PT) %': round(productive_time_percentage, 2),
#             'Non-Productive Time (NPT) %': round(non_productive_time_percentage, 2),
#             'Sewing Speed': round(data['sewing_speed'], 2),
#             'Stitch Count': data['total_stitch_count'],
#             'Needle Runtime': data['needle_runtime'],
#             'Machine ID': machine_id
#         })

#         # Accumulate totals
#         total_sewing_hours += sewing_hours
#         total_no_feeding_hours += no_feeding_hours
#         total_meeting_hours += meeting_hours
#         total_maintenance_hours += maintenance_hours
#         total_idle_hours += idle_hours
#         total_stitch_count += data['total_stitch_count'] or 0
#         total_needle_runtime += data['needle_runtime'] or 0

#     # Calculate overall PT and NPT
#     total_productive_time = total_sewing_hours
#     total_non_productive_time = (
#         total_no_feeding_hours + 
#         total_meeting_hours + 
#         total_maintenance_hours + 
#         total_idle_hours
#     )
    
#     # Calculate overall percentages
#     total_productive_percentage = (total_productive_time / total_hours * 100) if total_hours > 0 else 0
#     total_non_productive_percentage = (total_non_productive_time / total_hours * 100) if total_hours > 0 else 0

#     # Calculate average sewing speed
#     valid_speed_logs = logs.filter(reserve_numeric__gt=0)
#     average_sewing_speed = valid_speed_logs.aggregate(
#         avg_speed=Avg('reserve_numeric')
#     )['avg_speed'] or 0

#     return {
#         "machineId": machine_id,
#         "totalAvailableHours": total_available_hours,
#         "totalWorkingDays": total_working_days,
#         "totalHours": round(total_hours, 2),
#         "totalProductiveTime": {
#             "hours": round(total_productive_time, 2),
#             "percentage": round(total_productive_percentage, 2)
#         },
#         "totalNonProductiveTime": {
#             "hours": round(total_non_productive_time, 2),
#             "percentage": round(total_non_productive_percentage, 2),
#             "breakdown": {
#                 "noFeedingHours": round(total_no_feeding_hours, 2),
#                 "meetingHours": round(total_meeting_hours, 2),
#                 "maintenanceHours": round(total_maintenance_hours, 2),
#                 "idleHours": round(total_idle_hours, 2)
#             }
#         },
#         "totalStitchCount": total_stitch_count,
#         "averageSewingSpeed": round(average_sewing_speed, 2),
#         "totalNeedleRuntime": round(total_needle_runtime, 2),
#         "tableData": formatted_table_data
#     }

# @api_view(['GET'])
# def afl_machine_reports(request, machine_id):
#     try:
#         # Get valid operator IDs from OperatorAFL model
#         valid_operators = OperatorAFL.objects.filter(is_active=True).values_list('rfid_card_no', flat=True)
        
#         # Handle "all" case - convert machine_id to string first
#         machine_id_str = str(machine_id)
#         if machine_id_str.lower() == 'all':
#             logs = UserMachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
#             all_machines = True
#         else:
#             logs = UserMachineLog.objects.filter(MACHINE_ID=machine_id, OPERATOR_ID__in=valid_operators)
#             all_machines = False
#     except UserMachineLog.DoesNotExist:
#         return Response({"error": "Data not found"}, status=404)
#     except ValueError:
#         return Response({"error": "Invalid machine ID"}, status=400)

#     # Get date filters from query parameters
#     from_date_str = request.GET.get('from_date', '')
#     to_date_str = request.GET.get('to_date', '')

#     # Apply date filtering if dates are provided
#     if from_date_str:
#         from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
#         logs = logs.filter(DATE__gte=from_date)

#     if to_date_str:
#         to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
#         logs = logs.filter(DATE__lte=to_date)

#     # Calculate duration in hours for each log entry
#     logs = logs.annotate(
#         start_seconds=ExpressionWrapper(
#             ExtractHour('START_TIME') * 3600 + 
#             ExtractMinute('START_TIME') * 60 + 
#             ExtractSecond('START_TIME'),
#             output_field=FloatField()
#         ),
#         end_seconds=ExpressionWrapper(
#             ExtractHour('END_TIME') * 3600 + 
#             ExtractMinute('END_TIME') * 60 + 
#             ExtractSecond('END_TIME'),
#             output_field=FloatField()
#         ),
#         duration_hours=ExpressionWrapper(
#             (F('end_seconds') - F('start_seconds')) / 3600,
#             output_field=FloatField()
#         ),
#         reserve_numeric=Cast('RESERVE', output_field=IntegerField())
#     )

#     # Filter for working hours (8:25 AM to 7:35 PM)
#     logs = logs.filter(
#         start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
#         end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
#     )

#     # Exclude specific break periods (entirely within these ranges)
#     logs = logs.exclude(
#         Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
#         Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
#         Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
#     )

#     # For "all" case, we'll group by machine ID
#     if all_machines:
#         # Get distinct machine IDs
#         machine_ids = logs.order_by('MACHINE_ID').values_list('MACHINE_ID', flat=True).distinct()
        
#         all_machine_reports = []
        
#         for machine_id in machine_ids:
#             machine_logs = logs.filter(MACHINE_ID=machine_id)
            
#             # Process data for this machine
#             machine_report = process_machine_data_afl(machine_logs, machine_id)
#             all_machine_reports.append(machine_report)
        
#         return Response({
#             "allMachinesReport": all_machine_reports,
#             "totalMachines": len(all_machine_reports)
#         })
#     else:
#         # Process single machine data
#         machine_report = process_machine_data_afl(logs, machine_id)
#         return Response(machine_report)


# @api_view(['GET'])
# def afl_all_machines_report(request):
#     try:
#         # Get valid operator IDs from OperatorAFL model
#         valid_operators = OperatorAFL.objects.filter(is_active=True).values_list('rfid_card_no', flat=True)
#         logs = UserMachineLog.objects.filter(OPERATOR_ID__in=valid_operators)
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)

#     # Get date filters from query parameters
#     from_date_str = request.GET.get('from_date', '')
#     to_date_str = request.GET.get('to_date', '')

#     # Apply date filtering if dates are provided
#     if from_date_str:
#         try:
#             from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
#             logs = logs.filter(DATE__gte=from_date)
#         except ValueError:
#             return Response({"error": "Invalid from_date format. Use YYYY-MM-DD"}, status=400)

#     if to_date_str:
#         try:
#             to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
#             logs = logs.filter(DATE__lte=to_date)
#         except ValueError:
#             return Response({"error": "Invalid to_date format. Use YYYY-MM-DD"}, status=400)

#     # Calculate duration in hours for each log entry
#     logs = logs.annotate(
#         start_seconds=ExpressionWrapper(
#             ExtractHour('START_TIME') * 3600 + 
#             ExtractMinute('START_TIME') * 60 + 
#             ExtractSecond('START_TIME'),
#             output_field=FloatField()
#         ),
#         end_seconds=ExpressionWrapper(
#             ExtractHour('END_TIME') * 3600 + 
#             ExtractMinute('END_TIME') * 60 + 
#             ExtractSecond('END_TIME'),
#             output_field=FloatField()
#         ),
#         duration_hours=ExpressionWrapper(
#             (F('end_seconds') - F('start_seconds')) / 3600,
#             output_field=FloatField()
#         ),
#         reserve_numeric=Cast('RESERVE', output_field=IntegerField())
#     ).filter(
#         start_seconds__gte=30300,  # 8:25 AM (8.416667 * 3600)
#         end_seconds__lte=70500     # 7:35 PM (19.583333 * 3600)
#     ).exclude(
#         Q(start_seconds__gte=37800, end_seconds__lte=38400) |  # 10:30-10:40
#         Q(start_seconds__gte=48000, end_seconds__lte=50400) |  # 13:20-14:00
#         Q(start_seconds__gte=58800, end_seconds__lte=59400)    # 16:20-16:30
#     )

#     # Get distinct machine IDs
#     machine_ids = logs.order_by('MACHINE_ID').values_list('MACHINE_ID', flat=True).distinct()
    
#     all_machine_reports = []
    
#     for machine_id in machine_ids:
#         machine_logs = logs.filter(MACHINE_ID=machine_id)
        
#         # Process data for this machine
#         try:
#             machine_report = process_machine_data_afl(machine_logs, machine_id)
#             all_machine_reports.append(machine_report)
#         except Exception as e:
#             print(f"Error processing machine {machine_id}: {str(e)}")
#             continue
    
#     return Response({
#         "allMachinesReport": all_machine_reports,
#         "totalMachines": len(all_machine_reports),
#         "from_date": from_date_str,
#         "to_date": to_date_str
#     })
