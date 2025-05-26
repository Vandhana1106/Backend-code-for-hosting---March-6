# from django.db import models

# class MachineLog(models.Model):
#     """
#     Stores machine operational log data.
    
#     This model tracks machine usage metrics including runtime, operator information,
#     stitch counts, and operational time periods.
#     """
#     MACHINE_ID = models.IntegerField(help_text="Unique identifier for the machine")
#     LINE_NUMB = models.IntegerField(help_text="Production line number where the machine is located")
#     OPERATOR_ID = models.CharField(max_length=30, help_text="Identifier for the operator using the machine")
#     DATE = models.DateField(db_index=True, help_text="Date when the operation was performed")
#     START_TIME = models.TimeField(help_text="Time when operation started")
#     END_TIME = models.TimeField(help_text="Time when operation ended")
    
#     MODE = models.IntegerField(db_index=True, help_text="Operational mode of the machine")
#     STITCH_COUNT = models.IntegerField(help_text="Number of stitches performed during operation")
#     NEEDLE_RUNTIME = models.FloatField(help_text="Duration (in seconds) the needle was operational")
#     NEEDLE_STOPTIME = models.FloatField(help_text="Duration (in seconds) the needle was stopped")
#     Tx_LOGID = models.IntegerField(help_text="Transaction log identifier")
#     Str_LOGID = models.IntegerField(help_text="Storage log identifier")
#     DEVICE_ID = models.IntegerField(help_text="Unique identifier for the device component")
#     RESERVE = models.TextField(blank=True, null=True, help_text="Additional information or notes (optional)")
#     created_at = models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when the record was created")

#     class Meta:
#         indexes = [
#             models.Index(fields=['DATE']),
#             models.Index(fields=['created_at']),
#             models.Index(fields=['MODE']),
#         ]
        
#     def __str__(self):
#         return f"Machine {self.MACHINE_ID} - Line {self.LINE_NUMB} - {self.DATE}"

# class DuplicateLog(models.Model):
#     """
#     Logs duplicate data submissions.
    
#     This model stores copies of payloads that were identified as duplicates
#     to track and analyze potential duplicate submissions.
#     """
#     payload = models.JSONField(help_text="JSON data of the duplicate submission")
#     created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the duplicate was logged")
    
#     def __str__(self):
#         return f"Duplicate entry at {self.created_at}"


# class ModeMessage(models.Model):
#     """
#     Maps mode numbers to descriptive messages.
    
#     This model provides human-readable descriptions for different 
#     operational modes used by machines.
#     """
#     mode = models.IntegerField(unique=True, help_text="Unique mode identifier number")
#     message = models.TextField(help_text="Description or message associated with this mode")

#     def __str__(self):
#         return f"Mode {self.mode}: {self.message}"

# from django.db import models


# class Operator(models.Model):
#     """
#     Stores information about machine operators.
    
#     This model tracks operator identifiers and personal information for all
#     standard machine operators in the system.
#     """
#     rfid_card_no = models.CharField(max_length=20, unique=True, help_text="Unique RFID card number assigned to the operator")
#     operator_name = models.CharField(max_length=50, help_text="Full name of the operator")
#     remarks = models.CharField(max_length=100, blank=True, null=True, help_text="Additional notes about the operator")

#     def __str__(self):
#         return self.operator_name
    

# class OperatorAFL(models.Model):
#     """
#     Stores information about AFL-specific operators.
    
#     This model tracks RFID card numbers and personal information for operators
#     specifically working with AFL operations in the system.
#     """
#     rfid_card_no = models.CharField(max_length=20, unique=True, help_text="Unique RFID card number assigned to the AFL operator")
#     operatorAFL_name = models.CharField(max_length=50, default="", help_text="Full name of the AFL operator")
#     is_active = models.BooleanField(default=True, help_text="Indicates if the operator account is currently active")
#     created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the operator account was created")

#     def __str__(self):
#         return f"AFL Operator: {self.operatorAFL_name} ({self.rfid_card_no})"


# class UserMachineLog(models.Model):
#     """
#     Stores user-specific machine operational log data.
    
#     This model tracks machine usage metrics associated with specific users,
#     including runtime, stitch counts, and operational time periods.
#     Similar to MachineLog but with user-specific context.
#     """
#     MACHINE_ID = models.IntegerField(help_text="Unique identifier for the machine")
#     LINE_NUMB = models.IntegerField(help_text="Production line number where the machine is located")
#     OPERATOR_ID = models.CharField(max_length=30, help_text="Identifier for the operator using the machine")
#     DATE = models.DateField(db_index=True, help_text="Date when the operation was performed")
#     START_TIME = models.TimeField(help_text="Time when operation started")
#     END_TIME = models.TimeField(help_text="Time when operation ended")

#     MODE = models.IntegerField(db_index=True, help_text="Operational mode of the machine")
#     STITCH_COUNT = models.IntegerField(help_text="Number of stitches performed during operation")
#     NEEDLE_RUNTIME = models.FloatField(help_text="Duration (in seconds) the needle was operational")
#     NEEDLE_STOPTIME = models.FloatField(help_text="Duration (in seconds) the needle was stopped")
#     Tx_LOGID = models.IntegerField(help_text="Transaction log identifier")
#     Str_LOGID = models.IntegerField(help_text="Storage log identifier")
#     DEVICE_ID = models.IntegerField(help_text="Unique identifier for the device component")
#     RESERVE = models.TextField(blank=True, null=True, help_text="Additional information or notes (optional)")
#     created_at = models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when the record was created")

#     class Meta:
#         indexes = [
#             models.Index(fields=['DATE']),
#             models.Index(fields=['created_at']),
#             models.Index(fields=['MODE']),
#         ]
        
#     def __str__(self):
#         return f"User Machine {self.MACHINE_ID} - Line {self.LINE_NUMB} - {self.DATE} - Operator {self.OPERATOR_ID}"

from django.db import models

from django.db import models

class MachineLog(models.Model):
    MACHINE_ID = models.IntegerField()
    LINE_NUMB = models.IntegerField()
    OPERATOR_ID = models.CharField(max_length=30)
    DATE = models.DateField(db_index=True)  # Index added
    START_TIME = models.TimeField()
    END_TIME = models.TimeField()
    
    MODE = models.IntegerField(db_index=True)  # Index added
    STITCH_COUNT = models.IntegerField()
    NEEDLE_RUNTIME = models.FloatField()
    NEEDLE_STOPTIME = models.FloatField()
    Tx_LOGID = models.IntegerField()
    Str_LOGID = models.IntegerField()
    DEVICE_ID = models.IntegerField()
    RESERVE = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  # Index added

    class Meta:
        indexes = [
            models.Index(fields=['DATE']),
            models.Index(fields=['created_at']),
            models.Index(fields=['MODE']),
        ]
class DuplicateLog(models.Model):
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

class ModeMessage(models.Model):
    mode = models.IntegerField(unique=True)
    message = models.TextField()

    def __str__(self):
        return f"Mode {self.mode}: {self.message}"

from django.db import models

class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)

    def __str__(self):
        return self.username

class Operator(models.Model):
    rfid_card_no = models.CharField(max_length=20, unique=True)
    operator_name = models.CharField(max_length=50)
    remarks = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.operator_name




class UserMachineLog(models.Model):
    MACHINE_ID = models.IntegerField()
    LINE_NUMB = models.IntegerField()
    OPERATOR_ID = models.CharField(max_length=30)
    DATE = models.DateField(db_index=True)
    START_TIME = models.TimeField()
    END_TIME = models.TimeField()

    MODE = models.IntegerField(db_index=True)
    STITCH_COUNT = models.IntegerField()
    NEEDLE_RUNTIME = models.FloatField()
    NEEDLE_STOPTIME = models.FloatField()
    Tx_LOGID = models.IntegerField()
    Str_LOGID = models.IntegerField()
    DEVICE_ID = models.IntegerField()
    RESERVE = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['DATE']),
            models.Index(fields=['created_at']),
            models.Index(fields=['MODE']),
        ]


class OperatorAFL(models.Model):
    """Model to store specific RFID card numbers for AFL operators"""
    rfid_card_no = models.CharField(max_length=20, unique=True)
    operatorAFL_name = models.CharField(max_length=50, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AFL Operator: {self.operatorAFL_name} ({self.rfid_card_no})"
