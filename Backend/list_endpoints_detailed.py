
import os
import re

def list_endpoints_detailed(root_dir):
    # Regex to capture method and path
    # Matches @router.get("/some/path" or @app.post('/some/path'
    endpoint_pattern = re.compile(r'@(app|router|api)\.(get|post|put|delete|patch|options|head)\s*\(\s*["\']([^"\']+)["\']')
    
    categories = {}
    total_endpoints = 0

    for root, dirs, files in os.walk(root_dir):
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
                            # Use relative path as category name
                            rel_path = os.path.relpath(file_path, root_dir)
                            category = rel_path.replace('/', ' > ').replace('.py', '')
                            
                            if category not in categories:
                                categories[category] = []
                            
                            for match in matches:
                                # match = (app/router, method, path)
                                categories[category].append({
                                    'method': match[1].upper(),
                                    'path': match[2]
                                })
                                total_endpoints += 1
                except Exception as e:
                    pass

    # Sort categories by count desc
    sorted_cats = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"# API Endpoint Breakdown\n")
    print(f"**Total Endpoints:** {total_endpoints}\n")
    
    for cat, endpoints in sorted_cats:
        print(f"## {cat} ({len(endpoints)})")
        print("| Method | Path |")
        print("|--------|------|")
        for ep in endpoints:
            print(f"| {ep['method']} | `{ep['path']}` |")
        print("\n")

if __name__ == "__main__":
    list_endpoints_detailed('/Users/isaiahdupree/Documents/Software/MediaPoster/Backend')
