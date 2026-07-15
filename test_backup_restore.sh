#!/bin/bash

# Set variables
BACKUP_DIR="/home/john/Apache/apache_db/backups"
DB_NAME="apache_db"
TEST_DB_NAME="test_restore_db_$$"  # Unique name with process ID
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/test_backup_$TIMESTAMP.sql"

# Create backups directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Step 1: Create backup
echo "Creating backup of $DB_NAME..."
sudo -u postgres pg_dump "$DB_NAME" > "$BACKUP_FILE"
if [ $? -ne 0 ]; then
    echo "❌ Backup failed!"
    exit 1
fi
echo "✅ Backup created: $BACKUP_FILE"

# Step 2: Create test database
echo "Creating test database $TEST_DB_NAME..."
sudo -u postgres createdb "$TEST_DB_NAME"
if [ $? -ne 0 ]; then
    echo "❌ Failed to create test database!"
    exit 1
fi

# Step 3: Restore to test database
echo "Restoring backup to $TEST_DB_NAME..."
sudo -u postgres psql "$TEST_DB_NAME" < "$BACKUP_FILE"
if [ $? -ne 0 ]; then
    echo "❌ Restore failed!"
    sudo -u postgres dropdb "$TEST_DB_NAME"
    exit 1
fi
echo "✅ Restore successful!"

# Step 4: Verify the restore
echo "Verifying restored database..."
TABLE_COUNT=$(sudo -u postgres psql -d "$TEST_DB_NAME" -t -c "\dt" | wc -l)
if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "✅ Found $TABLE_COUNT tables in restored database"
else
    echo "❌ No tables found in restored database!"
    sudo -u postgres dropdb "$TEST_DB_NAME"
    exit 1
fi

# Step 5: Clean up
echo "Cleaning up test database..."
sudo -u postgres dropdb "$TEST_DB_NAME"
echo "✅ Test completed successfully!"

# Optional: Remove the test backup file
# rm "$BACKUP_FILE"