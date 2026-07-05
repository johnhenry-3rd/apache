from django.urls import path
from . import views
from .views import PrsDataListView, PrsDataDetailView
from .views import PaymentScheduleView
from .views import PaymentScheduleView, MarkPaidView  # Add MarkPaidView import
from .views import HighValuePaymentScheduleView

app_name = 'artist_logs'

urlpatterns = [
    # PRS Data URLs (these should come first to avoid conflicts)
    path('prs/', PrsDataListView.as_view(), name='prs_data_list'),
    path('prs/<int:pk>/', PrsDataDetailView.as_view(), name='prs_data_detail'),
    path('payments/mark-paid/', MarkPaidView.as_view(), name='mark_paid'),
    path('payments/', PaymentScheduleView.as_view(), name='payment_schedule'),
    path('payments/high-value/', HighValuePaymentScheduleView.as_view(), name='high_value_payment_schedule'),
    path('payments/mark-paid/', MarkPaidView.as_view(), name='mark_paid'),

    # Other URLs (keep your existing views)
    path('', views.index, name='index'),
    path('artists/', views.artists, name='artists'),
    path('tracks/', views.tracks, name='tracks'),
    path('payments/', PaymentScheduleView.as_view(), name='payment_schedule'),
    path('payments/mark-paid/', MarkPaidView.as_view(), name='mark_paid'),
    path('payments/', PaymentScheduleView.as_view(), name='payment_schedule'),
    path('payments/high-value/', HighValuePaymentScheduleView.as_view(), name='high_value_payment_schedule'),
    path('payments/mark-paid/', MarkPaidView.as_view(), name='mark_paid'),
]
