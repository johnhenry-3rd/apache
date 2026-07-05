# artist_logs/urls.py
from django.urls import path
from . import views

app_name = 'artist_logs'

urlpatterns = [
    path('', views.dashboard, name='home'),  # Add this line for the root URL
    path('table/', views.data_table, name='data_table'),
    path('charts/', views.charts, name='charts'),
    path('dashboard/', views.dashboard, name='dashboard'),
]