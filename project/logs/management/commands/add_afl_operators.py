from django.core.management.base import BaseCommand
from logs.models import OperatorAFL

class Command(BaseCommand):
    help = 'Add predefined RFID card numbers to the OperatorAFL model'

    def handle(self, *args, **options):
        # List of RFID card numbers to add
        rfid_cards = [
            '3661836147',
            '3666413299',
            '3662059059',
            '3660902739',
            '3661920979',
        ]

        # Count for tracking added and existing cards
        added_count = 0
        existing_count = 0

        # Add each RFID card number
        for rfid_card_no in rfid_cards:
            # Check if the RFID card already exists
            if not OperatorAFL.objects.filter(rfid_card_no=rfid_card_no).exists():
                # Create new OperatorAFL object
                OperatorAFL.objects.create(
                    rfid_card_no=rfid_card_no,
                    is_active=True
                )
                added_count += 1
                self.stdout.write(self.style.SUCCESS(f'Added RFID card: {rfid_card_no}'))
            else:
                existing_count += 1
                self.stdout.write(self.style.WARNING(f'RFID card already exists: {rfid_card_no}'))
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(f'Successfully added {added_count} RFID cards'))
        if existing_count > 0:
            self.stdout.write(self.style.WARNING(f'{existing_count} RFID cards already existed and were skipped'))
