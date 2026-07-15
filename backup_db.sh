#!/bin/bash

# Database backup script
BACKUP_DIR="/home/john/Apache/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/apache_db_$DATE.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Dump the database
pg_dump -U apache_user -h localhost apache_db > "$BACKUP_FILE"

# Compress the backup
gzip "$BACKUP_FILE"

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "apache_db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"