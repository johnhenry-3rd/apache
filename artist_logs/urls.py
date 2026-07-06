# artist_logs/urls.py
from django.urls import path
from . import views

app_name = 'artist_logs'

urlpatterns = [
    path('', views.front_page, name='front_page'),
    path('table/', views.data_table, name='data_table'),
    path('charts/', views.charts, name='charts'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('prs-admin/', views.prs_admin, name='prs_admin')
]