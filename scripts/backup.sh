#!/bin/bash

# AI Library Backup Script
# Backs up vector database, metadata database, and configuration

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATA_DIR="${DATA_DIR:-./data}"
MAX_BACKUPS="${MAX_BACKUPS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ai_library_backup_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AI Library backup...${NC}"
echo "Timestamp: ${TIMESTAMP}"

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Backup metadata database
echo -e "${YELLOW}Backing up metadata database...${NC}"
if [ -f "${DATA_DIR}/books_metadata.db" ]; then
    cp "${DATA_DIR}/books_metadata.db" "${BACKUP_DIR}/${BACKUP_NAME}/"
    echo "  ✓ Metadata database backed up"
else
    echo -e "${RED}  ✗ Metadata database not found${NC}"
fi

# Backup vector database
echo -e "${YELLOW}Backing up vector database...${NC}"
if [ -f "${DATA_DIR}/books_index.index" ]; then
    cp "${DATA_DIR}/books_index.index" "${BACKUP_DIR}/${BACKUP_NAME}/"
    cp "${DATA_DIR}/books_index.meta" "${BACKUP_DIR}/${BACKUP_NAME}/"
    echo "  ✓ Vector database backed up"
else
    echo -e "${RED}  ✗ Vector database not found${NC}"
fi

# Backup conversation history
echo -e "${YELLOW}Backing up conversation history...${NC}"
if [ -f "${DATA_DIR}/conversation_history.db" ]; then
    cp "${DATA_DIR}/conversation_history.db" "${BACKUP_DIR}/${BACKUP_NAME}/"
    echo "  ✓ Conversation history backed up"
fi

# Backup bookmarks
if [ -f "${DATA_DIR}/bookmarks.db" ]; then
    cp "${DATA_DIR}/bookmarks.db" "${BACKUP_DIR}/${BACKUP_NAME}/"
    echo "  ✓ Bookmarks backed up"
fi

# Backup configuration
echo -e "${YELLOW}Backing up configuration...${NC}"
if [ -f "config.yaml" ]; then
    cp "config.yaml" "${BACKUP_DIR}/${BACKUP_NAME}/"
    echo "  ✓ Configuration backed up"
fi

# Create backup manifest
cat > "${BACKUP_DIR}/${BACKUP_NAME}/MANIFEST.txt" <<EOF
AI Library Backup
Created: ${TIMESTAMP}
Hostname: $(hostname)
User: $(whoami)

Contents:
- books_metadata.db: Metadata database
- books_index.index: Vector database index
- books_index.meta: Vector database metadata
- conversation_history.db: Conversation history
- bookmarks.db: Bookmarks and reading lists
- config.yaml: System configuration

Restore Instructions:
1. Stop the AI Library service
2. Copy files from this backup to the data directory
3. Restart the AI Library service
EOF

# Compress backup
echo -e "${YELLOW}Compressing backup...${NC}"
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

# Get backup size
BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
echo "  ✓ Backup compressed: ${BACKUP_SIZE}"

# Cleanup old backups
echo -e "${YELLOW}Cleaning up old backups...${NC}"
BACKUP_COUNT=$(ls -1 ai_library_backup_*.tar.gz 2>/dev/null | wc -l)

if [ ${BACKUP_COUNT} -gt ${MAX_BACKUPS} ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - MAX_BACKUPS))
    ls -1t ai_library_backup_*.tar.gz | tail -${REMOVE_COUNT} | xargs rm -f
    echo "  ✓ Removed ${REMOVE_COUNT} old backup(s)"
else
    echo "  ✓ No old backups to remove"
fi

cd - > /dev/null

echo -e "${GREEN}Backup complete!${NC}"
echo "Backup saved to: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Total backups: $(ls -1 ${BACKUP_DIR}/ai_library_backup_*.tar.gz 2>/dev/null | wc -l)/${MAX_BACKUPS}"
