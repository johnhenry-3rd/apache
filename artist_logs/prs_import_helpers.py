# =============================================
#Segment 1: Helper Functions
# =============================================

def safe_decimal(value, default='0.00'):
    """Safely convert a value to Decimal."""
    try:
        if value is None or value == '':
            return Decimal(default)
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal(default)

def get_csv_preview(file_content):
    """Generate a preview of the CSV file."""
    try:
        csv_data = StringIO(file_content)
        reader = csv.DictReader(csv_data)
        headers = reader.fieldnames or []
        rows = [list(row.values())[:10] for _, row in zip(range(5), reader)]
        return {'headers': headers, 'rows': rows}
    except Exception as e:
        logger.error(f"Error generating CSV preview: {str(e)}")
        return {'headers': [], 'rows': []}

def read_file_content(csv_file):
    """Read and decode file content."""
    if isinstance(csv_file, InMemoryUploadedFile):
        file_content = csv_file.read()
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8-sig')
        csv_file.seek(0)
    else:
        with csv_file.open('r', encoding='utf-8-sig') as f:
            file_content = f.read()
    return file_content

# =============================================
#Segment 2: Row Processing Function
# =============================================

def process_prs_row(row, line_num, existing_song_codes, source_cache, income_type_cache):
    """
    Process a single CSV row and return:
    - prs_data: Prs_data instance (or None if error)
    - new_song_codes: Set of new song codes to add to cache
    - errors: List of error messages
    """
    errors = []
    new_song_codes = set()
    prs_data = None

    try:
        # Skip empty rows
        if not row.get('Song Title', '').strip():
            return None, new_song_codes, ["Skipped empty row"]

        # --- Handle Song ---
        song_code = row.get('Song Code', '').strip()
        if not song_code:
            return None, new_song_codes, [f"Row {line_num}: Missing Song Code"]

        song_title = row.get('Song Title', '').strip()
        if song_code not in existing_song_codes:
            song = Song.objects.create(code=song_code, title=song_title)
            existing_song_codes.add(song_code)
            new_song_codes.add(song_code)
        else:
            song = Song.objects.get(code=song_code)

        # --- Handle Source ---
        source_name = row.get('Source Name', '').strip()
        source_code = row.get('Source Code', '').strip()
        if source_code not in source_cache:
            source = Source.objects.create(code=source_code, name=source_name)
            source_cache[source_code] = source
        else:
            source = source_cache[source_code]

        # --- Handle IncomeType ---
        income_type_name = row.get('Main Income Type Name', '').strip()
        income_type_code = row.get('Income Type', '').strip()
        if income_type_code not in income_type_cache:
            income_type = IncomeType.objects.create(
                code=income_type_code,
                name=income_type_name
            )
            income_type_cache[income_type_code] = income_type
        else:
            income_type = income_type_cache[income_type_code]

        # --- Create or Update Prs_data ---
        existing_prs = Prs_data.objects.filter(song_code=song_code).first()

        if existing_prs:
            # UPDATE EXISTING RECORD
            existing_prs.units += int(row.get('Units', 0) or 0)
            existing_prs.amount_collected += safe_decimal(row.get('Amount Collected', 0))
            existing_prs.royalty_payable += safe_decimal(row.get('Royalty Payable', 0))

            # Update all fields
            existing_prs.song_title = song_title
            existing_prs.song = song
            existing_prs.song_code = song_code
            existing_prs.source = source
            existing_prs.source_code = source_code
            existing_prs.source_name = source_name
            existing_prs.income_type = income_type
            existing_prs.income_type_code = income_type_code
            existing_prs.income_type_name = row.get('Income Type Name', '').strip() or None
            existing_prs.main_income_type_name = income_type_name
            existing_prs.percentage_collected = safe_decimal(row.get('Percentage Collected by BMG', 0))
            existing_prs.royalty_payout_percentage = float(row.get('Royalty Payout Percentage', 0) or 0)
            existing_prs.domestic_or_foreign = row.get('Domestic Or Foreign Source Indicator', '').strip() or None
            existing_prs.foreign_source = row.get('Foreign Source', '').strip() or None
            existing_prs.royalty_country_code = row.get('Royalty Country Code', '').strip() or None
            existing_prs.royalty_country_description = row.get('Royalty Country Description', '').strip() or None
            existing_prs.statement_id_year = row.get('Statement ID Year', '').strip() or None
            existing_prs.statement_id_number = row.get('Statement ID Number', '').strip() or None
            existing_prs.income_period = row.get('Income Period', '').strip() or None
            existing_prs.catalogue_no = row.get('Catalogue No ', '').strip() or None
            existing_prs.composers = row.get('Composers', '').strip() or None
            existing_prs.original_source_as_received = row.get('Original Source As Received', '').strip() or None
            existing_prs.original_source = row.get('Original Source', '').strip() or None
            existing_prs.artist = row.get('Artist', '').strip() or None
            existing_prs.isrc = row.get('ISRC', '').strip() or None
            existing_prs.album_or_production = row.get('Album Or Production', '').strip() or None
            existing_prs.episode = row.get('Episode', '').strip() or None
            existing_prs.license_number = row.get('License Number', '').strip() or None
            existing_prs.is_paid = False

            existing_prs.full_clean()
            existing_prs.save()
            return existing_prs, new_song_codes, errors

        else:
            # CREATE NEW RECORD
            prs_data = Prs_data(
                # Required fields
                song_title=song_title,
                units=int(row.get('Units', 0) or 0),
                percentage_collected=safe_decimal(row.get('Percentage Collected by BMG', 0)),
                amount_collected=safe_decimal(row.get('Amount Collected', 0)),
                royalty_payout_percentage=float(row.get('Royalty Payout Percentage', 0) or 0),
                royalty_payable=safe_decimal(row.get('Royalty Payable', 0)),
                is_paid=False,

                # Other fields
                song=song,
                song_code=song_code,
                source=source,
                source_code=source_code,
                source_name=source_name,
                domestic_or_foreign=row.get('Domestic Or Foreign Source Indicator', '').strip() or None,
                foreign_source=row.get('Foreign Source', '').strip() or None,
                royalty_country_code=row.get('Royalty Country Code', '').strip() or None,
                royalty_country_description=row.get('Royalty Country Description', '').strip() or None,
                income_type=income_type,
                income_type_code=income_type_code,
                income_type_name=row.get('Income Type Name', '').strip() or None,
                main_income_type_name=income_type_name,
                statement_id_year=row.get('Statement ID Year', '').strip() or None,
                statement_id_number=row.get('Statement ID Number', '').strip() or None,
                income_period=row.get('Income Period', '').strip() or None,
                catalogue_no=row.get('Catalogue No ', '').strip() or None,
                composers=row.get('Composers', '').strip() or None,
                original_source_as_received=row.get('Original Source As Received', '').strip() or None,
                original_source=row.get('Original Source', '').strip() or None,
                artist=row.get('Artist', '').strip() or None,
                isrc=row.get('ISRC', '').strip() or None,
                album_or_production=row.get('Album Or Production', '').strip() or None,
                episode=row.get('Episode', '').strip() or None,
                license_number=row.get('License Number', '').strip() or None,
            )

            prs_data.full_clean()
            prs_data.save()
            return prs_data, new_song_codes, errors

    except ValidationError as e:
        errors.append(f"Row {line_num}: Validation error - {str(e)}")
        logger.error(f"Validation error in row {line_num}: {str(e)}")
        return None, new_song_codes, errors
    except IntegrityError as e:
        errors.append(f"Row {line_num}: Database error - {str(e)}")
        logger.error(f"Database error in row {line_num}: {str(e)}")
        return None, new_song_codes, errors
    except Exception as e:
        errors.append(f"Row {line_num}: Unexpected error - {str(e)}")
        logger.error(f"Unexpected error in row {line_num}: {str(e)}")
        return None, new_song_codes, errors