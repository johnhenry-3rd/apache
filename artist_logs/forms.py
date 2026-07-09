# artist_logs/forms.py
from django import forms
from .models import Composer, Song
from .models import PaymentStatement

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

# artist_logs/forms.py
from django import forms
from .models import Song, Composer

class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = [
            'title', 'code', 'catalogue_number', 'isrc',
            'album_or_production', 'episode', 'license_number', 'composer'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'code': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'catalogue_number': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'isrc': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'album_or_production': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'episode': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'composer': forms.Select(attrs={'class': 'form-select apache-form'}),
        }
        labels = {
            'album_or_production': 'Album/Production',
        }



class PaymentStatementForm(forms.ModelForm):
    class Meta:
        model = PaymentStatement
        fields = ['statement_number', 'statement_date', 'start_period', 'end_period', 'notes']
        widgets = {
            'statement_number': forms.TextInput(attrs={'class': 'form-control apache-form'}),
            'statement_date': forms.DateInput(attrs={'class': 'form-control apache-form', 'type': 'date'}),
            'start_period': forms.TextInput(attrs={'class': 'form-control apache-form', 'placeholder': 'YYYYMM'}),
            'end_period': forms.TextInput(attrs={'class': 'form-control apache-form', 'placeholder': 'YYYYMM'}),
            'notes': forms.Textarea(attrs={'class': 'form-control apache-form', 'rows': 3}),
        }