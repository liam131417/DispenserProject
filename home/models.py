from django.db import models

class Dispenser(models.Model):
    name = models.CharField(max_length=50)
    medicine_name = models.CharField(max_length=50)

class Threshold(models.Model):
    TEMP_THRESHOLD = models.FloatField(default=0.0)
    HUMID_THRESHOLD = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)
