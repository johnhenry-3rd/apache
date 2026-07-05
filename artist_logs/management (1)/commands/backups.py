# 1. Navigate to your project directory
cd /home/mypiwh/apache/

# 2. Create a backups directory
mkdir -p backups

# 3. Copy the database file with a timestamp
cp db.sqlite3 backups/db_$(date +%Y%m%d_%H%M%S).sqlite3

# 4. Verify the backup
ls -lh backups/