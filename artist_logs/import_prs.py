import csv
from django.core.management.base import BaseCommand
from artist_logs.models import Prs_data

class Command(BaseCommand):
    help = 'Import PRS data from CSV file'

    def handle(self, *args, **options):
        csv_file_path = '/home/mypiwh/apache/prs_data/131337_202603E.csv'

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            prs_entries = []
            for row in reader:
                prs_entries.append(Prs_data(
                    Client_Code=row['Client_Code'],
                    Client_Name=row['Client Name'],
                    Payee_Code=row['Payee Code'],
                    Payee_Name=row['Payee Name'],
                    Song_Code=row['Song Code'],
                    Song_Title=row['Song Title'],
                    Composers=row['Composers'],
                    Source_Code=row['Source Code'],
                    Source_Name=row['Source Name'],
                    Income_Type=row['Income Type'],
                    Income_Type_Name=row['Income Type Name'],
                    Main_Income_Type_Name=row['Main Income Type Name'],
                    Catalogue_No=row['Catalogue No'],
                    Units=row['Units'],
                    Income_Period=row['Income Period'],
                    Percentage_Collected_by_BMG=row['Percentage Collected by BMG'],
                    Amount_Collected=row['Amount Collected'],
                    Royalty_Payout_Percentage=row['Royalty Payout Percentage'],
                    Royalty_Payable=row['Royalty Payable'],
                    Domestic_Or_Foreign_Source_Indicator=row['Domestic Or Foreign Source Indicator'],
                    Foreign_Source=row[' Foreign Source'],
                    Statement_ID_Year=row['Statement ID Year'],
                    Statement_ID_Number=row['Statement ID Number'],
                    Royalty_Country_Code=row['Royalty Country Code'],
                    Royalty_Country_Description=row['Royalty Country Descriptione'],
                    Artist=row['Artist'],
                    ISRC=row['ISRC'],
                    Album_Or_Production=row['Album Or Production'],
                    Episode=row['Episode'],
                    Licence_Number=row['Licence Number'],
                    Original_Source_As_Received=row['Original Source As Received'],
                    Original_Source=row['Original Source'],
                ))

            Prs_data.objects.bulk_create(prs_entries)
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {len(prs_entries)} records'))