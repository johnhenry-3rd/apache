# In /home/mypiwh/apache/art_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('prs/', include('artist_logs.urls', namespace='artist_logs')),
    path('', RedirectView.as_view(url='/prs/')),  # Redirect root to /prs/
]