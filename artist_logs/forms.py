# artist_logs/forms.py
from django import forms
from .models import Composer, Song
from .models import PaymentStatement
from .models import Song, Composer

class ComposerForm(forms.ModelForm):
    class Meta:
        model = Composer
        fields = [
            'full_name', 'first_name', 'last_name', 'email', 'phone', 'address',
            'bank_name', 'bank_sort_code', 'bank_account_number',
            'vat_registered', 'vat_number', 'payment_threshold',
            'is_active', 'notes'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'email': forms.EmailInput(attrs={'class': 'form-control apache-form'}),
            'phone': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'address': forms.Textarea(attrs={'class': 'form-control apache-form', 'rows': 3}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'bank_sort_code': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'vat_number': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'payment_threshold': forms.NumberInput(attrs={'class': 'form-control apache-form', 'min': '0', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control apache-form', 'rows': 3}),
        }
        labels = {
            'payment_threshold': 'Payment Threshold (£)',
        }



class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ['title', 'code', 'composer', 'catalogue_number', 'isrc', 'album_or_production', 'episode', 'license_number']
        widgets = {
            'composer': forms.Select(attrs={
                'class': 'form-select apache-form',
                'style': 'color: #ffffff !important; background-color: var(--apache-dark) !important;'
            }),
            'title': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'code': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'catalogue_number': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'isrc': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'album_or_production': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'episode': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control apache-form'}),
        }



class PaymentStatementForm(forms.ModelForm):
    class Meta:
        model = PaymentStatement
        fields = [
            'statement_number',
            'statement_date',
            'start_period',
            'end_period',
            'total_amount',
            'status',
            'notes',
        ]
        widgets = {
            'statement_number': forms.TextInput(attrs={
                'class': 'form-control apache-form',
                'placeholder': 'e.g., BMG-2025-01'
            }),
            'statement_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control apache-form'
            }),
            'start_period': forms.TextInput(attrs={
                'class': 'form-control apache-form',
                'placeholder': 'e.g., 202501'
            }),
            'end_period': forms.TextInput(attrs={
                'class': 'form-control apache-form',
                'placeholder': 'e.g., 202506'
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control apache-form',
                'step': '0.01'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select apache-form'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control apache-form',
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            }),
        }
        labels = {
            'statement_date': 'Statement Date',
            'start_period': 'Start Period (YYYYMM)',
            'end_period': 'End Period (YYYYMM)',
            'total_amount': 'Total Amount (£)',
            'status': 'Status',
        }
        help_texts = {
            'start_period': 'Format: YYYYMM (e.g., 202501 for January 2025)',
            'end_period': 'Format: YYYYMM (e.g., 202506 for June 2025)',
        }