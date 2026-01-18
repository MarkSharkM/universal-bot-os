#!/bin/bash
# Database Backup Script for Universal Bot OS
# Usage: ./scripts/backup_database.sh
# Requires: postgresql-client, DATABASE_URL environment variable

set -e

# Configuration
BACKUP_DIR="./backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="universal_bot_os_backup_${DATE}.sql"
MAX_BACKUPS=10  # Keep last 10 backups

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ ERROR: DATABASE_URL environment variable not set${NC}"
    echo ""
    echo "To set DATABASE_URL:"
    echo "  1. Get from Railway Dashboard → Database → Connect → DATABASE_URL"
    echo "  2. Run: export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    echo ""
    exit 1
fi

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    echo -e "${RED}❌ ERROR: pg_dump not found${NC}"
    echo ""
    echo "Install PostgreSQL client:"
    echo "  macOS: brew install postgresql"
    echo "  Ubuntu: sudo apt-get install postgresql-client"
    echo ""
    exit 1
fi

echo -e "${GREEN}📦 Starting database backup...${NC}"
echo "Backup file: $BACKUP_DIR/$BACKUP_FILE"
echo ""

# Perform backup using pg_dump
echo "⏳ Dumping database..."
if pg_dump "$DATABASE_URL" > "$BACKUP_DIR/$BACKUP_FILE"; then
    echo -e "${GREEN}✅ Database dump complete${NC}"
else
    echo -e "${RED}❌ Backup failed!${NC}"
    rm -f "$BACKUP_DIR/$BACKUP_FILE"  # Remove failed backup
    exit 1
fi

# Compress backup
echo "🗜️  Compressing backup..."
gzip "$BACKUP_DIR/$BACKUP_FILE"

COMPRESSED_FILE="${BACKUP_FILE}.gz"
FILE_SIZE=$(du -h "$BACKUP_DIR/$COMPRESSED_FILE" | cut -f1)

# Cleanup old backups (keep last MAX_BACKUPS)
echo "🧹 Cleaning up old backups (keeping last $MAX_BACKUPS)..."
cd "$BACKUP_DIR"
ls -t *.sql.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f 2>/dev/null || true
cd - > /dev/null

BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo -e "${GREEN}✅ Backup complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "📁 File: ${YELLOW}$BACKUP_DIR/$COMPRESSED_FILE${NC}"
echo -e "📊 Size: ${YELLOW}$FILE_SIZE${NC}"
echo -e "📦 Total backups: ${YELLOW}$BACKUP_COUNT${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 To restore this backup:"
echo "   gunzip $BACKUP_DIR/$COMPRESSED_FILE"
echo "   psql \$DATABASE_URL < $BACKUP_DIR/$BACKUP_FILE"
echo ""
