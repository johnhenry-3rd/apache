# apache_db/settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'artist_logs',  # Add this line
]

BACKUP_DIR = os.path.join(BASE_DIR, 'backups')