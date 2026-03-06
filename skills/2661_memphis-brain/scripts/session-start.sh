#!/bin/bash
# Session Start Script for Memphis Brain
# Run at the beginning of each agent session

set -e

echo "🔥 Memphis Session Start"
echo "========================"
echo ""

# 1. Health check
echo "📊 Checking health..."
memphis status
echo ""

# 2. Daily reflection
echo "🤔 Running daily reflection..."
memphis reflect --daily
echo ""

# 3. Journal session start
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "📝 Journaling session start..."
memphis journal "Session started at $TIMESTAMP" --tags session,daily
echo ""

# 4. Check for share-sync (if configured)
if [ -f ~/.memphis/config.yaml ] && grep -q "pinata:" ~/.memphis/config.yaml; then
    echo "🌐 Checking for shared blocks..."
    memphis share-sync --pull || echo "Share-sync not configured or failed"
    echo ""
fi

# 5. Show recent activity
echo "📋 Recent journal entries:"
ls -lt ~/.memphis/chains/journal/ 2>/dev/null | head -5 || echo "No journal entries yet"
echo ""

echo "✅ Session initialized"
echo "💡 Remember to journal insights and embed regularly"
