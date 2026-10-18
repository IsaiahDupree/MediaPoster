#!/bin/bash
# Setup Motion Canvas Project
# Quick setup script for Motion Canvas

set -e

PROJECT_DIR="/Users/isaiahdupree/Documents/Software/MediaPoster/MotionCanvas"

echo "🎨 Setting up Motion Canvas project..."

cd "$PROJECT_DIR"

echo "📦 Installing dependencies..."
npm install

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Start editor: cd MotionCanvas && npm start"
echo "  2. Open http://localhost:9000"
echo "  3. Create animated text: python Backend/scripts/create_animated_text.py --text 'Hello'"
echo ""

