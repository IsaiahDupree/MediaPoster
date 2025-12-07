#!/bin/bash
# Quick test script for FYP engagement

echo "🚀 Testing FYP Engagement Script"
echo "================================"
echo ""
echo "This will:"
echo "  1. Navigate to TikTok FYP"
echo "  2. Like and comment on 3 videos"
echo "  3. Show results"
echo ""
echo "Make sure:"
echo "  - Safari is open (or will be opened)"
echo "  - You're logged into TikTok"
echo "  - Safari extension is installed (optional but recommended)"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

cd "$(dirname "$0")"
python3 run_fyp_engagement.py -n 3 -c "Great video! 🔥"

echo ""
echo "✅ Test complete!"

