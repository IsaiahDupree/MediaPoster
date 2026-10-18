#!/usr/bin/env python3
"""Analyze feature list status"""
import json

with open('feature_list.json') as f:
    data = json.load(f)

features = data['features']
total = len(features)
passing = sum(1 for f in features if f.get('passes', False))

print(f'Total Features: {total}')
print(f'Passing: {passing} ({passing/total*100:.1f}%)')
print(f'Remaining: {total - passing}')
print()

# Phase breakdown
print('Phase Breakdown:')
phases = {}
for f in features:
    p = f.get('phase', 0)
    if p not in phases:
        phases[p] = {'total': 0, 'passing': 0, 'features': []}
    phases[p]['total'] += 1
    if f.get('passes', False):
        phases[p]['passing'] += 1
    else:
        phases[p]['features'].append(f['id'])

for p in sorted(phases.keys()):
    print(f'  Phase {p}: {phases[p]["passing"]}/{phases[p]["total"]} passing ({phases[p]["passing"]/phases[p]["total"]*100:.1f}%)')

print()
print('Not Passing by Phase:')
for p in sorted(phases.keys()):
    if phases[p]['features']:
        print(f'  Phase {p}: {", ".join(phases[p]["features"][:10])}{"..." if len(phases[p]["features"]) > 10 else ""}')
