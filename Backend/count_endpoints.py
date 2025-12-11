
import os
import re

def count_endpoints(root_dir):
    endpoint_pattern = re.compile(r'@(app|router)\.(get|post|put|delete|patch|options|head)\(')
    categories = {}
    total_endpoints = 0

    for root, dirs, files in os.walk(root_dir):
        # Skip venv and other non-source dirs
        if 'venv' in root or '__pycache__' in root or '.git' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = endpoint_pattern.findall(content)
                        count = len(matches)
                        
                        if count > 0:
                            # Use relative path as category name for better context
                            rel_path = os.path.relpath(file_path, root_dir)
                            # Group by file directory + name (approx category)
                            category = rel_path.replace('/', ' > ').replace('.py', '')
                            categories[category] = count
                            total_endpoints += count
                except Exception as e:
                    print(f"Skipping {file_path}: {e}")

    # Sort categories by count desc
    sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    
    print(f"Total API Endpoints: {total_endpoints}\n")
    print("Breakdown by File/Category:")
    print("---------------------------")
    for cat, count in sorted_cats:
        print(f"{cat}: {count}")

if __name__ == "__main__":
    count_endpoints('/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')
