# artist_logs/management/commands/import_prs.py
from django.core.management.base import BaseCommand
from artist_logs.models import Prs_data, Artist, Track, Client, Payee
import csv
import os

class Command(BaseCommand):
    help = 'Import PRS data from CSV and create all relationships'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_file',
            type=str,
            default='/home/mypiwh/apache/prs_data/131337_202603E.csv',
            help='Path to the CSV file'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete existing data before importing'
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        clean_first = options['clean']

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
            return

        if clean_first:
            self.stdout.write("Deleting existing data...")
            Prs_data.objects.all().delete()
            Artist.objects.all().delete()
            Track.objects.all().delete()
            Client.objects.all().delete()
            Payee.objects.all().delete()

        imported_count = 0
        skipped_count = 0
        artist_count = 0
        track_count = 0
        client_count = 0
        payee_count = 0

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)

            for row_num, row in enumerate(reader, 1):
                try:
                    def clean_field(field_name, default=''):
                        value = row.get(field_name, '').strip()
                        return value if value else default

                    def clean_numeric(field_name, field_type=float, default=0):
                        value = clean_field(field_name)
                        if not value:
                            return default
                        try:
                            return field_type(value)
                        except ValueError:
                            return default

                    # 1. Client
                    client, client_created = Client.objects.get_or_create(
                        code=clean_field('Client Code'),
                        defaults={'name': clean_field('Client Name')}
                    )
                    if client_created:
                        client_count += 1

                    # 2. Payee
                    payee, payee_created = Payee.objects.get_or_create(
                        code=clean_field('Payee Code'),
                        defaults={'name': clean_field('Payee Name')}
                    )
                    if payee_created:
                        payee_count += 1

                    # 3. Track (FIXED: handles duplicate ISRCs)
                    track_title = clean_field('Song Title')
                    track_isrc = clean_field('ISRC') if clean_field('ISRC') else None

                    if track_isrc:
                        # Use filter().first() instead of get()
                        track = Track.objects.filter(isrc=track_isrc).first()
                        if track:
                            if track.title != track_title:
                                track.title = track_title
                                track.save()
                        else:
                            track = Track.objects.create(title=track_title, isrc=track_isrc)
                            track_count += 1
                    else:
                        # Use filter().first() for title too
                        track = Track.objects.filter(title=track_title).first()
                        if not track:
                            track = Track.objects.create(title=track_title, isrc=None)
                            track_count += 1

                    # 4. Composers
                    composer_names = []
                    composers_field = clean_field('Composers')
                    if composers_field:
                        for delimiter in [',', ';', '/', '&']:
                            composer_names.extend(
                                [name.strip() for name in composers_field.split(delimiter)]
                            )
                        composer_names = list({name for name in composer_names if name})

                    composers = []
                    for name in composer_names:
                        artist, created = Artist.objects.get_or_create(name=name)
                        if created:
                            artist_count += 1
                        composers.append(artist)

                    # 5. Create Prs_data record
                    prs_data = Prs_data.objects.create(
                        client=client,
                        payee=payee,
                        track=track,
                        Client_Code=clean_field('Client Code'),
                        Client_Name=clean_field('Client Name'),
                        Payee_Code=clean_field('Payee Code'),
                        Payee_Name=clean_field('Payee Name'),
                        Song_Code=clean_field('Song Code'),
                        Song_Title=track_title,
                        Composers=composers_field,
                        Source_Code=clean_field('Source Code'),
                        Source_Name=clean_field('Source Name'),
                        Income_Type=clean_field('Income Type'),
                        Income_Type_Name=clean_field('Income Type Name'),
                        Main_Income_Type_Name=clean_field('Main Income Type Name'),
                        Catalogue_No=clean_field('Catalogue No'),
                        Units=clean_numeric('Units', int, 0),
                        Income_Period=clean_field('Income Period'),
                        Percentage_Collected_by_BMG=clean_numeric('Percentage Collected by BMG', float, 0.0),
                        Amount_Collected=clean_numeric('Amount Collected', float, 0.0),
                        Royalty_Payout_Percentage=clean_numeric('Royalty Payout Percentage', float, 0.0),
                        Royalty_Payable=clean_numeric('Royalty Payable', float, 0.0),
                        Domestic_Or_Foreign_Source_Indicator=clean_field('Domestic Or Foreign Source Indicator'),
                        Foreign_Source=clean_field('Foreign Source'),
                        Statement_ID_Year=clean_numeric('Statement ID Year', int, 0),
                        Statement_ID_Number=clean_numeric('Statement ID Number', int, 0),
                        Royalty_Country_Code=clean_field('Royalty Country Code'),
                        Royalty_Country_Description=clean_field('Royalty Country Description'),
                        Artist=clean_field('Artist'),
                        ISRC=track_isrc,
                        Album_Or_Production=clean_field('Album Or Production'),
                        Episode=clean_field('Episode'),
                        Licence_Number=clean_field('License Number'),
                        Original_Source_As_Received=clean_field('Original Source As Received'),
                        Original_Source=clean_field('Original Source'),
                    )

                    if composers:
                        prs_data.composers.set(composers)

                    imported_count += 1

                    if imported_count % 1000 == 0:
                        self.stdout.write(f"Processed {imported_count} records...")

                except Exception as e:
                    skipped_count += 1
                    if skipped_count <= 5:
                        self.stdout.write(self.style.WARNING(
                            f'Row {row_num}: Skipped due to error: {str(e)}'
                        ))
                    continue

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(
            f'Import complete: {imported_count} records imported'
        ))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(
                f'{skipped_count} rows skipped due to errors'
            ))

        self.stdout.write("\nSummary:")
        self.stdout.write(f"- Artists: {Artist.objects.count()} (new: {artist_count})")
        self.stdout.write(f"- Tracks: {Track.objects.count()} (new: {track_count})")
        self.stdout.write(f"- Clients: {Client.objects.count()} (new: {client_count})")
        self.stdout.write(f"- Payees: {Payee.objects.count()} (new: {payee_count})")
        self.stdout.write(f"- PRS Data records: {Prs_data.objects.count()}")
        self.stdout.write("="*50)