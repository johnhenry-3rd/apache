# artist_logs/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Q, Sum, Count, Case, When, F, Min
from django.db.models.functions import Lower
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST, require_http_methods
from django.http import JsonResponse, FileResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone
from django.conf import settings
import pandas as pd
import plotly.express as px
import csv
import hashlib
import time
import json
import os
from datetime import datetime
from io import StringIO
from collections import defaultdict
import re
from datetime import datetime, date
from decimal import Decimal
from django.db import transaction
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.db.models import Q
from django.core.serializers import serialize, deserialize
from django.core.serializers.json import DjangoJSONEncoder

# Import all models
from .models import (
    Prs_data, UploadHistory, Source, Song, IncomeType, Artist,
    Composer, PaymentStatement, PaymentPlan, Song
)
from .forms import ComposerForm, SongForm, PaymentStatementForm

# =============================================
# Utility Functions
# =============================================

def format_file_size(size):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

# =============================================
# Main Views
# =============================================

def front_page(request):
    """
    Render the front page with summary statistics and quick links.
    """
    # Get summary statistics
    composer_count = Composer.objects.count()
    song_count = Song.objects.count()
    prs_count = Prs_data.objects.count()

    # Calculate total and unpaid royalties
    total_royalty = Prs_data.objects.aggregate(total=Sum('royalty_payable'))['total'] or 0
    unpaid_royalty = Prs_data.objects.filter(is_paid=False).aggregate(total=Sum('royalty_payable'))['total'] or 0

    # Get recent activity
    recent_uploads = UploadHistory.objects.all().order_by('-uploaded_at')[:5]
    recent_statements = PaymentStatement.objects.all().order_by('-created_at')[:3]
    recent_plans = PaymentPlan.objects.all().order_by('-created_at')[:3]

    # Get top composers by earnings
    top_composers = Composer.objects.annotate(
        total_earnings=Sum('songs__prs_records__royalty_payable')
    ).order_by('-total_earnings')[:5]

    # Get top songs by earnings
    top_songs = Song.objects.annotate(
        total_earnings=Sum('prs_records__royalty_payable')
    ).order_by('-total_earnings')[:5]

    return render(request, 'artist_logs/front_page.html', {
        'composer_count': composer_count,
        'song_count': song_count,
        'prs_count': prs_count,
        'total_royalty': total_royalty,
        'unpaid_royalty': unpaid_royalty,
        'recent_uploads': recent_uploads,
        'recent_statements': recent_statements,
        'recent_plans': recent_plans,
        'top_composers': top_composers,
        'top_songs': top_songs,
    })

def data_table(request):
    """View to display PRS data with filtering and pagination."""
    # Get filter parameters from the request
    artist_filter = request.GET.get('artist', '')
    song_title_filter = request.GET.get('song_title', '')
    source_filter = request.GET.get('source', '')
    income_type_filter = request.GET.get('income_type', '')

    # Start with all PRS data
    prs_data_list = Prs_data.objects.all().order_by('-income_period', 'song_title')

    # Apply filters
    if artist_filter:
        prs_data_list = prs_data_list.filter(artist__icontains=artist_filter)
    if song_title_filter:
        prs_data_list = prs_data_list.filter(song_title__icontains=song_title_filter)
    if source_filter:
        prs_data_list = prs_data_list.filter(source_name__icontains=source_filter)
    if income_type_filter:
        prs_data_list = prs_data_list.filter(income_type_name__icontains=income_type_filter)

    # Pagination
    paginator = Paginator(prs_data_list, 50)  # Show 50 records per page
    page = request.GET.get('page')
    try:
        prs_data = paginator.page(page)
    except PageNotAnInteger:
        prs_data = paginator.page(1)
    except EmptyPage:
        prs_data = paginator.page(paginator.num_pages)

    # Get unique sources and income types for the filter dropdowns
    sources = Source.objects.all()
    income_types = IncomeType.objects.all()

    return render(request, 'artist_logs/data_table.html', {
        'prs_data': prs_data,
        'sources': sources,
        'income_types': income_types,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': prs_data,
    })

def charts(request):
    """
    Display a chart of Royalty Payable by Composer with Apache Music styling.
    Supports filtering by composer and song title.
    """
    # Get filter parameters
    composer_filter = request.GET.get('composer', '')
    song_title_filter = request.GET.get('song_title', '')

    # Start with all data
    data = Prs_data.objects.all()

    # Apply filters
    if composer_filter:
        data = data.filter(composers__name__icontains=composer_filter)
    if song_title_filter:
        data = data.filter(song_title__icontains=song_title_filter)

    # Distinct results
    data = data.distinct()

    # Prepare data for Plotly
    df_data = []
    for item in data:
        artist_name = item.artist if item.artist else "Unknown"
        df_data.append({
            'Composer': artist_name,
            'Royalty_Payable': float(item.royalty_payable) if item.royalty_payable is not None else 0.0,
            'Song_Title': item.song_title if item.song_title else "Unknown",
            'Count': 1
        })

    if not df_data:
        return render(request, 'artist_logs/charts.html', {
            'chart': '<div class="alert alert-info text-center">No data matches the filters.</div>',
            'composer_filter': composer_filter,
            'song_title_filter': song_title_filter,
        })

    # Convert to DataFrame
    df = pd.DataFrame(df_data)

    # Aggregate by composer
    df_agg = df.groupby('Composer').agg({
        'Royalty_Payable': 'sum',
        'Song_Title': lambda x: ', '.join(x.unique()),
        'Count': 'sum'
    }).reset_index()

    # Sort by Royalty_Payable
    df_agg = df_agg.sort_values('Royalty_Payable', ascending=False)

    # Create the chart
    fig = px.bar(
        df_agg,
        x='Composer',
        y='Royalty_Payable',
        title='Total Royalty Payable by Composer',
        labels={
            'Royalty_Payable': 'Total Royalty Payable (£)',
            'Composer': 'Composer',
            'Count': 'Number of Songs'
        },
        hover_data={
            'Royalty_Payable': ':£.2f',
            'Count': True,
            'Song_Title': True
        },
        color='Royalty_Payable',
        color_continuous_scale=['#1a1a1a', '#c5a47e', '#f8f8f8'],
        text='Count'
    )

    # Improve layout
    fig.update_layout(
        title={
            'text': 'Total Royalty Payable by Composer',
            'font': {'size': 24, 'color': '#f8f8f8', 'family': 'Montserrat'},
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='Composer',
        yaxis_title='Total Royalty Payable (£)',
        height=600,
        showlegend=False,
        hovermode='x unified',
        plot_bgcolor='rgba(26, 26, 26, 0.8)',
        paper_bgcolor='rgba(26, 26, 26, 0)',
        font=dict(size=12, color='#f8f8f8', family='Montserrat'),
        margin=dict(l=50, r=50, t=80, b=150),
        yaxis=dict(
            tickformat="£,.2f",
            gridcolor='rgba(255, 255, 255, 0.1)',
            zerolinecolor='rgba(255, 255, 255, 0.1)',
            title=dict(
                text='Total Royalty Payable (£)',
                font=dict(size=14, color='#f8f8f8', family='Montserrat')
            )
        ),
        xaxis=dict(
            tickangle=-45,
            gridcolor='rgba(255, 255, 255, 0.1)',
            categoryorder='total descending',
            title=dict(
                text='Composer',
                font=dict(size=14, color='#f8f8f8', family='Montserrat')
            )
        )
    )

    # Add text to bars
    fig.update_traces(
        textposition='outside',
        texttemplate='%{text} songs',
        textfont=dict(size=10, color='#c5a47e'),
        hovertemplate='<b>%{x}</b><br>' +
                      'Total Royalty: £%{y:,.2f}<br>' +
                      'Number of Songs: %{customdata[0]}<br>' +
                      'Songs: %{customdata[1]}<extra></extra>',
        customdata=df_agg[['Count', 'Song_Title']].values,
        marker=dict(
            line=dict(
                width=1,
                color='rgba(197, 164, 126, 0.3)'
            )
        )
    )

    # Convert to HTML
    chart = fig.to_html(full_html=False)

    return render(request, 'artist_logs/charts.html', {
        'chart': chart,
        'composer_filter': composer_filter,
        'song_title_filter': song_title_filter,
    })

def dashboard(request):
    """Dashboard view with summary statistics and charts."""
    # Get counts
    prs_count = Prs_data.objects.count()
    artist_count = Artist.objects.count()
    source_count = Source.objects.count()
    song_count = Song.objects.count()
    income_type_count = IncomeType.objects.count()
    composer_count = Composer.objects.count()
    payment_statement_count = PaymentStatement.objects.count()
    payment_plan_count = PaymentPlan.objects.count()

    # Calculate total royalty
    total_royalty = Prs_data.objects.aggregate(total=Sum('royalty_payable'))['total'] or 0

    # Get recent records
    recent_records = Prs_data.objects.all().order_by('-created_at')[:10]

    # Royalty by Artist
    artist_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.artist:
            artist_royalties[record.artist] += float(record.royalty_payable or 0)

    # Royalty by Source
    source_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.source_name:
            source_royalties[record.source_name] += float(record.royalty_payable or 0)

    # Royalty Over Time
    period_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.income_period:
            period_royalties[record.income_period] += float(record.royalty_payable or 0)

    income_periods = sorted(period_royalties.keys())
    period_royalty_values = [period_royalties[period] for period in income_periods]

    return render(request, 'artist_logs/dashboard.html', {
        'prs_count': prs_count,
        'artist_count': artist_count,
        'source_count': source_count,
        'song_count': song_count,
        'income_type_count': income_type_count,
        'composer_count': composer_count,
        'payment_statement_count': payment_statement_count,
        'payment_plan_count': payment_plan_count,
        'total_royalty': total_royalty,
        'recent_records': recent_records,
        'artist_names': json.dumps(list(artist_royalties.keys())),
        'artist_royalties': json.dumps(list(artist_royalties.values())),
        'source_names': json.dumps(list(source_royalties.keys())),
        'source_royalties': json.dumps(list(source_royalties.values())),
        'income_periods': json.dumps(income_periods),
        'period_royalties': json.dumps(period_royalty_values),
    })

# =============================================
# PRS Admin Views
# =============================================

from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.shortcuts import render, redirect
from io import StringIO
import csv
import hashlib
from artist_logs.models import (
    Song, Composer, Prs_data, Source, IncomeType,
    UploadHistory, Artist, PaymentStatement, PaymentPlan, SongComposer
)
import re

def parse_composer_splits(composers_text):
    """
    Parse composer splits from text.
    Supports formats like:
    - "Scott Green (60%), Theo Rivers (40%)"
    - "Scott Green:60, Theo Rivers:40"
    - "Scott Green, Theo Rivers" (equal split)
    Returns a list of tuples: [(composer_name, percentage), ...]
    """
    if not composers_text:
        return []

    splits = []

    # Pattern 1: "Name (XX%)"
    pattern1 = r'([^(]+)\s*\((\d+)%\)'
    matches = re.findall(pattern1, composers_text)
    for name, percentage in matches:
        splits.append((name.strip(), float(percentage)))

    # If no matches with pattern 1, try pattern 2: "Name:XX"
    if not splits:
        pattern2 = r'([^:]+):(\d+)'
        matches = re.findall(pattern2, composers_text)
        for name, percentage in matches:
            splits.append((name.strip(), float(percentage)))

    # If still no matches, assume equal split
    if not splits:
        names = [name.strip() for name in composers_text.replace(';', ',').replace('/', ',').split(',') if name.strip()]
        if names:
            percentage = 100.0 / len(names)
            for name in names:
                splits.append((name, percentage))

    # Normalize percentages to sum to 100 if they don't
    total = sum(p for _, p in splits)
    if total > 0 and total != 100:
        factor = 100.0 / total
        splits = [(name, p * factor) for name, p in splits]

    return splits

@require_http_methods(["GET", "POST"])
def prs_admin(request):
    """
    View for uploading CSV files, tracking upload history, and displaying recent records.
    Handles both AJAX uploads (with progress tracking) and regular form submissions.
    Now supports multiple composers per song with royalty splits.
    """
    # --- Handle CSV upload ---
    if request.method == 'POST' and 'csv_file' in request.FILES:
        csv_file = request.FILES['csv_file']
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not csv_file.name.endswith('.csv'):
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Please upload a CSV file.'
                }, status=400)
            else:
                messages.error(request, "Please upload a CSV file.")
                return redirect('artist_logs:prs_admin')

        try:
            # --- Check for duplicate uploads ---
            if isinstance(csv_file, InMemoryUploadedFile):
                csv_file.seek(0)
                file_content = csv_file.read()
                file_hash = hashlib.md5(file_content).hexdigest()
                csv_file.seek(0)
            else:
                with open(csv_file.temporary_file_path(), 'rb') as f:
                    file_content = f.read()
                    file_hash = hashlib.md5(file_content).hexdigest()

            if UploadHistory.objects.filter(file_hash=file_hash).exists():
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f"This file ('{csv_file.name}') has already been uploaded and processed."
                    }, status=400)
                else:
                    messages.error(request, f"❌ This file ('{csv_file.name}') has already been uploaded and processed.")
                    return redirect('artist_logs:prs_admin')

            # --- Read CSV data for preview and processing ---
            csv_data = csv_file.read().decode('utf-8-sig')
            csv_file.seek(0)

            csv_io = StringIO(csv_data)
            reader = csv.DictReader(csv_io)
            fieldnames = reader.fieldnames

            # Create preview data (first 10 columns, first 5 rows)
            csv_io.seek(0)
            reader = csv.DictReader(csv_io)
            preview = [fieldnames[:10]] if fieldnames else []
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                preview_row = []
                for field in fieldnames[:10]:
                    preview_row.append(row.get(field, ''))
                preview.append(preview_row)

            # Reset for processing
            csv_io = StringIO(csv_data)
            reader = csv.DictReader(csv_io)

            # CSV-to-model field mapping
            csv_to_model = {
                'Client Code': 'client_code',
                'Client Name': 'client_name',
                'Payee Code': 'payee_code',
                'Payee Name': 'payee_name',
                'Song Code': 'song_code',
                'Song Title': 'song_title',
                'Composers': 'composers',
                'Source Code': 'source_code',
                'Source Name': 'source_name',
                'Income Type': 'income_type_code',
                'Income Type Name': 'income_type_name',
                'Main Income Type Name': 'main_income_type_name',
                'Catalogue No ': 'catalogue_no',
                'Units': 'units',
                'Income Period': 'income_period',
                'Percentage Collected by BMG': 'percentage_collected',
                'Amount Collected': 'amount_collected',
                'Royalty Payout Percentage': 'royalty_payout_percentage',
                'Royalty Payable': 'royalty_payable',
                'Domestic Or Foreign Source Indicator': 'domestic_or_foreign',
                'Foreign Source': 'foreign_source',
                'Statement ID Year': 'statement_id_year',
                'Statement ID Number': 'statement_id_number',
                'Royalty Country Code': 'royalty_country_code',
                'Royalty Country Description': 'royalty_country_description',
                'Artist': 'artist',
                'ISRC': 'isrc',
                'Album Or Production': 'album_or_production',
                'Episode': 'episode',
                'License Number': 'license_number',
                'Original Source As Received': 'original_source_as_received',
                'Original Source': 'original_source',
            }

            # Check for required fields
            required_csv_fields = ['Song Title', 'Royalty Payable']
            missing = [field for field in required_csv_fields if field not in fieldnames]
            if missing:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f"CSV file is missing required fields: {', '.join(missing)}"
                    }, status=400)
                else:
                    messages.error(request, f"CSV file is missing required fields: {', '.join(missing)}")
                    return redirect('artist_logs:prs_admin')

            imported_count = 0
            skipped_count = 0
            errors = []

            with transaction.atomic():
                for row in reader:
                    try:
                        # Skip empty rows
                        if not row.get('Song Title', '').strip():
                            skipped_count += 1
                            continue

                        # Map CSV row to model fields
                        mapped_row = {}
                        for csv_header, model_field in csv_to_model.items():
                            if csv_header in row:
                                value = row[csv_header].strip() if row[csv_header] else ''
                                mapped_row[model_field] = value

                        # --- Handle Source ---
                        source_code = mapped_row.get('source_code', '')
                        source_name = mapped_row.get('source_name', '')
                        country_code = mapped_row.get('royalty_country_code', '')
                        country_name = mapped_row.get('royalty_country_description', '')
                        foreign_source = mapped_row.get('foreign_source', '')
                        original_source = mapped_row.get('original_source_as_received', '')
                        domestic_or_foreign = mapped_row.get('domestic_or_foreign', '')

                        is_domestic = domestic_or_foreign == 'D' if domestic_or_foreign else True

                        source, _ = Source.objects.get_or_create(
                            code=source_code if source_code else "UNKNOWN",
                            defaults={
                                'name': source_name if source_name else "Unknown Source",
                                'is_domestic': is_domestic,
                                'country_code': country_code,
                                'country_name': country_name,
                                'foreign_source': foreign_source,
                                'original_source': original_source
                            }
                        )

                        # --- Handle IncomeType ---
                        income_type_code = mapped_row.get('income_type_code', '')
                        income_type_name = mapped_row.get('income_type_name', '')
                        main_income_type = mapped_row.get('main_income_type_name', '')

                        income_type, _ = IncomeType.objects.get_or_create(
                            code=income_type_code if income_type_code else "UNKNOWN",
                            defaults={
                                'name': income_type_name if income_type_name else "Unknown Income Type",
                                'main_type': main_income_type
                            }
                        )

                        # --- Handle Song ---
                        song_code = mapped_row.get('song_code', '').strip() or None
                        song_title = mapped_row.get('song_title', '').strip()
                        catalogue_no = mapped_row.get('catalogue_no', '').strip()
                        isrc = mapped_row.get('isrc', '').strip()
                        album = mapped_row.get('album_or_production', '').strip()
                        episode = mapped_row.get('episode', '').strip()
                        license_number = mapped_row.get('license_number', '').strip()
                        composers_text = mapped_row.get('composers', '').strip()

                        # Create or get the song
                        song, created = Song.objects.get_or_create(
                            code=song_code,
                            defaults={
                                'title': song_title,
                                'catalogue_number': catalogue_no,
                                'isrc': isrc,
                                'album_or_production': album,
                                'episode': episode,
                                'license_number': license_number,
                            }
                        )

                        # Update song fields if they've changed
                        if not created:
                            if song.title != song_title:
                                song.title = song_title
                            if song.catalogue_number != catalogue_no:
                                song.catalogue_number = catalogue_no
                            if song.isrc != isrc:
                                song.isrc = isrc
                            if song.album_or_production != album:
                                song.album_or_production = album
                            if song.episode != episode:
                                song.episode = episode
                            if song.license_number != license_number:
                                song.license_number = license_number
                            song.save()

                        # --- Handle Composers with Splits ---
                        if composers_text:
                            try:
                                # Parse composer splits
                                splits = parse_composer_splits(composers_text)

                                # Clear existing composers for this song
                                song.song_composers.all().delete()

                                # Add new composers with splits
                                for composer_name, percentage in splits:
                                    # Parse the name
                                    parts = composer_name.split()
                                    if len(parts) > 1:
                                        first_name = ' '.join(parts[:-1])
                                        last_name = parts[-1]
                                    else:
                                        first_name = ''
                                        last_name = parts[0]

                                    # Get or create the composer
                                    composer, _ = Composer.objects.get_or_create(
                                        first_name=first_name,
                                        last_name=last_name,
                                        defaults={'full_name': composer_name}
                                    )

                                    # Create SongComposer record
                                    SongComposer.objects.create(
                                        song=song,
                                        composer=composer,
                                        split_percentage=percentage
                                    )

                                # Set the first composer as the legacy composer for backward compatibility
                                if song.song_composers.exists():
                                    song.composer = song.song_composers.first().composer
                                    song.save(update_fields=['composer'])

                            except Exception as e:
                                errors.append(f"Error processing composer splits for song {song_code}: {str(e)}")
                                # Continue with the PRS data creation even if composer splits fail

                        # --- Create Prs_data (ALLOWS DUPLICATES) ---
                        prs_data = Prs_data.objects.create(
                            song=song,
                            song_title=song_title,
                            song_code=song_code,
                            income_period=mapped_row.get('income_period', ''),
                            source=source,
                            source_code=source_code,
                            source_name=source_name,
                            domestic_or_foreign=domestic_or_foreign,
                            foreign_source=foreign_source,
                            royalty_country_code=country_code,
                            royalty_country_description=country_name,
                            income_type=income_type,
                            income_type_code=income_type_code,
                            income_type_name=income_type_name,
                            main_income_type_name=main_income_type,
                            units=int(mapped_row.get('units', 0)) if mapped_row.get('units') else 0,
                            percentage_collected=float(mapped_row.get('percentage_collected', 0)) if mapped_row.get('percentage_collected') else 0.00,
                            amount_collected=float(mapped_row.get('amount_collected', 0)) if mapped_row.get('amount_collected') else 0.00,
                            royalty_payout_percentage=float(mapped_row.get('royalty_payout_percentage', 0)) if mapped_row.get('royalty_payout_percentage') else 0.00,
                            royalty_payable=float(mapped_row.get('royalty_payable', 0)) if mapped_row.get('royalty_payable') else 0.00,
                            statement_id_year=mapped_row.get('statement_id_year', ''),
                            statement_id_number=mapped_row.get('statement_id_number', ''),
                            catalogue_no=catalogue_no,
                            composers=composers_text,
                            artist=mapped_row.get('artist', ''),
                            isrc=isrc,
                            album_or_production=album,
                            episode=episode,
                            license_number=license_number,
                            original_source_as_received=original_source,
                            original_source=mapped_row.get('original_source', ''),
                            is_paid=False,
                        )
                        imported_count += 1

                    except Exception as e:
                        errors.append(f"Error importing row {reader.line_num}: {str(e)}")
                        continue

                # Create upload history record
                UploadHistory.objects.create(
                    file_name=csv_file.name,
                    file_hash=file_hash,
                    records_imported=imported_count,
                    status="Success"
                )

            # Return appropriate response
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'✅ Successfully processed {imported_count} new records. '
                               f'⏭️ Skipped {skipped_count} empty rows.',
                    'preview': preview,
                    'records_processed': imported_count
                })
            else:
                if imported_count > 0:
                    messages.success(request, f"✅ Successfully imported {imported_count} new records.")
                if skipped_count > 0:
                    messages.warning(request, f"⏭️ Skipped {skipped_count} empty rows.")
                if errors:
                    for error in errors[:10]:
                        messages.error(request, error)
                    if len(errors) > 10:
                        messages.error(request, f"... and {len(errors) - 10} more errors.")
                return redirect('artist_logs:prs_admin')

        except Exception as e:
            # Log failed upload
            UploadHistory.objects.create(
                file_name=csv_file.name,
                file_hash=file_hash if 'file_hash' in locals() else "",
                records_imported=0,
                status="Failed",
                error_message=str(e)
            )
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f"❌ An error occurred: {str(e)}"
                }, status=500)
            else:
                messages.error(request, f"❌ An error occurred: {str(e)}")
                return redirect('artist_logs:prs_admin')

    # --- Display page (GET request) ---
    upload_history = UploadHistory.objects.all().order_by('-uploaded_at')[:20]
    recent_records = Prs_data.objects.all().select_related('song', 'source', 'income_type').order_by('-created_at')[:100]

    # Get counts
    prs_count = Prs_data.objects.count()
    artist_count = Artist.objects.count()
    source_count = Source.objects.count()
    song_count = Song.objects.count()
    income_type_count = IncomeType.objects.count()
    composer_count = Composer.objects.count()
    payment_statement_count = PaymentStatement.objects.count()
    payment_plan_count = PaymentPlan.objects.count()
    payment_statements = PaymentStatement.objects.all().order_by('-created_at')[:5]

    return render(request, 'artist_logs/prs_admin.html', {
        'upload_history': upload_history,
        'recent_records': recent_records,
        'prs_count': prs_count,
        'artist_count': artist_count,
        'source_count': source_count,
        'song_count': song_count,
        'income_type_count': income_type_count,
        'composer_count': composer_count,
        'payment_statement_count': payment_statement_count,
        'payment_plan_count': payment_plan_count,
        'payment_statements': payment_statements,
    })

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from artist_logs.models import Song

def song_composer_splits(request, song_id):
    """
    Return composer splits for a song as JSON.
    """
    song = get_object_or_404(Song, pk=song_id)

    composer_splits = []
    for sc in song.song_composers.all():
        composer_splits.append({
            'composer_name': sc.composer.full_name,
            'split_percentage': sc.split_percentage,
            'notes': sc.notes or ''
        })

    return JsonResponse({
        'song_id': song.id,
        'song_title': song.title,
        'composers': composer_splits,
        'total_percentage': song.total_split_percentage
    })

# =============================================
# Backup/Restore Views
# =============================================

@require_POST
def backup_database(request):
    """
    Create a backup of all PRS-related data using manual serialization.
    This ensures a consistent format that can be properly verified and restored.
    """
    try:
        from django.core.serializers import serialize
        from django.core.serializers.json import DjangoJSONEncoder

        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'prs_backup_{timestamp}.json')

        # Get all model data using manual serialization
        data = {}

        # Define models in dependency order (parents first)
        models_to_backup = [
            ('IncomeType', IncomeType),
            ('Source', Source),
            ('Artist', Artist),
            ('Composer', Composer),
            ('Song', Song),
            ('UploadHistory', UploadHistory),
            ('PaymentStatement', PaymentStatement),
            ('Prs_data', Prs_data),
            ('PaymentPlan', PaymentPlan),
        ]

        for model_name, model in models_to_backup:
            try:
                records = model.objects.all()
                # Serialize with natural keys to handle relationships properly
                serialized = serialize('json', records, use_natural_foreign_keys=True)
                # Convert string to list
                data[model_name] = json.loads(serialized)
            except Exception as e:
                print(f"Error serializing {model_name}: {str(e)}")
                data[model_name] = []
                continue

        # Add metadata
        data['metadata'] = {
            'backup_date': datetime.now().isoformat(),
            'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
            'app_version': '1.0',
            'backup_method': 'manual_serialization',
            'model_count': len(models_to_backup)
        }

        # Write to file with proper JSON formatting
        with open(backup_file, 'w') as f:
            json.dump(data, f, indent=2, cls=DjangoJSONEncoder)

        messages.success(request, f"✅ Database backup created: {os.path.basename(backup_file)}")
    except Exception as e:
        messages.error(request, f"❌ Error creating backup: {str(e)}")
        import traceback
        print(f"Backup error: {str(e)}\n{traceback.format_exc()}")

    return redirect('artist_logs:backup_list')

@require_POST
def restore_database(request):
    """
    Restore database from a specific backup file.
    Only handles manual serialization format backups.
    """
    backup_filename = request.POST.get('backup_filename')

    if not backup_filename:
        messages.error(request, "❌ No backup file specified.")
        return redirect('artist_logs:backup_list')

    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, backup_filename)

    if not os.path.exists(backup_path):
        messages.error(request, f"❌ Backup file {backup_filename} not found.")
        return redirect('artist_logs:backup_list')

    try:
        # Load backup data
        with open(backup_path, 'r') as f:
            data = json.load(f)

        # Check if this is a valid manual serialization backup
        if not isinstance(data, dict) or 'metadata' not in data:
            messages.error(request, f"❌ Backup file {backup_filename} is not in the expected format. Please create a new backup.")
            return redirect('artist_logs:backup_list')

        # Check backup method
        backup_method = data.get('metadata', {}).get('backup_method', 'unknown')
        if backup_method != 'manual_serialization':
            messages.error(request, f"❌ Backup file {backup_filename} was created with {backup_method}. Please create a new backup with the current method.")
            return redirect('artist_logs:backup_list')

        # Clear existing data in reverse order of dependencies
        with transaction.atomic():
            # Delete all existing data in reverse order of dependencies
            PaymentPlan.objects.all().delete()
            Prs_data.objects.all().delete()
            PaymentStatement.objects.all().delete()
            UploadHistory.objects.all().delete()
            Song.objects.all().delete()
            Composer.objects.all().delete()
            Source.objects.all().delete()
            IncomeType.objects.all().delete()
            Artist.objects.all().delete()

            # Restore all data
            restore_model_data(data)

        messages.success(request, f"✅ Database restored from backup: {backup_filename}")
    except Exception as e:
        messages.error(request, f"❌ Error restoring backup: {str(e)}")
        import traceback
        print(f"Restore error: {str(e)}\n{traceback.format_exc()}")

    return redirect('artist_logs:backup_list')

@require_POST
def clear_prs_data(request):
    """
    Clear all PRS data and upload history while preserving composers and songs.
    """
    try:
        with transaction.atomic():
            # Count records before deletion
            prs_count = Prs_data.objects.count()
            upload_count = UploadHistory.objects.count()

            # Delete ONLY PRS data and upload history
            Prs_data.objects.all().delete()
            UploadHistory.objects.all().delete()

        messages.success(
            request,
            f"✅ Successfully deleted {prs_count} PRS data records and {upload_count} upload history records. "
            "Composers and Songs were preserved."
        )
    except Exception as e:
        messages.error(request, f"❌ Error clearing PRS data: {str(e)}")

    return redirect('artist_logs:prs_admin')

# =============================================
# Payment Statement Views
# =============================================

def payment_statement_list(request):
    """List all payment statements."""
    payment_statements = PaymentStatement.objects.all().order_by('-statement_date')
    return render(request, 'artist_logs/payment_statement_list.html', {
        'payment_statements': payment_statements,
    })

def payment_statement_detail(request, statement_id):
    """Show details of a specific payment statement."""
    statement = get_object_or_404(PaymentStatement, id=statement_id)
    prs_records = Prs_data.objects.filter(payment_statement=statement).order_by('-income_period')
    total_royalty = prs_records.aggregate(total=Sum('royalty_payable'))['total'] or 0

    return render(request, 'artist_logs/payment_statement_detail.html', {
        'statement': statement,
        'prs_records': prs_records,
        'total_royalty': total_royalty,
    })

def create_payment_statement(request):
    """Create a new payment statement."""
    if request.method == 'POST':
        form = PaymentStatementForm(request.POST)
        if form.is_valid():
            statement = form.save()
            messages.success(request, f"Payment statement '{statement.statement_number}' created successfully!")
            return redirect('artist_logs:payment_statement_detail', pk=statement.pk)
    else:
        form = PaymentStatementForm()

    return render(request, 'artist_logs/payment_statement_form.html', {
        'form': form,
        'title': 'Create Payment Statement',
    })

# =============================================
# PRS Data Views
# =============================================

def prs_data_detail(request, pk):
    """Show details for a single PRS data record."""
    record = get_object_or_404(Prs_data, pk=pk)
    return render(request, 'artist_logs/prs_data_detail.html', {
        'record': record,
    })

@require_POST
def mark_prs_data_as_paid(request, pk):
    """Mark a PRS data record as paid."""
    prs_data = get_object_or_404(Prs_data, pk=pk)

    try:
        prs_data.mark_as_paid(
            payment_statement=None,
            payment_date=timezone.now().date(),
            payment_amount=prs_data.royalty_payable,
            notes=f"Marked as paid manually via admin interface"
        )
        messages.success(request, f"PRS record for '{prs_data.song_title}' marked as paid!")
    except Exception as e:
        messages.error(request, f"Error marking as paid: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', 'artist_logs:data_table'))

@require_POST
def mark_prs_data_as_unpaid(request, pk):
    """Mark a PRS data record as unpaid."""
    prs_data = get_object_or_404(Prs_data, pk=pk)

    try:
        prs_data.mark_as_unpaid()
        messages.success(request, f"PRS record for '{prs_data.song_title}' marked as unpaid!")
    except Exception as e:
        messages.error(request, f"Error marking as unpaid: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', 'artist_logs:data_table'))

# =============================================
# Composer Views
# =============================================

def composer_list(request):
    """List all composers with filtering and pagination."""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    vat_filter = request.GET.get('vat', '')

    composers = Composer.objects.all().order_by('last_name', 'first_name')

    if search_query:
        composers = composers.filter(
            Q(full_name__icontains=search_query) |
            Q(composer_id__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if status_filter:
        if status_filter == 'active':
            composers = composers.filter(is_active=True)
        elif status_filter == 'inactive':
            composers = composers.filter(is_active=False)

    if vat_filter:
        if vat_filter == 'yes':
            composers = composers.filter(vat_registered=True)
        elif vat_filter == 'no':
            composers = composers.filter(vat_registered=False)

    composers = composers.annotate(
        song_count=Count('songs'),
        total_earnings=Sum('songs__prs_records__royalty_payable'),
        unpaid_earnings=Sum(
            Case(
                When(songs__prs_records__is_paid=False, then='songs__prs_records__royalty_payable'),
                default=0,
                output_field=models.DecimalField()
            )
        )
    )

    total_songs = Song.objects.count()
    total_earnings = Prs_data.objects.aggregate(total=Sum('royalty_payable'))['total'] or 0
    unpaid_earnings = Prs_data.objects.filter(is_paid=False).aggregate(total=Sum('royalty_payable'))['total'] or 0

    paginator = Paginator(composers, 20)
    page = request.GET.get('page')
    try:
        composers_page = paginator.page(page)
    except PageNotAnInteger:
        composers_page = paginator.page(1)
    except EmptyPage:
        composers_page = paginator.page(paginator.num_pages)

    return render(request, 'artist_logs/composer_list.html', {
        'composers': composers_page,
        'total_songs': total_songs,
        'total_earnings': total_earnings,
        'unpaid_earnings': unpaid_earnings,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': composers_page,
    })

def composer_detail(request, pk):
    """Show details for a single composer."""
    composer = get_object_or_404(Composer, pk=pk)
    songs = Song.objects.filter(composer=composer).order_by('title').annotate(
        prs_count=Count('prs_records'),
        total_earnings=Sum('prs_records__royalty_payable')
    )
    prs_records = Prs_data.objects.filter(song__composer=composer).order_by('-income_period')
    total_earnings = prs_records.aggregate(total=Sum('royalty_payable'))['total'] or 0
    unpaid_earnings = prs_records.filter(is_paid=False).aggregate(total=Sum('royalty_payable'))['total'] or 0
    payment_plans = PaymentPlan.objects.filter(composer=composer).order_by('-created_at')

    return render(request, 'artist_logs/composer_detail.html', {
        'composer': composer,
        'songs': songs,
        'prs_records': prs_records,
        'total_earnings': total_earnings,
        'unpaid_earnings': unpaid_earnings,
        'payment_plans': payment_plans,
    })

def composer_create(request):
    """Create a new composer."""
    if request.method == 'POST':
        form = ComposerForm(request.POST)
        if form.is_valid():
            composer = form.save()
            messages.success(request, f"Composer '{composer.full_name}' created successfully!")
            return redirect('artist_logs:composer_detail', pk=composer.pk)
    else:
        form = ComposerForm()

    return render(request, 'artist_logs/composer_form.html', {
        'form': form,
        'title': 'Add Composer',
    })

def composer_edit(request, pk):
    """Edit an existing composer."""
    composer = get_object_or_404(Composer, pk=pk)
    if request.method == 'POST':
        form = ComposerForm(request.POST, instance=composer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Composer '{composer.full_name}' updated successfully!")
            return redirect('artist_logs:composer_detail', pk=composer.pk)
    else:
        form = ComposerForm(instance=composer)

    return render(request, 'artist_logs/composer_form.html', {
        'form': form,
        'title': f'Edit {composer.full_name}',
    })

def composer_payment_history(request, pk):
    """Show payment history for a composer."""
    composer = get_object_or_404(Composer, pk=pk)
    payment_plans = PaymentPlan.objects.filter(composer=composer).order_by('-created_at')

    return render(request, 'artist_logs/composer_payment_history.html', {
        'composer': composer,
        'payment_plans': payment_plans,
    })

# =============================================
# Song Views
# =============================================

from django.shortcuts import render
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from .models import Song, Composer

def song_list(request):
    """
    List all songs with search, filtering, and pagination.
    Now supports multiple composers with royalty splits.
    """
    # Get filter parameters from the request
    search_query = request.GET.get('search', '')
    composer_id = request.GET.get('composer', '')
    has_composer = request.GET.get('has_composer', '')
    has_multiple_composers = request.GET.get('has_multiple_composers', '')

    # Base queryset - use prefetch_related for composer splits
    songs = Song.objects.all().prefetch_related('song_composers__composer').order_by('title')

    # Apply search filter
    if search_query:
        songs = songs.filter(
            Q(title__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(isrc__icontains=search_query) |
            Q(catalogue_number__icontains=search_query)
        )

    # Apply composer filter - now checks both legacy composer and song_composers
    if composer_id:
        songs = songs.filter(
            Q(composer_id=composer_id) |  # Legacy composer
            Q(song_composers__composer_id=composer_id)  # New composer splits
        ).distinct()

    # Apply "has composer" filter
    if has_composer == 'yes':
        songs = songs.filter(
            Q(composer__isnull=False) |  # Legacy composer
            Q(song_composers__isnull=False)  # New composer splits
        ).distinct()
    elif has_composer == 'no':
        songs = songs.filter(
            Q(composer__isnull=True) &
            Q(song_composers__isnull=True)
        )

    # Apply "has multiple composers" filter
    if has_multiple_composers == 'yes':
        # Songs with more than one composer in song_composers
        songs = songs.annotate(
            composer_count=Count('song_composers')
        ).filter(composer_count__gt=1)
    elif has_multiple_composers == 'no':
        # Songs with one or zero composers
        songs = songs.annotate(
            composer_count=Count('song_composers')
        ).filter(composer_count__lte=1)

    # Get all composers for the dropdown
    composers = Composer.objects.all().order_by('full_name')

    # Calculate statistics
    total_earnings = sum(song.total_earnings() for song in songs) if songs.exists() else 0

    # Count composers with songs (using either legacy or new relationships)
    composers_with_songs = Composer.objects.filter(
        Q(songs__in=songs) | Q(song_composers__song__in=songs)
    ).distinct().count()

    songs_with_prs = songs.filter(prs_records__isnull=False).distinct().count()

    # Pagination
    paginator = Paginator(songs, 20)  # Show 20 songs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'artist_logs/song_list.html', {
        'songs': page_obj,
        'composers': composers,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'total_earnings': total_earnings,
        'composers_with_songs': composers_with_songs,
        'songs_with_prs': songs_with_prs,
        'has_multiple_composers_filter': has_multiple_composers,
    })

def song_detail(request, pk):
    """
    Show details for a single song.
    """
    song = get_object_or_404(Song, pk=pk)

    # Get all PRS records for this song
    prs_records = Prs_data.objects.filter(song=song).order_by('-income_period')

    # Calculate totals
    total_earnings = prs_records.aggregate(total=Sum('royalty_payable'))['total'] or 0
    unpaid_earnings = prs_records.filter(is_paid=False).aggregate(total=Sum('royalty_payable'))['total'] or 0
    paid_earnings = prs_records.filter(is_paid=True).aggregate(total=Sum('royalty_payable'))['total'] or 0

    return render(request, 'artist_logs/song_detail.html', {
        'song': song,
        'prs_records': prs_records,
        'total_earnings': total_earnings,
        'unpaid_earnings': unpaid_earnings,
        'paid_earnings': paid_earnings,
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Song, Composer
from .forms import SongForm, SongComposerForm

def song_create(request):
    """
    Create a new song.
    """
    if request.method == 'POST':
        form = SongForm(request.POST)
        if form.is_valid():
            song = form.save()
            messages.success(request, f"Song '{song.title}' created successfully!")
            return redirect('artist_logs:song_detail', pk=song.pk)
    else:
        form = SongForm()

    return render(request, 'artist_logs/song_form.html', {
        'form': form,
        'title': 'Create New Song'
    })

def song_edit(request, pk):
    """
    Edit an existing song.
    """
    song = get_object_or_404(Song, pk=pk)

    if request.method == 'POST':
        form = SongForm(request.POST, instance=song)
        if form.is_valid():
            form.save()
            messages.success(request, f"Song '{song.title}' updated successfully!")
            return redirect('artist_logs:song_detail', pk=song.pk)
    else:
        form = SongForm(instance=song)

    return render(request, 'artist_logs/song_form.html', {
        'form': form,
        'song': song,
        'title': f'Edit {song.title}'
    })

# =============================================
# Composer Views
# =============================================

def composer_list(request):
    """
    List all composers with filtering and pagination.
    """
    # Get filter parameters from request
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    vat_filter = request.GET.get('vat', '')

    # Base queryset
    composers = Composer.objects.all().order_by('last_name', 'first_name')

    # Apply filters
    if search_query:
        composers = composers.filter(
            Q(full_name__icontains=search_query) |
            Q(composer_id__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if status_filter:
        if status_filter == 'active':
            composers = composers.filter(is_active=True)
        elif status_filter == 'inactive':
            composers = composers.filter(is_active=False)

    if vat_filter:
        if vat_filter == 'yes':
            composers = composers.filter(vat_registered=True)
        elif vat_filter == 'no':
            composers = composers.filter(vat_registered=False)

    # Annotate with song count and earnings
    composers = composers.annotate(
        song_count=Count('songs'),
        total_earnings=Sum('songs__prs_records__royalty_payable'),
        unpaid_earnings=Sum(
            Case(
                When(songs__prs_records__is_paid=False, then='songs__prs_records__royalty_payable'),
                default=0,
                output_field=models.DecimalField()
            )
        )
    )

    # Calculate totals for summary cards
    total_songs = Song.objects.count()
    total_earnings = Prs_data.objects.aggregate(total=Sum('royalty_payable'))['total'] or 0
    unpaid_earnings = Prs_data.objects.filter(is_paid=False).aggregate(total=Sum('royalty_payable'))['total'] or 0

    # Pagination
    paginator = Paginator(composers, 20)  # Show 20 composers per page
    page = request.GET.get('page')
    try:
        composers_page = paginator.page(page)
    except PageNotAnInteger:
        composers_page = paginator.page(1)
    except EmptyPage:
        composers_page = paginator.page(paginator.num_pages)

    return render(request, 'artist_logs/composer_list.html', {
        'composers': composers_page,
        'total_songs': total_songs,
        'total_earnings': total_earnings,
        'unpaid_earnings': unpaid_earnings,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': composers_page,
    })

def composer_detail(request, pk):
    """
    Show details for a single composer.
    """
    composer = get_object_or_404(Composer, pk=pk)

    # Get all songs by this composer
    songs = Song.objects.filter(composer=composer).order_by('title').annotate(
        prs_count=Count('prs_records'),
        total_earnings=Sum('prs_records__royalty_payable')
    )

    # Get all PRS records for this composer's songs
    prs_records = Prs_data.objects.filter(song__composer=composer).order_by('-income_period')

    # Calculate totals
    total_earnings = prs_records.aggregate(total=Sum('royalty_payable'))['total'] or 0
    unpaid_earnings = prs_records.filter(is_paid=False).aggregate(total=Sum('royalty_payable'))['total'] or 0

    # Get payment plans for this composer
    payment_plans = PaymentPlan.objects.filter(composer=composer).order_by('-created_at')

    return render(request, 'artist_logs/composer_detail.html', {
        'composer': composer,
        'songs': songs,
        'prs_records': prs_records,
        'total_earnings': total_earnings,
        'unpaid_earnings': unpaid_earnings,
        'payment_plans': payment_plans,
    })

def composer_create(request):
    """
    Create a new composer.
    """
    if request.method == 'POST':
        form = ComposerForm(request.POST)
        if form.is_valid():
            composer = form.save()
            messages.success(request, f"✅ Composer '{composer.full_name}' created successfully!")
            return redirect('artist_logs:composer_detail', pk=composer.pk)
    else:
        form = ComposerForm()

    return render(request, 'artist_logs/composer_form.html', {
        'form': form,
        'title': 'Add Composer',
    })

def composer_edit(request, pk):
    """
    Edit an existing composer.
    """
    composer = get_object_or_404(Composer, pk=pk)
    if request.method == 'POST':
        form = ComposerForm(request.POST, instance=composer)
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ Composer '{composer.full_name}' updated successfully!")
            return redirect('artist_logs:composer_detail', pk=composer.pk)
    else:
        form = ComposerForm(instance=composer)

    return render(request, 'artist_logs/composer_form.html', {
        'form': form,
        'title': f'Edit {composer.full_name}',
    })

def composer_payment_history(request, pk):
    """
    Show payment history for a composer.
    """
    composer = get_object_or_404(Composer, pk=pk)
    payment_plans = PaymentPlan.objects.filter(composer=composer).order_by('-created_at')

    return render(request, 'artist_logs/composer_payment_history.html', {
        'composer': composer,
        'payment_plans': payment_plans,
    })

# =============================================
# Payment Statement Views
# =============================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import PaymentStatement
from .forms import PaymentStatementForm

def create_payment_statement(request):
    """
    Create a new payment statement.
    """
    if request.method == 'POST':
        form = PaymentStatementForm(request.POST)
        if form.is_valid():
            statement = form.save()
            messages.success(request, f"Payment statement '{statement.statement_number}' created successfully!")
            return redirect('artist_logs:payment_statement_detail', pk=statement.pk)
    else:
        form = PaymentStatementForm()

    return render(request, 'artist_logs/payment_statement_form.html', {
        'form': form,
        'title': 'Create New Payment Statement'
    })

def payment_statement_detail(request, pk):
    """
    View details of a specific payment statement.
    """
    statement = get_object_or_404(PaymentStatement, pk=pk)
    prs_records = statement.prs_records.all().select_related('song', 'source', 'income_type')

    return render(request, 'artist_logs/payment_statement_detail.html', {
        'statement': statement,
        'prs_records': prs_records,
    })

def payment_statement_edit(request, pk):
    """
    Edit an existing payment statement.
    """
    statement = get_object_or_404(PaymentStatement, pk=pk)

    if request.method == 'POST':
        form = PaymentStatementForm(request.POST, instance=statement)
        if form.is_valid():
            form.save()
            messages.success(request, f"Payment statement '{statement.statement_number}' updated successfully!")
            return redirect('artist_logs:payment_statement_detail', pk=statement.pk)
    else:
        form = PaymentStatementForm(instance=statement)

    return render(request, 'artist_logs/payment_statement_form.html', {
        'form': form,
        'statement': statement,
        'title': f'Edit Payment Statement {statement.statement_number}'
    })

# =============================================
# PRS Data Views
# =============================================

def prs_data_detail(request, pk):
    """
    Show details for a single PRS data record.
    """
    record = get_object_or_404(Prs_data, pk=pk)
    return render(request, 'artist_logs/prs_data_detail.html', {
        'record': record,
    })

@require_POST
def mark_prs_data_as_paid(request, pk):
    """
    Mark a PRS data record as paid.
    """
    prs_data = get_object_or_404(Prs_data, pk=pk)

    try:
        prs_data.mark_as_paid(
            payment_statement=None,
            payment_date=timezone.now().date(),
            payment_amount=prs_data.royalty_payable,
            notes=f"Marked as paid manually via admin interface"
        )
        messages.success(request, f"✅ PRS record for '{prs_data.song_title}' marked as paid!")
    except Exception as e:
        messages.error(request, f"❌ Error marking as paid: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', 'artist_logs:data_table'))

@require_POST
def mark_prs_data_as_unpaid(request, pk):
    """
    Mark a PRS data record as unpaid.
    """
    prs_data = get_object_or_404(Prs_data, pk=pk)

    try:
        prs_data.mark_as_unpaid()
        messages.success(request, f"✅ PRS record for '{prs_data.song_title}' marked as unpaid!")
    except Exception as e:
        messages.error(request, f"❌ Error marking as unpaid: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', 'artist_logs:data_table'))

# =============================================
# Backup/Restore Views
# =============================================

@require_POST
def backup_database(request):
    """
    Create a backup of all PRS-related data using Django's dumpdata.
    """
    try:
        from django.core.management import call_command
        from django.core.management.color import no_style
        from io import StringIO

        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'prs_backup_{timestamp}.json')

        # Use Django's dumpdata command
        out = StringIO()
        call_command('dumpdata',
                    'artist_logs.Prs_data',
                    'artist_logs.UploadHistory',
                    'artist_logs.Composer',
                    'artist_logs.Song',
                    'artist_logs.Source',
                    'artist_logs.IncomeType',
                    'artist_logs.Artist',
                    'artist_logs.PaymentStatement',
                    'artist_logs.PaymentPlan',
                    stdout=out,
                    indent=2,
                    use_natural_foreign_keys=True,
                    use_natural_primary_keys=True)

        # Write to file
        with open(backup_file, 'w') as f:
            f.write(out.getvalue())

        messages.success(request, f"✅ Database backup created: {os.path.basename(backup_file)}")
    except Exception as e:
        messages.error(request, f"❌ Error creating backup: {str(e)}")
        import traceback
        print(f"Backup error: {str(e)}\n{traceback.format_exc()}")

    return redirect('artist_logs:prs_admin')

@require_POST
def restore_database(request):
    """
    Restore database from the most recent backup using Django's loaddata.
    """
    try:
        from django.core.management import call_command

        # Find the most recent backup
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            messages.error(request, "❌ No backups found. Please create a backup first.")
            return redirect('artist_logs:prs_admin')

        # Get all backup files
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('prs_backup_') and f.endswith('.json')]
        if not backup_files:
            messages.error(request, "❌ No backups found. Please create a backup first.")
            return redirect('artist_logs:prs_admin')

        # Sort by filename (which includes timestamp) and get the most recent
        backup_files.sort(reverse=True)
        latest_backup = os.path.join(backup_dir, backup_files[0])

        # Clear existing data in reverse order of dependencies
        with transaction.atomic():
            # Delete all existing data in reverse order of dependencies
            PaymentPlan.objects.all().delete()
            PaymentStatement.objects.all().delete()
            Prs_data.objects.all().delete()
            UploadHistory.objects.all().delete()
            Song.objects.all().delete()
            Composer.objects.all().delete()
            Source.objects.all().delete()
            IncomeType.objects.all().delete()
            Artist.objects.all().delete()

            # Use Django's loaddata command
            call_command('loaddata', latest_backup)

        messages.success(request, f"✅ Database restored from backup: {os.path.basename(latest_backup)}")
    except Exception as e:
        messages.error(request, f"❌ Error restoring backup: {str(e)}")
        import traceback
        print(f"Restore error: {str(e)}\n{traceback.format_exc()}")

    return redirect('artist_logs:prs_admin')

@require_POST
def clear_prs_data(request):
    """
    Clear all PRS data and upload history while preserving composers and songs.
    """
    try:
        with transaction.atomic():
            # Count records before deletion
            prs_count = Prs_data.objects.count()
            upload_count = UploadHistory.objects.count()

            # Delete ONLY PRS data and upload history
            Prs_data.objects.all().delete()
            UploadHistory.objects.all().delete()

        messages.success(
            request,
            f"✅ Successfully deleted {prs_count} PRS data records and {upload_count} upload history records. "
            "Composers and Songs were preserved."
        )
    except Exception as e:
        messages.error(request, f"❌ Error clearing PRS data: {str(e)}")

    return redirect('artist_logs:prs_admin')

# =============================================
# Backup List and Management Views
# =============================================

def backup_list(request):
    """
    List all available backups with proper error handling for invalid JSON.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = []

    if os.path.exists(backup_dir):
        try:
            for filename in sorted(os.listdir(backup_dir), reverse=True):
                if filename.startswith('prs_backup_') and filename.endswith('.json'):
                    filepath = os.path.join(backup_dir, filename)
                    stat = os.stat(filepath)

                    # Initialize metadata with defaults
                    metadata = {
                        'backup_date': 'Unknown',
                        'django_version': 'Unknown',
                        'app_version': 'Unknown'
                    }

                    # Try to read metadata from the backup file
                    try:
                        with open(filepath, 'r') as f:
                            # Read the first 10KB to check if it's valid JSON
                            # (We don't need to load the entire file just to get metadata)
                            first_part = f.read(10240)  # Read first 10KB
                            try:
                                data = json.loads(first_part)
                                if 'metadata' in data:
                                    metadata = data['metadata']
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error in {filename}: {str(e)}")
                                # File is not valid JSON, but we'll still list it
                                metadata['error'] = f"Invalid JSON: {str(e)}"
                    except Exception as e:
                        print(f"Error reading {filename}: {str(e)}")
                        metadata['error'] = f"Read error: {str(e)}"

                    backups.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'size_formatted': format_file_size(stat.st_size),
                        'backup_date': metadata.get('backup_date', 'Unknown'),
                        'has_error': 'error' in metadata,
                        'error_message': metadata.get('error', '')
                    })
        except Exception as e:
            print(f"Error listing backups: {str(e)}")
            messages.error(request, f"Error accessing backup directory: {str(e)}")

    # Sort by filename (which includes timestamp) in reverse order
    backups.sort(key=lambda x: x['filename'], reverse=True)

    return render(request, 'artist_logs/backup_list.html', {
        'backups': backups,
        'backup_count': len(backups)
    })

def verify_backup(request, filename):
    """
    Verify the contents of a backup file.
    Only handles manual serialization format.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, filename)

    if not os.path.exists(backup_path):
        messages.error(request, f"Backup file {filename} not found.")
        return redirect('artist_logs:backup_list')

    try:
        with open(backup_path, 'r') as f:
            data = json.load(f)

        # Check if this is a valid manual serialization backup
        if not isinstance(data, dict) or 'metadata' not in data:
            messages.error(request, f"Backup file {filename} is not in the expected format.")
            return redirect('artist_logs:backup_list')

        # Get record counts
        counts = {}
        for model_name, records in data.items():
            if model_name == 'metadata':
                continue
            if isinstance(records, list):
                counts[model_name] = len(records)
            else:
                counts[model_name] = 0

        # Get backup date
        backup_date = data.get('metadata', {}).get('backup_date', 'Unknown')

        return render(request, 'artist_logs/backup_verify.html', {
            'filename': filename,
            'counts': counts,
            'backup_date': backup_date,
            'backup_method': data.get('metadata', {}).get('backup_method', 'unknown')
        })

    except json.JSONDecodeError as e:
        messages.error(request, f"Error reading backup file (invalid JSON): {str(e)}")
        return redirect('artist_logs:backup_list')
    except Exception as e:
        messages.error(request, f"Error verifying backup: {str(e)}")
        return redirect('artist_logs:backup_list')

def download_backup(request, filename):
    """
    Download a backup file.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, filename)

    if os.path.exists(backup_path):
        return FileResponse(open(backup_path, 'rb'), as_attachment=True, filename=filename)
    else:
        messages.error(request, f"Backup file {filename} not found.")
        return redirect('artist_logs:backup_list')

@require_POST
def delete_backup(request, filename):
    """
    Delete a backup file.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, filename)

    if os.path.exists(backup_path):
        try:
            os.remove(backup_path)
            messages.success(request, f"✅ Backup {filename} deleted successfully.")
        except Exception as e:
            messages.error(request, f"❌ Error deleting backup: {str(e)}")
    else:
        messages.error(request, f"❌ Backup file {filename} not found.")

    return redirect('artist_logs:backup_list')

def format_file_size(size):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

# =============================================
# Mark as Paid/Unpaid Views
# =============================================

def mark_as_paid(request, record_id):
    """
    View to mark a Prs_data record as paid.
    """
    record = get_object_or_404(Prs_data, id=record_id)
    statement_id = request.POST.get('payment_statement_id')

    if not statement_id:
        messages.error(request, "❌ No payment statement selected.")
        return redirect('artist_logs:prs_admin')

    try:
        payment_statement = get_object_or_404(PaymentStatement, id=statement_id)

        record.mark_as_paid(
            payment_statement=payment_statement,
            payment_date=timezone.now().date(),
            payment_amount=record.royalty_payable,
            notes=f"Marked as paid via statement {payment_statement.statement_number}"
        )
        messages.success(request, f"✅ Record {record.id} marked as paid under {payment_statement.statement_number}!")
    except Exception as e:
        messages.error(request, f"❌ Error marking as paid: {str(e)}")

    return redirect('artist_logs:payment_statement_detail', statement_id=statement_id)

def mark_as_unpaid(request, record_id):
    """
    View to mark a Prs_data record as unpaid.
    """
    record = get_object_or_404(Prs_data, id=record_id)

    try:
        record.mark_as_unpaid()
        messages.success(request, f"✅ Record {record.id} marked as unpaid!")
    except Exception as e:
        messages.error(request, f"❌ Error marking as unpaid: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', 'artist_logs:prs_admin'))

# =============================================
# Backup/Restore Views
# =============================================

@require_POST
def backup_database(request):
    """
    Create a backup of all PRS-related data using Django's dumpdata.
    Ensures valid JSON output.
    """
    try:
        from django.core.management import call_command
        from io import StringIO

        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'prs_backup_{timestamp}.json')

        # Use Django's dumpdata command with proper formatting
        out = StringIO()
        try:
            call_command('dumpdata',
                        'artist_logs.Prs_data',
                        'artist_logs.UploadHistory',
                        'artist_logs.Composer',
                        'artist_logs.Song',
                        'artist_logs.Source',
                        'artist_logs.IncomeType',
                        'artist_logs.Artist',
                        'artist_logs.PaymentStatement',
                        'artist_logs.PaymentPlan',
                        stdout=out,
                        indent=2,
                        use_natural_foreign_keys=True,
                        use_natural_primary_keys=True)

            # Write to file
            with open(backup_file, 'w') as f:
                f.write(out.getvalue())

            messages.success(request, f"✅ Database backup created: {os.path.basename(backup_file)}")
        except Exception as e:
            # If dumpdata fails, try a manual backup
            print(f"dumpdata failed, trying manual backup: {str(e)}")
            try:
                # Fallback to manual serialization
                from django.core.serializers import serialize
                from django.core.serializers.json import DjangoJSONEncoder

                data = {}
                models_to_backup = [
                    ('IncomeType', IncomeType),
                    ('Source', Source),
                    ('Artist', Artist),
                    ('Composer', Composer),
                    ('Song', Song),
                    ('UploadHistory', UploadHistory),
                    ('PaymentStatement', PaymentStatement),
                    ('Prs_data', Prs_data),
                    ('PaymentPlan', PaymentPlan),
                ]

                for model_name, model in models_to_backup:
                    records = model.objects.all()
                    serialized = serialize('json', records, use_natural_foreign_keys=True)
                    data[model_name] = json.loads(serialized)

                # Add metadata
                data['metadata'] = {
                    'backup_date': datetime.now().isoformat(),
                    'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
                    'app_version': '1.0',
                    'backup_method': 'manual'
                }

                # Write to file
                with open(backup_file, 'w') as f:
                    json.dump(data, f, indent=2, cls=DjangoJSONEncoder)

                messages.success(request, f"✅ Database backup created (manual method): {os.path.basename(backup_file)}")
            except Exception as e:
                messages.error(request, f"❌ Error creating backup (both methods failed): {str(e)}")
                import traceback
                print(f"Backup error: {str(e)}\n{traceback.format_exc()}")
                # Clean up empty file if it was created
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                return redirect('artist_logs:prs_admin')

    except Exception as e:
        messages.error(request, f"❌ Error creating backup: {str(e)}")
        import traceback
        print(f"Backup error: {str(e)}\n{traceback.format_exc()}")

    return redirect('artist_logs:backup_list')

@require_POST
def restore_database(request):
    """
    Restore database from the most recent backup.
    Uses Django's deserializer for proper handling of all field types.
    """
    try:
        # Find the most recent backup
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            messages.error(request, "❌ No backups found. Please create a backup first.")
            return redirect('artist_logs:prs_admin')

        # Get all backup files
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('prs_backup_') and f.endswith('.json')]
        if not backup_files:
            messages.error(request, "❌ No backups found. Please create a backup first.")
            return redirect('artist_logs:prs_admin')

        # Sort by filename (which includes timestamp) and get the most recent
        backup_files.sort(reverse=True)
        latest_backup = os.path.join(backup_dir, backup_files[0])

        # Load backup data
        with open(latest_backup, 'r') as f:
            data = json.load(f)

        # Clear existing data in reverse order of dependencies
        with transaction.atomic():
            # Delete all existing data in reverse order of dependencies
            PaymentPlan.objects.all().delete()
            Prs_data.objects.all().delete()
            PaymentStatement.objects.all().delete()
            UploadHistory.objects.all().delete()
            Song.objects.all().delete()
            Composer.objects.all().delete()
            Source.objects.all().delete()
            IncomeType.objects.all().delete()
            Artist.objects.all().delete()

            # Restore all data
            restore_model_data(data)

        messages.success(request, f"✅ Database restored from backup: {os.path.basename(latest_backup)}")
    except Exception as e:
        messages.error(request, f"❌ Error restoring backup: {str(e)}")
        import traceback
        print(f"Restore error: {str(e)}\n{traceback.format_exc()}")

    return redirect('artist_logs:prs_admin')

@require_POST
def clear_prs_data(request):
    """
    Clear all PRS data and upload history while preserving composers and songs.
    """
    try:
        with transaction.atomic():
            # Count records before deletion
            prs_count = Prs_data.objects.count()
            upload_count = UploadHistory.objects.count()

            # Delete ONLY PRS data and upload history
            Prs_data.objects.all().delete()
            UploadHistory.objects.all().delete()

        messages.success(
            request,
            f"✅ Successfully deleted {prs_count} PRS data records and {upload_count} upload history records. "
            "Composers and Songs were preserved."
        )
    except Exception as e:
        messages.error(request, f"❌ Error clearing PRS data: {str(e)}")

    return redirect('artist_logs:prs_admin')

def backup_list(request):
    """List all available backups with proper error handling and metadata."""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = []

    if os.path.exists(backup_dir):
        try:
            for filename in os.listdir(backup_dir):
                if filename.startswith('prs_backup_') and filename.endswith('.json'):
                    filepath = os.path.join(backup_dir, filename)
                    stat = os.stat(filepath)

                    # Try to get metadata from the backup file
                    metadata = {'backup_date': 'Unknown'}
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            if 'metadata' in data:
                                metadata = data['metadata']
                    except Exception as e:
                        print(f"Error reading {filename}: {str(e)}")

                    backups.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'size_formatted': format_file_size(stat.st_size),
                        'backup_date': metadata.get('backup_date', 'Unknown')
                    })
        except Exception as e:
            print(f"Error listing backups: {str(e)}")
            messages.error(request, f"Error accessing backup directory: {str(e)}")

    # Sort by filename (which includes timestamp) in reverse order
    backups.sort(key=lambda x: x['filename'], reverse=True)

    return render(request, 'artist_logs/backup_list.html', {
        'backups': backups,
        'backup_count': len(backups)
    })

def format_file_size(size):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def get_all_model_data():
    """
    Get all data from all relevant models in a format suitable for backup.
    Handles foreign keys and other relationships properly.
    """
    data = {}

    # Get all models in the correct order for restoration
    models = [
        ('IncomeType', IncomeType),
        ('Source', Source),
        ('Artist', Artist),
        ('Composer', Composer),
        ('Song', Song),
        ('UploadHistory', UploadHistory),
        ('PaymentStatement', PaymentStatement),
        ('Prs_data', Prs_data),
        ('PaymentPlan', PaymentPlan),
    ]

    for model_name, model in models:
        # Get all records for this model
        records = model.objects.all()

        # Serialize using Django's serializer
        serialized = serialize('json', records, use_natural_foreign_keys=True, use_natural_primary_keys=True)
        data[model_name] = json.loads(serialized)

    return data

def restore_model_data(data):
    """
    Helper function to restore data from manual serialization format.
    """
    from django.core.serializers import deserialize

    # Order is critical - must restore in dependency order
    models_to_restore = [
        ('IncomeType', IncomeType),
        ('Source', Source),
        ('Artist', Artist),
        ('Composer', Composer),
        ('Song', Song),
        ('UploadHistory', UploadHistory),
        ('PaymentStatement', PaymentStatement),
        ('Prs_data', Prs_data),
        ('PaymentPlan', PaymentPlan),
    ]

    for model_name, model in models_to_restore:
        if model_name in data:
            serialized_data = json.dumps(data[model_name])
            try:
                objects = deserialize('json', serialized_data)
                for obj in objects:
                    obj.save()
            except Exception as e:
                print(f"Error restoring {model_name}: {str(e)}")
                continue

def verify_backup(request, filename):
    """
    Verify the contents of a backup file.
    Handles both manual serialization format and dumpdata format.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, filename)

    if not os.path.exists(backup_path):
        messages.error(request, f"Backup file {filename} not found.")
        return redirect('artist_logs:backup_list')

    try:
        with open(backup_path, 'r') as f:
            data = json.load(f)

        counts = {}

        # Check if this is the dumpdata format (list of objects)
        if isinstance(data, list):
            # Count records by model
            for item in data:
                model_name = item.get('model', 'unknown')
                if model_name != 'unknown':
                    # Extract the model name from "app.model" format
                    if '.' in model_name:
                        model_name = model_name.split('.')[-1]
                    counts[model_name] = counts.get(model_name, 0) + 1

        # Check if this is the manual serialization format (dict with model names as keys)
        elif isinstance(data, dict):
            for model_name, records in data.items():
                if model_name == 'metadata':
                    continue
                if isinstance(records, list):
                    counts[model_name] = len(records)
                elif isinstance(records, dict):
                    # Handle case where records is a single object
                    counts[model_name] = 1

        # Get backup date from metadata if available
        backup_date = 'Unknown'
        if isinstance(data, dict) and 'metadata' in data:
            backup_date = data['metadata'].get('backup_date', 'Unknown')
        elif isinstance(data, list):
            # For dumpdata format, we don't have metadata
            backup_date = datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime('%Y-%m-%d %H:%M:%S')

        return render(request, 'artist_logs/backup_verify.html', {
            'filename': filename,
            'counts': counts,
            'backup_date': backup_date,
            'is_dumpdata_format': isinstance(data, list)  # Pass format info to template
        })

    except json.JSONDecodeError as e:
        messages.error(request, f"Error reading backup file (invalid JSON): {str(e)}")
        return redirect('artist_logs:backup_list')
    except Exception as e:
        messages.error(request, f"Error verifying backup: {str(e)}")
        return redirect('artist_logs:backup_list')

def download_backup(request, filename):
    """Download a backup file"""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, filename)

    if os.path.exists(backup_path):
        return FileResponse(open(backup_path, 'rb'), as_attachment=True, filename=filename)
    else:
        messages.error(request, f"Backup file {filename} not found.")
        return redirect('artist_logs:backup_list')        
    
# ======================
# COMPOSER-SONG RELATIONSHIP VIEWS
# ======================

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from .models import Song, Composer, SongComposer
from .forms import ComposerForm, SongComposerForm

def composer_songs(request, pk):
    """
    View all songs by a specific composer with their split percentages.
    """
    composer = get_object_or_404(Composer, pk=pk)
    song_composers = composer.song_composers.all().select_related('song').order_by('-song__title')

    # Calculate total earnings for this composer
    total_earnings = sum(
        sc.song.total_earnings * (sc.split_percentage / 100)
        for sc in song_composers
    )

    return render(request, 'artist_logs/composer_songs.html', {
        'composer': composer,
        'song_composers': song_composers,
        'total_earnings': total_earnings,
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Song, Composer, SongComposer
from .forms import SongComposerForm

def add_composer_to_song(request, song_id):
    """
    View for adding/editing composers for a specific song with split percentages.
    """
    song = get_object_or_404(Song, pk=song_id)
    composers = Composer.objects.all().order_by('full_name')

    if request.method == 'POST':
        # Pass the song to the form
        form = SongComposerForm(request.POST, song=song)

        if form.is_valid():
            song_composer = form.save(commit=False)
            song_composer.song = song
            song_composer.save()

            # Set as legacy composer if this is the first one
            if not song.composer:
                song.composer = song_composer.composer
                song.save()

            messages.success(request, f"Added {song_composer.composer.full_name} with {song_composer.split_percentage}% split")
            return redirect('artist_logs:add_composer_to_song', song_id=song.id)
    else:
        # Pass the song to the form for GET requests too
        form = SongComposerForm(song=song)

    # Get current composers for this song
    current_composers = song.song_composers.all().select_related('composer')

    return render(request, 'artist_logs/add_composer_to_song.html', {
        'song': song,
        'form': form,
        'composers': composers,
        'current_composers': current_composers,
    })

def remove_composer_from_song(request, song_id, composer_id):
    """
    Remove a composer from a song.
    """
    song = get_object_or_404(Song, pk=song_id)
    song_composer = get_object_or_404(SongComposer, song=song, composer_id=composer_id)

    composer_name = song_composer.composer.full_name
    song_composer.delete()

    messages.success(request, f"Removed {composer_name} from {song.title}")

    # If this was the last composer, clear the legacy composer field
    if not song.song_composers.exists():
        song.composer = None
        song.save()

    return redirect('artist_logs:song_edit', pk=song.id)

def song_composer_splits(request, song_id):
    """
    Return composer splits for a song as JSON (for AJAX requests).
    """
    song = get_object_or_404(Song, pk=song_id)

    composer_splits = []
    for sc in song.song_composers.all():
        composer_splits.append({
            'composer_name': sc.composer.full_name,
            'split_percentage': float(sc.split_percentage),
            'notes': sc.notes or ''
        })

    return JsonResponse({
        'song_id': song.id,
        'song_title': song.title,
        'composers': composer_splits,
        'total_percentage': float(song.total_split_percentage)
    })

def quick_add_composer(request):
    """
    Quick form to add a new composer (used in the add_composer_to_song template).
    """
    if request.method == 'POST':
        form = ComposerForm(request.POST)
        if form.is_valid():
            composer = form.save()
            messages.success(request, f"Composer {composer.full_name} created successfully!")

            # Redirect to the referer or the next URL
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('artist_logs:composer_list')
    else:
        form = ComposerForm()

    next_url = request.GET.get('next', '')
    return render(request, 'artist_logs/quick_add_composer.html', {
        'form': form,
        'next': next_url
    })

def payment_statement_detail(request, pk):
    """
    View details of a specific payment statement.
    """
    statement = get_object_or_404(PaymentStatement, pk=pk)
    prs_records = statement.prs_records.all().select_related('song', 'source', 'income_type')

    return render(request, 'artist_logs/payment_statement_detail.html', {
        'statement': statement,
        'prs_records': prs_records,
    })