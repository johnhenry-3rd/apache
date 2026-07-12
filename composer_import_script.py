# composer_import_script.py
import os
import sys
import django

# Add your project directory to the Python path
sys.path.append('/home/john/Apache/apache_db')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apache_db.settings')

# Setup Django
django.setup()

from artist_logs.models import Composer

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

def parse_composer_name(full_name):
    """Parse a composer name into first and last names"""
    parts = full_name.split()

    # Special case for names with hyphens (like "Indee R-S")
    if '-' in parts[-1]:
        # If the last part contains a hyphen, it's part of the last name
        last_name = parts[-1]
        first_name = ' '.join(parts[:-1])
    else:
        # Otherwise, last part is last name, rest is first name
        last_name = parts[-1]
        first_name = ' '.join(parts[:-1])

    return first_name, last_name

def import_composers():
    """Import all composers into the database"""
    created_count = 0
    updated_count = 0

    for full_name in composer_names:
        first_name, last_name = parse_composer_name(full_name)

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
            print(f"Updated: {full_name}")
        else:
            # Create new composer
            composer = Composer.objects.create(
                first_name=first_name,
                last_name=last_name,
                full_name=f"{first_name} {last_name}"
            )
            created_count += 1
            print(f"Created: {full_name}")

    print(f"\nImport complete!")
    print(f"Created {created_count} new composers")
    print(f"Updated {updated_count} existing composers")

if __name__ == "__main__":
    import_composers()