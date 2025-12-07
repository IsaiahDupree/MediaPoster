# Inventory-Aware Scheduler

## Overview

The Inventory-Aware Scheduler automatically schedules content from your resource folder based on available inventory. It maintains consistent posts per day across a fixed horizon (default: 2 months) and adapts dynamically when new content is added.

## Features

✅ **Automatic Scheduling**: Pulls from resource folder (videos/clips) and schedules automatically
✅ **Fixed Horizon**: Looks ahead 1-3 months into the future (configurable)
✅ **Content Type Differentiation**: Separate scheduling for short-form and long-form content
✅ **Consistency Optimization**: Maintains consistent posts per day across the horizon
✅ **Dynamic Adaptation**: Automatically extends schedule when new content is added
✅ **Rate-Based Adjustment**: Increases posts per day when upload rate increases

## How It Works

1. **Inventory Assessment**: Scans available clips (short-form) and videos (long-form)
2. **Optimal Calculation**: Calculates optimal posts per day based on:
   - Available inventory count
   - Target horizon (default: 2 months)
   - Min/max posts per day constraints
3. **Schedule Generation**: Creates schedule with specific posting times
4. **Dynamic Updates**: When new content is added, extends schedule to maintain consistency

## Configuration

### Default Settings

- **Horizon**: 2 months
- **Short-form posts/day**: 1.0 - 3.0 (adaptive)
- **Long-form posts/day**: 0.2 - 1.0 (adaptive)
- **Short-form duration**: ≤ 60 seconds
- **Long-form duration**: ≥ 60 seconds
- **Preferred posting times**: 8am, 12pm, 5pm, 8pm
- **Platforms**: Instagram, TikTok, YouTube Shorts

### Custom Configuration

You can customize the scheduler via API:

```json
{
  "horizon_months": 2,
  "min_posts_per_day_short": 1.0,
  "max_posts_per_day_short": 3.0,
  "min_posts_per_day_long": 0.2,
  "max_posts_per_day_long": 1.0,
  "short_form_duration_max": 60.0,
  "long_form_duration_min": 60.0,
  "preferred_posting_times": [8, 12, 17, 20],
  "platforms": ["instagram", "tiktok", "youtube_shorts"]
}
```

## API Endpoints

### Get Inventory
```
GET /api/scheduler/inventory
```
Returns current available content inventory (short-form and long-form).

### Get Schedule Plan
```
GET /api/scheduler/plan
```
Returns optimal schedule plan based on current inventory (posts per day, total days, etc.).

### Auto Schedule
```
POST /api/scheduler/auto-schedule
Body: {
  "force_reschedule": false,
  "config": { ... }  // Optional custom config
}
```
Automatically schedules content based on inventory.

### Update on New Content
```
POST /api/scheduler/update-on-new-content
```
Called when new content is added to resource folder. Extends schedule if needed.

### Get Status
```
GET /api/scheduler/status
```
Returns current scheduler status, inventory, and plan.

## Usage Examples

### 1. Initial Schedule Setup

```bash
# Get current inventory
curl http://localhost:5555/api/scheduler/inventory

# Get optimal plan
curl http://localhost:5555/api/scheduler/plan

# Create schedule
curl -X POST http://localhost:5555/api/scheduler/auto-schedule \
  -H "Content-Type: application/json" \
  -d '{"force_reschedule": false}'
```

### 2. Custom Configuration

```bash
curl -X POST http://localhost:5555/api/scheduler/auto-schedule \
  -H "Content-Type: application/json" \
  -d '{
    "force_reschedule": false,
    "config": {
      "horizon_months": 3,
      "min_posts_per_day_short": 2.0,
      "max_posts_per_day_short": 4.0,
      "platforms": ["instagram", "tiktok"]
    }
  }'
```

### 3. Update When New Content Added

```bash
# When you upload new videos/clips to resource folder
curl -X POST http://localhost:5555/api/scheduler/update-on-new-content
```

## Resource Folder Monitor

The scheduler can automatically monitor your resource folder for new content:

```python
from services.resource_folder_monitor import ResourceFolderMonitor
from services.inventory_aware_scheduler import InventoryAwareScheduler

async def on_new_content(file_path: Path):
    """Called when new content is detected"""
    scheduler = InventoryAwareScheduler()
    await scheduler.update_schedule_on_new_content()

# Start monitoring
monitor = ResourceFolderMonitor(
    resource_folder=Path("/path/to/resource/folder"),
    on_new_content=on_new_content
)
monitor.start()
```

## Algorithm Details

### Posts Per Day Calculation

```
posts_per_day = available_inventory / horizon_days
posts_per_day = clamp(posts_per_day, min_posts_per_day, max_posts_per_day)
```

### Horizon Extension

If inventory exceeds what can be scheduled in default horizon:
- Calculate extended days needed: `extended_days = inventory / posts_per_day`
- If `extended_days <= horizon * 2`, extend schedule
- Otherwise, use max posts per day

### Time Distribution

Posts are distributed across preferred posting times:
- Rotates through preferred hours each day
- Long-form: Prefers morning/afternoon (10am, 2pm, 4pm)
- Short-form: Uses configured preferred times

## Integration with Publishing Queue

The scheduler creates `ScheduledPost` records that integrate with the existing publishing queue system. Posts are automatically published at their scheduled times by the publishing service.

## Status Tracking

Check scheduler status:

```bash
curl http://localhost:5555/api/scheduler/status
```

Returns:
- Current inventory counts
- Optimal plan details
- Number of scheduled posts
- Configuration settings

## Next Steps

1. ✅ Core scheduler service - **COMPLETE**
2. ✅ API endpoints - **COMPLETE**
3. ⏳ Resource folder monitor integration
4. ⏳ Frontend UI for scheduler management
5. ⏳ Background task for automatic monitoring
6. ⏳ Analytics and reporting






