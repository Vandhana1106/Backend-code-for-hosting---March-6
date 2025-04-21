from django.db import models

from django.db import models

class MachineLog(models.Model):
    MACHINE_ID = models.IntegerField()
    LINE_NUMB = models.IntegerField()
    OPERATOR_ID = models.CharField(max_length=30)
    DATE = models.DateField()
    START_TIME = models.TimeField()
    END_TIME = models.TimeField()
    
    MODE = models.IntegerField()
    STITCH_COUNT = models.IntegerField()
    NEEDLE_RUNTIME = models.FloatField()
    NEEDLE_STOPTIME = models.FloatField()
    Tx_LOGID = models.IntegerField()
    Str_LOGID = models.IntegerField()
    DEVICE_ID = models.IntegerField()
    RESERVE = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        pass

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