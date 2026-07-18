from django.urls import path
from artist_logs import views
from .progress_tracker import sse_upload_progress 
from .views import generate_remittance_advice
from .views import prs_data_list, prs_data_detail 
from .views import mark_composer_unpaid_as_paid

app_name = 'artist_logs'

urlpatterns = [
    # ======================
    # FRONT PAGE
    # ======================
    path('', views.front_page, name='front_page'),

    # ======================
    # COMPOSER URLs
    # ======================
    path('composers/', views.composer_list, name='composer_list'),
    path('composers/create/', views.composer_create, name='composer_create'),
    path('composers/<int:pk>/', views.composer_detail, name='composer_detail'),
    path('composers/<int:pk>/edit/', views.composer_edit, name='composer_edit'),
    path('composers/<int:pk>/payments/', views.composer_payment_history, name='composer_payment_history'),
    path('composers/<int:pk>/songs/', views.composer_songs, name='composer_songs'),
    path('composers/<int:pk>/mark-unpaid-as-paid/', mark_composer_unpaid_as_paid, name='mark_composer_unpaid_as_paid'),

    # ======================
    # SONG URLs
    # ======================
    path('songs/', views.song_list, name='song_list'),
    path('songs/create/', views.song_create, name='song_create'),
    path('songs/<int:pk>/', views.song_detail, name='song_detail'),
    path('songs/<int:pk>/edit/', views.song_edit, name='song_edit'),
    path('songs/<int:song_id>/add-composer/', views.add_composer_to_song, name='add_composer_to_song'),
    path('songs/<int:song_id>/remove-composer/<int:composer_id>/', views.remove_composer_from_song, name='remove_composer_from_song'),
    path('songs/<int:song_id>/composer-splits/', views.song_composer_splits, name='song_composer_splits'),

    # ======================
    # PRS DATA URLs
    # ======================
    path('prs-data/<int:pk>/', views.prs_data_detail, name='prs_record_detail'),
    path('prs-admin/', views.prs_admin, name='prs_admin'),
    path('data-table/', views.data_table, name='data_table'),
    path('prs-data/', prs_data_list, name='prs_data_list'),
    path('prs-data/<int:pk>/', prs_data_detail, name='prs_data_detail'),

    # ======================
    # PAYMENT URLs
    # ======================
    path('payment-statements/', views.payment_statement_list, name='payment_statement_list'),
    path('payment-statements/create/', views.create_payment_statement, name='create_payment_statement'),
    path('payment-statements/<int:pk>/', views.payment_statement_detail, name='payment_statement_detail'),

    # ======================
    # DASHBOARD
    # ======================
    path('dashboard/', views.dashboard, name='dashboard'),

    # ======================
    # PRS DATA ACTIONS
    # ======================
    path('prs-data/<int:pk>/mark-as-paid/', views.mark_prs_data_as_paid, name='mark_as_paid'),
    path('prs-data/<int:pk>/mark-as-unpaid/', views.mark_prs_data_as_unpaid, name='mark_as_unpaid'),

    # ======================
    # DATA MANAGEMENT
    # ======================
    path('clear-prs-data/', views.clear_prs_data, name='clear_prs_data'),

    # ======================
    # BACKUP/RESTORE URLs
    # ======================
    path('backup-database/', views.backup_database, name='backup_database'),
    path('restore-database/', views.restore_database, name='restore_database'),
    path('backup-list/', views.backup_list, name='backup_list'),
    path('verify-backup/<str:filename>/', views.verify_backup, name='verify_backup'),
    path('download-backup/<str:filename>/', views.download_backup, name='download_backup'),
    path('delete-backup/<str:filename>/', views.delete_backup, name='delete_backup'),
    path('upload-prs-csv/', views.upload_prs_csv, name='upload_prs_csv'),
    path('prs-admin/', views.prs_admin, name='prs_admin'),
    path('test-backups/', views.test_backup_list, name='test_backup_list'),
    path('sse-upload-progress/', views.sse_upload_progress, name='sse_upload_progress'),
    path('backup/', views.backup_database, name='backup_database'),
    path('backups/', views.backup_list, name='backup_list'),
    path('restore/', views.restore_database, name='restore_database'),
    path('restore/confirm/<str:backup_filename>/', views.confirm_restore, name='confirm_restore'),
    path('backups/verify/<str:backup_filename>/', views.verify_backup, name='verify_backup'),
    path('backups/restore/confirm/<str:backup_filename>/', views.confirm_restore, name='confirm_restore'),
    path('backups/restore/', views.restore_database, name='restore_database'),
    path('backups/download/<str:backup_filename>/', views.download_backup, name='download_backup'),
    path('backups/delete/<str:backup_filename>/', views.delete_backup, name='delete_backup'),



    # ======================
    # QUICK ACTIONS
    # ======================
    path('quick-add-composer/', views.quick_add_composer, name='quick_add_composer'),
    path('sse-upload-progress/', sse_upload_progress, name='sse_upload_progress'),
    #path('__debug__/', include('debug_toolbar.urls')),

    # ======================
    # Remittance
    # ======================

    path(
        'generate-remittance-advice/',
        generate_remittance_advice,
        name='generate_remittance_advice'
    ),
]

