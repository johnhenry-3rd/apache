# composer_import_script.py
import os
import sys
import django
from django.db import IntegrityError, transaction

# --- Django Setup ---
# Use a relative path to the project directory
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apache_db.settings')

# Initialize Django
django.setup()

from artist_logs.models import Composer

# --- Composer Data ---
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

# --- Helper Functions ---
def parse_composer_name(full_name):
    """Parse a composer name into first and last names."""
    parts = full_name.split()

    # Handle hyphenated last names (e.g., "Indee R-S")
    if '-' in parts[-1]:
        last_name = parts[-1]
        first_name = ' '.join(parts[:-1])
    else:
        last_name = parts[-1]
        first_name = ' '.join(parts[:-1])

    return first_name.strip(), last_name.strip()

# --- Main Function ---
def import_composers():
    """Import all composers into the database."""
    created_count = 0
    updated_count = 0
    skipped_count = 0

    with transaction.atomic():
        for full_name in composer_names:
            try:
                first_name, last_name = parse_composer_name(full_name)
                full_name_clean = f"{first_name} {last_name}"

                # Check for existing composer (case-insensitive)
                existing = Composer.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()

                if existing:
                    # Update existing composer
                    existing.first_name = first_name
                    existing.last_name = last_name
                    existing.full_name = full_name_clean
                    existing.save()
                    updated_count += 1
                    print(f"✅ Updated: {full_name_clean}")
                else:
                    # Create new composer
                    Composer.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        full_name=full_name_clean
                    )
                    created_count += 1
                    print(f"✅ Created: {full_name_clean}")

            except IntegrityError as e:
                print(f"⚠️  Skipped (duplicate or error): {full_name} - {str(e)}")
                skipped_count += 1
            except Exception as e:
                print(f"❌ Failed to import {full_name}: {str(e)}")
                skipped_count += 1

    print("\n" + "="*50)
    print(f"📊 Import Summary:")
    print(f"   Created: {created_count}")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count}")
    print("="*50)

if __name__ == "__main__":
    import_composers()