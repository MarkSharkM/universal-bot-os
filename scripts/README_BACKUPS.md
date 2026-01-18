# Database Backup Scripts

Automated backup and restore scripts for Universal Bot OS PostgreSQL database.

## 📦 backup_database.sh

Creates a compressed backup of the production database.

**Features:**
- Automatic compression with gzip
- Timestamps for easy identification  
- Automatic cleanup (keeps last 10 backups)
- Error handling and validation
- Color-coded output

**Usage:**
```bash
# Set DATABASE_URL (get from Railway Dashboard)
export DATABASE_URL="postgresql://user:password@host:port/database"

# Run backup
./scripts/backup_database.sh
```

**Output:**
- Backup location: `backups/database/universal_bot_os_backup_YYYYMMDD_HHMMSS.sql.gz`
- Automatically removes backups older than the last 10

## 📥 restore_database.sh

Restores database from a backup file.

**⚠️ WARNING:** This will OVERWRITE all existing data!

**Features:**
- Safety confirmation before restore
- Automatic decompression
- Post-restore verification
- Record counts verification

**Usage:**
```bash
# Set DATABASE_URL
export DATABASE_URL="postgresql://user:password@host:port/database"

# Restore from backup
./scripts/restore_database.sh backups/database/universal_bot_os_backup_20260118_120000.sql.gz
```

## 🔧 Requirements

**macOS:**
```bash
brew install postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql-client
```

## 📊 Backup Schedule Recommendations

| Frequency | When | Retention |
|-----------|------|-----------|
| **Daily** | Automated via Railway | 7 days |
| **Pre-deploy** | Before major releases | 30 days |
| **Weekly** | Sunday 2 AM | 4 weeks |
| **Monthly** | 1st of month | 12 months |

## 🚨 Disaster Recovery

See [`backup_strategy.md`](../backup_strategy.md) in artifacts for complete DR procedures.

**Quick Recovery:**
1. List available backups: `ls -lh backups/database/`
2. Restore latest: `./scripts/restore_database.sh backups/database/[latest].sql.gz`
3. Verify: Check bot counts in database

## 💡 Best Practices

- ✅ Test restores monthly
- ✅ Store backups in multiple locations
- ✅ Document DATABASE_URL securely
- ✅ Run backup before major deployments
- ❌ Never commit backups to Git
- ❌ Don't store DATABASE_URL in code

## 📞 Support

Issues? Check:
1. DATABASE_URL is set correctly
2. PostgreSQL client is installed
3. Network connectivity to Railway
4. Disk space for backups

---

**Last Updated:** 18 січня 2026
