# artist_logs/management/commands/clear_prs_data.py
from django.core.management.base import BaseCommand
from django.db import transaction
from artist_logs.models import Prs_data, UploadHistory

class Command(BaseCommand):
    help = 'Clears all PRS data and upload history while preserving composers and songs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting anything',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.WARNING('⚠️  This command will delete ALL PRS data and upload history!'))
        self.stdout.write(self.style.SUCCESS('✅ Composers and Songs will be preserved.'))

        # Count records to be deleted
        prs_count = Prs_data.objects.count()
        upload_count = UploadHistory.objects.count()

        self.stdout.write(self.style.SUCCESS(f'\nRecords to be deleted:'))
        self.stdout.write(self.style.SUCCESS(f'  - PRS Data: {prs_count}'))
        self.stdout.write(self.style.SUCCESS(f'  - Upload History: {upload_count}'))

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 Dry run: No records were actually deleted.'))
            return

        # Ask for confirmation
        confirmation = input("\nAre you sure you want to delete ALL PRS data and upload history? (yes/no): ")
        if confirmation.lower() != 'yes':
            self.stdout.write(self.style.ERROR('❌ Operation cancelled.'))
            return

        # Delete in a transaction to ensure atomicity
        try:
            with transaction.atomic():
                # Delete ONLY PRS data and upload history
                prs_deleted = Prs_data.objects.all().delete()[0]
                upload_deleted = UploadHistory.objects.all().delete()[0]

                self.stdout.write(self.style.SUCCESS('\n✅ Successfully deleted:'))
                self.stdout.write(self.style.SUCCESS(f'  - {prs_deleted} PRS data records'))
                self.stdout.write(self.style.SUCCESS(f'  - {upload_deleted} upload history records'))
                self.stdout.write(self.style.SUCCESS('\n✅ Composers and Songs were PRESERVED.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}'))
            raise