# In artist_logs/management/commands/migrate_composers.py
from django.core.management.base import BaseCommand
from artist_logs.models import Prs_data, Song, Composer
from collections import defaultdict
import re

class Command(BaseCommand):
    help = 'Migrates existing composer data to the new Composer model with one composer per song'

    def handle(self, *args, **options):
        self.stdout.write("Starting composer migration...")

        # Step 1: Collect all unique composer names from Prs_data and Song
        composer_names = set()

        # From Prs_data.artist field
        for record in Prs_data.objects.exclude(artist__isnull=True).exclude(artist__exact=''):
            names = [name.strip() for name in record.artist.replace(';', ',').replace('/', ',').split(',') if name.strip()]
            composer_names.update(names)

        # From Song.artist (if it's a text field)
        for song in Song.objects.all():
            if hasattr(song, 'artist') and song.artist:
                names = [name.strip() for name in song.artist.replace(';', ',').replace('/', ',').split(',') if name.strip()]
                composer_names.update(names)

        self.stdout.write(f"Found {len(composer_names)} unique composer names")

        # Step 2: Create Composer records for each unique name
        composer_map = {}  # Maps normalized names to Composer objects
        for name in composer_names:
            if not name:
                continue

            # Normalize the name
            normalized = re.sub(r'[^\w\s-]', ' ', name).strip()
            normalized = re.sub(r'\s+', ' ', normalized).title()

            # Create or get the composer
            composer, created = Composer.objects.get_or_create(
                full_name__iexact=normalized,
                defaults={'full_name': normalized}
            )

            composer_map[normalized.lower()] = composer
            composer_map[name.lower()] = composer

        self.stdout.write(f"Created {Composer.objects.count()} composer records")

        # Step 3: Link composers to songs
        for song in Song.objects.all():
            # Try to get composer from artist field (if it's a text field)
            if hasattr(song, 'artist') and song.artist:
                names = [name.strip() for name in song.artist.replace(';', ',').replace('/', ',').split(',') if name.strip()]
                if names:
                    # Use the first name as the composer
                    name = names[0]
                    normalized = re.sub(r'[^\w\s-]', ' ', name).strip().lower()
                    if normalized in composer_map:
                        song.composer = composer_map[normalized]
                        song.save()
                        self.stdout.write(f"Linked composer {song.composer.full_name} to song: {song.title}")

            # If no artist field, try to get composer from PRS records
            elif song.prs_records.count() > 0:
                first_record = song.prs_records.first()
                if first_record.artist:
                    names = [name.strip() for name in first_record.artist.replace(';', ',').replace('/', ',').split(',') if name.strip()]
                    if names:
                        name = names[0]
                        normalized = re.sub(r'[^\w\s-]', ' ', name).strip().lower()
                        if normalized in composer_map:
                            song.composer = composer_map[normalized]
                            song.save()
                            self.stdout.write(f"Linked composer {song.composer.full_name} to song: {song.title}")

        # Step 4: Update PRS records to ensure they reference songs with composers
        for record in Prs_data.objects.all():
            if record.song and not record.song.composer:
                if record.artist:
                    names = [name.strip() for name in record.artist.replace(';', ',').replace('/', ',').split(',') if name.strip()]
                    if names:
                        name = names[0]
                        normalized = re.sub(r'[^\w\s-]', ' ', name).strip().lower()
                        if normalized in composer_map:
                            record.song.composer = composer_map[normalized]
                            record.song.save()
                            self.stdout.write(f"Updated song {record.song.title} with composer {record.song.composer.full_name}")

        self.stdout.write(self.style.SUCCESS('Composer migration completed successfully!'))