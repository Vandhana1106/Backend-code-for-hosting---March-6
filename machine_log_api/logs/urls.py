from django.urls import path
from .views import *

urlpatterns = [
    path('log/', log_machine_data, name='log-machine-data'),
    path('logs/', get_machine_logs, name='get-machine-logs'),
    path('user_login/', user_login, name='user_login'),
    path('machine_count/', get_machine_id_count, name='get_machine_count'),  
    path('line_count/', get_line_number_count, name='get_line_count'),  
    path('calculate_efficiency/', calculate_line_efficiency, name='calculate_efficiency'),
    path('calculate_operator_efficiency/', calculate_operator_efficiency, name='calculate_operator_efficiency'),
    path('api/calculate_operator_efficiency/',calculate_operator_efficiency, name='calculate_operator_efficiency'),
]
