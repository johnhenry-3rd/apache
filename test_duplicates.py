#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
project_path = '/home/john/Apache/apache_db'
sys.path.insert(0, project_path)

# Set the Django settings module - your settings.py is in the root directory
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# Setup Django
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {str(e)}")
    print("\nTroubleshooting:")
    print(f"1. Project path: {project_path}")
    print(f"2. Settings module: settings (root level)")
    print(f"3. Check if {project_path}/settings.py exists: {os.path.exists(os.path.join(project_path, 'settings.py'))}")
    print(f"4. Current working directory: {os.getcwd()}")
    print(f"5. Python path: {sys.path[:3]}")  # Show first 3 paths
    sys.exit(1)

from artist_logs.models import Prs_data, Song, Source, IncomeType
from django.db import transaction

def main():
    # Create test data
    song = Song.objects.first()
    source = Source.objects.first()
    income_type = IncomeType.objects.first()

    if not all([song, source, income_type]):
        print("Error: Missing required test data (Song, Source, or IncomeType)")
        print("Please create at least one Song, Source, and IncomeType record first.")
        print("You can do this with:")
        print("python manage.py shell")
        print("from artist_logs.models import Song, Source, IncomeType")
        print("Song.objects.create(code='TEST001', title='Test Song')")
        print("Source.objects.create(code='SRC001', name='Test Source')")
        print("IncomeType.objects.create(code='INC001', name='Test Income')")
        return

    print(f"Using test data: Song={song.code}, Source={source.code}, IncomeType={income_type.code}")

    # Clean up any existing test records
    Prs_data.objects.filter(song_code="TESTDUP001").delete()
    print("Cleaned up any existing test records")

    # Test 1: Create first record
    try:
        with transaction.atomic():
            first = Prs_data.objects.create(
                song=song,
                song_title="Test Song for Duplicates",
                song_code="TESTDUP001",
                source=source,
                source_code="SRC001",
                income_type=income_type,
                income_type_code="INC001",
                income_period="202607",
                royalty_payable=100.00
            )
            print(f"✅ Created first record: ID={first.id}")
    except Exception as e:
        print(f"❌ Error creating first record: {str(e)}")
        return

    # Test 2: Try to create a duplicate
    try:
        with transaction.atomic():
            second = Prs_data.objects.create(
                song=song,
                song_title="Test Song for Duplicates",
                song_code="TESTDUP001",
                source=source,
                source_code="SRC001",
                income_type=income_type,
                income_type_code="INC001",
                income_period="202607",
                royalty_payable=200.00  # Different amount to distinguish
            )
            print(f"✅ Created duplicate record: ID={second.id}")
            print("✅ Duplicates are now allowed in the database!")

            # Verify both records exist
            records = Prs_data.objects.filter(song_code="TESTDUP001", income_period="202607")
            print(f"\n✅ Found {records.count()} records with song_code=TESTDUP001 and income_period=202607")
            for record in records:
                print(f"   - ID={record.id}, royalty_payable={record.royalty_payable}")

            # Clean up
            records.delete()
            print("\n✅ Cleaned up test records.")

    except Exception as e:
        print(f"❌ Error creating duplicate: {str(e)}")
        print("❌ Duplicates are still not allowed.")

        # Check for existing records with these values
        existing = Prs_data.objects.filter(
            song_code="TESTDUP001",
            income_period="202607"
        )
        if existing.exists():
            print(f"\nFound {existing.count()} existing records with these values:")
            for record in existing:
                print(f"   - ID={record.id}")
            print("\nTry deleting these first with:")
            print("python manage.py shell")
            print("from artist_logs.models import Prs_data")
            print("Prs_data.objects.filter(song_code='TESTDUP001').delete()")

if __name__ == "__main__":
    main()