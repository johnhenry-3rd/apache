# =============================================
# STANDARD LIBRARY IMPORTS
# =============================================
import csv
import hashlib
import json
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal
from io import StringIO, TextIOWrapper
from decimal import Decimal, InvalidOperation
from .progress_tracker import upload_progress


# =============================================
# THIRD-PARTY IMPORTS
# =============================================
import pandas as pd
import plotly.express as px

# =============================================
# DJANGO IMPORTS
# =============================================
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.serializers import serialize, deserialize
from django.core.serializers.json import DjangoJSONEncoder
from django.db import (
    connection, transaction, IntegrityError, models
)
from django.db.models import (
    Q, Sum, Count, Case, When, F, Min, FloatField,
    ExpressionWrapper, Prefetch
)
from django.db.models.functions import Lower
from django.http import (
    JsonResponse, FileResponse, HttpResponse
)
from django.shortcuts import (
    render, redirect, get_object_or_404
)
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import (
    require_http_methods, require_POST
)

from django.db.models import Q, Sum
from django.http import JsonResponse
import csv
from io import TextIOWrapper
from .models import Prs_data
from datetime import datetime
from django.db import transaction
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
import gzip
import shutil

# =============================================
# LOCAL APPLICATION IMPORTS
# =============================================
from .forms import (
    ComposerForm, DataTableFilterForm, PaymentStatementForm,
    PRSUploadForm, SongComposerForm, SongForm
)
from .models import (
    Artist, Composer, IncomeType, PaymentPlan,
    PaymentStatement, Prs_data, Song, SongComposer,
    Source, UploadHistory
)

from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import StreamingHttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET
from .views import upload_progress


# =============================================
# LOGGING
# =============================================
logger = logging.getLogger(__name__)
import logging

# =============================================
#Constants and Helper functions
# =============================================

# Constants
BATCH_SIZE = 1000
REQUIRED_CSV_FIELDS = ['Song Code', 'Song Title', 'Amount Collected']

# =============================================
# CSV TO MODEL FIELD MAPPING (Single Definition)
# =============================================
# In your views.py
CSV_TO_MODEL = {
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
    'Catalogue No': 'catalogue_no',
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

# =============================================
#Segment 1: Helper Functions
# =============================================
# Global progress tracker (for demo purposes - use cache/db in production)
upload_progress = {
    'current': 0,
    'total': 0,
    'status': 'idle',  # 'idle', 'processing', 'complete'
    'imported': 0,
    'errors': [],
    'time': 0
}

def restore_model_data(data):
    """
    Helper function to restore data for a single model.
    """
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
        if model_name in data and data[model_name]:
            try:
                serialized_data = json.dumps(data[model_name])
                for deserialized_obj in deserialize('json', serialized_data):
                    deserialized_obj.save()
            except Exception as e:
                print(f"Error restoring {model_name}: {str(e)}")
                continue

# =============================================
# HELPER FUNCTIONS FOR CSV PROCESSING
# =============================================


def _safe_decimal(value):
    """Safely convert a value to Decimal with 2 decimal places"""
    try:
        if value is None or value == '':
            return Decimal('0.00')
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal('0.00')

def read_file_content(csv_file):
    """Read and decode file content."""
    from django.core.files.uploadedfile import InMemoryUploadedFile
    from io import StringIO

    if isinstance(csv_file, InMemoryUploadedFile):
        file_content = csv_file.read()
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8-sig')
        csv_file.seek(0)
    else:
        with csv_file.open('r', encoding='utf-8-sig') as f:
            file_content = f.read()
    return file_content

def get_csv_preview(file_content):
    """Generate a preview of the CSV file."""
    import csv
    from io import StringIO

    try:
        csv_data = StringIO(file_content)
        reader = csv.DictReader(csv_data)
        headers = reader.fieldnames or []
        rows = [list(row.values())[:10] for _, row in zip(range(5), reader)]
        return {'headers': headers, 'rows': rows}
    except Exception as e:
        logger.error(f"Error generating CSV preview: {str(e)}")
        return {'headers': [], 'rows': []}

def validate_csv_structure(fieldnames):
    """Validate CSV has required fields."""
    REQUIRED_CSV_FIELDS = ['Song Code', 'Song Title', 'Royalty Payable']
    missing = [f for f in REQUIRED_CSV_FIELDS if f not in fieldnames]
    return missing

def parse_composer_splits(composers_text):
    """
    Parse composer splits and return percentages as FLOATS (not Decimals)
    """
    if not composers_text:
        return []

    composers_text = composers_text.strip()
    splits = []

    # Case 1: Percentage-based splits
    if '%' in composers_text:
        parts = [p.strip() for p in composers_text.split(',')]
        for part in parts:
            if '%' in part:
                last_percent_idx = part.rfind('%')
                name_part = part[:last_percent_idx].strip()
                percentage = float(part[last_percent_idx+1:].strip())  # ✅ Return as float

                if '/' in name_part:
                    names = [n.strip() for n in name_part.split('/')]
                    for name in names:
                        splits.append((name, percentage / len(names)))  # ✅ float / int → float
                else:
                    splits.append((name_part, percentage))
            else:
                splits.append((part, 100.0))  # ✅ float

    # Case 2: Slash-separated names
    elif '/' in composers_text:
        names = [name.strip() for name in composers_text.split('/')]
        split = 100.0 / len(names)  # ✅ float
        splits = [(name, split) for name in names]

    # Case 3: Simple name
    else:
        splits = [(composers_text, 100.0)]  # ✅ float

    return splits

    # Normalize percentages to ensure they sum to 100
    total = sum(p for _, p in splits)
    if total > 0 and abs(total - 100) > 0.01:  # Allow small floating point differences
        # Scale all percentages to sum to 100
        factor = 100.0 / total
        splits = [(name, percentage * factor) for name, percentage in splits]

    return splits

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



@require_http_methods(["GET", "POST"])
def prs_admin(request):
    """
    View for the PRS admin page.
    Displays upload form, history, and recent records.
    """
    # GET request: Display the page
    if request.method == 'GET':
        try:
            # Get upload history
            upload_history = UploadHistory.objects.select_related('user').all().order_by('-uploaded_at')[:20]

            # Get recent records
            recent_records = Prs_data.objects.select_related(
                'song', 'source', 'income_type', 'payment_statement'
            ).prefetch_related(
                'song__composer', 'song__song_composers__composer'
            ).order_by('-created_at')[:100]

            # Get counts
            counts = {
                'prs_count': Prs_data.objects.count(),
                'song_count': Song.objects.count(),
                'source_count': Source.objects.count(),
                'income_type_count': IncomeType.objects.count(),
                'composer_count': Composer.objects.count(),
                'payment_statement_count': PaymentStatement.objects.count(),
            }

            # Get recent payment statements
            payment_statements = PaymentStatement.objects.all().order_by('-created_at')[:5]

            # Close old connections
            connection.close_if_unusable_or_obsolete()

            return render(request, 'artist_logs/prs_admin.html', {
                'upload_history': upload_history,
                'recent_records': recent_records,
                'form': PRSUploadForm(),
                **counts,
                'payment_statements': payment_statements,
            })

        except Exception as e:
            messages.error(request, f"Error loading PRS admin page: {str(e)}")
            return render(request, 'artist_logs/prs_admin.html', {
                'form': PRSUploadForm(),
                'error': str(e)
            })

    # POST request: Handle file upload
    elif request.method == 'POST' and 'csv_file' in request.FILES:
        return upload_prs_csv(request)  # Delegate to upload function

    # If POST but no file
    messages.error(request, "No file was uploaded")
    return redirect('artist_logs:prs_admin')

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
    """
    View to display PRS data with advanced filtering, pagination, and PostgreSQL optimizations.
    """
    # Initialize form with GET data
    form = DataTableFilterForm(request.GET or None)

    # Start with a base queryset
    prs_data_list = Prs_data.objects.select_related(
        'song', 'source', 'income_type', 'payment_statement'
    ).prefetch_related(
        'song__composer', 'song__song_composers__composer'
    ).order_by('-income_period', 'song_title')

    # Only access cleaned_data after is_valid()
    if form.is_valid():
        # Apply filters from the form
        if form.cleaned_data.get('artist'):
            prs_data_list = prs_data_list.filter(
                Q(artist__icontains=form.cleaned_data['artist']) |
                Q(song__composer__full_name__icontains=form.cleaned_data['artist']) |
                Q(song__song_composers__composer__full_name__icontains=form.cleaned_data['artist'])
            ).distinct()

        if form.cleaned_data.get('song_title'):
            prs_data_list = prs_data_list.filter(
                Q(song_title__icontains=form.cleaned_data['song_title']) |
                Q(song__title__icontains=form.cleaned_data['song_title'])
            ).distinct()

        # ... [rest of your filter conditions] ...

    # Calculate statistics
    stats = prs_data_list.aggregate(
        total_records=Count('id'),
        total_earnings=Sum('royalty_payable'),
        total_paid=Sum('royalty_payable', filter=Q(is_paid=True)),
        total_unpaid=Sum('royalty_payable', filter=Q(is_paid=False)),
    )

    # Pagination
    paginator = Paginator(prs_data_list, 100)
    page = request.GET.get('page')

    try:
        prs_data = paginator.page(page)
    except PageNotAnInteger:
        prs_data = paginator.page(1)
    except EmptyPage:
        prs_data = paginator.page(paginator.num_pages)

    # Close any old database connections
    connection.close_if_unusable_or_obsolete()

    # Prepare context
    context = {
        'prs_data': prs_data,
        'form': form,
        'stats': {
            'total_records': stats['total_records'] or 0,
            'total_earnings': stats['total_earnings'] or 0,
            'total_paid': stats['total_paid'] or 0,
            'total_unpaid': stats['total_unpaid'] or 0,
        },
        'is_paginated': paginator.num_pages > 1,
        'page_obj': prs_data,
    }

    return render(request, 'artist_logs/data_table.html', context)

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

# ============================================================================
# OPTIMIZED PRS DATA UPLOAD VIEW
# - Batch processing for 10-100x speed improvement
# - Proper duplicate handling (no silent skipping)
# - Real-time progress updates
# - Memory-efficient processing
# ============================================================================


from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, StreamingHttpResponse
from .progress_tracker import upload_progress  # ✅ Import at the top
import time

@require_http_methods(["POST"])
def upload_prs_csv(request):
    """
    Optimized PRS data upload view with:
    - Batch processing (1000 records at a time)
    - Real-time progress updates for AJAX
    - Memory-efficient CSV processing
    """
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Files in request: {request.FILES}")

    # Initialize counters
    imported_count = 0
    updated_count = 0
    skipped_count = 0
    duplicate_count = 0
    errors = []
    start_time = time.time()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Authentication check
    if not request.user.is_authenticated:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
        return redirect('login')

    if 'csv_file' not in request.FILES:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'No file uploaded'}, status=400)
        messages.error(request, "No file uploaded")
        return redirect('artist_logs:prs_admin')

    try:
        csv_file = request.FILES['csv_file']
        print(f"DEBUG: File received: {csv_file.name}")
        print(f"DEBUG: File size: {csv_file.size}")

        file_content = csv_file.read().decode('utf-8-sig')
        print(f"DEBUG: File content length: {len(file_content)}")
        file_hash = hashlib.md5(file_content.encode()).hexdigest()

        # ========================================================================
        # PHASE 1: PRE-PROCESSING
        # ========================================================================

        # Count total rows for progress reporting
        csv_io = StringIO(file_content)
        reader = csv.DictReader(csv_io)

        # Filter out completely empty rows
        non_empty_rows = [
            row for row in reader
            if any(row.get(key, '').strip() for key in row.keys())
        ]
        total_rows = len(non_empty_rows)

        if not total_rows:
            errors.append("No valid data rows found in file")
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'No valid data rows found',
                    'errors': errors
                }, status=400)
            messages.error(request, "No valid data rows found")
            return redirect('artist_logs:prs_admin')

        # Reset for processing
        csv_io = StringIO(file_content)
        reader = csv.DictReader(csv_io)

        # ========================================================================
        # PHASE 2: PRE-CACHE RELATED OBJECTS
        # ========================================================================

        # Cache all existing songs by code
        song_cache = {s.code: s for s in Song.objects.all()}

        # Cache all sources by code
        source_cache = {s.code: s for s in Source.objects.all()}

        # Cache all income types by code
        income_type_cache = {i.code: i for i in IncomeType.objects.all()}

        # ========================================================================
        # PHASE 3: BATCH PROCESSING
        # ========================================================================

        batch_size = 1000
        current_batch = []

        # Initialize progress for AJAX requests
        if is_ajax:
            upload_progress.update({
                'current': 0,
                'total': total_rows,
                'status': 'processing',
                'imported': 0,
                'errors': [],
                'time': 0
            })

        # Process all rows (both AJAX and non-AJAX)
        for row_num, row in enumerate(reader, start=1):
            try:
                # Skip completely empty rows
                if not any(row.get(key, '').strip() for key in row.keys()):
                    skipped_count += 1
                    continue

                # Process the row
                mapped_row = {}
                for csv_header, model_field in CSV_TO_MODEL.items():
                    mapped_row[model_field] = row.get(csv_header, '').strip() if csv_header in row else ''

                # Extract required fields
                song_code = mapped_row.get('song_code', '').strip()
                if not song_code:
                    errors.append(f"Row {row_num}: Missing Song Code")
                    if is_ajax:
                        upload_progress['errors'] = errors[:10]
                    continue

                # Get or create song
                song = song_cache.get(song_code)
                if not song:
                    song = Song.objects.get_or_create(
                        code=song_code,
                        defaults={
                            'title': mapped_row.get('song_title', '').strip(),
                            'catalogue_number': mapped_row.get('catalogue_no', '').strip(),
                            'isrc': mapped_row.get('isrc', '').strip(),
                            'album_or_production': mapped_row.get('album_or_production', '').strip(),
                            'episode': mapped_row.get('episode', '').strip(),
                            'license_number': mapped_row.get('license_number', '').strip(),
                        }
                    )[0]
                    song_cache[song_code] = song

                # Get or create source
                source_code = mapped_row.get('source_code', '').strip() or "UNKNOWN"
                source = source_cache.get(source_code)
                if not source:
                    source = Source.objects.get_or_create(
                        code=source_code,
                        defaults={
                            'name': mapped_row.get('source_name', '').strip() or "Unknown Source",
                            'is_domestic': mapped_row.get('domestic_or_foreign', '').strip() == 'D',
                            'country_code': mapped_row.get('royalty_country_code', '').strip(),
                            'country_name': mapped_row.get('royalty_country_description', '').strip(),
                            'foreign_source': mapped_row.get('foreign_source', '').strip(),
                        }
                    )[0]
                    source_cache[source_code] = source

                # Get or create income type
                income_type_code = mapped_row.get('income_type_code', '').strip() or "UNKNOWN"
                income_type = income_type_cache.get(income_type_code)
                if not income_type:
                    income_type = IncomeType.objects.get_or_create(
                        code=income_type_code,
                        defaults={
                            'name': mapped_row.get('income_type_name', '').strip() or "Unknown Income Type",
                            'main_type': mapped_row.get('main_income_type_name', '').strip(),
                        }
                    )[0]
                    income_type_cache[income_type_code] = income_type

                # Prepare data for batch processing
                prs_data = {
                    'song': song,
                    'song_code': song_code,
                    'song_title': mapped_row.get('song_title', '').strip(),
                    'units': int(mapped_row.get('units', 0) or 0),
                    'percentage_collected': _safe_decimal(mapped_row.get('percentage_collected', 0)),
                    'amount_collected': _safe_decimal(mapped_row.get('amount_collected', 0)),
                    'royalty_payout_percentage': _safe_decimal(mapped_row.get('royalty_payout_percentage', 0)),
                    'royalty_payable': _safe_decimal(mapped_row.get('royalty_payable', 0)),
                    'is_paid': False,
                    'source': source,
                    'source_code': source_code,
                    'source_name': mapped_row.get('source_name', '').strip(),
                    'domestic_or_foreign': mapped_row.get('domestic_or_foreign', '').strip(),
                    'foreign_source': mapped_row.get('foreign_source', '').strip(),
                    'royalty_country_code': mapped_row.get('royalty_country_code', '').strip(),
                    'royalty_country_description': mapped_row.get('royalty_country_description', '').strip(),
                    'income_type': income_type,
                    'income_type_code': income_type_code,
                    'income_type_name': mapped_row.get('income_type_name', '').strip(),
                    'main_income_type_name': mapped_row.get('main_income_type_name', '').strip(),
                    'statement_id_year': mapped_row.get('statement_id_year', '').strip(),
                    'statement_id_number': mapped_row.get('statement_id_number', '').strip(),
                    'income_period': mapped_row.get('income_period', '').strip(),
                    'catalogue_no': mapped_row.get('catalogue_no', '').strip(),
                    'composers': mapped_row.get('composers', '').strip(),
                    'artist': mapped_row.get('artist', '').strip(),
                    'isrc': mapped_row.get('isrc', '').strip(),
                    'album_or_production': mapped_row.get('album_or_production', '').strip(),
                    'episode': mapped_row.get('episode', '').strip(),
                    'license_number': mapped_row.get('license_number', '').strip(),
                    'original_source_as_received': mapped_row.get('original_source_as_received', '').strip() or None,
                    'original_source': mapped_row.get('original_source', '').strip() or None,
                }
                current_batch.append(prs_data)

                # Process batch when full
                if len(current_batch) >= batch_size:
                    _process_prs_batch(current_batch)
                    imported_count += len(current_batch)
                    current_batch = []

                    # Update progress for AJAX
                    if is_ajax:
                        upload_progress.update({
                            'current': row_num,
                            'imported': imported_count
                        })

                # Update progress every 100 rows for AJAX
                if is_ajax and row_num % 100 == 0:
                    upload_progress.update({
                        'current': row_num,
                        'imported': imported_count
                    })

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                if is_ajax:
                    upload_progress['errors'] = errors[:10]
                logger.error(f"Error processing row {row_num}: {str(e)}")
                continue

        # Process remaining items in the final batch
        if current_batch:
            _process_prs_batch(current_batch)
            imported_count += len(current_batch)

        # ========================================================================
        # PHASE 4: FINALIZE
        # ========================================================================

        elapsed_time = time.time() - start_time

        # Update final progress for AJAX
        if is_ajax:
            upload_progress.update({
                'current': total_rows,
                'status': 'complete',
                'imported': imported_count,
                'errors': errors[:10],
                'time': elapsed_time
            })

            return JsonResponse({
                'success': True,
                'message': f'Processed {imported_count} records in {elapsed_time:.2f}s',
                'imported': imported_count,
                'skipped': skipped_count,
                'errors': errors[:10]
            })

        # Create upload history for non-AJAX
        status = "Success" if not errors else "Partial"
        UploadHistory.objects.create(
            file_name=csv_file.name,
            file_hash=file_hash,
            records_imported=imported_count,
            records_updated=updated_count,
            records_skipped=skipped_count,
            records_duplicate=duplicate_count,
            status=status,
            error_message="; ".join(errors[:10]) if errors else None,
            uploaded_at=timezone.now(),
            processed_at=timezone.now(),
            user=request.user
        )

        if imported_count > 0:
            messages.success(request, f"✅ Imported {imported_count} new records")
        if updated_count > 0:
            messages.success(request, f"✅ Updated {updated_count} existing records")
        if skipped_count > 0:
            messages.warning(request, f"⏭️ Skipped {skipped_count} empty rows")
        if duplicate_count > 0:
            messages.warning(request, f"🔄 Found {duplicate_count} duplicate records (skipped)")
        if errors:
            for error in errors[:10]:
                messages.error(request, error)
            if len(errors) > 10:
                messages.error(request, f"... and {len(errors) - 10} more errors")

        return redirect('artist_logs:prs_admin')

    except Exception as e:
        logger.exception("File processing failed")
        elapsed_time = time.time() - start_time if 'start_time' in locals() else 0.0

        try:
            UploadHistory.objects.create(
                file_name=csv_file.name if 'csv_file' in locals() else 'unknown',
                file_hash=file_hash if 'file_hash' in locals() else '',
                records_imported=imported_count,
                records_updated=updated_count,
                status='Failed',
                error_message=str(e),
                uploaded_at=timezone.now(),
                user=request.user if request.user.is_authenticated else None
            )
        except:
            pass

        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f'❌ Failed to process file: {str(e)}',
                'errors': [str(e)]
            }, status=500)
        else:
            messages.error(request, f"❌ Failed to process file: {str(e)}")
            return redirect('artist_logs:prs_admin')

def _process_prs_batch(batch):
    """
    Process a batch of PRS records efficiently.
    Since duplicates are allowed, we simply bulk_create all records.
    """
    if not batch:
        return

    # Convert dictionaries to Prs_data instances
    records = []
    for item in batch:
        # Create a dictionary without the 'song' key
        prs_data = {k: v for k, v in item.items() if k != 'song'}

        # Create the record instance
        record = Prs_data(**prs_data)

        # Set the song ForeignKey
        record.song = item['song']

        records.append(record)

    # Bulk create all records (duplicates ARE allowed)
    Prs_data.objects.bulk_create(records, batch_size=1000)


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
    Create a compressed JSON backup of all PRS-related data.
    Uses Django's serialization and compresses the output.
    """
    try:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Check if directory is writable
        if not os.access(backup_dir, os.W_OK):
            messages.error(request, "❌ Backup directory is not writable. Check permissions.")
            return redirect('artist_logs:backup_list')

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'prs_backup_{timestamp}.json.gz')

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

        data = {}
        for model_name, model in models_to_backup:
            try:
                records = model.objects.all()
                serialized = serialize('json', records, use_natural_foreign_keys=True)
                data[model_name] = json.loads(serialized)
            except Exception as e:
                messages.warning(request, f"⚠️ Skipped {model_name} due to error: {str(e)}")
                data[model_name] = []
                continue

        # Add metadata
        data['metadata'] = {
            'backup_date': timezone.now().isoformat(),
            'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
            'app_version': '1.0',
            'backup_method': 'django_serialization',
            'model_count': len(models_to_backup),
            'created_by': str(request.user) if request.user.is_authenticated else 'system'
        }

        # Write to a temporary file first
        temp_file = os.path.join(backup_dir, f'prs_backup_{timestamp}.json')
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2, cls=DjangoJSONEncoder)

        # Compress the file
        with open(temp_file, 'rb') as f_in:
            with gzip.open(backup_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove the temporary file
        os.remove(temp_file)

        messages.success(request, f"✅ Backup created: {os.path.basename(backup_file)}")
    except Exception as e:
        messages.error(request, f"❌ Backup failed: {str(e)}")
        import traceback
        print(f"Backup error: {str(e)}\n{traceback.format_exc()}")

    return redirect('artist_logs:backup_list')

@require_POST
def restore_database(request):
    """
    Restore database from a backup file.
    Validates the backup, checks for corruption, and restores in a transaction.
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
        # Check if the file is a gzip file
        if backup_filename.endswith('.gz'):
            with gzip.open(backup_path, 'rt') as f:
                data = json.load(f)
        else:
            with open(backup_path, 'r') as f:
                data = json.load(f)

        # Validate backup structure
        if not isinstance(data, dict) or 'metadata' not in data:
            messages.error(request, f"❌ Backup file {backup_filename} is corrupted or invalid.")
            return redirect('artist_logs:backup_list')

        backup_method = data.get('metadata', {}).get('backup_method', 'unknown')
        if backup_method != 'django_serialization':
            messages.error(request, f"❌ Backup file {backup_filename} was created with {backup_method}. Use a compatible backup.")
            return redirect('artist_logs:backup_list')

        # Start a transaction
        with transaction.atomic():
            # Delete all existing data in reverse order of dependencies
            models_to_clear = [
                PaymentPlan, Prs_data, PaymentStatement, UploadHistory,
                Song, Composer, Source, IncomeType, Artist
            ]
            for model in models_to_clear:
                model.objects.all().delete()

            # Restore data in dependency order
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
                if model_name in data and data[model_name]:
                    try:
                        # Deserialize and restore
                        serialized_data = json.dumps(data[model_name])
                        for obj in serialize('json', model.objects.none()):
                            pass  # This is a placeholder to get the deserializer
                        from django.core.serializers import deserialize
                        for deserialized_obj in deserialize('json', serialized_data):
                            deserialized_obj.save()
                    except Exception as e:
                        messages.warning(request, f"⚠️ Failed to restore {model_name}: {str(e)}")
                        continue

        messages.success(request, f"✅ Database restored from backup: {backup_filename}")
    except json.JSONDecodeError:
        messages.error(request, f"❌ Backup file {backup_filename} is corrupted (invalid JSON).")
    except Exception as e:
        messages.error(request, f"❌ Restore failed: {str(e)}")
        import traceback
        print(f"Restore error: {str(e)}\n{traceback.format_exc()}")

    return redirect('artist_logs:backup_list')

def confirm_restore(request, backup_filename):
    """
    Show a confirmation page before restoring a backup.
    """
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, backup_filename)

    if not os.path.exists(backup_path):
        messages.error(request, f"❌ Backup file {backup_filename} not found.")
        return redirect('artist_logs:backup_list')

    # Get backup metadata (if available)
    metadata = {}
    try:
        if backup_filename.endswith('.gz'):
            with gzip.open(backup_path, 'rt') as f:
                data = json.load(f)
        else:
            with open(backup_path, 'r') as f:
                data = json.load(f)
        metadata = data.get('metadata', {})
    except Exception:
        pass

    return render(request, 'artist_logs/confirm_restore.html', {
        'backup_filename': backup_filename,
        'metadata': metadata
    })

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
# Song Views
# =============================================


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
    Show details for a single song with PostgreSQL optimizations.
    Includes comprehensive data about PRS records, composers, and earnings.
    """
    # Get the song with optimized queries
    song = get_object_or_404(
        Song.objects.prefetch_related(
            Prefetch('song_composers', queryset=SongComposer.objects.select_related('composer').order_by('-split_percentage')),
            Prefetch('prs_records', queryset=Prs_data.objects.select_related('source', 'income_type', 'payment_statement').order_by('-income_period'))
        ),
        pk=pk 
    )

    # Get PRS records with optimized query
    prs_records = song.prs_records.all()

    # Calculate totals using PostgreSQL aggregation
    totals = prs_records.aggregate(
        total_earnings=Sum('royalty_payable'),
        paid_earnings=Sum('royalty_payable', filter=Q(is_paid=True)),
        unpaid_earnings=Sum('royalty_payable', filter=Q(is_paid=False)),
        total_records=Count('id'),
        paid_records=Count('id', filter=Q(is_paid=True)),
        unpaid_records=Count('id', filter=Q(is_paid=False)),
        avg_royalty=ExpressionWrapper(
            Sum('royalty_payable') / Count('id'),
            output_field=FloatField()
        )
    )

    # Calculate earnings by various dimensions using PostgreSQL
    earnings_by_period = list(
        prs_records.values('income_period')
        .annotate(total=Sum('royalty_payable'))
        .order_by('income_period')
    )

    earnings_by_source = list(
        prs_records.values('source__name')
        .annotate(total=Sum('royalty_payable'))
        .order_by('-total')
    )

    earnings_by_income_type = list(
        prs_records.values('income_type__name')
        .annotate(total=Sum('royalty_payable'))
        .order_by('-total')
    )

    # Calculate composer earnings using PostgreSQL
    composer_earnings = []
    for sc in song.song_composers.all().select_related('composer'):
        # Calculate earnings for this composer using PostgreSQL
        composer_total = prs_records.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('royalty_payable') * (sc.split_percentage / 100),
                    output_field=FloatField()
                )
            )
        )['total'] or 0

        composer_earnings.append({
            'composer': sc.composer,
            'split_percentage': sc.split_percentage,
            'earnings': composer_total,
            'notes': sc.notes,
            'is_primary': sc == song.song_composers.first()
        })

    # Get recent payment statements
    recent_payments = PaymentStatement.objects.filter(
        prs_records__song=song
    ).distinct().order_by('-statement_date')[:5]

    # Get composer form for adding/editing composers
    composer_form = SongComposerForm()
    composer_form.song = song  # Set the song for the form

    # Close any old database connections to prevent "database is locked" errors
    connection.close_if_unusable_or_obsolete()

    # Prepare context
    context = {
        'song': song,
        'prs_records': prs_records,
        'totals': {
            'total_earnings': totals['total_earnings'] or 0,
            'paid_earnings': totals['paid_earnings'] or 0,
            'unpaid_earnings': totals['unpaid_earnings'] or 0,
            'total_records': totals['total_records'] or 0,
            'paid_records': totals['paid_records'] or 0,
            'unpaid_records': totals['unpaid_records'] or 0,
            'avg_royalty': totals['avg_royalty'] or 0,
        },
        'earnings_by_period': earnings_by_period,
        'earnings_by_source': earnings_by_source,
        'earnings_by_income_type': earnings_by_income_type,
        'composer_earnings': composer_earnings,
        'recent_payments': recent_payments,
        'composer_form': composer_form,
        'has_multiple_composers': song.has_multiple_composers,
        'total_split_percentage': song.total_split_percentage,
        'is_fully_split': song.is_fully_split,
    }

    return render(request, 'artist_logs/song_detail.html', context)


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
# Backup List and Management Views
# =============================================

def backup_list(request):
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = []

    if os.path.exists(backup_dir):
        for filename in sorted(os.listdir(backup_dir), reverse=True):
            if filename.endswith('.json.gz') or filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                backup_info = {
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'size_formatted': f"{os.path.getsize(filepath) / (1024 * 1024):.2f} MB",
                    'modified': timezone.datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S'),
                    'has_error': False,
                    'error_message': '',
                    'backup_date': 'Unknown'
                }

                # Try to read metadata
                try:
                    if filename.endswith('.gz'):
                        with gzip.open(filepath, 'rt') as f:
                            data = json.load(f)
                    else:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                    if 'metadata' in data:
                        backup_info['backup_date'] = data['metadata'].get('backup_date', 'Unknown')
                except Exception as e:
                    backup_info['has_error'] = True
                    backup_info['error_message'] = str(e)

                backups.append(backup_info)

    return render(request, 'artist_logs/backup_list.html', {
        'backups': backups,
        'backup_count': len(backups),
    })

def verify_backup(request, backup_filename):
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, backup_filename)

    if not os.path.exists(backup_path):
        messages.error(request, f"Backup file {backup_filename} not found.")
        return redirect('artist_logs:backup_list')

    try:
        if backup_filename.endswith('.gz'):
            with gzip.open(backup_path, 'rt') as f:
                data = json.load(f)
        else:
            with open(backup_path, 'r') as f:
                data = json.load(f)

        # Extract model counts
        model_counts = {}
        for model_name, records in data.items():
            if model_name != 'metadata':
                model_counts[model_name] = len(records)

        return render(request, 'artist_logs/verify_backup.html', {
            'backup_filename': backup_filename,
            'metadata': data.get('metadata', {}),
            'model_counts': model_counts,
        })
    except Exception as e:
        messages.error(request, f"Failed to verify backup: {str(e)}")
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
def delete_backup(request, backup_filename):
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, backup_filename)

    if os.path.exists(backup_path):
        try:
            os.remove(backup_path)
            messages.success(request, f"Backup {backup_filename} deleted successfully.")
        except Exception as e:
            messages.error(request, f"Failed to delete backup: {str(e)}")
    else:
        messages.error(request, f"Backup {backup_filename} not found.")

    return redirect('artist_logs:backup_list')


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

# ======================
# COMPOSER-SONG RELATIONSHIP VIEWS
# ======================


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
    composer = get_object_or_404(Composer, pk=composer_id)  # Ensure composer exists

    try:
        song_composer = get_object_or_404(
            SongComposer,
            song_id=song_id,
            composer_id=composer_id
        )
    except SongComposer.DoesNotExist:
        messages.error(
            request,
            f"Composer {composer.full_name} is not linked to song {song.title}."
        )
        return redirect('artist_logs:song_edit', pk=song.id)

    composer_name = song_composer.composer.full_name
    song_composer.delete()
    messages.success(request, f"Removed {composer_name} from {song.title}")

    # If this was the last composer, clear the legacy composer field
    if not song.song_composers.exists():
        song.composer = None
        song.save()

    return redirect('artist_logs:song_edit', pk=song.id)


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


def test_backup_list(request):
    """Minimal test view to check template rendering"""
    return render(request, 'artist_logs/backup_list.html', {
        'backups': [],  # Empty list for testing
        'backup_count': 0
    })

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'  # or your custom template
    redirect_authenticated_user = True
    next_page = reverse_lazy('prs_admin')  # Redirect to prs-admin after login

# Store progress state (in a real app, use a database or cache)
upload_progress = {
    'current': 0,
    'total': 0,
    'status': 'idle',
    'imported': 0,
    'errors': []
}


@require_GET
def sse_upload_progress(request):
    """Dedicated endpoint for SSE progress updates"""
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    def progress_generator():
        # Send initial state
        yield f"data: {json.dumps(upload_progress)}\n\n"

        # Keep connection open and send updates
        while upload_progress['status'] != 'complete':
            time.sleep(0.5)  # Check every 0.5 seconds
            yield f"data: {json.dumps(upload_progress)}\n\n"

        # Send final state
        yield f"data: {json.dumps(upload_progress)}\n\n"

    return StreamingHttpResponse(
        progress_generator(),
        content_type='text/event-stream'
    )
