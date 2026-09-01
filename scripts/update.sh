#!/bin/bash
set -e

echo "🔄 Updating Yandex Cloud Resources Watcher Bot..."
echo ""

# 1. Backup current state
echo "💾 Creating backup..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

if [ -d "data" ]; then
    cp -r data $BACKUP_DIR/
    echo "✅ Backed up data directory to $BACKUP_DIR"
fi

if [ -f "config/config.yaml" ]; then
    cp config/config.yaml $BACKUP_DIR/
    echo "✅ Backed up config/config.yaml"
fi

echo ""

# 2. Pull latest changes
echo "📥 Pulling latest changes..."
if [ -d ".git" ]; then
    git pull origin main
    echo "✅ Latest changes pulled"
else
    echo "⚠️  Not a git repository, skipping pull"
fi

echo ""

# 3. Rebuild Docker image
echo "🔨 Rebuilding Docker image..."
docker-compose -f docker/docker-compose.yml build
echo "✅ Docker image rebuilt"
echo ""

# 4. Restart bot
echo "🚀 Restarting bot..."
docker-compose -f docker/docker-compose.yml up -d
echo "✅ Bot restarted"
echo ""

# 5. Verify
echo "🔍 Verifying..."
sleep 5
docker-compose -f docker/docker-compose.yml ps

echo ""
echo "✅ Update complete!"
echo ""
echo "📜 View logs with: docker-compose -f docker/docker-compose.yml logs -f"
echo ""
echo "If you need to rollback:"
echo "1. Stop bot: docker-compose -f docker/docker-compose.yml down"
echo "2. Restore data: cp -r $BACKUP_DIR/data data"
echo "3. Start bot: docker-compose -f docker/docker-compose.yml up -d"
