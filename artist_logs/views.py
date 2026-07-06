# artist_logs/views.py
from django.shortcuts import render
from .models import Prs_data
from django.db.models import Q, Min
from django.db.models.functions import Lower
import pandas as pd
import plotly.express as px
from django.db.models import Sum, Count, Avg

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
    """Render the dashboard with top earning songs graph and statistics."""
    # Get all data
    all_data = Prs_data.objects.all()

    # Top 10 earning songs
    top_songs = all_data.order_by('-Royalty_Payable')[:10]

    # Calculate statistics
    total_songs = all_data.count()
    total_royalty = all_data.aggregate(Sum('Royalty_Payable'))['Royalty_Payable__sum'] or 0
    avg_royalty = all_data.aggregate(Avg('Royalty_Payable'))['Royalty_Payable__avg'] or 0

    # Top composer (by total royalty)
    top_composer_data = all_data.values('composers__name') \
        .annotate(total_royalty=Sum('Royalty_Payable')) \
        .order_by('-total_royalty') \
        .first()

    top_composer = top_composer_data['composers__name'] if top_composer_data else "N/A"
    top_composer_royalty = top_composer_data['total_royalty'] if top_composer_data else 0

    # Prepare data for top songs chart
    df_data = []
    for item in top_songs:
        composers = ", ".join([composer.name for composer in item.composers.all()]) if item.composers.exists() else "Unknown"
        df_data.append({
            'Song_Title': item.Song_Title if item.Song_Title else "Unknown",
            'Royalty_Payable': float(item.Royalty_Payable) if item.Royalty_Payable is not None else 0.0,
            'Composers': composers,
        })

    # Convert to DataFrame
    df = pd.DataFrame(df_data)

    if not df.empty:
        # Create the top earning songs chart
        fig = px.bar(
            df,
            x='Song_Title',
            y='Royalty_Payable',
            title='Top 10 Earning Songs',
            labels={
                'Royalty_Payable': 'Royalty Payable (£)',
                'Song_Title': 'Song Title',
            },
            hover_data={
                'Royalty_Payable': ':£.2f',
                'Composers': True
            },
            color='Royalty_Payable',
            color_continuous_scale=['#1a1a1a', '#c5a47e', '#f8f8f8'],
        )

        # Improve layout with Apache Music theme
        fig.update_layout(
            xaxis_title='Song Title',
            yaxis_title='Royalty Payable (£)',
            height=500,
            showlegend=False,
            hovermode='x unified',
            plot_bgcolor='rgba(26, 26, 26, 0.8)',
            paper_bgcolor='rgba(26, 26, 26, 0)',
            font=dict(size=12, color='#f8f8f8', family='Montserrat'),
            margin=dict(l=50, r=50, t=80, b=150),
            yaxis=dict(
                tickformat="£,.2f",
                gridcolor='rgba(255, 255, 255, 0.1)',
                zerolinecolor='rgba(255, 255, 255, 0.1)'
            ),
            xaxis=dict(
                tickangle=-45,
                gridcolor='rgba(255, 255, 255, 0.1)'
            ),
            title_font_color='#f8f8f8',
            title_font_size=20
        )

        # Add text to bars
        fig.update_traces(
            textposition='outside',
            texttemplate='£%{y:,.0f}',
            textfont=dict(size=10, color='#c5a47e'),
            hovertemplate='<b>%{x}</b><br>' +
                          'Royalty: £%{y:,.2f}<br>' +
                          'Composers: %{customdata[0]}<extra></extra>',
            customdata=df[['Composers']].values
        )

        top_songs_chart = fig.to_html(full_html=False)
    else:
        top_songs_chart = '<div class="alert alert-info text-center">No data available for top earning songs.</div>'

    return render(request, 'artist_logs/dashboard.html', {
        'top_songs_chart': top_songs_chart,
        'total_songs': total_songs,
        'total_royalty': total_royalty,
        'avg_royalty': avg_royalty,
        'top_composer': top_composer,
        'top_composer_royalty': top_composer_royalty,
    })

def front_page(request):
    """Render the front page with Apache Music banner and navigation links."""
    return render(request, 'artist_logs/front_page.html')