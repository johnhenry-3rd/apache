# artist_logs/urls.py
from django.urls import path
from . import views

app_name = 'artist_logs'

urlpatterns = [
    path('', views.front_page, name='front_page'),
    path('table/', views.data_table, name='data_table'),
    path('charts/', views.charts, name='charts'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('prs-admin/', views.prs_admin, name='prs_admin'),
    path('create-payment-statement/', views.create_payment_statement, name='create_payment_statement'),
    path('mark-as-paid/<int:record_id>/', views.mark_as_paid, name='mark_as_paid'),
    path('mark-as-unpaid/<int:record_id>/', views.mark_as_unpaid, name='mark_as_unpaid'),
    path('prs-admin/', views.prs_admin, name='prs_admin'),
    path('payment-statements/', views.payment_statement_list, name='payment_statement_list'),
    path('payment-statements/create/', views.create_payment_statement, name='create_payment_statement'),
    path('payment-statements/<int:statement_id>/', views.payment_statement_detail, name='payment_statement_detail'),
    path('mark-as-paid/<int:record_id>/', views.mark_as_paid, name='mark_as_paid'),
    path('mark-as-unpaid/<int:record_id>/', views.mark_as_unpaid, name='mark_as_unpaid'),
]