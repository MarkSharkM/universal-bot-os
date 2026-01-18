#!/bin/bash
# Database Restore Script for Universal Bot OS
# Usage: ./scripts/restore_database.sh <backup_file>
# WARNING: This will OVERWRITE existing data!

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check arguments
if [ -z "$1" ]; then
    echo -e "${RED}❌ ERROR: No backup file specified${NC}"
    echo ""
    echo "Usage: ./scripts/restore_database.sh <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh backups/database/*.sql.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    echo ""
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ ERROR: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ ERROR: DATABASE_URL environment variable not set${NC}"
    exit 1
fi

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ ERROR: psql not found${NC}"
    echo "Install PostgreSQL client first"
    exit 1
fi

echo -e "${YELLOW}⚠️  WARNING: This will OVERWRITE all data in the database!${NC}"
echo ""
echo "Database: $(echo $DATABASE_URL | sed 's/:.*/.../')"
echo "Backup file: $BACKUP_FILE"
echo ""
echo -e "${BLUE}Press Enter to continue, or Ctrl+C to cancel...${NC}"
read

# Decompress if needed
SQL_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "🗜️  Decompressing backup..."
    SQL_FILE="${BACKUP_FILE%.gz}"
    gunzip -c "$BACKUP_FILE" > "$SQL_FILE"
    TEMP_FILE=true
fi

echo "📥 Restoring database..."
if psql "$DATABASE_URL" < "$SQL_FILE"; then
    echo -e "${GREEN}✅ Database restored successfully!${NC}"
else
    echo -e "${RED}❌ Restore failed!${NC}"
    [ "$TEMP_FILE" = true ] && rm -f "$SQL_FILE"
    exit 1
fi

# Cleanup temp file
[ "$TEMP_FILE" = true ] && rm -f "$SQL_FILE"

# Verify restoration
echo ""
echo "🔍 Verifying restoration..."
psql "$DATABASE_URL" -c "SELECT 'Bots: ' || COUNT(*)::text FROM bots;"
psql "$DATABASE_URL" -c "SELECT 'Users: ' || COUNT(*)::text FROM users;"
psql "$DATABASE_URL" -c "SELECT 'Messages: ' || COUNT(*)::text FROM messages;"

echo ""
echo -e "${GREEN}✅ Restoration complete and verified!${NC}"
