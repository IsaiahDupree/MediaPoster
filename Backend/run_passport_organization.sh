#!/bin/bash
# Simple wrapper to run Passport organization

echo "=========================================="
echo "📁 Passport Drive Organization"
echo "=========================================="
echo ""

# Check if drive is mounted
if [ ! -d "/Volumes/My Passport" ]; then
    echo "❌ Drive not found at /Volumes/My Passport"
    echo "   Attempting to mount..."
    diskutil mount "My Passport" 2>&1
    sleep 2
fi

# Check again
if [ ! -d "/Volumes/My Passport" ]; then
    echo "❌ Drive still not found. Please connect/mount the drive first."
    exit 1
fi

echo "✅ Drive found: /Volumes/My Passport"
echo ""
echo "🚀 Starting organization..."
echo ""

# Run the script
cd "$(dirname "$0")"
python3 scripts/organize_passport_comprehensive.py \
    --passport "/Volumes/My Passport" \
    --output "passport_organization_docs" \
    --max-depth 3

echo ""
echo "=========================================="
echo "✅ Organization Complete!"
echo "=========================================="
echo ""
echo "📁 Documentation saved to: passport_organization_docs/"
echo "📝 Log file: /tmp/mediaposter/logs/passport_organization.log"
echo ""

