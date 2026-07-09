# delete_all_data.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'art_project.settings')
django.setup()

from artist_logs.models import Prs_data, UploadHistory, Song, Artist, Source, IncomeType

# Delete all PRS data records
prs_count = Prs_data.objects.count()
Prs_data.objects.all().delete()
print(f"✅ Deleted {prs_count} PRS records.")

# Delete all Song records (and their many-to-many relationships with Artist)
song_count = Song.objects.count()
Song.objects.all().delete()
print(f"✅ Deleted {song_count} Song records.")

# Delete all Artist records
artist_count = Artist.objects.count()
Artist.objects.all().delete()
print(f"✅ Deleted {artist_count} Artist records.")

# Delete all Source records
source_count = Source.objects.count()
Source.objects.all().delete()
print(f"✅ Deleted {source_count} Source records.")

# Delete all IncomeType records
income_type_count = IncomeType.objects.count()
IncomeType.objects.all().delete()
print(f"✅ Deleted {income_type_count} IncomeType records.")

# Delete all UploadHistory records
upload_count = UploadHistory.objects.count()
UploadHistory.objects.all().delete()
print(f"✅ Deleted {upload_count} UploadHistory records.")

# Verify all counts are zero
print("\n📊 Final Counts:")
print(f"PRS records: {Prs_data.objects.count()}")
print(f"Songs: {Song.objects.count()}")
print(f"Artists: {Artist.objects.count()}")
print(f"Sources: {Source.objects.count()}")
print(f"Income Types: {IncomeType.objects.count()}")
print(f"Upload History: {UploadHistory.objects.count()}")