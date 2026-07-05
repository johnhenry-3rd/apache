from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('artist_logs.urls')),  # Include artist_logs URLs
]