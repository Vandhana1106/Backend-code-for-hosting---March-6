from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import OperatorAFL, Operator
from django.db.models import Q

@api_view(['GET'])
def get_afl_operators(request):
    """
    Get all AFL operators with their active status
    """
    afl_operators = OperatorAFL.objects.all().order_by('rfid_card_no')
    
    # Get all regular operators for name mapping
    all_operators = {op.rfid_card_no: op.operator_name for op in Operator.objects.all()}
    
    result = []
    for afl_op in afl_operators:
        operator_name = all_operators.get(afl_op.rfid_card_no, "Unknown")
        result.append({
            "rfid_card_no": afl_op.rfid_card_no,
            "operator_name": operator_name,
            "is_active": afl_op.is_active,
            "created_at": afl_op.created_at
        })
    
    return Response(result)

@api_view(['POST'])
def add_afl_operator(request):
    """
    Add a new AFL operator or update existing one
    """
    rfid_card_no = request.data.get('rfid_card_no')
    is_active = request.data.get('is_active', True)
    
    if not rfid_card_no:
        return Response({"error": "RFID card number is required"}, status=400)
    
    # Check if operator exists in the main Operator table
    try:
        operator = Operator.objects.get(rfid_card_no=rfid_card_no)
    except Operator.DoesNotExist:
        return Response({"error": f"Operator with RFID {rfid_card_no} does not exist in main operators database"}, status=404)
    
    # Create or update the AFL operator entry
    afl_operator, created = OperatorAFL.objects.update_or_create(
        rfid_card_no=rfid_card_no,
        defaults={'is_active': is_active}
    )
    
    return Response({
        "rfid_card_no": afl_operator.rfid_card_no,
        "operator_name": operator.operator_name,
        "is_active": afl_operator.is_active,
        "created_at": afl_operator.created_at,
        "created": created
    })

@api_view(['DELETE'])
def delete_afl_operator(request, rfid_card_no):
    """
    Remove an AFL operator
    """
    try:
        operator = OperatorAFL.objects.get(rfid_card_no=rfid_card_no)
        operator.delete()
        return Response({"success": f"Operator with RFID {rfid_card_no} removed from AFL operators"})
    except OperatorAFL.DoesNotExist:
        return Response({"error": f"AFL Operator with RFID {rfid_card_no} not found"}, status=404)

@api_view(['PATCH'])
def update_afl_operator_status(request, rfid_card_no):
    """
    Update the active status of an AFL operator
    """
    is_active = request.data.get('is_active')
    
    if is_active is None:
        return Response({"error": "is_active status is required"}, status=400)
    
    try:
        operator = OperatorAFL.objects.get(rfid_card_no=rfid_card_no)
        operator.is_active = is_active
        operator.save()
        
        # Get operator name
        try:
            main_operator = Operator.objects.get(rfid_card_no=rfid_card_no)
            operator_name = main_operator.operator_name
        except Operator.DoesNotExist:
            operator_name = "Unknown"
        
        return Response({
            "rfid_card_no": operator.rfid_card_no,
            "operator_name": operator_name,
            "is_active": operator.is_active,
            "created_at": operator.created_at
        })
    except OperatorAFL.DoesNotExist:
        return Response({"error": f"AFL Operator with RFID {rfid_card_no} not found"}, status=404)
