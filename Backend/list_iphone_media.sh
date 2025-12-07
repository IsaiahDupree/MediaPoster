#!/bin/bash
# List media on connected iPhone using idevice tools

echo "==================================="
echo "iPhone Media Lister"
echo "==================================="

# Check device
UDID=$(idevice_id -l)
if [ -z "$UDID" ]; then
    echo "✗ No iPhone detected"
    exit 1
fi

echo "✓ Device: $UDID"

# Get device name
NAME=$(ideviceinfo -k DeviceName 2>/dev/null)
echo "✓ Name: $NAME"

# Get iOS version
VERSION=$(ideviceinfo -k ProductVersion 2>/dev/null)
echo "✓ iOS: $VERSION"

# Note: Direct file access requires additional tools
echo ""
echo "⚠️ Note: macOS doesn't support ifuse (Linux only)"
echo ""
echo "Available methods:"
echo "  1. Use Image Capture app (GUI)"
echo "  2. Use Photos app import"
echo "  3. Use AirDrop"
echo ""
echo "Programmatic options:"
echo "  • AppleScript automation of Image Capture"
echo "  • Python PIL/ImageCaptureCore framework"
echo "  • Network-based transfer (WiFi sync)"
