# artist_logs/views.py
from .models import Prs_data
from django.db.models import Q, Min
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

# Import all models
from .models import (
    Prs_data,
    Artist,
    Client,
    Payee,
    Track,
    ImportedFile,
    ImportLog
)

def data_table(request):
    # Get filter parameters - use empty string as default instead of None
    composer_filter = request.GET.get('composer', '')
    song_title_filter = request.GET.get('song_title', '')
    sort_by = request.GET.get('sort', 'Song_Title')

    # Start with all data
    data = Prs_data.objects.all()

    # Apply filters - only if the filter value is not empty
    if composer_filter:
        data = data.filter(composers__name__icontains=composer_filter)
    if song_title_filter:
        data = data.filter(Song_Title__icontains=song_title_filter)

    # Apply sorting
    if sort_by == 'composers':
        data = data.annotate(
            first_composer=Min('composers__name')
        ).order_by(Lower('first_composer'))
    elif sort_by == '-composers':
        data = data.annotate(
            first_composer=Min('composers__name')
        ).order_by(Lower('-first_composer'))
    elif sort_by in ['Song_Title', '-Song_Title', 'Royalty_Payable', '-Royalty_Payable']:
        data = data.order_by(sort_by)
    else:
        data = data.order_by('Song_Title')

    # Distinct results
    data = data.distinct()

    return render(request, 'artist_logs/data_table.html', {
        'table_data': data,
        'composer_filter': composer_filter,
        'song_title_filter': song_title_filter,
        'sort_by': sort_by,
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
        data = data.filter(Song_Title__icontains=song_title_filter)

    # Distinct results (important for ManyToMany filtering)
    data = data.distinct()

    # Prepare data for Plotly - Group by Composer
    df_data = []
    for item in data:
        # Handle cases where there are no composers
        if item.composers.exists():
            for composer in item.composers.all():
                df_data.append({
                    'Composer': composer.name,
                    'Royalty_Payable': float(item.Royalty_Payable) if item.Royalty_Payable is not None else 0.0,
                    'Song_Title': item.Song_Title if item.Song_Title else "Unknown",
                    'Count': 1  # For counting songs per composer
                })
        else:
            # If no composers, use "Unknown" as composer name
            df_data.append({
                'Composer': "Unknown",
                'Royalty_Payable': float(item.Royalty_Payable) if item.Royalty_Payable is not None else 0.0,
                'Song_Title': item.Song_Title if item.Song_Title else "Unknown",
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
        color_continuous_scale=['#1a1a1a', '#c5a47e', '#f8f8f8'],  # Apache Music colors
        text='Count'
    )

    # Improve layout with Apache Music theme
    fig.update_layout(
        # Title styling
        title={
            'text': 'Total Royalty Payable by Composer',
            'font': {'size': 24, 'color': '#f8f8f8', 'family': 'Montserrat'},
            'x': 0.5,
            'xanchor': 'center'
        },

        # Axis styling
        xaxis_title='Composer',
        yaxis_title='Total Royalty Payable (£)',
        height=600,

        # Plot styling
        showlegend=False,
        hovermode='x unified',
        plot_bgcolor='rgba(26, 26, 26, 0.8)',
        paper_bgcolor='rgba(26, 26, 26, 0)',
        font=dict(size=12, color='#f8f8f8', family='Montserrat'),

        # Margins
        margin=dict(l=50, r=50, t=80, b=150),

        # Y-axis formatting
        yaxis=dict(
            tickformat="£,.2f",
            gridcolor='rgba(255, 255, 255, 0.1)',
            zerolinecolor='rgba(255, 255, 255, 0.1)',
            title=dict(
                text='Total Royalty Payable (£)',
                font=dict(size=14, color='#f8f8f8', family='Montserrat')
            )
        ),

        # X-axis formatting
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
    # Basic counts
    prs_count = Prs_data.objects.count()
    artist_count = Artist.objects.count()
    client_count = Client.objects.count()
    payee_count = Payee.objects.count()

    # Total royalty
    total_royalty = Prs_data.objects.aggregate(total=Sum('Royalty_Payable'))['total'] or 0

    # Recent records
    recent_records = Prs_data.objects.all().order_by('-created_at')[:10]

    # Data for Royalty by Artist chart
    artist_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.Artist:
            artist_royalties[record.Artist] += float(record.Royalty_Payable or 0)

    artist_names = list(artist_royalties.keys())
    artist_royalty_values = list(artist_royalties.values())

    # Data for Royalty by Client chart
    client_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.Client_Name:
            client_royalties[record.Client_Name] += float(record.Royalty_Payable or 0)

    client_names = list(client_royalties.keys())
    client_royalty_values = list(client_royalties.values())

    # Data for Royalty Over Time chart
    period_royalties = defaultdict(float)
    for record in Prs_data.objects.all():
        if record.Income_Period:
            period_royalties[record.Income_Period] += float(record.Royalty_Payable or 0)

    income_periods = sorted(period_royalties.keys())
    period_royalty_values = [period_royalties[period] for period in income_periods]

    return render(request, 'artist_logs/dashboard.html', {
        'prs_count': prs_count,
        'artist_count': artist_count,
        'client_count': client_count,
        'payee_count': payee_count,
        'total_royalty': total_royalty,
        'recent_records': recent_records,
        'artist_names': json.dumps(artist_names),
        'artist_royalties': json.dumps(artist_royalty_values),
        'client_names': json.dumps(client_names),
        'client_royalties': json.dumps(client_royalty_values),
        'income_periods': json.dumps(income_periods),
        'period_royalties': json.dumps(period_royalty_values),
    })

def front_page(request):
    """Render the front page with Apache Music banner and navigation links."""
    return render(request, 'artist_logs/front_page.html')

def prs_admin(request):
    """View for uploading and managing PRS data."""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a CSV file.")
            return redirect('artist_logs:prs_admin')

        try:
            csv_data = TextIOWrapper(csv_file.file, encoding='utf-8-sig')
            reader = csv.DictReader(csv_data)
            fieldnames = reader.fieldnames

            required_fields = ['Song_Title', 'Royalty_Payable']
            if not all(field in fieldnames for field in required_fields):
                messages.error(request, f"CSV file is missing required fields: {', '.join(required_fields)}")
                return redirect('artist_logs:prs_admin')

            csv_file.seek(0)
            csv_data = TextIOWrapper(csv_file.file, encoding='utf-8-sig')
            reader = csv.DictReader(csv_data)

            imported_count = 0
            with transaction.atomic():
                for row in reader:
                    # Get or create Client
                    client_code = row.get('Client_Code', '').strip()
                    client_name = row.get('Client_Name', '').strip()
                    if client_code or client_name:
                        client, _ = Client.objects.get_or_create(
                            code=client_code if client_code else "UNKNOWN",
                            defaults={'name': client_name if client_name else "Unknown Client"}
                        )
                    else:
                        client = None

                    # Get or create Payee
                    payee_code = row.get('Payee_Code', '').strip()
                    payee_name = row.get('Payee_Name', '').strip()
                    if payee_code or payee_name:
                        payee, _ = Payee.objects.get_or_create(
                            code=payee_code if payee_code else "UNKNOWN",
                            defaults={'name': payee_name if payee_name else "Unknown Payee"}
                        )
                    else:
                        payee = None

                    # Create or update PRS Data
                    prs_data, created = Prs_data.objects.get_or_create(
                        Song_Title=row.get('Song_Title', '').strip(),
                        defaults={
                            'Client_Code': client_code,
                            'Client_Name': client_name,
                            'Payee_Code': payee_code,
                            'Payee_Name': payee_name,
                            'Royalty_Payable': float(row.get('Royalty_Payable', 0)) if row.get('Royalty_Payable') else 0.0,
                            'Composers': row.get('Composers', ''),
                            'client': client,
                            'payee': payee,
                        }
                    )

                    if not created:
                        prs_data.Royalty_Payable = float(row.get('Royalty_Payable', 0)) if row.get('Royalty_Payable') else 0.0
                        prs_data.Composers = row.get('Composers', prs_data.Composers)
                        prs_data.Client_Code = client_code
                        prs_data.Client_Name = client_name
                        prs_data.Payee_Code = payee_code
                        prs_data.Payee_Name = payee_name
                        prs_data.client = client
                        prs_data.payee = payee

                    # Handle Artists
                    if 'Artist' in fieldnames and row.get('Artist'):
                        artist_name = row['Artist'].strip()
                        if artist_name:
                            artist, _ = Artist.objects.get_or_create(
                                name=artist_name,
                                defaults={
                                    'first_name': artist_name.split()[-1] if artist_name.split() else "Unknown",
                                    'last_name': artist_name.split()[0] if len(artist_name.split()) > 1 else "Unknown"
                                }
                            )
                            prs_data.composers.add(artist)

                    # Update other fields
                    for field in fieldnames:
                        if hasattr(prs_data, field) and field not in [
                            'Song_Title', 'Royalty_Payable', 'Composers', 'Artist',
                            'Client_Code', 'Client_Name', 'Payee_Code', 'Payee_Name'
                        ]:
                            value = row.get(field, '')
                            if value:
                                setattr(prs_data, field, value)

                    prs_data.save()
                    imported_count += 1

            messages.success(request, f"Successfully imported {imported_count} records from the CSV file.")
            return redirect('artist_logs:prs_admin')

        except Exception as e:
            messages.error(request, f"An error occurred while importing the CSV file: {str(e)}")
            return redirect('artist_logs:prs_admin')

    # Get counts for the template
    prs_count = Prs_data.objects.count()
    artist_count = Artist.objects.count()
    client_count = Client.objects.count()
    payee_count = Payee.objects.count()

    # Get recent imports for display
    recent_imports = Prs_data.objects.all().order_by('-created_at')[:10]

    return render(request, 'artist_logs/prs_admin.html', {
        'prs_count': prs_count,
        'artist_count': artist_count,
        'client_count': client_count,
        'payee_count': payee_count,
        'recent_imports': recent_imports,
    })

