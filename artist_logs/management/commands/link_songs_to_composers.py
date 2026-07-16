from django.core.management.base import BaseCommand
from artist_logs.models import Song, Composer, Prs_data, SongComposer

class Command(BaseCommand):
    help = 'Link songs to composers (single composer only) based on the composers field in PRS data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test the linking without making changes to the database',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each song',
        )
        parser.add_argument(
            '--sample',
            type=int,
            default=0,
            help='Only process this many records (for testing)',
        )

    def extract_last_names(self, composers_text):
        """
        Extract last names from the composers text field.
        Handles multiple composers separated by commas, semicolons, or slashes.
        """
        if not composers_text:
            return []

        # Split by common separators
        separators = [',', ';', '/', ' & ', ' and ']
        names = [composers_text]

        for sep in separators:
            new_names = []
            for name in names:
                new_names.extend(name.split(sep))
            names = [n.strip() for n in new_names if n.strip()]

        # Extract last names
        last_names = []
        for name in names:
            parts = name.split()
            if len(parts) > 0:
                last_names.append(parts[-1])  # Last part is the last name

        return last_names

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        sample_size = options['sample']

        # Mapping of PRS last names to Composer last names
        last_name_mapping = {
            'James': 'James',
            'Downes': 'Downes',
            'Groves': 'Groves',
            'Friend': 'Friend',
            'Tenku': 'Tenku',
            'Hogston': 'Hogston',
            'Seed': 'Seed',
            'Baluteau': 'Baluteau',
            'Perry': 'Perry',
            'Mcnicholas': 'Mcnicholas',
            'Kellegher': 'Kellegher',
            'Ross': 'Ross',
            'Burns': 'Burns',
            'Peck': 'Peck',
            'Verboom': 'Verboom',
            'Cole': 'Cole',
            'Poucher': 'Poucher',
            'Leventis': 'Leventis',
            'Parry': 'Parry',
            'Cousins': 'Cousins',
            'Trueman': 'Trueman',
            'Johnson': 'Johnson',
            'Pilkington': 'Pilkington',
            'Plowman': 'Plowman',
            'Binns': 'Binns',
            'Diggens': 'Diggens',
            'Glover': 'Glover',
            'Watt': 'Watt',
            'Hughes': 'Hughes',
            'Sanger': 'Sanger',
            'Newbold': 'Newbold',
            'Wade': 'Wade',
            'Luka': 'Luka',
            'Burrow': 'Burrow',
            'Berenyi': 'Berenyi',
            'Kubicki': 'Kubicki',
            'Gray': 'Gray',
            'Hill': 'Hill',
            'Rivers': 'Rivers',
            'R-S': 'R-S',
        }

        # Get PRS records to process
        prs_query = Prs_data.objects.filter(song__isnull=False).select_related('song')

        if sample_size > 0:
            prs_query = prs_query[:sample_size]

        if not prs_query.exists():
            self.stdout.write(self.style.WARNING("No PRS records with associated songs found."))
            return

        self.stdout.write(self.style.SUCCESS(f"Processing {prs_query.count()} PRS records..."))

        linked_count = 0
        not_found_count = 0
        already_linked_count = 0
        skipped_count = 0
        no_composers_count = 0
        multi_composer_count = 0

        for prs in prs_query:
            song = prs.song

            # Skip if already linked via SongComposer
            if song.song_composers.exists():
                already_linked_count += 1
                if verbose:
                    self.stdout.write(self.style.SUCCESS(f"Already linked via SongComposer: '{song.title}'"))
                continue

            # Get composers from the composers field
            composers_text = prs.composers
            if not composers_text:
                no_composers_count += 1
                if verbose:
                    self.stdout.write(self.style.WARNING(f"No composers info for song '{song.title}' (code: {song.code})"))
                continue

            # Extract last names from composers text
            last_names = self.extract_last_names(composers_text)

            if not last_names:
                no_composers_count += 1
                if verbose:
                    self.stdout.write(self.style.WARNING(f"No valid composer names found in '{composers_text}' for song '{song.title}'"))
                continue

            # Find matching composers
            matched_composers = []
            for last_name in last_names:
                if last_name in last_name_mapping:
                    composer_last_name = last_name_mapping[last_name]
                    try:
                        composer = Composer.objects.filter(last_name__iexact=composer_last_name).first()
                        if composer and composer not in matched_composers:
                            matched_composers.append(composer)
                    except Exception as e:
                        if verbose:
                            self.stdout.write(self.style.ERROR(f"Error finding composer for '{last_name}': {str(e)}"))

            if not matched_composers:
                not_found_count += 1
                if verbose:
                    self.stdout.write(self.style.WARNING(
                        f"Composer not found for '{song.title}' (tried last names: {last_names})"
                    ))
                continue

            # Skip songs with multiple composers (for manual handling)
            if len(matched_composers) > 1:
                multi_composer_count += 1
                if verbose:
                    self.stdout.write(self.style.WARNING(
                        f"Skipped multi-composer song: '{song.title}' (composers: {', '.join([c.full_name for c in matched_composers])})"
                    ))
                continue

            # Link single-composer songs
            composer = matched_composers[0]
            if not dry_run:
                # Clear existing SongComposer entries (if any)
                song.song_composers.all().delete()

                # Set the legacy composer field
                song.composer = composer
                song.save()

                # Create SongComposer entry with 100% split
                SongComposer.objects.create(
                    song=song,
                    composer=composer,
                    split_percentage=100.0,
                    notes=f"Linked via PRS data (composers: {composers_text})"
                )

            linked_count += 1
            action = "Would link" if dry_run else "Linked"
            if verbose:
                self.stdout.write(self.style.SUCCESS(
                    f"{action} '{song.title}' (code: {song.code}) to {composer.full_name} (100%)"
                ))

        # Print summary
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("Linking Summary:"))
        self.stdout.write(self.style.SUCCESS(f"  Successfully {'would link' if dry_run else 'linked'}: {linked_count} songs"))
        self.stdout.write(self.style.SUCCESS(f"  Already linked via SongComposer: {already_linked_count} songs"))
        self.stdout.write(self.style.SUCCESS(f"  Not linked (composer not found): {not_found_count} songs"))
        self.stdout.write(self.style.SUCCESS(f"  Skipped (no composers info): {no_composers_count} songs"))
        self.stdout.write(self.style.WARNING(f"  Skipped (multi-composer, needs manual review): {multi_composer_count} songs"))

        if sample_size > 0:
            self.stdout.write(self.style.WARNING(f"\nOnly processed {sample_size} records (sample mode)"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run complete - no changes were made to the database"))