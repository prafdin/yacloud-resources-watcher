#!/bin/bash
set -e

echo "🚀 Installing Yandex Cloud Resources Watcher Bot..."
echo ""

# 1. Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# 2. Create directories
echo "📁 Creating directories..."
mkdir -p config
echo "✅ Directories created"
echo ""

# 3. Generate config files
echo "⚙️  Generating configuration files..."

if [ ! -f config/config.yaml ]; then
    cp config.yaml.example config/config.yaml
    echo "✅ Created config/config.yaml"
else
    echo "⚠️  config/config.yaml already exists, skipping"
fi

if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env"
else
    echo "⚠️  .env already exists, skipping"
fi

echo ""

# 4. Prompt for configuration
echo "📝 Configuration Required:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Edit .env and set:"
echo "   - TELEGRAM_BOT_TOKEN (get from @BotFather)"
echo ""
echo "2. Edit config/config.yaml and set:"
echo "   - telegram.allowed_user_id (your Telegram user ID)"
echo "   - yandex_cloud.folder_id (from YC console)"
echo "   - yandex_cloud.cloud_id (from YC console)"
echo "   - scheduler.timezone (if different from Europe/Moscow)"
echo ""
echo "3. Create Service Account in Yandex Cloud:"
echo "   yc iam service-account create --name bot-watcher"
echo ""
echo "4. Assign viewer role:"
echo "   FOLDER_ID=\$(yc config get folder-id)"
echo "   SA_ID=\$(yc iam service-account get --name bot-watcher --format json | jq -r .id)"
echo "   yc resource-manager folder add-access-binding \$FOLDER_ID --role viewer --subject serviceAccount:\$SA_ID"
echo ""
echo "5. Create authorized key:"
echo "   yc iam key create --service-account-name bot-watcher --output config/sa-key.json"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 5. Build and start
read -p "Ready to build and start the bot? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔨 Building Docker image..."
    docker compose -f docker/docker-compose.yml build
    
    echo ""
    echo "🚀 Starting bot..."
    docker compose -f docker/docker-compose.yml up -d
    
    echo ""
    echo "✅ Bot started successfully!"
    echo ""
    echo "📊 Check status with: docker compose -f docker/docker-compose.yml ps"
    echo "📜 View logs with: docker compose -f docker/docker-compose.yml logs -f"
else
    echo ""
    echo "⚠️  Bot not started. To start manually:"
    echo "   docker compose -f docker/docker-compose.yml up -d"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "1. Configure .env and config/config.yaml"
echo "2. Place SA key at config/sa-key.json"
echo "3. Start bot: docker compose -f docker/docker-compose.yml up -d"
echo "4. Message your bot in Telegram: /start"
