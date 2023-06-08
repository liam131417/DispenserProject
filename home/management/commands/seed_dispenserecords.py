from django.core.management.base import BaseCommand
from sensors.models import DispenseRecord
from sensors.models import MedicalDispensor
from random import randint
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Seeds the DispenseRecord model with random data for the last 365 days'

    def handle(self, *args, **options):
        # Calculate the date 365 days ago
        start_date = datetime.now() - timedelta(days=365)

        # Generate data for each day
        for day in range(365):
            current_date = start_date + timedelta(days=day)
            
            # Generate between 5 and 20 entries per day
            entries = randint(5, 20)
            for _ in range(entries):
                dispid = randint(1, 3)
                DispenseRecord.objects.create(
                    dispId=dispid,
                    medicine = MedicalDispensor.objects.get(id=dispid).medicine,
                    quantity=randint(1, 6),
                    created_at=current_date,
                )

        self.stdout.write(self.style.SUCCESS('Successfully seeded DispenseRecord data'))
