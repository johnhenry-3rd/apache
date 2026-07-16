from django.core.management.base import BaseCommand
from artist_logs.models import Composer
from django.db import transaction, IntegrityError

class Command(BaseCommand):
    help = 'Import composers into the database'

    def handle(self, *args, **options):
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
            "Andrew James Johnson",
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

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for full_name in composer_names:
                try:
                    first_name, last_name = self.parse_composer_name(full_name)
                    full_name_clean = f"{first_name} {last_name}"

                    existing = Composer.objects.filter(
                        first_name__iexact=first_name,
                        last_name__iexact=last_name
                    ).first()

                    if existing:
                        existing.first_name = first_name
                        existing.last_name = last_name
                        existing.full_name = full_name_clean
                        existing.save()
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Updated: {full_name_clean}"))
                    else:
                        Composer.objects.create(
                            first_name=first_name,
                            last_name=last_name,
                            full_name=full_name_clean
                        )
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Created: {full_name_clean}"))

                except IntegrityError as e:
                    self.stdout.write(self.style.WARNING(f"Skipped (duplicate): {full_name} - {str(e)}"))
                    skipped_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to import {full_name}: {str(e)}"))
                    skipped_count += 1

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Import Summary:"))
        self.stdout.write(self.style.SUCCESS(f"   Created: {created_count}"))
        self.stdout.write(self.style.SUCCESS(f"   Updated: {updated_count}"))
        self.stdout.write(self.style.SUCCESS(f"   Skipped: {skipped_count}"))
        self.stdout.write("="*50)

    def parse_composer_name(self, full_name):
        parts = full_name.split()
        if '-' in parts[-1]:
            last_name = parts[-1]
            first_name = ' '.join(parts[:-1])
        else:
            last_name = parts[-1]
            first_name = ' '.join(parts[:-1])
        return first_name.strip(), last_name.strip()