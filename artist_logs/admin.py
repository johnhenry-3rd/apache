from django.contrib import admin
from django.contrib import admin
from .models import Song
from .models import (
    Prs_data,
    Artist,
    Source,
    IncomeType,
    Song,
    PaymentStatement
)

# Register your models here.
admin.site.register(Prs_data)
admin.site.register(Artist)
admin.site.register(Source)
admin.site.register(IncomeType)
admin.site.register(Song)
admin.site.register(PaymentStatement)