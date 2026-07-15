from django.core.management.base import BaseCommand
from artist_logs.models import Composer
import re

class Command(BaseCommand):
    help = 'Import composers from a predefined list, optimized for your Composer model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test the import without saving to database',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing composers with new data',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        update_existing = options['update_existing']

        # List of composer names
        composer_names = [
            "Tobias James", "Eamonn Patrick Downes", "Lee Austin Groves",
            "Ollie Friend", "Charlie Tenku", "Edward Hogston", "Edward Henry Seed",
            "David Baluteau", "David Lol Perry", "Finn Mcnicholas", "James Kellegher",
            "John Francis Ross", "Michael James Burns", "Peter George Marett",
            "Stuart Dale Thomas", "Robert Dylan Thomas", "Gordon Cole",
            "Andrew Stuart Poucher", "Nicholas Leventis", "Jonny Parry",
            "Paul Cousins", "Thomas Trueman", "Tristan Pilkington", "Jack Saturn",
            "Will Plowman", "Francis Binns", "Peter John Diggens", "Martin Glover",
            "Joesph Watt", "Kevin David Hughes", "Luke Jethro Sanger", "Miles Newbold",
            "Jack Wade", "Romek Luka", "Max Burrow", "Miki Berenyi", "John Kubicki",
            "Stuart Peck", "Ronnie Verboom", "Kelvin Lewis", "John Gray",
            "Indee R-S", "Christina Hill", "Theo Rivers"
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        self.stdout.write(self.style.SUCCESS("Starting composer import..."))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: No changes will be saved to database"))

        for full_name in composer_names:
            try:
                # Use your model's find_or_create_by_name method
                composer = Composer.find_or_create_by_name(full_name)

                if composer:
                    if update_existing:
                        # Force update by saving again (triggers your save() method)
                        composer.full_name = full_name  # This will trigger the save() logic
                        if not dry_run:
                            composer.save()
                        updated_count += 1
                        action = "Would update" if dry_run else "Updated"
                    else:
                        # Just created
                        created_count += 1
                        action = "Would create" if dry_run else "Created"

                    self.stdout.write(self.style.SUCCESS(f"{action}: {composer.full_name} (ID: {composer.composer_id})"))
                else:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f"Skipped (invalid name): {full_name}"))

            except Exception as e:
                errors.append(f"{full_name}: {str(e)}")
                skipped_count += 1
                self.stdout.write(self.style.ERROR(f"Skipped {full_name} due to error: {str(e)}"))

        # Print summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("Import Summary:"))
        self.stdout.write(self.style.SUCCESS(f"  Created: {created_count} composers"))
        self.stdout.write(self.style.SUCCESS(f"  Updated: {updated_count} composers"))
        self.stdout.write(self.style.SUCCESS(f"  Skipped: {skipped_count} composers"))

        if errors:
            self.stdout.write(self.style.ERROR("\nErrors encountered:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        self.stdout.write("="*50)