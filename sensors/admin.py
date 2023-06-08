from django.contrib import admin

# Register your models here.
from .models import HumiditySensor, MotionSensor, UltrasonicSensor,MedicalDispensor,DispenseRecord

admin.site.register(HumiditySensor)
admin.site.register(MotionSensor)
admin.site.register(UltrasonicSensor)
admin.site.register(MedicalDispensor)
admin.site.register(DispenseRecord)
