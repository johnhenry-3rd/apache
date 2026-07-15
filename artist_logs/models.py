# artist_logs/models.py
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import re
import datetime
from django.db.models import Sum, Q, Count  
from django.contrib.postgres.fields import ArrayField 
from django.db.models import JSONField  # ✅ Correct import for Django 3.1+
from .fields import ListField  # ✅ Import the custom ListField
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.db import migrations, models
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
import hashlib
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
import csv
from io import TextIOWrapper, StringIO
from django.db import models
from django.db.models import Sum, Q, F, DecimalField, Min, Max
from decimal import Decimal
import time


# =============================================
# Base Models (No Dependencies)
# =============================================

class Artist(models.Model):
    """
    Legacy model for artists.
    Kept for backward compatibility but will be phased out in favor of Composer.
    """
    name = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    isrc = models.CharField(max_length=12, blank=True, null=True)
    earnings_to_date = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    vat_reg = models.CharField(max_length=1, default="N")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Artist"
        verbose_name_plural = "Artists"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.first_name and self.name:
            name_parts = self.name.split()
            if len(name_parts) > 1:
                self.last_name = name_parts[0]
                self.first_name = ' '.join(name_parts[1:])
            else:
                self.first_name = self.name
        super().save(*args, **kwargs)

class Source(models.Model):
    """Model representing the source of royalty income."""
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    is_domestic = models.BooleanField(default=True)
    country_code = models.CharField(max_length=10, blank=True, null=True)
    country_name = models.CharField(max_length=255, blank=True, null=True)
    original_source = models.CharField(max_length=255, blank=True, null=True)
    foreign_source = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Source"
        verbose_name_plural = "Sources"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class IncomeType(models.Model):
    """Model representing the type of income."""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    main_type = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Income Type"
        verbose_name_plural = "Income Types"
        ordering = ['name']

    def __str__(self):
        return self.name

# =============================================
# Composer Model (Core Model)
# =============================================

class Composer(models.Model):
    """
    Reference table for composers/artists.
    Each composer has:
    - Unique identifier (composer_id)
    - Name (full_name, first_name, last_name)
    - Contact details (email, phone, address)
    - Financial details (bank account, sort code, VAT info)
    - Payment threshold (£100 default)
    - Status (active/inactive)
    """

    # --- Unique Identifiers ---
    composer_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique identifier for the composer (auto-generated)"
    )

    # --- Name Fields ---
    full_name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Full name of the composer (e.g., 'Thomas Trueman')"
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="First name of the composer"
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Last name of the composer"
    )

    # --- Contact Information ---
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address for the composer"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Phone number for the composer"
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Postal address for the composer"
    )

    # --- Financial Details ---
    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Bank account number for payments"
    )
    bank_sort_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Bank sort code for payments"
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name of the bank"
    )
    vat_registered = models.BooleanField(
        default=False,
        help_text="Whether the composer is VAT registered"
    )
    vat_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="VAT registration number"
    )
    payment_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100.00,
        help_text="Minimum amount (£) before payment is issued"
    )

    # --- Status and Metadata ---
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the composer is active"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the composer"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this composer record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this composer record was last updated"
    )

    # --- Model Metadata ---
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Composer"
        verbose_name_plural = "Composers"

    # --- String Representation ---
    def __str__(self):
        return self.full_name

    # --- Save Method ---
    def save(self, *args, **kwargs):
        if not self.full_name:
            name_parts = []
            if self.first_name:
                name_parts.append(self.first_name)
            if self.last_name:
                name_parts.append(self.last_name)
            if name_parts:
                self.full_name = ' '.join(name_parts)

        if not self.composer_id:
            name_parts = []
            if self.first_name:
                name_parts.append(self.first_name)
            if self.last_name:
                name_parts.append(self.last_name)
            if name_parts:
                hash_str = hashlib.md5(self.full_name.encode()).hexdigest()[:8]
                self.composer_id = f"{name_parts[0]}-{hash_str}"
            else:
                self.composer_id = f"unknown-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"

        super().save(*args, **kwargs)

    # --- Class Method ---
    @classmethod
    def find_or_create_by_name(cls, name):
        if not name or not name.strip():
            return None

        normalized = re.sub(r'[^\w\s-]', ' ', name).strip()
        normalized = re.sub(r'\s+', ' ', normalized).title()

        if ',' in normalized:
            parts = [p.strip() for p in normalized.split(',')]
            if len(parts) == 2:
                normalized = f"{parts[1]} {parts[0]}"

        composer = cls.objects.filter(full_name__iexact=normalized).first()
        if not composer:
            composer = cls.objects.create(full_name=normalized)
        return composer

class Song(models.Model):
    """
    Model representing a song with a unique code.
    Each song can have multiple composers with royalty splits.
    """
    # --- Basic Information ---
    code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        help_text="Unique code for the song (e.g., '6087301')"
    )
    title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Title of the song"
    )
    catalogue_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="Catalogue number of the song"
    )
    isrc = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="International Standard Recording Code"
    )

    # --- Production Information ---
    album_or_production = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Album or production the song belongs to"
    )
    episode = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Episode the song belongs to (if applicable)"
    )
    license_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="License number for the song"
    )

    # --- Composer Relationship ---
    composer = models.ForeignKey(
        'Composer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='songs',
        help_text="Legacy: The primary composer of this song (for backward compatibility)"
    )

    # --- Metadata ---
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this song was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this song was last updated"
    )

    # --- Model Metadata ---
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                name='unique_song_code',
                condition=models.Q(code__isnull=False)
            )
        ]
        verbose_name = "Song"
        verbose_name_plural = "Songs"
        ordering = ['title']
        indexes = [
            models.Index(fields=['title'], name='song_title_idx'),
            models.Index(fields=['code'], name='song_code_idx'),
            models.Index(fields=['catalogue_number'], name='song_catalogue_idx'),
            models.Index(fields=['isrc'], name='song_isrc_idx'),
            models.Index(fields=['created_at'], name='song_created_idx'),
        ]

    # --- String Representation ---
    def __str__(self):
        return f"{self.title} ({self.code})" if self.code else self.title

    # --- Save Method ---
    def save(self, *args, **kwargs):
        """
        Custom save method.
        If this is a new song and no composer is set, but there are SongComposer relationships,
        set the primary composer to the first one for backward compatibility.
        """
        if not self.pk:  # New song being created
            super().save(*args, **kwargs)
            # If no legacy composer is set, but we have SongComposer relationships,
            # set the first one as the legacy composer
            if not self.composer and hasattr(self, 'song_composers') and self.song_composers.exists():
                first_composer = self.song_composers.first().composer
                self.composer = first_composer
                super().save(update_fields=['composer'])
        else:
            super().save(*args, **kwargs)

    # --- Earnings Methods ---
    def total_earnings(self):
        return self.prs_records.aggregate(  # ✅ Use prs_records
            total=models.Sum('royalty_payable')
        )['total'] or Decimal('0.00')

    def paid_earnings(self):
        return self.prs_records.filter(is_paid=True).aggregate(
            total=Sum('royalty_payable')
        )['total'] or 0

    def unpaid_earnings(self):
        return self.total_earnings() - self.paid_earnings()

    def earnings_by_source(self):
        return list(
            self.prs_records.values('source__name')
            .annotate(total=Sum('royalty_payable'))
            .order_by('-total')
        )

    def earnings_by_income_type(self):
        return list(
            self.prs_records.values('income_type__name')
            .annotate(total=Sum('royalty_payable'))
            .order_by('-total')
        )

    def earnings_by_period(self):
        return list(
            self.prs_records.values('income_period')
            .annotate(total=Sum('royalty_payable'))
            .order_by('income_period')
        )

    # --- Composer Relationship Methods ---
    @property
    def composers(self):
        return [sc.composer for sc in self.song_composers.all().select_related('composer')]

    @property
    def composer_names(self):
        return ", ".join([c.full_name for c in self.composers])

    @property
    def has_multiple_composers(self):
        return self.song_composers.count() > 1

    @property
    def total_split_percentage(self):
        return self.song_composers.aggregate(
            total=Sum('split_percentage')
        )['total'] or 0

    def add_composer(self, composer, split_percentage=100.0, notes=""):
        if not (0 <= split_percentage <= 100):
            raise ValueError("Split percentage must be between 0 and 100")

        current_total = self.total_split_percentage
        if current_total + split_percentage > 100:
            raise ValueError(
                f"Total split percentage would exceed 100% "
                f"(current: {current_total}%, adding: {split_percentage}%)"
            )

        SongComposer = self.song_composers.model
        SongComposer.objects.create(
            song=self,
            composer=composer,
            split_percentage=split_percentage,
            notes=notes
        )

        if self.song_composers.count() == 1:
            self.composer = composer
            self.save(update_fields=['composer'])

    def set_composers(self, composer_splits):
        total_percentage = sum(percentage for _, percentage in composer_splits)
        if total_percentage != 100:
            raise ValueError(
                f"Total split percentage must equal 100% (got {total_percentage}%)"
            )

        self.song_composers.all().delete()

        SongComposer = self.song_composers.model
        for composer, percentage in composer_splits:
            SongComposer.objects.create(
                song=self,
                composer=composer,
                split_percentage=percentage
            )

        if composer_splits:
            first_composer, _ = composer_splits[0]
            self.composer = first_composer
            self.save(update_fields=['composer'])

    def get_composer_splits(self):
        return [{
            'composer_id': sc.composer.id,
            'composer_name': sc.composer.full_name,
            'split_percentage': sc.split_percentage,
            'notes': sc.notes
        } for sc in self.song_composers.all()]

    def get_composer_earnings(self):
        # Implement based on your PRS data structure
        return []

    def get_prs_summary(self):
        return {
            'total_records': self.prs_records.count(),
            'total_earnings': self.total_earnings(),
            'paid_earnings': self.paid_earnings(),
            'unpaid_earnings': self.unpaid_earnings(),
            'sources': self.earnings_by_source(),
            'income_types': self.earnings_by_income_type(),
            'periods': self.earnings_by_period(),
        }

    def get_composer_summary(self):
        return {
            'composers': self.composers,
            'composer_names': self.composer_names,
            'has_multiple_composers': self.has_multiple_composers,
            'total_split_percentage': self.total_split_percentage,
            'is_fully_split': self.total_split_percentage == 100,
            'composer_splits': self.get_composer_splits(),
            'composer_earnings': self.get_composer_earnings(),
        }

    def get_full_summary(self):
        return {
            **self.get_prs_summary(),
            **self.get_composer_summary(),
            'id': self.id,
            'title': self.title,
            'code': self.code,
            'catalogue_number': self.catalogue_number,
            'isrc': self.isrc,
            'album_or_production': self.album_or_production,
            'episode': self.episode,
            'license_number': self.license_number,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'code': self.code,
            'catalogue_number': self.catalogue_number,
            'isrc': self.isrc,
            'album_or_production': self.album_or_production,
            'episode': self.episode,
            'license_number': self.license_number,
            'composer': self.composer.full_name if self.composer else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
class SongComposer(models.Model):
    """
    Intermediate model to handle multiple composers per song with royalty splits.
    This allows a song to have multiple composers, each with their own percentage of royalties.
    """
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='song_composers'
    )
    composer = models.ForeignKey(
        'Composer',
        on_delete=models.CASCADE,
        related_name='song_composers'
    )
    split_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of royalties for this composer (0-100)"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about this composer's contribution"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['song', 'composer']]
        verbose_name = "Song Composer Split"
        verbose_name_plural = "Song Composer Splits"
        ordering = ['song', '-split_percentage']

    def __str__(self):
        return f"{self.song.title} - {self.composer.full_name} ({self.split_percentage}%)"

    def save(self, *args, **kwargs):
        """
        Ensure the total split percentage for a song doesn't exceed 100%.
        """
        # Calculate total percentage for this song (excluding current instance if it exists)
        existing_splits = SongComposer.objects.filter(song=self.song).exclude(pk=self.pk)
        total = existing_splits.aggregate(total=models.Sum('split_percentage'))['total'] or 0
        total += self.split_percentage

        if total > 100:
            raise ValueError(
                f"Total split percentage for song '{self.song.title}' would exceed 100% "
                f"(current total: {total}%). Please adjust the percentages."
            )

        super().save(*args, **kwargs)

# =============================================
# Payment Statement Model
# =============================================

class PaymentStatement(models.Model):
    """Model to represent a payment statement/period."""
    statement_number = models.CharField(max_length=50, unique=True)
    statement_date = models.DateField()
    start_period = models.CharField(max_length=20, help_text="Start of the income period (e.g., 202501)")
    end_period = models.CharField(max_length=20, help_text="End of the income period (e.g., 202506)")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('finalized', 'Finalized'),
            ('paid', 'Paid'),
        ],
        default='draft'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-statement_date']
        verbose_name = "Payment Statement"
        verbose_name_plural = "Payment Statements"

    def __str__(self):
        return f"Statement {self.statement_number} ({self.start_period}-{self.end_period})"

# =============================================
# PRS Data Model (Depends on Song, Source, IncomeType, PaymentStatement)
# unique_together defines the allowance of duplicates in the prs data
# =============================================

    """
    Model to store PRS data records.
    Each record links to a Song, which links to a Composer.
    Optimized for PostgreSQL with additional helper methods.
    """
    # Basic identifiers
class Prs_data(models.Model):
    song = models.ForeignKey(
        Song,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prs_records'  # ✅ Revert to original name
    )
    song_title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Title of the song (denormalized from Song for performance)"
    )
    song_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="Unique code for the song (denormalized from Song)"
    )

    # Source information
    source = models.ForeignKey(
        'Source',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The source of the royalty income",
        db_index=True
    )
    source_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="Code of the source (denormalized from Source)"
    )
    source_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the source (denormalized from Source)"
    )
    domestic_or_foreign = models.CharField(
        max_length=1,
        choices=[('D', 'Domestic'), ('F', 'Foreign')],
        blank=True,
        null=True,
        db_index=True,
        help_text="Whether the source is domestic or foreign"
    )
    foreign_source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the foreign source if applicable"
    )
    royalty_country_code = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        db_index=True,
        help_text="Country code for the royalty source"
    )
    royalty_country_description = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Description of the royalty country"
    )

    # Income information
    income_type = models.ForeignKey(
        'IncomeType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The type of income",
        db_index=True
    )
    income_type_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="Code of the income type (denormalized from IncomeType)"
    )
    income_type_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name of the income type (denormalized from IncomeType)"
    )
    main_income_type_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Main category of the income type"
    )

    # Financial data
    units = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of units (e.g., plays, streams)"
    )
    percentage_collected = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage of royalty collected"
    )
    amount_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Total amount collected"
    )
    royalty_payout_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage of royalty to be paid out"
    )
    royalty_payable = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        db_index=True,
        help_text="Amount payable to the composer"
    )

    # Statement information
    statement_id_year = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        db_index=True,
        help_text="Year part of the statement ID"
    )
    statement_id_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Number part of the statement ID"
    )
    income_period = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="Period for which the royalty was earned (e.g., 202604)"
    )

    # Additional fields (legacy)
    catalogue_no = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Catalogue number of the song (legacy field)"
    )
    composers = models.TextField(
        blank=True,
        null=True,
        help_text="Legacy field: Composer names as text (for backward compatibility)"
    )
    original_source_as_received = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Original source as received in the data"
    )
    original_source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Original source of the royalty"
    )
    artist = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Legacy field: Artist name as text (for backward compatibility)"
    )
    isrc = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        db_index=True,
        help_text="International Standard Recording Code"
    )
    album_or_production = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Album or production the song belongs to"
    )
    episode = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Episode the song belongs to (if applicable)"
    )
    license_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="License number for the song"
    )

    # Payment tracking fields
    is_paid = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this record has been paid"
    )
    payment_date = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Date when the payment was made"
    )
    payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Amount paid for this record"
    )
    payment_statement = models.ForeignKey(
        'PaymentStatement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prs_records',
        help_text="The payment statement this record is associated with",
        db_index=True
    )
    payment_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about the payment"
    )

    # PostgreSQL-specific fields - CORRECTED
    metadata = JSONField(  # ✅ Using Django's built-in JSONField
        blank=True,
        null=True,
        help_text="Additional metadata for this PRS record"
    )

    tags = ArrayField(  # ✅ Using PostgreSQL's ArrayField
        models.CharField(max_length=50),
        blank=True,
        null=True,
        help_text="Tags for categorizing this PRS record"
    )
    
    tags = ListField(  # ✅ Now using the custom ListField
        blank=True,
        null=True,
        help_text="Tags for categorizing this PRS record"
    )

    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )

    class Meta:
        verbose_name = "PRS Data Record"
        verbose_name_plural = "PRS Data Records"
        ordering = ['-income_period', 'song_title']
        indexes = [
            models.Index(fields=['song_title']),
            models.Index(fields=['income_period']),
            # ... other indexes ...
        ]

    def __str__(self):
        return f"{self.song_title} - £{self.royalty_payable} ({self.income_period})"

    def save(self, *args, **kwargs):
        """
        Custom save method to auto-populate denormalized fields.
        """
        if self.song and not self.song_title:
            self.song_title = self.song.title
        if self.song and self.song.code and not self.song_code:
            self.song_code = self.song.code
        if self.source:
            if not self.source_code:
                self.source_code = self.source.code
            if not self.source_name:
                self.source_name = self.source.name
        if self.income_type:
            if not self.income_type_code:
                self.income_type_code = self.income_type.code
            if not self.income_type_name:
                self.income_type_name = self.income_type.name

        # Update legacy composer field
        if self.song:
            self.composers = self.song.composer_names
            self.artist = self.song.composer_names if self.song.composer else None

        super().save(*args, **kwargs)

    # ====================
    # Property Methods
    # ====================

    @property
    def composer(self):
        """
        Returns the first composer from the song for backward compatibility.
        """
        return self.song.composer if self.song else None

    @property
    def composer_name(self):
        """
        Returns the composer names from the song.
        """
        return self.song.composer_names if self.song else "Unknown"

    @property
    def composer_list(self):
        """
        Returns a list of composer objects from the song.
        """
        return self.song.composers if self.song else []

    @property
    def is_domestic(self):
        """
        Returns True if this record is from a domestic source.
        """
        return self.domestic_or_foreign == 'D'

    @property
    def is_foreign(self):
        """
        Returns True if this record is from a foreign source.
        """
        return self.domestic_or_foreign == 'F'

    @property
    def full_statement_id(self):
        """
        Returns the full statement ID as a string.
        """
        if self.statement_id_year and self.statement_id_number:
            return f"{self.statement_id_year}-{self.statement_id_number}"
        return None

    # ====================
    # Payment Methods
    # ====================

    def mark_as_paid(self, payment_statement=None, payment_date=None, payment_amount=None, notes=None):
        """
        Helper method to mark this record as paid.
        """
        self.is_paid = True

        if payment_statement:
            self.payment_statement = payment_statement
        if payment_date:
            self.payment_date = payment_date
        if payment_amount:
            self.payment_amount = payment_amount
        if notes:
            self.payment_notes = notes
        else:
            if self.payment_notes:
                self.payment_notes += f"\nMarked as paid on {timezone.now().date()}"
            else:
                self.payment_notes = f"Marked as paid on {timezone.now().date()}"

        self.save()

    def mark_as_unpaid(self):
        """
        Helper method to mark this record as unpaid.
        """
        self.is_paid = False
        self.payment_date = None
        self.payment_amount = None
        self.payment_statement = None
        self.payment_notes = None
        self.save()

    def toggle_paid_status(self):
        """
        Toggle the paid status of this record.
        """
        if self.is_paid:
            self.mark_as_unpaid()
        else:
            self.mark_as_paid()

    # ====================
    # Calculation Methods
    # ====================

    def calculate_composer_shares(self):
        """
        Calculate how the royalty_payable would be split among the song's composers.
        Returns a list of tuples: (composer, amount)
        """
        if not self.song:
            return []

        return self.song.distribute_royalties(self.royalty_payable)

    def get_composer_earnings(self):
        """
        Get the earnings for each composer based on their split percentage.
        Returns a list of tuples: (composer, amount)
        """
        return self.calculate_composer_shares()

    # ====================
    # Query Methods
    # ====================

    @classmethod
    def get_paid_records(cls):
        """
        Returns a queryset of all paid PRS records.
        """
        return cls.objects.filter(is_paid=True)

    @classmethod
    def get_unpaid_records(cls):
        """
        Returns a queryset of all unpaid PRS records.
        """
        return cls.objects.filter(is_paid=False)

    @classmethod
    def get_by_period(cls, period):
        """
        Returns a queryset of PRS records for a specific income period.
        """
        return cls.objects.filter(income_period=period)

    @classmethod
    def get_by_source(cls, source):
        """
        Returns a queryset of PRS records for a specific source.
        """
        return cls.objects.filter(source=source)

    @classmethod
    def get_by_income_type(cls, income_type):
        """
        Returns a queryset of PRS records for a specific income type.
        """
        return cls.objects.filter(income_type=income_type)

    @classmethod
    def get_by_song(cls, song):
        """
        Returns a queryset of PRS records for a specific song.
        """
        return cls.objects.filter(song=song)

    @classmethod
    def get_total_earnings(cls):
        """
        Returns the total earnings across all PRS records.
        """
        return cls.objects.aggregate(
            total=Sum('royalty_payable')
        )['total'] or 0

    @classmethod
    def get_paid_earnings(cls):
        """
        Returns the total paid earnings across all PRS records.
        """
        return cls.objects.filter(is_paid=True).aggregate(
            total=Sum('royalty_payable')
        )['total'] or 0

    @classmethod
    def get_unpaid_earnings(cls):
        """
        Returns the total unpaid earnings across all PRS records.
        """
        return cls.get_total_earnings() - cls.get_paid_earnings()

    @classmethod
    def get_earnings_by_period(cls):
        """
        Returns earnings grouped by income period.
        Returns a list of dictionaries: [{'period': str, 'total': float}]
        """
        return list(
            cls.objects.values('income_period')
            .annotate(total=Sum('royalty_payable'))
            .order_by('income_period')
        )

    @classmethod
    def get_earnings_by_source(cls):
        """
        Returns earnings grouped by source.
        Returns a list of dictionaries: [{'source': str, 'total': float}]
        """
        return list(
            cls.objects.values('source__name')
            .annotate(total=Sum('royalty_payable'))
            .order_by('-total')
        )

    @classmethod
    def get_earnings_by_income_type(cls):
        """
        Returns earnings grouped by income type.
        Returns a list of dictionaries: [{'income_type': str, 'total': float}]
        """
        return list(
            cls.objects.values('income_type__name')
            .annotate(total=Sum('royalty_payable'))
            .order_by('-total')
        )

    @classmethod
    def get_earnings_by_song(cls):
        """
        Returns earnings grouped by song.
        Returns a list of dictionaries: [{'song': str, 'total': float}]
        """
        return list(
            cls.objects.values('song__title', 'song__code')
            .annotate(total=Sum('royalty_payable'))
            .order_by('-total')
        )

    @classmethod
    def get_earnings_by_composer(cls):
        """
        Returns earnings grouped by composer.
        Returns a list of dictionaries: [{'composer': str, 'total': float}]
        """
        return list(
            cls.objects.values('song__composer__full_name')
            .annotate(total=Sum('royalty_payable'))
            .order_by('-total')
        )

    @classmethod
    def get_records_by_date_range(cls, start_date=None, end_date=None):
        """
        Returns PRS records within a specific date range.
        """
        qs = cls.objects.all()
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        return qs

    @classmethod
    def get_summary_statistics(cls):
        """
        Returns summary statistics for all PRS records.
        """
        return {
            'total_records': cls.objects.count(),
            'total_earnings': cls.get_total_earnings(),
            'paid_earnings': cls.get_paid_earnings(),
            'unpaid_earnings': cls.get_unpaid_earnings(),
            'paid_records': cls.get_paid_records().count(),
            'unpaid_records': cls.get_unpaid_records().count(),
            'earnings_by_period': cls.get_earnings_by_period(),
            'earnings_by_source': cls.get_earnings_by_source(),
            'earnings_by_income_type': cls.get_earnings_by_income_type(),
            'earnings_by_song': cls.get_earnings_by_song(),
            'earnings_by_composer': cls.get_earnings_by_composer(),
        }

    # ====================
    # Bulk Operations
    # ====================

    @classmethod
    def bulk_mark_as_paid(cls, record_ids, payment_statement=None, payment_date=None, notes=None):
        """
        Mark multiple PRS records as paid in a single query.
        """
        records = cls.objects.filter(id__in=record_ids)
        records.update(
            is_paid=True,
            payment_statement=payment_statement,
            payment_date=payment_date,
            updated_at=timezone.now()
        )

        if notes:
            for record in records:
                if record.payment_notes:
                    record.payment_notes += f"\n{notes}"
                else:
                    record.payment_notes = notes
                record.save(update_fields=['payment_notes'])

    @classmethod
    def bulk_mark_as_unpaid(cls, record_ids):
        """
        Mark multiple PRS records as unpaid in a single query.
        """
        cls.objects.filter(id__in=record_ids).update(
            is_paid=False,
            payment_date=None,
            payment_amount=None,
            payment_statement=None,
            payment_notes=None,
            updated_at=timezone.now()
        )

    # ====================
    # Utility Methods
    # ====================

    def to_dict(self):
        """
        Returns the PRS record as a dictionary.
        """
        return {
            'id': self.id,
            'song': self.song.to_dict() if self.song else None,
            'song_title': self.song_title,
            'song_code': self.song_code,
            'source': self.source.name if self.source else None,
            'source_code': self.source_code,
            'source_name': self.source_name,
            'domestic_or_foreign': self.domestic_or_foreign,
            'foreign_source': self.foreign_source,
            'royalty_country_code': self.royalty_country_code,
            'royalty_country_description': self.royalty_country_description,
            'income_type': self.income_type.name if self.income_type else None,
            'income_type_code': self.income_type_code,
            'income_type_name': self.income_type_name,
            'main_income_type_name': self.main_income_type_name,
            'units': self.units,
            'percentage_collected': float(self.percentage_collected),
            'amount_collected': float(self.amount_collected),
            'royalty_payout_percentage': float(self.royalty_payout_percentage),
            'royalty_payable': float(self.royalty_payable),
            'statement_id_year': self.statement_id_year,
            'statement_id_number': self.statement_id_number,
            'full_statement_id': self.full_statement_id,
            'income_period': self.income_period,
            'catalogue_no': self.catalogue_no,
            'composers': self.composer_name,
            'original_source_as_received': self.original_source_as_received,
            'original_source': self.original_source,
            'artist': self.artist,
            'isrc': self.isrc,
            'album_or_production': self.album_or_production,
            'episode': self.episode,
            'license_number': self.license_number,
            'is_paid': self.is_paid,
            'payment_date': self.payment_date,
            'payment_amount': float(self.payment_amount) if self.payment_amount else None,
            'payment_statement': self.payment_statement.statement_number if self.payment_statement else None,
            'payment_notes': self.payment_notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'composer_shares': self.calculate_composer_shares(),
        }

    @classmethod
    def get_duplicate_records(cls, song_code=None, income_period=None, source_code=None, income_type_code=None):
        """
        Find potential duplicate PRS records based on various criteria.
        """
        qs = cls.objects.all()

        if song_code:
            qs = qs.filter(song_code=song_code)
        if income_period:
            qs = qs.filter(income_period=income_period)
        if source_code:
            qs = qs.filter(source_code=source_code)
        if income_type_code:
            qs = qs.filter(income_type_code=income_type_code)

        # Group by key fields and count
        return list(
            qs.values('song_code', 'income_period', 'source_code', 'income_type_code')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .order_by('-count')
        )
# =============================================
# Payment Plan Model (Depends on Composer, PaymentStatement)
# =============================================

class PaymentPlan(models.Model):
    """
    Model to track payment plans for composers.
    A payment plan is generated when a composer's unpaid royalties reach the £100 threshold.
    """
    composer = models.ForeignKey(Composer, on_delete=models.CASCADE, related_name='payment_plans')
    payment_statement = models.ForeignKey(
        PaymentStatement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_plans'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft'
    )
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment Plan"
        verbose_name_plural = "Payment Plans"
        constraints = [
            models.UniqueConstraint(
                fields=['composer', 'payment_statement'],
                name='unique_payment_plan_per_composer_per_statement'
            )
        ]

    def __str__(self):
        return f"Payment Plan #{self.id} - {self.composer.full_name} (£{self.total_amount})"

    def get_prs_records(self):
        """Get all PRS records associated with this payment plan."""
        return Prs_data.objects.filter(
            song__composer=self.composer,
            is_paid=False,
            income_period__gte=self.start_date,
            income_period__lte=self.end_date
        ).order_by('-income_period')

    @classmethod
    def generate_payment_plans(cls, statement):
        from django.db.models import Sum

        # Get all unpaid PRS records for this statement's period
        prs_records = Prs_data.objects.filter(
            is_paid=False,
            income_period__gte=statement.start_period,
            income_period__lte=statement.end_period
        )

        # Group by composer (via song.composer) and sum royalties
        composer_totals = prs_records.values('song__composer').annotate(
            total_royalty=Sum('royalty_payable')
        ).filter(total_royalty__gte=100)

        # Create payment plans for composers who meet the threshold
        created_plans = []
        for entry in composer_totals:
            composer = Composer.objects.get(id=entry['song__composer'])
            total = entry['total_royalty']

            # Check if a payment plan already exists
            existing_plan = PaymentPlan.objects.filter(
                composer=composer,
                payment_statement=statement,
                status__in=['draft', 'pending']
            ).first()

            if not existing_plan:
                plan = PaymentPlan.objects.create(
                    composer=composer,
                    payment_statement=statement,
                    start_date=statement.statement_date,
                    end_date=statement.statement_date,
                    total_amount=total,
                    status='draft',
                 notes=f"Auto-generated for {statement.statement_number}"
                )
                created_plans.append(plan)

        return created_plans

    def mark_as_paid(self, payment_date=None, payment_reference=None):
        """Mark this payment plan as paid and update all associated PRS records."""
        if payment_date is None:
            payment_date = timezone.now().date()

        self.status = 'paid'
        self.payment_date = payment_date
        if payment_reference:
            self.payment_reference = payment_reference
        self.save()

        for record in self.get_prs_records():
            record.mark_as_paid(
                payment_statement=self.payment_statement,
                payment_date=payment_date,
                payment_amount=record.royalty_payable,
                notes=f"Paid via Payment Plan #{self.id}"
            )

        return True

# =============================================
# Upload History Model
# =============================================


class UploadHistory(models.Model):
    file_name = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=32)
    records_imported = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)  # ✅ Add this
    status = models.CharField(max_length=20, choices=[
        ('Success', 'Success'),
        ('Partial', 'Partial'),
        ('Failed', 'Failed'),
    ])
    error_message = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ Add this

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.file_name} ({self.status}) - {self.uploaded_at}"

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Upload History"
        verbose_name_plural = "Upload Histories"

    def __str__(self):
        return f"{self.file_name} ({self.uploaded_at.strftime('%Y-%m-%d %H:%M')}) - {self.status}"

    @classmethod
    def is_file_uploaded(cls, file):
        """
        Check if a file has already been uploaded by comparing its hash.
        Works with both InMemoryUploadedFile and temporary files.

        Args:
            file: The file to check (InMemoryUploadedFile or temporary file)

        Returns:
            bool: True if the file has been uploaded before, False otherwise
        """
        try:
            # Read the file content and compute its hash
            if isinstance(file, InMemoryUploadedFile):
                file.seek(0)
                file_content = file.read()
                file_hash = hashlib.md5(file_content).hexdigest()
                file.seek(0)  # Reset file pointer for later use
            else:
                # For temporary files or other types
                with open(file.temporary_file_path(), 'rb') as f:
                    file_content = f.read()
                    file_hash = hashlib.md5(file_content).hexdigest()

            # Check if this hash already exists
            return cls.objects.filter(file_hash=file_hash).exists()
        except Exception as e:
            # Log the error and return False to allow the upload to proceed
            print(f"Error checking file hash: {str(e)}")
            return False

    def clean_up_temp_file(self):
        """
        Clean up the temporary file if it exists.
        """
        if self.file_path and default_storage.exists(self.file_path):
            try:
                default_storage.delete(self.file_path)
                self.file_path = ''
                self.save(update_fields=['file_path'])
                return True
            except Exception as e:
                print(f"Error deleting temporary file {self.file_path}: {str(e)}")
                return False
        return True

    def get_status_badge_color(self):
        """
        Return the Bootstrap badge color for the status.
        """
        status_colors = {
            'Pending': 'secondary',
            'Processing': 'primary',
            'Success': 'success',
            'Failed': 'danger',
            'Partial': 'warning',
        }
        return status_colors.get(self.status, 'secondary')

    def get_status_display(self):
        """
        Return the human-readable status.
        """
        return dict(self._meta.get_field('status').choices).get(self.status, self.status)


