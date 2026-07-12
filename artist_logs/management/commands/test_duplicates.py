# test_duplicates.py
import os
import sys
import django

sys.path.append('/home/john/Apache/apache_db')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apache_db.settings')
django.setup()

from artist_logs.models import Prs_data, Song, Source, IncomeType
from django.db import transaction

# Create test data
song = Song.objects.first()
source = Source.objects.first()
income_type = IncomeType.objects.first()

if not all([song, source, income_type]):
    print("Error: Missing required test data (Song, Source, or IncomeType)")
    sys.exit(1)

print(f"Using test data: Song={song.code}, Source={source.code}, IncomeType={income_type.code}")

# Test 1: Create first record
try:
    with transaction.atomic():
        first = Prs_data.objects.create(
            song=song,
            song_title="Test Song",
            song_code="TEST001",
            source=source,
            source_code="SRC001",
            income_type=income_type,
            income_type_code="INC001",
            income_period="202601",
            royalty_payable=100.00
        )
        print(f"✅ Created first record: ID={first.id}")
except Exception as e:
    print(f"❌ Error creating first record: {str(e)}")
    sys.exit(1)

# Test 2: Try to create a duplicate
try:
    with transaction.atomic():
        second = Prs_data.objects.create(
            song=song,
            song_title="Test Song",
            song_code="TEST001",
            source=source,
            source_code="SRC001",
            income_type=income_type,
            income_type_code="INC001",
            income_period="202601",
            royalty_payable=200.00  # Different amount to distinguish
        )
        print(f"✅ Created duplicate record: ID={second.id}")
        print("✅ Duplicates are now allowed in the database!")
except Exception as e:
    print(f"❌ Error creating duplicate: {str(e)}")
    print("❌ Duplicates are still not allowed.")
    sys.exit(1)

# Test 3: Verify both records exist
records = Prs_data.objects.filter(song_code="TEST001", income_period="202601")
print(f"\nFound {records.count()} records with song_code=TEST001 and income_period=202601")
for record in records:
    print(f"  - ID={record.id}, royalty_payable={record.royalty_payable}")

# Clean up
records.delete()
print("\nCleaned up test records.")