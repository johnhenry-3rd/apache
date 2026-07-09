from django.urls import path
from . import views

app_name = 'artist_logs'

urlpatterns = [
    # Front page
    path('', views.front_page, name='front_page'),

    # Composer URLs
    path('composers/', views.composer_list, name='composer_list'),
    path('composers/create/', views.composer_create, name='composer_create'),
    path('composers/<int:pk>/', views.composer_detail, name='composer_detail'),
    path('composers/<int:pk>/edit/', views.composer_edit, name='composer_edit'),
    path('composers/<int:pk>/payments/', views.composer_payment_history, name='composer_payment_history'),
    # artist_logs/urls.py

    #Payment URL's
    # Add this to your existing urlpatterns list
    path('payment-statements/create/', views.create_payment_statement, name='create_payment_statement'),

    # Song URLs
    path('songs/', views.song_list, name='song_list'),
    path('songs/create/', views.song_create, name='song_create'),
    path('songs/<int:pk>/', views.song_detail, name='song_detail'),
    path('songs/<int:pk>/edit/', views.song_edit, name='song_edit'),
    path('prs-data/<int:pk>/', views.prs_data_detail, name='prs_record_detail'),

    # Existing URLs
    path('data-table/', views.data_table, name='data_table'),
    path('prs-admin/', views.prs_admin, name='prs_admin'),
    path('payment-statements/', views.payment_statement_list, name='payment_statement_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('prs-data/<int:pk>/mark-as-paid/', views.mark_prs_data_as_paid, name='mark_as_paid'),
    path('prs-data/<int:pk>/mark-as-unpaid/', views.mark_prs_data_as_unpaid, name='mark_as_unpaid')
]