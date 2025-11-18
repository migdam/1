#!/bin/bash

# AI Library Restore Script
# Restores from a backup archive

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Backup file required${NC}"
    echo "Usage: $0 <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -1t ./backups/ai_library_backup_*.tar.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
DATA_DIR="${DATA_DIR:-./data}"
TEMP_DIR=$(mktemp -d)

# Verify backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}Error: Backup file not found: ${BACKUP_FILE}${NC}"
    exit 1
fi

echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║          AI Library Restore Utility                          ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Backup file: ${BACKUP_FILE}"
echo "Target directory: ${DATA_DIR}"
echo ""
echo -e "${RED}WARNING: This will overwrite existing data!${NC}"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Extract backup
echo -e "${YELLOW}Extracting backup...${NC}"
tar -xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"

# Find backup directory
BACKUP_DIR=$(ls -1d ${TEMP_DIR}/ai_library_backup_* 2>/dev/null | head -1)

if [ -z "${BACKUP_DIR}" ]; then
    echo -e "${RED}Error: Invalid backup archive${NC}"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

# Show manifest
if [ -f "${BACKUP_DIR}/MANIFEST.txt" ]; then
    echo ""
    echo -e "${GREEN}Backup Manifest:${NC}"
    cat "${BACKUP_DIR}/MANIFEST.txt"
    echo ""
fi

# Create backup of current data
echo -e "${YELLOW}Creating safety backup of current data...${NC}"
SAFETY_BACKUP="./backups/pre_restore_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
mkdir -p ./backups
tar -czf "${SAFETY_BACKUP}" "${DATA_DIR}" 2>/dev/null || true
echo "  ✓ Safety backup created: ${SAFETY_BACKUP}"

# Restore files
echo -e "${YELLOW}Restoring files...${NC}"

# Metadata database
if [ -f "${BACKUP_DIR}/books_metadata.db" ]; then
    cp "${BACKUP_DIR}/books_metadata.db" "${DATA_DIR}/"
    echo "  ✓ Restored metadata database"
fi

# Vector database
if [ -f "${BACKUP_DIR}/books_index.index" ]; then
    cp "${BACKUP_DIR}/books_index.index" "${DATA_DIR}/"
    cp "${BACKUP_DIR}/books_index.meta" "${DATA_DIR}/"
    echo "  ✓ Restored vector database"
fi

# Conversation history
if [ -f "${BACKUP_DIR}/conversation_history.db" ]; then
    cp "${BACKUP_DIR}/conversation_history.db" "${DATA_DIR}/"
    echo "  ✓ Restored conversation history"
fi

# Bookmarks
if [ -f "${BACKUP_DIR}/bookmarks.db" ]; then
    cp "${BACKUP_DIR}/bookmarks.db" "${DATA_DIR}/"
    echo "  ✓ Restored bookmarks"
fi

# Configuration
if [ -f "${BACKUP_DIR}/config.yaml" ]; then
    read -p "Restore configuration? (yes/no): " restore_config
    if [ "$restore_config" = "yes" ]; then
        cp "${BACKUP_DIR}/config.yaml" ./
        echo "  ✓ Restored configuration"
    fi
fi

# Cleanup
rm -rf "${TEMP_DIR}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Restore Complete!                               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Restored from: ${BACKUP_FILE}"
echo "Safety backup: ${SAFETY_BACKUP}"
echo ""
echo -e "${YELLOW}Please restart the AI Library service for changes to take effect${NC}"
