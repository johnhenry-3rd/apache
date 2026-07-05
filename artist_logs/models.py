# artist_logs/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Prs_data(models.Model):
    # Foreign keys (all nullable)
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True)
    payee = models.ForeignKey('Payee', on_delete=models.SET_NULL, null=True, blank=True)
    track = models.ForeignKey('Track', on_delete=models.SET_NULL, null=True, blank=True)

    # ManyToMany for composers
    composers = models.ManyToManyField('Artist', related_name='compositions', blank=True)

    # Original fields (keep all existing fields)
    Client_Code = models.CharField(max_length=50, blank=True, null=True)
    Client_Name = models.CharField(max_length=255, blank=True, null=True)
    Payee_Code = models.CharField(max_length=50, blank=True, null=True)
    Payee_Name = models.CharField(max_length=255, blank=True, null=True)  # <-- Fixed: Now nullable

    # Song information
    Song_Code = models.CharField(max_length=100, blank=True, null=True)
    Song_Title = models.CharField(max_length=255, blank=True, null=True)
    Composers = models.TextField(blank=True, null=True)

    # Source information
    Source_Code = models.CharField(max_length=100, blank=True, null=True)
    Source_Name = models.CharField(max_length=255, blank=True, null=True)

    # Income information
    Income_Type = models.CharField(max_length=100, blank=True, null=True)
    Income_Type_Name = models.CharField(max_length=255, blank=True, null=True)
    Main_Income_Type_Name = models.CharField(max_length=255, blank=True, null=True)
    Catalogue_No = models.CharField(max_length=100, blank=True, null=True)
    Income_Period = models.CharField(max_length=50, blank=True, null=True)

    # Numeric fields with defaults (nullable)
    Units = models.IntegerField(null=True, blank=True, default=0)

    Percentage_Collected_by_BMG = models.FloatField(
        null=True,
        blank=True,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    Amount_Collected = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00')
    )

    Royalty_Payout_Percentage = models.FloatField(
        null=True,
        blank=True,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    Royalty_Payable = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal('0.00')
    )

    # Statement information
    Statement_ID_Year = models.PositiveIntegerField(null=True, blank=True, default=0)
    Statement_ID_Number = models.PositiveIntegerField(null=True, blank=True, default=0)

    # Geographic information
    Domestic_Or_Foreign_Source_Indicator = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('Domestic', 'Domestic'),
            ('Foreign', 'Foreign'),
            ('Unknown', 'Unknown')
        ]
    )
    Foreign_Source = models.CharField(max_length=255, blank=True, null=True)
    Royalty_Country_Code = models.CharField(max_length=10, blank=True, null=True)
    Royalty_Country_Description = models.CharField(max_length=255, blank=True, null=True)

    # Artist and work information
    Artist = models.CharField(max_length=255, blank=True, null=True)
    ISRC = models.CharField(max_length=12, blank=True, null=True)
    Album_Or_Production = models.CharField(max_length=255, blank=True, null=True)
    Episode = models.CharField(max_length=255, blank=True, null=True)

    # License and source information
    Licence_Number = models.CharField(max_length=100, blank=True, null=True)
    Original_Source_As_Received = models.CharField(max_length=255, blank=True, null=True)
    Original_Source = models.CharField(max_length=255, blank=True, null=True)

    # Timestamps (nullable)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "PRS Data"
        verbose_name_plural = "PRS Data Records"
        # No constraints - allowing duplicates as per your requirement
        indexes = [
            models.Index(fields=['Client_Code']),
            models.Index(fields=['Song_Code']),
            models.Index(fields=['Income_Period']),
            models.Index(fields=['ISRC']),
        ]

    def __str__(self):
        return f"{self.Song_Title or 'Untitled'} - {self.Artist or 'Unknown'} ({self.Income_Period or 'No Period'})"

    def clean(self):
        """Additional validation"""
        if self.Percentage_Collected_by_BMG < 0 or self.Percentage_Collected_by_BMG > 100:
            raise ValidationError({'Percentage_Collected_by_BMG': 'Must be between 0 and 100'})

        if self.Royalty_Payout_Percentage < 0 or self.Royalty_Payout_Percentage > 100:
            raise ValidationError({'Royalty_Payout_Percentage': 'Must be between 0 and 100'})

        if self.Amount_Collected < 0 or self.Royalty_Payable < 0:
            raise ValidationError({'Amount_Collected': 'Monetary values cannot be negative'})


class Artist(models.Model):
    name = models.CharField(max_length=255, default="Unknown Artist")  # Add default
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    earnings_to_date =models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vat_reg = models.CharField(max_length=1, default="N")
    
    def __str__(self):
        return self.name


class Track(models.Model):
    title = models.CharField(max_length=255)
    isrc = models.CharField(max_length=12, blank=True, null=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.title
    

class ImportedFile(models.Model):
    file_name = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, unique=True)  # MD5 hash of the file
    imported_at = models.DateTimeField(auto_now_add=True)
    record_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Imported File"
        verbose_name_plural = "Imported Files"

    def __str__(self):
        return f"{self.file_name} ({self.imported_at})"
    

class ImportLog(models.Model):
    file_path = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=32, unique=True)  # MD5 hash
    imported_at = models.DateTimeField(auto_now_add=True)
    records_imported = models.IntegerField()
    file_name = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Import Log"
        verbose_name_plural = "Import Logs"

    def __str__(self):
        return f"{self.file_name} ({self.imported_at})"
    
class Client(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.name}"
    
class Payee(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.name}"

