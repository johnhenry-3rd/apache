from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import re
import datetime

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
    # Unique identifiers
    composer_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique identifier for the composer (auto-generated)"
    )
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

    # Contact information
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

    # Financial details
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

    # Status and metadata
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

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Composer"
        verbose_name_plural = "Composers"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        """
        Auto-generate composer_id and populate first_name/last_name from full_name.
        """
        # Auto-generate composer_id if not provided
        if not self.composer_id:
            name_parts = self.full_name.upper().split()
            if len(name_parts) >= 2:
                self.composer_id = f"{name_parts[-1]}-{name_parts[0]}-{abs(hash(self.full_name))[:3]}"
            else:
                self.composer_id = f"{name_parts[0]}-{abs(hash(self.full_name))[:3]}"

        # Auto-populate first_name and last_name from full_name
        if self.full_name and not (self.first_name and self.last_name):
            name_parts = self.full_name.split()
            if len(name_parts) > 1:
                self.last_name = name_parts[-1]
                self.first_name = ' '.join(name_parts[:-1])
            else:
                self.first_name = self.full_name

        super().save(*args, **kwargs)

    @classmethod
    def find_or_create_by_name(cls, name):
        """
        Find a composer by name or create a new one.
        Handles name variations (e.g., "Thomas/Trueman" → "Thomas Trueman").
        """
        if not name or not name.strip():
            return None

        # Normalize the name: remove special chars, extra spaces, and standardize case
        normalized = re.sub(r'[^\w\s-]', ' ', name).strip()  # Remove /, ;, etc.
        normalized = re.sub(r'\s+', ' ', normalized).title()  # Collapse spaces and title case

        # Handle "Last, First" format (e.g., "Trueman, Thomas")
        if ',' in normalized:
            parts = [p.strip() for p in normalized.split(',')]
            if len(parts) == 2:
                normalized = f"{parts[1]} {parts[0]}"

        # Try to find an existing composer (case-insensitive)
        composer = cls.objects.filter(full_name__iexact=normalized).first()

        if not composer:
            composer = cls.objects.create(full_name=normalized)

        return composer

# =============================================
# Song Model (Depends on Composer)
# =============================================

class Song(models.Model):
    """
    Model representing a song with a unique code.
    Each song has exactly one composer (ForeignKey to Composer).
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique code for the song (e.g., '6087301')"
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of the song (e.g., 'Dank')"
    )
    catalogue_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Catalogue number of the song"
    )
    isrc = models.CharField(
        max_length=12,
        blank=True,
        null=True,
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

    # One composer per song (ForeignKey to Composer)
    composer = models.ForeignKey(
        Composer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='songs',
        help_text="The composer of this song (each song has exactly one composer)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this song was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this song was last updated"
    )

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

    def __str__(self):
        return f"{self.title} ({self.code})" if self.code else self.title

    def save(self, *args, **kwargs):
        """
        Custom save method to handle composer linking.
        """
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
# =============================================

class Prs_data(models.Model):
    """
    Model to store PRS data records.
    Each record links to a Song, which links to a Composer.
    """
    # Basic identifiers
    song = models.ForeignKey(
        Song,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prs_records',
        help_text="The song this PRS record relates to"
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
        Source,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The source of the royalty income"
    )
    source_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
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
        help_text="Whether the source is domestic or foreign"
    )
    foreign_source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the foreign source if applicable"
    )
    royalty_country_code = models.CharField(
        max_length=3,
        blank=True,
        null=True,
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
        IncomeType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The type of income"
    )
    income_type_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
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
        help_text="Amount payable to the composer"
    )

    # Statement information
    statement_id_year = models.CharField(
        max_length=10,
        blank=True,
        null=True,
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
        help_text="Whether this record has been paid"
    )
    payment_date = models.DateField(
        blank=True,
        null=True,
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
        PaymentStatement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prs_records',
        help_text="The payment statement this record is associated with"
    )
    payment_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about the payment"
    )

    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
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
        unique_together = [['song_code', 'income_period', 'source_code', 'income_type_code']]
        indexes = [
            models.Index(fields=['song_title']),
            models.Index(fields=['income_period']),
            models.Index(fields=['is_paid']),
            models.Index(fields=['payment_statement']),
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
        super().save(*args, **kwargs)

    @property
    def composer(self):
        """
        Property to get the composer from the song.
        Returns None if no song or no composer is linked.
        """
        return self.song.composer if self.song else None

    @property
    def composer_name(self):
        """
        Property to get the composer's name.
        Falls back to the legacy artist field if no composer is linked.
        """
        if self.composer:
            return self.composer.full_name
        return self.artist or "Unknown"

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
    """
    Model to track CSV file uploads and prevent duplicates.
    Stores metadata about each uploaded file including its hash for duplicate detection.
    """
    file_name = models.CharField(
        max_length=255,
        help_text="Original name of the uploaded file"
    )
    file_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="MD5 hash of the file content for duplicate detection"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the file was uploaded"
    )
    records_imported = models.IntegerField(
        default=0,
        help_text="Number of records successfully imported from this file"
    )
    status = models.CharField(
        max_length=50,
        default="Success",
        choices=[
            ('Success', 'Success'),
            ('Failed', 'Failed'),
            ('Partial', 'Partial'),
        ],
        help_text="Status of the upload (Success/Failed/Partial)"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if the upload failed"
    )

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
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import hashlib

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

