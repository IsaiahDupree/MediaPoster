"""
Update Experiment Features in feature_list.json
"""
import json
from pathlib import Path
from datetime import datetime

# Feature IDs to mark as complete
COMPLETED_FEATURES = [
    "EXP-001",  # Experiment Agent
    "EXP-002",  # Hypothesis Framework
    "EXP-003",  # Content Experiment Tagging
    "EXP-004",  # Winner Detection & Promotion
    "EXP-005",  # A/B Test Variants
]

# Load feature_list.json
feature_list_path = Path(__file__).parent.parent / "feature_list.json"

with open(feature_list_path, 'r') as f:
    data = json.load(f)

# Update features
today = datetime.now().strftime("%Y-%m-%d")
updated_count = 0

for feature in data['features']:
    if feature['id'] in COMPLETED_FEATURES:
        if not feature.get('passes', False):
            feature['passes'] = True
            feature['completed'] = today
            updated_count += 1
            print(f"✓ Marked {feature['id']} as complete: {feature['name']}")

# Update stats
total = data['totalFeatures']
passing = sum(1 for f in data['features'] if f.get('passes', False))
data['completedFeatures'] = passing

print(f"\nUpdated {updated_count} features")
print(f"Total passing: {passing}/{total} ({passing/total*100:.1f}%)")

# Save
with open(feature_list_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"✅ Saved to {feature_list_path}")
