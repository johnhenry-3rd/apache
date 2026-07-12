from django import forms
from .models import Composer, Song, SongComposer, PaymentStatement
from django.db.models import Sum

# Song Form
class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = [
            'title', 'code', 'catalogue_number', 'isrc',
            'album_or_production', 'episode', 'license_number', 'composer'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter song title'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter song code (e.g., 6087301)'
            }),
            'catalogue_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter catalogue number'
            }),
            'isrc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter ISRC code'
            }),
            'album_or_production': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter album or production name'
            }),
            'episode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter episode name'
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter license number'
            }),
            'composer': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'title': 'Title *',
            'code': 'Code',
            'catalogue_number': 'Catalogue Number',
            'isrc': 'ISRC',
            'album_or_production': 'Album/Production',
            'episode': 'Episode',
            'license_number': 'License Number',
            'composer': 'Primary Composer',
        }
        help_texts = {
            'code': 'Unique code for the song (e.g., 6087301)',
            'isrc': 'International Standard Recording Code',
            'composer': 'Primary composer for backward compatibility',
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code and Song.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A song with this code already exists.")
        return code

# Composer Form
class ComposerForm(forms.ModelForm):
    class Meta:
        model = Composer
        fields = [
            'first_name', 'last_name', 'full_name', 'email', 'phone', 'address',
            'bank_name', 'bank_sort_code', 'bank_account_number',
            'vat_registered', 'vat_number', 'payment_threshold', 'is_active', 'notes'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_sort_code': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'vat_number': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'payment_threshold': 'Payment Threshold (£)',
        }

# SongComposer Form
class SongComposerForm(forms.ModelForm):
    class Meta:
        model = SongComposer
        fields = ['composer', 'split_percentage', 'notes']
        widgets = {
            'composer': forms.Select(attrs={'class': 'form-select'}),
            'split_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional notes about this composer\'s contribution'
            }),
        }
        labels = {
            'composer': 'Composer',
            'split_percentage': 'Split Percentage (%)',
            'notes': 'Notes',
        }
        help_texts = {
            'split_percentage': 'Percentage of royalties for this composer (0-100)',
        }

    def __init__(self, *args, **kwargs):
        self.song = kwargs.pop('song', None)  # Get song from kwargs
        super().__init__(*args, **kwargs)

    def clean_split_percentage(self):
        split_percentage = self.cleaned_data.get('split_percentage')
        if split_percentage is not None:
            if split_percentage < 0 or split_percentage > 100:
                raise forms.ValidationError("Split percentage must be between 0 and 100.")
        return split_percentage

    def clean(self):
        cleaned_data = super().clean()
        composer = cleaned_data.get('composer')
        split_percentage = cleaned_data.get('split_percentage')

        if composer and split_percentage and self.song:
            # Check if this composer is already in the song
            if SongComposer.objects.filter(song=self.song, composer=composer).exists():
                if not self.instance.pk:  # Only raise error if this is a new instance
                    raise forms.ValidationError(
                        f"{composer.full_name} is already assigned to this song. "
                        "Use the edit form to update the split percentage."
                    )

            # Check if adding this composer would exceed 100% total
            # Get the sum of existing splits for this song (excluding current instance if editing)
            existing_splits = SongComposer.objects.filter(song=self.song)
            if self.instance.pk:
                existing_splits = existing_splits.exclude(pk=self.instance.pk)

            # Use the Sum function from django.db.models
            existing_total = existing_splits.aggregate(total=Sum('split_percentage'))['total'] or 0
            new_total = existing_total + split_percentage

            if new_total > 100:
                raise forms.ValidationError(
                    f"Total split percentage would exceed 100% (current total: {existing_total}% + {split_percentage}% = {new_total}%)"
                )

        return cleaned_data

# PaymentStatement Form
class PaymentStatementForm(forms.ModelForm):
    class Meta:
        model = PaymentStatement
        fields = [
            'statement_number', 'start_period', 'end_period',
            'statement_date', 'total_amount', 'status', 'notes'
        ]
        widgets = {
            'statement_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter statement number (e.g., PS-2026-001)'
            }),
            'start_period': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'YYYYMM (e.g., 202601)'
            }),
            'end_period': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'YYYYMM (e.g., 202601)'
            }),
            'statement_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes about this payment statement'
            }),
        }
        labels = {
            'statement_number': 'Statement Number *',
            'start_period': 'Start Period *',
            'end_period': 'End Period *',
            'statement_date': 'Statement Date *',
            'total_amount': 'Total Amount (£) *',
            'status': 'Status *',
            'notes': 'Notes',
        }
        help_texts = {
            'statement_number': 'Unique identifier for this payment statement',
            'start_period': 'Period start in YYYYMM format',
            'end_period': 'Period end in YYYYMM format',
            'total_amount': 'Total amount of this payment statement',
            'status': 'Current status of this payment statement',
        }

    def clean_total_amount(self):
        total_amount = self.cleaned_data.get('total_amount')
        if total_amount is not None and total_amount < 0:
            raise forms.ValidationError("Total amount cannot be negative.")
        return total_amount

    def clean(self):
        cleaned_data = super().clean()
        start_period = cleaned_data.get('start_period')
        end_period = cleaned_data.get('end_period')

        if start_period and end_period:
            if len(start_period) != 6 or len(end_period) != 6:
                raise forms.ValidationError("Periods must be in YYYYMM format (6 digits).")

            try:
                start_year = int(start_period[:4])
                start_month = int(start_period[4:])
                end_year = int(end_period[:4])
                end_month = int(end_period[4:])

                if start_month < 1 or start_month > 12 or end_month < 1 or end_month > 12:
                    raise forms.ValidationError("Month must be between 01 and 12.")

                if start_year < 2000 or end_year < 2000:
                    raise forms.ValidationError("Year must be 2000 or later.")

                if (start_year > end_year) or (start_year == end_year and start_month > end_month):
                    raise forms.ValidationError("Start period must be before or equal to end period.")

            except ValueError:
                raise forms.ValidationError("Periods must be numeric in YYYYMM format.")

        return cleaned_data