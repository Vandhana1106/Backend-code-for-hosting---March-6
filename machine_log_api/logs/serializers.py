from rest_framework import serializers
from .models import MachineLog, ModeMessage
from datetime import datetime

class MachineLogSerializer(serializers.ModelSerializer):
    DATE = serializers.CharField()  # Accept date as a string initially
    START_TIME = serializers.CharField()  # Accept time as a string initially
    END_TIME = serializers.CharField()  # Accept time as a string initially
    
    class Meta:
        model = MachineLog
        fields = '__all__'

    def get_mode_description(self, obj):
        mode_message = ModeMessage.objects.filter(mode=obj.mode).first()
        return mode_message.message if mode_message else "N/A"
    
    def validate_DATE(self, value):
        """Validate and convert date from YYYY:MM:DD format"""
        try:
            date_obj = datetime.strptime(value, '%Y:%m:%d').date()
            return date_obj
        except ValueError:
            raise serializers.ValidationError("Date must be in YYYY:MM:DD format")
    
    def validate_START_TIME(self, value):
        """Validate and normalize time format"""
        try:
            # Handle single-digit hours and minutes
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
    
    def validate_END_TIME(self, value):
        """Validate and normalize time format"""
        try:
            # Handle single-digit hours and minutes
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