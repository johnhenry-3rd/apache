from django.contrib import admin

from .models import Artist
from .models import Track
from .models import Prs_data

admin.site.register(Track)

@admin.register(Prs_data)
class Prs_dataAdmin(admin.ModelAdmin):
    list_display=['Composers','Song_Title','Source_Name','Income_Type_Name','Main_Income_Type_Name','Royalty_Payable']
    list_filter=['Composers','Song_Title','Source_Name','Income_Type_Name','Main_Income_Type_Name']
    search_fields=['Composers','Song_Title']
    ordering = ['Composers','Song_Title']
    show_facets=admin.ShowFacets.ALWAYS

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display=['name','first_name','last_name','earnings_to_date','vat_reg']
    list_filter=['name','first_name','last_name']
    search_fields=['name','first_name','last_name']
    ordering = ['name']
    show_facets=admin.ShowFacets.ALWAYS
