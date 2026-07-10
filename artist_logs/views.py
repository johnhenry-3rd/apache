from django.db import models
from .models import Prs_data
from django.db.models import Q, Min
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.functions import Lower
import pandas as pd
import plotly.express as px
from django.db.models import Sum, Count, Avg
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from io import TextIOWrapper
import csv
from django.db.models import Sum
from collections import defaultdict
import json
from .models import Prs_data, Artist, Source, Song, IncomeType
from .models import Prs_data, UploadHistory
import hashlib
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import Prs_data, UploadHistory, Source, Song, IncomeType, Artist
import io
from io import StringIO
from django.shortcuts import render, redirect, get_object_or_404
from .models import Prs_data, PaymentStatement, UploadHistory
from django.utils import timezone
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Case, When, Q, F
from django import forms
from .models import (
    Composer, Song, Prs_data, PaymentStatement, PaymentPlan,
    UploadHistory, Source, IncomeType
)
from .forms import ComposerForm, SongForm
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from .forms import PaymentStatementForm
from .models import PaymentStatement


# Import models
from .models import (
    Prs_data,
    Artist,
    Source,
    IncomeType,
    Song,
    PaymentStatement,
    UploadHistory
)

from django.shortcuts import render
from .models import Prs_data, Source, IncomeType
from django.core.paginator import Paginator
from django.db.models import Q


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
    # Get filter parameters - use empty string as default
    composer_filter = request.GET.get('composer', '')
    song_title_filter = request.GET.get('song_title', '')

    # Start with all data
    data = Prs_data.objects.all()

    # Apply filters independently
    if composer_filter:
        data = data.filter(composers__name__icontains=composer_filter)
    if song_title_filter:
        data = data.filter(song_title__icontains=song_title_filter)

    # Distinct results (important for ManyToMany filtering)
    data = data.distinct()

    # Prepare data for Plotly - Group by Composer
    df_data = []
    for item in data:
        artist_name = item.artist if item.artist else "Unknown"
        df_data.append({
            'Composer': artist_name,
            'Royalty_Payable': float(item.royalty_payable) if item.royalty_payable is not None else 0.0,
            'Song_Title': item.song_title if item.song_title else "Unknown",
            'Count': 1
        })

    # Check if we have any data
    if not df_data:
        return render(request, 'artist_logs/charts.html', {
            'chart': '<div class="alert alert-info text-center">No data matches the filters.</div>',
            'composer_filter': composer_filter,
            'song_title_filter': song_title_filter,
        })

    # Convert to DataFrame
    df = pd.DataFrame(df_data)

    # Aggregate by composer (sum of royalties and count of songs)
    df_agg = df.groupby('Composer').agg({
        'Royalty_Payable': 'sum',
        'Song_Title': lambda x: ', '.join(x.unique()),  # List of unique song titles
        'Count': 'sum'
    }).reset_index()

    # Sort by Royalty_Payable (descending)
    df_agg = df_agg.sort_values('Royalty_Payable', ascending=False)

    # Create the chart with Apache Music styling
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

    # Improve layout with Apache Music theme
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

    # Add text to bars and customize hover
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
    print("🚀 DASHBOARD VIEW CALLED!")

    # --- DEBUG: Check total counts ---
    prs_count = Prs_data.objects.count()
    artist_count = Artist.objects.count()
    source_count = Source.objects.count()
    song_count = Song.objects.count()
    income_type_count = IncomeType.objects.count()
    print(f"📊 Dashboard Debug - Total Counts:")
    print(f"   PRS Records: {prs_count}")
    print(f"   Artists: {artist_count}")
    print(f"   Sources: {source_count}")
    print(f"   Songs: {song_count}")
    print(f"   Income Types: {income_type_count}")

    # --- Total Royalty ---
    total_royalty = Prs_data.objects.aggregate(total=Sum('royalty_payable'))['total'] or 0
    print(f"💰 Total Royalty: {total_royalty}")

    # --- Recent Records ---
    recent_records = Prs_data.objects.all().order_by('-created_at')[:10]
    print(f"📜 Recent Records ({recent_records.count()}):")
    for record in recent_records:
        print(f"   ID: {record.id}, Song: '{record.song_title}', Artist: '{record.artist}', Royalty: {record.royalty_payable}")

    # --- Royalty by Artist Chart ---
    artist_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.artist:
            artist_royalties[record.artist] += float(record.royalty_payable or 0)

    artist_names = list(artist_royalties.keys())
    artist_royalty_values = list(artist_royalties.values())
    print(f"🎤 Royalty by Artist - Names: {artist_names[:5]}")
    print(f"   Values: {artist_royalty_values[:5]}")

    # --- Royalty by Source Chart ---
    source_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.source_name:
            source_royalties[record.source_name] += float(record.royalty_payable or 0)

    source_names = list(source_royalties.keys())
    source_royalty_values = list(source_royalties.values())
    print(f"🌍 Royalty by Source - Names: {source_names[:5]}")
    print(f"   Values: {source_royalty_values[:5]}")

    # --- Royalty Over Time Chart ---
    period_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.income_period:
            period_royalties[record.income_period] += float(record.royalty_payable or 0)

    income_periods = sorted(period_royalties.keys())
    period_royalty_values = [period_royalties[period] for period in income_periods]
    print(f"📅 Royalty Over Time - Periods: {income_periods[:5]}")
    print(f"   Values: {period_royalty_values[:5]}")

    # --- Debug: Check if data is being passed to the template ---
    print("\n📦 Context Data Being Passed to Template:")
    print(f"   prs_count: {prs_count}")
    print(f"   artist_count: {artist_count}")
    print(f"   source_count: {source_count}")
    print(f"   song_count: {song_count}")
    print(f"   income_type_count: {income_type_count}")
    print(f"   total_royalty: {total_royalty}")
    print(f"   recent_records count: {recent_records.count()}")
    print(f"   artist_names count: {len(artist_names)}")
    print(f"   source_names count: {len(source_names)}")
    print(f"   income_periods count: {len(income_periods)}")

    return render(request, 'artist_logs/dashboard.html', {
        'prs_count': prs_count,
        'artist_count': artist_count,
        'source_count': source_count,
        'song_count': song_count,
        'income_type_count': income_type_count,
        'total_royalty': total_royalty,
        'recent_records': recent_records,
        'artist_names': json.dumps(artist_names),
        'artist_royalties': json.dumps(artist_royalty_values),
        'source_names': json.dumps(source_names),
        'source_royalties': json.dumps(source_royalty_values),
        'income_periods': json.dumps(income_periods),
        'period_royalties': json.dumps(period_royalty_values),
    })


from django.shortcuts import render
from django.db.models import Sum
from .models import Composer, Song, Prs_data, PaymentStatement, PaymentPlan, UploadHistory


from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Count, Case, When, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Composer, Song, Prs_data, PaymentStatement, PaymentPlan, UploadHistory, Source, IncomeType
from .forms import ComposerForm, SongForm  # If you have forms for these models

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
            messages.success(request, f"Composer '{composer.full_name}' created successfully!")
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
            messages.success(request, f"Composer '{composer.full_name}' updated successfully!")
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
# Song Views
# =============================================

def song_list(request):
    """
    List all songs with filtering and pagination.
    """
    # Get filter parameters from request
    search_query = request.GET.get('search', '')
    composer_filter = request.GET.get('composer', '')
    has_composer_filter = request.GET.get('has_composer', '')

    # Base queryset
    songs = Song.objects.all().order_by('title')

    # Apply filters
    if search_query:
        songs = songs.filter(
            Q(title__icontains=search_query) |
            Q(code__icontains=search_query)
        )

    if composer_filter:
        songs = songs.filter(composer_id=composer_filter)

    if has_composer_filter:
        if has_composer_filter == 'yes':
            songs = songs.filter(composer__isnull=False)
        elif has_composer_filter == 'no':
            songs = songs.filter(composer__isnull=True)

    # Annotate with PRS record count and earnings
    songs = songs.annotate(
        prs_count=Count('prs_records'),
        total_earnings=Sum('prs_records__royalty_payable')
    )

    # Get all composers for the filter dropdown
    composers = Composer.objects.all().order_by('full_name')

    # Calculate totals for summary cards
    composers_with_songs = Composer.objects.filter(songs__isnull=False).distinct().count()
    total_earnings = Prs_data.objects.aggregate(total=Sum('royalty_payable'))['total'] or 0
    songs_with_prs = Song.objects.filter(prs_records__isnull=False).distinct().count()

    # Pagination
    paginator = Paginator(songs, 20)  # Show 20 songs per page
    page = request.GET.get('page')
    try:
        songs_page = paginator.page(page)
    except PageNotAnInteger:
        songs_page = paginator.page(1)
    except EmptyPage:
        songs_page = paginator.page(paginator.num_pages)

    return render(request, 'artist_logs/song_list.html', {
        'songs': songs_page,
        'composers': composers,
        'composers_with_songs': composers_with_songs,
        'total_earnings': total_earnings,
        'songs_with_prs': songs_with_prs,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': songs_page,
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



def song_create(request):
    if request.method == 'POST':
        form = SongForm(request.POST)
        if form.is_valid():
            try:
                song = form.save()
                messages.success(request, f"Song '{song.title}' created successfully!")
                return redirect('artist_logs:song_detail', pk=song.pk)
            except IntegrityError as e:
                if 'unique_song_title_per_composer' in str(e):
                    form.add_error('title', f"A song with the title '{form.cleaned_data['title']}' already exists for this composer.")
                else:
                    messages.error(request, "An error occurred while saving the song.")
    else:
        form = SongForm()

    return render(request, 'artist_logs/song_form.html', {
        'form': form,
        'title': 'Add Song',
    })

def song_edit(request, pk):
    song = get_object_or_404(Song, pk=pk)
    if request.method == 'POST':
        form = SongForm(request.POST, instance=song)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Song '{song.title}' updated successfully!")
                return redirect('artist_logs:song_detail', pk=song.pk)
            except IntegrityError as e:
                if 'unique_song_title_per_composer' in str(e):
                    form.add_error('title', f"A song with the title '{form.cleaned_data['title']}' already exists for this composer.")
                else:
                    messages.error(request, "An error occurred while updating the song.")
    else:
        form = SongForm(instance=song)

    return render(request, 'artist_logs/song_form.html', {
        'form': form,
        'title': f'Edit {song.title}',
    })

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

def prs_admin(request):
    """
    View for uploading CSV files, tracking upload history, and displaying recent records.
    Handles composer deduplication and song-composer linking.
    """
    # --- Handle CSV upload ---
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a CSV file.")
            return redirect('artist_logs:prs_admin')

        try:
            # --- Check for duplicate uploads ---
            if isinstance(csv_file, InMemoryUploadedFile):
                csv_file.seek(0)
                file_content = csv_file.read()
                file_hash = hashlib.md5(file_content).hexdigest()
                csv_file.seek(0)  # Reset file pointer
            else:
                with open(csv_file.temporary_file_path(), 'rb') as f:
                    file_content = f.read()
                    file_hash = hashlib.md5(file_content).hexdigest()

            if UploadHistory.objects.filter(file_hash=file_hash).exists():
                messages.error(request, f"❌ This file ('{csv_file.name}') has already been uploaded and processed.")
                return redirect('artist_logs:prs_admin')

            # --- Process the CSV file ---
            csv_data = csv_file.read().decode('utf-8-sig')
            csv_file.seek(0)

            csv_io = StringIO(csv_data)
            reader = csv.DictReader(csv_io)
            fieldnames = reader.fieldnames

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
                messages.error(request, f"CSV file is missing required fields: {', '.join(missing)}")
                return redirect('artist_logs:prs_admin')

            # Rewind the StringIO object for processing
            csv_io.seek(0)
            reader = csv.DictReader(csv_io)

            imported_count = 0
            skipped_count = 0
            duplicate_count = 0
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

                        # --- Handle Composer ---
                        composer_name = None

                        # Try to get composer from 'Composers' field first
                        if 'Composers' in mapped_row and mapped_row['Composers'].strip():
                            names = [name.strip() for name in mapped_row['Composers'].replace(';', ',').replace('/', ',').split(',') if name.strip()]
                            composer_name = names[0] if names else None

                        # Fall back to 'Artist' field if no composer found
                        if not composer_name and 'Artist' in mapped_row and mapped_row['Artist'].strip():
                            names = [name.strip() for name in mapped_row['Artist'].replace(';', ',').replace('/', ',').split(',') if name.strip()]
                            composer_name = names[0] if names else None

                        # Create or get the composer
                        composer = None
                        if composer_name:
                            composer = Composer.find_or_create_by_name(composer_name)

                        # --- Handle Song ---
                        song_code = mapped_row.get('song_code', '').strip() or None
                        song_title = mapped_row.get('song_title', '').strip()
                        catalogue_no = mapped_row.get('catalogue_no', '').strip()
                        isrc = mapped_row.get('isrc', '').strip()
                        album = mapped_row.get('album_or_production', '').strip()
                        episode = mapped_row.get('episode', '').strip()
                        license_number = mapped_row.get('license_number', '').strip()

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
                                'composer': composer,
                            }
                        )

                        # If the song already existed, ONLY set composer if it's currently None
                        if not created:
                            if not song.composer and composer:
                                song.composer = composer
                                song.save()  # Only save if we updated the composer

                        # --- Create or update Prs_data ---
                        prs_data, created = Prs_data.objects.get_or_create(
                            song=song,
                            income_period=mapped_row.get('income_period', ''),
                            source=source,
                            income_type=income_type,
                            defaults={
                                'song_title': song_title,
                                'song_code': song_code,
                                'source_code': source_code,
                                'source_name': source_name,
                                'domestic_or_foreign': domestic_or_foreign,
                                'foreign_source': foreign_source,
                                'royalty_country_code': country_code,
                                'royalty_country_description': country_name,
                                'income_type_code': income_type_code,
                                'income_type_name': income_type_name,
                                'main_income_type_name': main_income_type,
                                'units': int(mapped_row.get('units', 0)) if mapped_row.get('units') else 0,
                                'percentage_collected': float(mapped_row.get('percentage_collected', 0)) if mapped_row.get('percentage_collected') else 0.00,
                                'amount_collected': float(mapped_row.get('amount_collected', 0)) if mapped_row.get('amount_collected') else 0.00,
                                'royalty_payout_percentage': float(mapped_row.get('royalty_payout_percentage', 0)) if mapped_row.get('royalty_payout_percentage') else 0.00,
                                'royalty_payable': float(mapped_row.get('royalty_payable', 0)) if mapped_row.get('royalty_payable') else 0.00,
                                'statement_id_year': mapped_row.get('statement_id_year', ''),
                                'statement_id_number': mapped_row.get('statement_id_number', ''),
                                'catalogue_no': catalogue_no,
                                'composers': mapped_row.get('composers', ''),
                                'artist': mapped_row.get('artist', ''),  # Keep as text for backward compatibility
                                'isrc': isrc,
                                'album_or_production': album,
                                'episode': episode,
                                'license_number': license_number,
                                'original_source_as_received': original_source,
                                'original_source': mapped_row.get('original_source', ''),
                                'is_paid': False,
                            }
                        )

                        if not created:
                            # Update existing record
                            prs_data.song_title = song_title
                            prs_data.song_code = song_code
                            prs_data.royalty_payable = float(mapped_row.get('royalty_payable', 0)) if mapped_row.get('royalty_payable') else 0.00
                            prs_data.composers = mapped_row.get('composers', prs_data.composers)
                            prs_data.units = int(mapped_row.get('units', 0)) if mapped_row.get('units') else prs_data.units
                            prs_data.percentage_collected = float(mapped_row.get('percentage_collected', 0)) if mapped_row.get('percentage_collected') else prs_data.percentage_collected
                            prs_data.amount_collected = float(mapped_row.get('amount_collected', 0)) if mapped_row.get('amount_collected') else prs_data.amount_collected
                            prs_data.royalty_payout_percentage = float(mapped_row.get('royalty_payout_percentage', 0)) if mapped_row.get('royalty_payout_percentage') else prs_data.royalty_payout_percentage
                            prs_data.save()
                            duplicate_count += 1
                        else:
                            imported_count += 1

                    except Exception as e:
                        errors.append(f"Error importing row {reader.line_num}: {str(e)}")
                        continue

                # --- Log the upload in UploadHistory ---
                UploadHistory.objects.create(
                    file_name=csv_file.name,
                    file_hash=file_hash,
                    records_imported=imported_count,
                    status="Success"
                )

            # --- Show results to user ---
            if imported_count > 0:
                messages.success(request, f"✅ Successfully imported {imported_count} new records.")
            if duplicate_count > 0:
                messages.info(request, f"🔄 Updated {duplicate_count} existing records.")
            if skipped_count > 0:
                messages.warning(request, f"⏭️ Skipped {skipped_count} empty rows.")
            if errors:
                for error in errors[:10]:  # Show first 10 errors
                    messages.error(request, error)
                if len(errors) > 10:
                    messages.error(request, f"... and {len(errors) - 10} more errors.")

        except Exception as e:
            # Log failed upload
            UploadHistory.objects.create(
                file_name=csv_file.name,
                file_hash=file_hash if 'file_hash' in locals() else "",
                records_imported=0,
                status="Failed",
                error_message=str(e)
            )
            messages.error(request, f"❌ An error occurred while processing the CSV file: {str(e)}")
            return redirect('artist_logs:prs_admin')

        return redirect('artist_logs:prs_admin')

    # --- Display page (GET request) ---
    # Fetch upload history
    upload_history = UploadHistory.objects.all().order_by('-uploaded_at')[:20]

    # Fetch recently imported records (last 100)
    recent_records = Prs_data.objects.all().order_by('-created_at')[:100]

    # Get counts for the template
    prs_count = Prs_data.objects.count()
    artist_count = Artist.objects.count()
    source_count = Source.objects.count()
    song_count = Song.objects.count()
    income_type_count = IncomeType.objects.count()
    composer_count = Composer.objects.count()
    payment_statement_count = PaymentStatement.objects.count()
    payment_plan_count = PaymentPlan.objects.count()

    # Get recent payment statements
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

def payment_statement_list(request):
    """
    View to list all payment statements.
    """
    payment_statements = PaymentStatement.objects.all().order_by('-statement_date')
    return render(request, 'artist_logs/payment_statement_list.html', {
        'payment_statements': payment_statements,
    })

def payment_statement_detail(request, statement_id):
    """
    View to show details of a specific payment statement and its associated PRS records.
    """
    statement = get_object_or_404(PaymentStatement, id=statement_id)
    prs_records = Prs_data.objects.filter(payment_statement=statement).order_by('-income_period')

    # Calculate total royalty payable for this statement
    total_royalty = prs_records.aggregate(total=Sum('royalty_payable'))['total'] or 0

    return render(request, 'artist_logs/payment_statement_detail.html', {
        'statement': statement,
        'prs_records': prs_records,
        'total_royalty': total_royalty,
    })

def create_payment_statement(request):
    """
    View to create a new PaymentStatement.
    """
    if request.method == 'POST':
        statement_number = request.POST.get('statement_number')
        statement_date = request.POST.get('statement_date')
        start_period = request.POST.get('start_period')
        end_period = request.POST.get('end_period')
        total_amount = request.POST.get('total_amount')
        status = request.POST.get('status')
        notes = request.POST.get('notes')

        # Validate required fields
        if not all([statement_number, statement_date, start_period, end_period, total_amount]):
            messages.error(request, "All fields except 'Notes' are required.")
            return redirect('artist_logs:payment_statement_list')

        try:
            PaymentStatement.objects.create(
                statement_number=statement_number,
                statement_date=statement_date,
                start_period=start_period,
                end_period=end_period,
                total_amount=total_amount,
                status=status,
                notes=notes
            )
            messages.success(request, "Payment statement created successfully!")
        except Exception as e:
            messages.error(request, f"Failed to create payment statement: {str(e)}")

        return redirect('artist_logs:payment_statement_list')

    return render(request, 'artist_logs/payment_statement_form.html')

def mark_as_paid(request, record_id):
    """
    View to mark a Prs_data record as paid.
    """
    record = get_object_or_404(Prs_data, id=record_id)
    statement_id = request.POST.get('payment_statement_id')

    if not statement_id:
        messages.error(request, "No payment statement selected.")
        return redirect('artist_logs:prs_admin')

    payment_statement = get_object_or_404(PaymentStatement, id=statement_id)

    record.mark_as_paid(
        payment_statement=payment_statement,
        payment_date=timezone.now().date(),
        payment_amount=record.royalty_payable,
        notes=f"Marked as paid via statement {payment_statement.statement_number}"
    )
    messages.success(request, f"Record {record.id} marked as paid under {payment_statement.statement_number}!")
    return redirect('artist_logs:payment_statement_detail', statement_id=statement_id)

def mark_as_unpaid(request, record_id):
    """
    View to mark a Prs_data record as unpaid.
    """
    record = get_object_or_404(Prs_data, id=record_id)
    record.mark_as_unpaid()
    messages.success(request, f"Record {record.id} marked as unpaid!")
    return redirect('artist_logs:prs_admin')


def prs_data_detail(request, pk):
    """
    Show details for a single PRS data record.
    """
    record = get_object_or_404(Prs_data, pk=pk)
    return render(request, 'artist_logs/prs_data_detail.html', {
        'record': record,
    })

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
        'title': 'Create Payment Statement',
    })



def mark_prs_data_as_paid(request, pk):
    """
    Mark a PRS data record as paid.
    """
    prs_data = get_object_or_404(Prs_data, pk=pk)

    if request.method == 'POST':
        prs_data.mark_as_paid(
            payment_statement=None,  # You can set this if needed
            payment_date=timezone.now().date(),
            payment_amount=prs_data.royalty_payable,
            notes=f"Marked as paid manually via admin interface"
        )
        messages.success(request, f"PRS record for '{prs_data.song_title}' marked as paid!")
    else:
        messages.warning(request, "Invalid request method for marking as paid.")

    return redirect(request.META.get('HTTP_REFERER', 'artist_logs:data_table'))

def mark_prs_data_as_unpaid(request, pk):
    """
    Mark a PRS data record as unpaid.
    """
    prs_data = get_object_or_404(Prs_data, pk=pk)

    if request.method == 'POST':
        prs_data.mark_as_unpaid()
        messages.success(request, f"PRS record for '{prs_data.song_title}' marked as unpaid!")
    else:
        messages.warning(request, "Invalid request method for marking as unpaid.")

    return redirect(request.META.get('HTTP_REFERER', 'artist_logs:data_table'))
