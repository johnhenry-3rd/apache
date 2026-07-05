# artist_logs/views.py
from django.shortcuts import render
from .models import Prs_data  # Your model
import pandas as pd
import plotly.express as px

def data_table(request):
    # Get filter parameters from the URL
    composer_filter = request.GET.get('composer', None)
    song_title_filter = request.GET.get('song_title', None)

    # Get sorting parameter (e.g., ?sort=Composers or ?sort=-Composers)
    sort_by = request.GET.get('sort', 'Composers')  # Default: sort by Composers

    # Start with all data
    data = Prs_data.objects.all()

    # Apply filters
    if composer_filter:
        data = data.filter(Composers__icontains=composer_filter)
    if song_title_filter:
        data = data.filter(Song_Title__icontains=song_title_filter)

    # Apply sorting
    if sort_by in ['Composers', 'Song_Title', 'Royalty_Payable', '-Composers', '-Song_Title', '-Royalty_Payable']:
        data = data.order_by(sort_by)
    else:
        data = data.order_by('Composers')  # Default sorting

    return render(request, 'artist_logs/data_table.html', {
        'table_data': data,
        'composer_filter': composer_filter,
        'song_title_filter': song_title_filter,
        'sort_by': sort_by,
    })

def charts(request):
    # Get filter parameters
    composer_filter = request.GET.get('composer', None)
    song_title_filter = request.GET.get('song_title', None)

    # Apply filters
    data = Prs_data.objects.all()
    if composer_filter:
        data = data.filter(Composers__icontains=composer_filter)
    if song_title_filter:
        data = data.filter(Song_Title__icontains=song_title_filter)

    # Convert to DataFrame for Plotly
    df = pd.DataFrame(data.values())

    if df.empty:
        return render(request, 'artist_logs/charts.html', {'chart': '<p>No data matches the filters.</p>'})

    # Example: Bar chart (customize fields as needed)
    fig = px.bar(df, x='Song_Title', y='Royalty_Payable', color='Composers', title='Royalty Payable by Composer')
    chart = fig.to_html()

    return render(request, 'artist_logs/charts.html', {
        'chart': chart,
        'composer_filter': composer_filter,
        'song_title_filter': song_title_filter,
    })

def dashboard(request):
    # Apply the same filtering logic for the dashboard
    composer_filter = request.GET.get('composer', None)
    song_title_filter = request.GET.get('song_title', None)

    data = Prs_data.objects.all()
    if composer_filter:
        data = data.filter(Composers__icontains=composer_filter)
    if song_title_filter:
        data = data.filter(Song_Title__icontains=song_title_filter)

    return render(request, 'artist_logs/dashboard.html', {
        'data': data,
        'composer_filter': composer_filter,
        'song_title_filter': song_title_filter,
    })