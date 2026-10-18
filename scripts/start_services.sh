#!/bin/bash
# Start MediaPoster Services
# This script starts Supabase and provides instructions for starting the backend

set -e

echo "🚀 Starting MediaPoster Services"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found. Install with: brew install supabase/tap/supabase"
    exit 1
fi

# Start Supabase
echo "📦 Starting Supabase Database..."
cd "$(dirname "$0")/../supabase" || exit 1

if supabase status &> /dev/null && supabase status | grep -q "API URL"; then
    echo -e "${GREEN}✅ Supabase already running${NC}"
    supabase status
else
    echo "🔄 Starting Supabase (this may take a minute)..."
    supabase start
fi

echo ""
echo -e "${GREEN}✅ Supabase is running!${NC}"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Start Backend (in a new terminal):"
echo "   cd Backend"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --port 5555 --reload"
echo ""
echo "2. Start Frontend (optional, in another terminal):"
echo "   cd dashboard"
echo "   npm run dev"
echo ""
echo "3. Test iOS Import:"
echo "   curl -X POST http://localhost:5555/api/import/ios/scan \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"path\": \"~/Documents/IphoneImport\", \"filters\": {\"skip_duplicates\": true}}'"
echo ""
echo "4. Find Duplicates:"
echo "   curl http://localhost:5555/api/ai-curation/duplicates?threshold=0.9"
echo ""
echo "🔗 URLs:"
echo "   • Backend API: http://localhost:5555"
echo "   • API Docs: http://localhost:5555/docs"
echo "   • Supabase Studio: http://localhost:54323"
echo ""

