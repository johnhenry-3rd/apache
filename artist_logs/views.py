from django.shortcuts import render
from .models import Prs_data
from django_tables2 import Table
import pandas as pd
import plotly.express as px

# --- Table View ---
class YourModelTable(Table):
    class Meta:
        model = Prs_data
        fields = ('composers', 'Song_Title','Income_Type_Name','Royalty_Payable',)

def data_table(request):
    table = YourModelTable(Prs_data.objects.all())
    return render(request, 'artist_logs/data_table.html', {'table': table})

# --- Chart View ---
def charts(request):
    # Fetch data from your model
    data = Prs_data.objects.all().values()
    df = pd.DataFrame(data)

    # Example: Bar chart (customize based on your data)
    fig = px.bar(df, x='Composers', y='Royalty_Payable', color='Song_Title')  # Replace with your fields
    chart = fig.to_html()

    return render(request, 'artist_logs/charts.html', {'chart': chart})

# --- Dashboard View ---
def dashboard(request):
    return render(request, 'artist_logs/dashboard.html')