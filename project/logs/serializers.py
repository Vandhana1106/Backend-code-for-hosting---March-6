"""
This module provides Django Rest Framework serializers for the logging application.
It handles conversion between JSON and Python objects for all model instances.
"""
# Standard library imports
from datetime import datetime

# Third-party imports
from rest_framework import serializers

# Local application imports
from .models import (
    MachineLog, ModeMessage, Operator, 
    UserMachineLog, OperatorAFL
)
from .constants import MODES


class MachineLogSerializer(serializers.ModelSerializer):
    """
    Serializer for MachineLog model.
    
    Handles conversion between JSON and MachineLog model instances,
    with additional fields for operator name and mode description.
    """
    # Define custom fields
    DATE = serializers.CharField()  # Accept date as a string initially
    START_TIME = serializers.CharField()  # Accept time as a string initially
    END_TIME = serializers.CharField()  # Accept time as a string initially
    operator_name = serializers.SerializerMethodField()
    mode_description = serializers.SerializerMethodField()

    class Meta:
        model = MachineLog
        fields = '__all__'  # Include all model fields plus the custom fields defined above

    def get_operator_name(self, obj):
        """Get operator name based on OPERATOR_ID."""
        try:
            operator = Operator.objects.get(rfid_card_no=obj.OPERATOR_ID)
            return operator.operator_name
        except Operator.DoesNotExist:
            return None

    def get_mode_description(self, obj):
        """Get mode description from ModeMessage model or MODES dictionary."""
        # First try to get from ModeMessage model
        mode_message = ModeMessage.objects.filter(mode=obj.MODE).first()
        if mode_message:
            return mode_message.message
        
        # Fall back to MODES dictionary if no database record found
        return MODES.get(obj.MODE, "N/A")

    def validate_DATE(self, value):
        """Validate and convert date string to date object."""
        try:
            date_obj = datetime.strptime(value, '%Y:%m:%d').date()
            return date_obj
        except ValueError:
            raise serializers.ValidationError("Date must be in YYYY:MM:DD format")

    def validate_START_TIME(self, value):
        """Validate start time format."""
        return self._validate_time(value)

    def validate_END_TIME(self, value):
        """Validate end time format."""
        return self._validate_time(value)

    def _validate_time(self, value):
        """Helper method to validate and convert time strings to time objects."""
        try:
            parts = value.split(':')
            if len(parts) == 3:
                hour, minute, second = parts
                time_str = f"{int(hour):02d}:{int(minute):02d}:{int(second):02d}"
            elif len(parts) == 2:
                hour, minute = parts
                time_str = f"{int(hour):02d}:{int(minute):02d}:00"
            else:
                raise ValueError("Invalid time format")
            time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
            return time_obj
        except ValueError:
            raise serializers.ValidationError("Time must be in HH:MM:SS format")







class UserMachineLogSerializer(serializers.ModelSerializer):
    """
    Serializer for UserMachineLog model.
    
    Handles user-specific machine log data with enhanced field validation
    and additional derived fields.
    """
    # Define fields with appropriate formats and validation
    DATE = serializers.DateField(format='%Y-%m-%d', 
                                input_formats=['%Y-%m-%d', '%Y:%m:%d'], 
                                required=False)
    START_TIME = serializers.TimeField(format='%H:%M:%S', 
                                      input_formats=['%H:%M:%S', '%H:%M'], 
                                      required=False)
    END_TIME = serializers.TimeField(format='%H:%M:%S', 
                                    input_formats=['%H:%M:%S', '%H:%M'], 
                                    required=False)
    operator_name = serializers.SerializerMethodField()
    mode_description = serializers.SerializerMethodField()
    
    class Meta:
        model = UserMachineLog
        fields = [
            'id', 'MACHINE_ID', 'LINE_NUMB', 'OPERATOR_ID', 'DATE', 'START_TIME', 'END_TIME',
            'MODE', 'STITCH_COUNT', 'NEEDLE_RUNTIME', 'NEEDLE_STOPTIME', 'Tx_LOGID',
            'Str_LOGID', 'DEVICE_ID', 'RESERVE', 'created_at', 'operator_name', 'mode_description'
        ]
        
    def get_operator_name(self, obj):
        """
        Get operator name from either Operator or OperatorAFL models.
        
        Handles different storage formats and returns appropriate fallbacks if not found.
        """
        try:
            # Return empty string for null or zero operator IDs
            if not obj.OPERATOR_ID or obj.OPERATOR_ID == '0':
                return ''
                
            # Check in both Operator and OperatorAFL tables
            # First try Operator model with exact match
            operator = Operator.objects.filter(rfid_card_no=obj.OPERATOR_ID).first()
            if operator:
                return operator.operator_name
            
            # Then try OperatorAFL model with exact match
            operator_afl = OperatorAFL.objects.filter(rfid_card_no=obj.OPERATOR_ID).first()
            if operator_afl:
                return operator_afl.operatorAFL_name
            
            # If no exact match, try converting OPERATOR_ID to string (in case it's stored differently)
            operator_id_str = str(obj.OPERATOR_ID)
            
            # Try regular Operator with string conversion
            operator = Operator.objects.filter(rfid_card_no=operator_id_str).first()
            if operator:
                return operator.operator_name
            
            # Try OperatorAFL with string conversion
            operator_afl = OperatorAFL.objects.filter(rfid_card_no=operator_id_str).first()
            if operator_afl:
                return operator_afl.operatorAFL_name
                
            # If no match found, return a formatted unknown string
            return f"Unknown ({obj.OPERATOR_ID})"
        except Exception as e:
            # Log error and return formatted error string
            print(f"Error getting operator name: {e}")
            return f"Error ({obj.OPERATOR_ID})"

    def get_mode_description(self, obj):
        """
        Get mode description from ModeMessage model or MODES dictionary.
        
        Handles null modes and provides appropriate fallbacks if description not found.
        """
        try:
            if obj.MODE is None:
                return ''
                
            # Try to get description from ModeMessage model
            mode_message = ModeMessage.objects.filter(mode=obj.MODE).first()
            if mode_message and mode_message.message:
                return mode_message.message
            
            # Fall back to MODES dictionary if no database record found
            mode_description = MODES.get(obj.MODE)
            if mode_description:
                return mode_description
                
            # If all else fails, return a default with the mode number
            return f"Mode {obj.MODE}"
        except Exception as e:
            # Log error and return formatted error string
            print(f"Error getting mode description: {e}")
            return f"Mode {obj.MODE}"
