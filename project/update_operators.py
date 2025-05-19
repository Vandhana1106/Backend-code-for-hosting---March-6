import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'machine_log_api.settings')
django.setup()

from logs.models import OperatorAFL

# Get all OperatorAFL records
operators = OperatorAFL.objects.all()

# Check if there are 5 operators as mentioned
count = operators.count()
print(f"Found {count} OperatorAFL records")

# Update operator names to OPERATOR-41 through OPERATOR-45
if count > 0:
    # If there are exactly 5 records, we'll assign them sequentially
    if count == 5:
        for idx, operator in enumerate(operators):
            operator_name = f"OPERATOR-{41+idx}"
            operator.operatorAFL_name = operator_name
            operator.save()
            print(f"Updated operator {operator.rfid_card_no} to {operator_name}")
    # If there are fewer or more than 5, we'll update them but note this discrepancy
    else:
        print(f"Warning: Found {count} operators instead of the expected 5")
        for idx, operator in enumerate(operators):
            # We'll still assign names, but we'll note if we're going out of the expected range
            operator_num = 41 + idx
            operator_name = f"OPERATOR-{operator_num}"
            operator.operatorAFL_name = operator_name
            operator.save()
            print(f"Updated operator {operator.rfid_card_no} to {operator_name}")
else:
    print("No OperatorAFL records found. Please add operators first.")

print("Operation completed.")
