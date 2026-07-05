from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, TemplateView, View
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json
from .models import Prs_data, ImportedFile



# Utility function for splitting composers
def split_composers(composer_string):
    """Split a comma-separated composer string into a list of individual composers"""
    if not composer_string:
        return []
    return [c.strip() for c in composer_string.split(',') if c.strip()]

class PrsDataListView(ListView):
    """View for listing all PRS data records"""
    model = Prs_data
    template_name = 'artist_logs/prs_data_list.html'
    context_object_name = 'records'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(Client_Code__icontains=search_query) |
                Q(Client_Name__icontains=search_query) |
                Q(Song_Code__icontains=search_query) |
                Q(Song_Title__icontains=search_query) |
                Q(Artist__icontains=search_query)
            )
        return queryset.order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_records'] = Prs_data.objects.count()
        context['total_amount'] = Prs_data.objects.aggregate(
            total=Sum('Amount_Collected')
        )['total'] or 0
        context['imported_files'] = ImportedFile.objects.all().order_by('-imported_at')[:5]
        context['search_query'] = self.request.GET.get('q', '')
        return context

class PrsDataDetailView(DetailView):
    """View for showing a single PRS data record"""
    model = Prs_data
    template_name = 'artist_logs/prs_data_detail.html'
    context_object_name = 'record'

class PaymentScheduleView(TemplateView):
    """View for displaying the payment schedule with composer filtering"""
    template_name = 'artist_logs/payment_schedule.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter parameters from URL
        payment_status = self.request.GET.get('status', 'all')
        composer_filter = self.request.GET.get('composer', None)

        # Get all PRS data
        prs_data = Prs_data.objects.all()

        # Apply filters
        if payment_status == 'paid':
            prs_data = prs_data.filter(is_paid=True)
        elif payment_status == 'unpaid':
            prs_data = prs_data.filter(is_paid=False)

        if composer_filter:
            # Filter by composer (case-insensitive)
            prs_data = prs_data.filter(Composers__icontains=composer_filter)

        # Process each record to split composers
        individual_payments = []
        composer_totals = {}
        all_composers = set()

        for record in prs_data:
            composers = split_composers(record.Composers)
            if not composers:
                composers = ["Unknown"]

            # Split royalty equally among composers
            try:
                royalty_per_composer = float(record.Royalty_Payable) / len(composers) if len(composers) > 0 else 0
            except (TypeError, ValueError):
                royalty_per_composer = 0

            for composer in composers:
                all_composers.add(composer)

                # If filtering by composer, only include matching composers
                if composer_filter and composer.lower() != composer_filter.lower():
                    continue

                individual_payments.append({
                    'id': record.id,
                    'Composer': composer,
                    'Song_Code': record.Song_Code,
                    'Song_Title': record.Song_Title,
                    'Source_Name': record.Source_Name,
                    'Main_Income_Type_Name': record.Main_Income_Type_Name,
                    'Royalty_Payable': royalty_per_composer,
                    'Income_Period': record.Income_Period,
                    'is_paid': record.is_paid,
                })

                # Update composer totals
                if composer not in composer_totals:
                    composer_totals[composer] = {
                        'Composer': composer,
                        'total_royalty': 0,
                        'paid_royalty': 0,
                        'unpaid_royalty': 0,
                        'song_count': set(),
                        'payment_count': 0,
                        'paid_count': 0,
                        'unpaid_count': 0
                    }

                composer_totals[composer]['total_royalty'] += royalty_per_composer
                composer_totals[composer]['song_count'].add(record.Song_Code)
                composer_totals[composer]['payment_count'] += 1

                if record.is_paid:
                    composer_totals[composer]['paid_royalty'] += royalty_per_composer
                    composer_totals[composer]['paid_count'] += 1
                else:
                    composer_totals[composer]['unpaid_royalty'] += royalty_per_composer
                    composer_totals[composer]['unpaid_count'] += 1

        # Convert composer_totals dict to a list and calculate percentages
        composer_totals_list = []
        grand_total = sum(data['total_royalty'] for data in composer_totals.values())
        grand_total_paid = sum(data['paid_royalty'] for data in composer_totals.values())
        grand_total_unpaid = sum(data['unpaid_royalty'] for data in composer_totals.values())

        for composer, data in composer_totals.items():
            percentage = (data['total_royalty'] / grand_total * 100) if grand_total > 0 else 0
            composer_totals_list.append({
                'Composer': composer,
                'total_royalty': data['total_royalty'],
                'paid_royalty': data['paid_royalty'],
                'unpaid_royalty': data['unpaid_royalty'],
                'song_count': len(data['song_count']),
                'payment_count': data['payment_count'],
                'paid_count': data['paid_count'],
                'unpaid_count': data['unpaid_count'],
                'percentage': percentage
            })

        # Sort composer_totals_list by total_royalty (descending)
        composer_totals_list.sort(key=lambda x: x['total_royalty'], reverse=True)

        # Sort individual_payments by Composer name (A-Z)
        individual_payments.sort(key=lambda x: x['Composer'].lower())

        # Add all composers to context for the filter dropdown
        context['all_composers'] = sorted(all_composers)
        context['individual_payments'] = individual_payments
        context['composer_totals'] = composer_totals_list
        context['grand_total'] = grand_total
        context['grand_total_paid'] = grand_total_paid
        context['grand_total_unpaid'] = grand_total_unpaid
        context['total_composers'] = len(composer_totals_list)
        context['total_songs'] = len(set(p['Song_Code'] for p in individual_payments))
        context['current_status'] = payment_status
        context['current_composer'] = composer_filter

        return context

@method_decorator(csrf_exempt, name='dispatch')
class MarkPaidView(View):
    """View to mark selected payments as paid using AJAX"""

    def post(self, request, *args, **kwargs):
        try:
            # Parse JSON data from the request body
            data = json.loads(request.body)

            # Extract payment IDs, composer filter, and status from the data
            payment_ids = data.get('payment_ids', [])
            composer = data.get('composer', '')
            status = data.get('status', 'all')

            if payment_ids:
                # Convert string IDs to integers
                payment_ids = [int(id) for id in payment_ids]

                # Update the selected records to mark them as paid
                count = Prs_data.objects.filter(id__in=payment_ids).update(is_paid=True)

                # Return success response with count of updated records
                return JsonResponse({'success': True, 'count': count})

            # Return error if no payment IDs were provided
            return JsonResponse({'success': False, 'error': 'No payment IDs provided'}, status=400)

        except json.JSONDecodeError:
            # Handle invalid JSON data
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
        except ValueError as e:
            # Handle invalid payment ID format
            return JsonResponse({'success': False, 'error': f'Invalid payment ID: {str(e)}'}, status=400)
        except Exception as e:
            # Handle any other unexpected errors
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
class HighValuePaymentScheduleView(TemplateView):
    template_name = 'artist_logs/high_value_payment_schedule.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Set the minimum payment threshold for composers
        MIN_COMPOSER_TOTAL = 100.00
        context['min_payment_amount'] = MIN_COMPOSER_TOTAL
        context['page_title'] = f'High Value Composers (≥£{MIN_COMPOSER_TOTAL})'

        # Get filter parameters from URL
        payment_status = self.request.GET.get('status', 'all')
        composer_filter = self.request.GET.get('composer', None)

        # Get all PRS data
        prs_data = Prs_data.objects.all()

        # Apply status filter
        if payment_status == 'paid':
            prs_data = prs_data.filter(is_paid=True)
        elif payment_status == 'unpaid':
            prs_data = prs_data.filter(is_paid=False)

        # Apply composer filter if provided
        if composer_filter:
            prs_data = prs_data.filter(Composers__icontains=composer_filter)

        # First pass: Calculate composer totals to identify high-value composers
        composer_totals_temp = {}
        all_composers = set()

        for record in prs_data:
            composers = split_composers(record.Composers)
            if not composers:
                composers = ["Unknown"]

            try:
                royalty_per_composer = float(record.Royalty_Payable) / len(composers) if len(composers) > 0 else 0
            except (TypeError, ValueError):
                royalty_per_composer = 0

            for composer in composers:
                all_composers.add(composer)
                if composer not in composer_totals_temp:
                    composer_totals_temp[composer] = 0
                composer_totals_temp[composer] += royalty_per_composer

        # Identify high-value composers (total ≥ £100)
        high_value_composers = set()
        for composer, total in composer_totals_temp.items():
            if total >= MIN_COMPOSER_TOTAL:
                high_value_composers.add(composer)

        # If composer filter is applied, only include that composer if they're high-value
        if composer_filter and composer_filter not in high_value_composers:
            high_value_composers = set()  # No composers to show

        # Initialize composer_totals with high-value composers only
        composer_totals = {}
        for composer in high_value_composers:
            composer_totals[composer] = {
                'Composer': composer,
                'total_royalty': 0,
                'paid_royalty': 0,
                'unpaid_royalty': 0,
                'song_count': set(),
                'payment_count': 0,
                'paid_count': 0,
                'unpaid_count': 0
            }

        # Second pass: Collect all individual payments for high-value composers
        individual_payments = []
        for record in prs_data:
            composers = split_composers(record.Composers)
            if not composers:
                composers = ["Unknown"]

            try:
                royalty_per_composer = float(record.Royalty_Payable) / len(composers) if len(composers) > 0 else 0
            except (TypeError, ValueError):
                royalty_per_composer = 0

            for composer in composers:
                # Only process payments for high-value composers
                if composer not in high_value_composers:
                    continue

                # Include ALL payments for high-value composers (even if < £100)
                individual_payments.append({
                    'id': record.id,
                    'Composer': composer,
                    'Song_Code': record.Song_Code,
                    'Song_Title': record.Song_Title,
                    'Source_Name': record.Source_Name,
                    'Main_Income_Type_Name': record.Main_Income_Type_Name,
                    'Royalty_Payable': royalty_per_composer,
                    'Income_Period': record.Income_Period,
                    'is_paid': record.is_paid,
                })

                # Update composer totals
                composer_totals[composer]['total_royalty'] += royalty_per_composer
                composer_totals[composer]['song_count'].add(record.Song_Code)
                composer_totals[composer]['payment_count'] += 1

                if record.is_paid:
                    composer_totals[composer]['paid_royalty'] += royalty_per_composer
                    composer_totals[composer]['paid_count'] += 1
                else:
                    composer_totals[composer]['unpaid_royalty'] += royalty_per_composer
                    composer_totals[composer]['unpaid_count'] += 1

        # Convert composer_totals dict to a list and calculate percentages
        composer_totals_list = []
        grand_total = sum(data['total_royalty'] for data in composer_totals.values())
        grand_total_paid = sum(data['paid_royalty'] for data in composer_totals.values())
        grand_total_unpaid = sum(data['unpaid_royalty'] for data in composer_totals.values())

        for composer, data in composer_totals.items():
            percentage = (data['total_royalty'] / grand_total * 100) if grand_total > 0 else 0
            composer_totals_list.append({
                'Composer': composer,
                'total_royalty': data['total_royalty'],
                'paid_royalty': data['paid_royalty'],
                'unpaid_royalty': data['unpaid_royalty'],
                'song_count': len(data['song_count']),
                'payment_count': data['payment_count'],
                'paid_count': data['paid_count'],
                'unpaid_count': data['unpaid_count'],
                'percentage': percentage
            })

        # Sort composer_totals_list by total_royalty (descending)
        composer_totals_list.sort(key=lambda x: x['total_royalty'], reverse=True)

        # Sort individual_payments by Composer (A-Z), then by Song_Code
        individual_payments.sort(key=lambda x: (x['Composer'].lower(), x['Song_Code'].lower()))

        context['all_composers'] = sorted(high_value_composers)  # Only high-value composers
        context['individual_payments'] = individual_payments
        context['composer_totals'] = composer_totals_list
        context['grand_total'] = grand_total
        context['grand_total_paid'] = grand_total_paid
        context['grand_total_unpaid'] = grand_total_unpaid
        context['total_composers'] = len(composer_totals_list)
        context['total_songs'] = len(set(p['Song_Code'] for p in individual_payments))
        context['current_status'] = payment_status
        context['current_composer'] = composer_filter

        return context

def index(request):
    """View for the home page"""
    return render(request, 'artist_logs/index.html')

def artists(request):
    """View for the artists page"""
    return render(request, 'artist_logs/artists.html')

def tracks(request):
    """View for the tracks page"""
    return render(request, 'artist_logs/tracks.html')