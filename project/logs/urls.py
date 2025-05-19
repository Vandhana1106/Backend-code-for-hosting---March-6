from django.urls import path
from .views import *

urlpatterns = [
    path('log/', log_machine_data, name='log-machine-data'),
    path('logs/', get_machine_logs, name='get-machine-logs'),
    path('get_consolidated_logs/', get_consolidated_logs, name='get_consolidated_logs/'),
    path('user_login/', user_login, name='user_login'),
    path('register_user/', register_user, name='register_user'),  # New user registration endpoint
    path('admin_login/', admin_login, name='admin_login'),  # New admin login endpoint
    path('register_admin/', register_admin_user, name='register_admin_user'),  # Register new admin user
    path('admin/logs/', get_admin_machine_logs, name='get-admin-machine-logs'),  # Admin logs endpoint
    path('admin/log/', admin_log_machine_data, name='admin-log-machine-data'),  # Admin log machine data endpoint
    path('machine_count/', get_machine_id_count, name='get_machine_count'),  
    path('line_count/', get_line_number_count, name='get_line_count'),  
    path('calculate_efficiency/', calculate_line_efficiency, name='calculate_efficiency'),
    path('calculate_operator_efficiency/', calculate_operator_efficiency, name='calculate_operator_efficiency'),
    path('calculate_operator_efficiency/',calculate_operator_efficiency, name='calculate_operator_efficiency'),
    path('operator_report_by_name/<str:operator_name>/', operator_reports_by_name, name='operator_reports_by_name'),
    path('line-reports/<int:line_number>/', line_reports, name='line-reports'),
    path('line-reports/<str:line_number>/', line_reports, name='line-reports'),
    path('machines/<str:machine_id>/reports/', machine_reports, name='machine-reports'),
    path('machines/<str:machine_id>/reports/', machine_reports),
    path('machines/all/reports/', all_machines_report),
    path('operator_reports/', operator_reports_all, name='operator_reports_all'),
    
    path('logs/filter/', filter_logs, name='filter-logs'),
    path('logs/machine-filter',filter_logs_by_machine_id, name='filter-logs-by-machine-id'),
    path('logs/line-numbers/', get_line_numbers, name='get-line-numbers'),
    path('logs/machine-ids/',  get_machine_ids, name=' get_machine_ids'),



    path('user-machine-log/', log_user_machine_data, name='log-user-machine-data'),
    path('user-machine-logs/', get_user_machine_logs, name='get-user-machine-logs'),
    
]
