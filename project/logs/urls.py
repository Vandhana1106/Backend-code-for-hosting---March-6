from django.urls import path
from .views import *
from .views_user_afl_reports import machine_reports as user_afl_machine_reports
from .views_user_afl_reports import all_machines_report as user_afl_all_machines_report
from .views_user_afl_reports import operatorAFL_reports_by_name
from .views_user_afl import get_consolidated_user_AFL_logs
from .views_operation_metrics import machine_operation_metrics, user_machine_operation_metrics
# from .views_afl_reports import afl_machine_reports, afl_all_machines_report


urlpatterns = [
    path('log/', log_machine_data, name='log-machine-data'),
    path('logs/', get_machine_logs, name='get-machine-logs'),
    path('get_consolidated_logs/', get_consolidated_logs, name='get_consolidated_logs/'),
    path('user_login/', user_login, name='user_login'),
   
    path('machine_count/', get_machine_id_count, name='get_machine_count'),  
    path('line_count/', get_line_number_count, name='get_line_count'),  
    path('calculate_efficiency/', calculate_line_efficiency, name='calculate_efficiency'),
    path('calculate_operator_efficiency/', calculate_operator_efficiency, name='calculate_operator_efficiency'),
    path('api/calculate_operator_efficiency/',calculate_operator_efficiency, name='calculate_operator_efficiency'),
    path('operator_report_by_name/<str:operator_name>/', operator_reports_by_name, name='operator_reports_by_name'),
    path('line-reports/<int:line_number>/', line_reports, name='line-reports'),
    path('line-reports/<str:line_number>/', line_reports, name='line-reports'),
    path('machines/<str:machine_id>/reports/', machine_reports, name='machine-reports'),
    path('machines/<str:machine_id>/reports/', machine_reports),
    path('machines/all/reports/', all_machines_report),
   
    
    
    
    path('logs/filter/', filter_logs, name='filter-logs'),
    
    path('logs/line-numbers/', get_line_numbers, name='get-line-numbers'),
    


    # path('user-machine-log/', log_user_machine_data, name='log-user-machine-data'),
    # path('user-machine-logs/', get_user_machine_logs, name='get-user-machine-logs'),




    # path('user-machine-reports/<str:machine_id>/', user_afl_machine_reports, name='user-machine-reports'),
    # path('user-all-machines-report/', user_afl_all_machines_report, name='user-all-machines-report'),
    # path('operatorAFL_report_by_name/<str:operator_name>/', operatorAFL_reports_by_name, name='operatorAFL_reports_by_name'),
    # path('get_consolidated_user_AFL_logs/', get_consolidated_user_AFL_logs, name='get_consolidated_user_AFL_logs'),



    # path('api/afl/machines/<str:machine_id>/reports/', afl_machine_reports, name='afl_machine_reports'),
    
    
    # path('api/afl/machines/reports/', afl_all_machines_report, name='afl_all_machines_report'),
    # path('api/operator-afl-reports/<str:operator_name>/', operator_afl_reports_by_name, name='operator_afl_reports_by_name'),
    
    # path('api/user-line-reports/<str:line_number>/', user_line_reports, name='user_line_reports'),
    # path('api/filter-user-logs/', filter_user_logs, name='filter_user_logs'),
    # path('api/get-user-line-numbers/', get_user_line_numbers, name='get_user_line_numbers'),
    
   
  
]