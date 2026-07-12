from django.core.management.base import BaseCommand
from artist_logs.models import Composer

class Command(BaseCommand):
    help = 'Import composers from a predefined list'

    def handle(self, *args, **options):
        # List of composer names
        composer_names = [
            "Tobias James",
            "Eamonn Patrick Downes",
            "Lee Austin Groves",
            "Ollie Friend",
            "Charlie Tenku",
            "Edward Hogston",
            "Edward Henry Seed",
            "David Baluteau",
            "David Lol Perry",
            "Finn Mcnicholas",
            "James Kellegher",
            "John Francis Ross",
            "Michael James Burns",
            "Peter George Marett",
            "Stuart Dale Thomas",
            "Robert Dylan Thomas",
            "Gordon Cole",
            "Andrew Stuart Poucher",
            "Nicholas Leventis",
            "Jonny Parry",
            "Paul Cousins",
            "Thomas Trueman",
            "Tristan Pilkington",
            "Jack Saturn",
            "Will Plowman",
            "Francis Binns",
            "Peter John Diggens",
            "Martin Glover",
            "Joesph Watt",
            "Kevin David Hughes",
            "Luke Jethro Sanger",
            "Miles Newbold",
            "Jack Wade",
            "Romek Luka",
            "Max Burrow",
            "Miki Berenyi",
            "John Kubicki",
            "Stuart Peck",
            "Ronnie Verboom",
            "Kelvin Lewis",
            "John Gray",
            "Indee R-S",
            "Christina Hill",
            "Theo Rivers"
        ]

        def parse_composer_name(full_name):
            """Parse a composer name into first and last names"""
            parts = full_name.split()

            # Special case for names with hyphens (like "Indee R-S")
            if '-' in parts[-1]:
                last_name = parts[-1]
                first_name = ' '.join(parts[:-1])
            else:
                last_name = parts[-1]
                first_name = ' '.join(parts[:-1])

            return first_name, last_name

        created_count = 0
        updated_count = 0
        skipped_count = 0

        self.stdout.write(self.style.SUCCESS("Starting composer import..."))

        for full_name in composer_names:
            first_name, last_name = parse_composer_name(full_name)

            try:
                # Check if composer already exists
                existing = Composer.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()

                if existing:
                    # Update existing composer
                    existing.first_name = first_name
                    existing.last_name = last_name
                    existing.full_name = f"{first_name} {last_name}"
                    existing.save()
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Updated: {full_name}"))
                else:
                    # Create new composer
                    Composer.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        full_name=f"{first_name} {last_name}"
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Created: {full_name}"))

            except Exception as e:
                skipped_count += 1
                self.stdout.write(self.style.ERROR(f"Skipped {full_name} due to error: {str(e)}"))

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Import Summary:"))
        self.stdout.write(self.style.SUCCESS(f"  Created: {created_count} composers"))
        self.stdout.write(self.style.SUCCESS(f"  Updated: {updated_count} composers"))
        self.stdout.write(self.style.SUCCESS(f"  Skipped: {skipped_count} composers"))
        self.stdout.write("="*50)