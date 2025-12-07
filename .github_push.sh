#!/bin/bash
# Safe GitHub Push Script
# This script helps push to GitHub while ensuring secrets are protected

set -e

echo "🔒 Checking for sensitive files..."

# Check if sensitive files would be committed
SENSITIVE_FILES=(
    "client_secret*.json"
    "Backend/automation/sessions/*.json"
    "Backend/automation/tiktok_cookies.json"
    "Backend/automation/tiktok_session.json"
    ".env"
)

FOUND_SENSITIVE=false

for pattern in "${SENSITIVE_FILES[@]}"; do
    if git ls-files | grep -q "$pattern"; then
        echo "❌ WARNING: Sensitive file found in staging: $pattern"
        FOUND_SENSITIVE=true
    fi
done

if [ "$FOUND_SENSITIVE" = true ]; then
    echo ""
    echo "⚠️  STOP! Sensitive files detected in staging area!"
    echo "Please remove them from .gitignore or unstage them:"
    echo "  git rm --cached <file>"
    exit 1
fi

echo "✅ No sensitive files detected"
echo ""

# Check if remote is set
if ! git remote get-url origin &>/dev/null; then
    echo "📝 Setting up GitHub remote..."
    echo "Please enter your GitHub repository URL:"
    read -r REPO_URL
    git remote add origin "$REPO_URL"
fi

# Show what will be committed
echo "📋 Files to be committed:"
git status --short | head -20
echo ""

# Ask for confirmation
read -p "Continue with commit and push? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# Create initial commit if needed
if [ -z "$(git log --oneline -1 2>/dev/null)" ]; then
    echo "📝 Creating initial commit..."
    git commit -m "Initial commit: MediaPoster automation system

- TikTok engagement automation with Safari Web Extension
- Video ingestion and analysis pipeline
- Multi-platform social media automation
- AI-powered content analysis and highlight detection"
fi

# Push to GitHub
echo "🚀 Pushing to GitHub..."
BRANCH=$(git branch --show-current)
git push -u origin "$BRANCH"

echo ""
echo "✅ Successfully pushed to GitHub!"
echo "🔒 Remember: Never commit secrets, API keys, or session data!"

