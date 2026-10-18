#!/bin/bash
# Apply all migrations to local Supabase instance
# Usage: ./apply_all_migrations.sh [DATABASE_URL]

set -e  # Exit on error

# Get database URL from argument or environment variable
DATABASE_URL="${1:-${DATABASE_URL}}"

if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL not provided"
    echo "Usage: ./apply_all_migrations.sh [DATABASE_URL]"
    echo "Or set DATABASE_URL environment variable"
    exit 1
fi

echo "🚀 Applying all migrations to local Supabase..."
echo "Database: $DATABASE_URL"
echo ""

# Migration order (respecting dependencies)
MIGRATIONS=(
    "000_content_base_tables.sql"
    "001_people_graph.sql"
    "002_content_graph_extensions.sql"
    "003_connectors.sql"
    "003_base_video_tables.sql"
    "004_content_intelligence_video_analysis.sql"
    "005_content_intelligence_platform_tracking.sql"
    "006_content_intelligence_insights_metrics.sql"
    "008_video_library.sql"
    "009_fix_video_library_fk.sql"
    "009_video_thumbnails.sql"
    "005_video_clips.sql"
    "006_segment_editing.sql"
    "007_publishing_queue.sql"
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUCCESS_COUNT=0
FAILED_COUNT=0
FAILED_MIGRATIONS=()

for migration in "${MIGRATIONS[@]}"; do
    migration_path="$SCRIPT_DIR/$migration"
    
    if [ ! -f "$migration_path" ]; then
        echo "⚠️  Skipping $migration (file not found)"
        continue
    fi
    
    echo "📄 Applying $migration..."
    
    if psql "$DATABASE_URL" -f "$migration_path" > /dev/null 2>&1; then
        echo "✅ $migration applied successfully"
        ((SUCCESS_COUNT++))
    else
        echo "❌ Failed to apply $migration"
        ((FAILED_COUNT++))
        FAILED_MIGRATIONS+=("$migration")
    fi
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Migration Summary:"
echo "   ✅ Successful: $SUCCESS_COUNT"
echo "   ❌ Failed: $FAILED_COUNT"

if [ $FAILED_COUNT -gt 0 ]; then
    echo ""
    echo "Failed migrations:"
    for failed in "${FAILED_MIGRATIONS[@]}"; do
        echo "   - $failed"
    done
    exit 1
else
    echo ""
    echo "🎉 All migrations applied successfully!"
    exit 0
fi


