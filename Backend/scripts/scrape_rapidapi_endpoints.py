#!/usr/bin/env python3
"""
RapidAPI Endpoint Scraper
Scrapes all endpoint URLs and parameters from a RapidAPI API page using Safari automation.

Usage:
    python scrape_rapidapi_endpoints.py [api_url]
    
Example:
    python scrape_rapidapi_endpoints.py https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api
"""

import subprocess
import json
import time
import sys
import re
from pathlib import Path
from datetime import datetime


def run_applescript(script: str) -> str:
    """Execute AppleScript and return output"""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def navigate_safari(url: str):
    """Navigate Safari to a URL"""
    script = f'''
    tell application "Safari"
        activate
        open location "{url}"
    end tell
    '''
    run_applescript(script)
    time.sleep(3)  # Wait for page load


def get_endpoint_list() -> list:
    """Extract list of endpoints from the RapidAPI sidebar"""
    script = '''
    tell application "Safari"
        tell front document
            set jsCode to "
                var endpoints = [];
                var links = document.querySelectorAll('a[href*=endpoint]');
                links.forEach(function(link) {
                    var text = link.innerText.trim();
                    var href = link.href;
                    if (text && href && href.includes('endpoint_')) {
                        var id = href.split('endpoint_')[1];
                        if (id) {
                            var method = 'GET';
                            if (text.includes('POST')) method = 'POST';
                            endpoints.push(JSON.stringify({
                                name: text.replace(/^(GET|POST)\\s*/, '').trim(),
                                method: method,
                                endpoint_id: id.split('/')[0]
                            }));
                        }
                    }
                });
                '[' + endpoints.join(',') + ']';
            "
            return do JavaScript jsCode
        end tell
    end tell
    '''
    result = run_applescript(script)
    try:
        return json.loads(result) if result else []
    except json.JSONDecodeError:
        return []


def get_endpoint_details(endpoint_id: str, base_url: str) -> dict:
    """Navigate to endpoint page and extract curl command and parameters"""
    # Navigate to endpoint page
    url = f"{base_url}/playground/apiendpoint_{endpoint_id}"
    navigate_safari(url)
    time.sleep(2)
    
    # Extract curl command and parameters
    script = '''
    tell application "Safari"
        tell front document
            set jsCode to "
                var result = {curl: '', params: [], endpoint_path: ''};
                
                // Get curl command
                var curlEls = document.querySelectorAll('pre, code');
                for (var i = 0; i < curlEls.length; i++) {
                    var text = curlEls[i].innerText;
                    if (text.includes('--url')) {
                        result.curl = text;
                        var urlMatch = text.match(/--url\\s+'?([^'\\s]+)/);
                        if (urlMatch) {
                            var path = urlMatch[1].split('.com')[1];
                            if (path) result.endpoint_path = path.split('?')[0];
                        }
                        break;
                    }
                }
                
                // Get parameters from input fields
                var inputs = document.querySelectorAll('input[type=text], input:not([type])');
                inputs.forEach(function(inp) {
                    var parent = inp.parentElement;
                    while (parent && parent.tagName !== 'BODY') {
                        var text = parent.innerText.replace(/\\\\s+/g, ' ').trim();
                        if (text.length < 150 && text.length > 0) {
                            var required = text.includes('*');
                            var paramMatch = text.match(/^([a-z_]+)/i);
                            if (paramMatch && inp.value) {
                                result.params.push({
                                    name: paramMatch[1],
                                    required: required,
                                    example: inp.value,
                                    description: text.substring(0, 100)
                                });
                            }
                            break;
                        }
                        parent = parent.parentElement;
                    }
                });
                
                JSON.stringify(result);
            "
            return do JavaScript jsCode
        end tell
    end tell
    '''
    result = run_applescript(script)
    try:
        return json.loads(result) if result else {}
    except json.JSONDecodeError:
        return {}


def scrape_all_endpoints(api_url: str) -> dict:
    """Scrape all endpoints from a RapidAPI page"""
    print(f"🔍 Scraping endpoints from: {api_url}")
    
    # Navigate to main API page
    navigate_safari(api_url)
    time.sleep(3)
    
    # Get list of endpoints
    endpoints = get_endpoint_list()
    print(f"📋 Found {len(endpoints)} endpoints")
    
    # Get details for each endpoint
    all_endpoints = []
    for i, ep in enumerate(endpoints):
        print(f"  [{i+1}/{len(endpoints)}] Scraping: {ep['name']}")
        details = get_endpoint_details(ep['endpoint_id'], api_url)
        all_endpoints.append({
            **ep,
            **details
        })
        time.sleep(1)  # Rate limit
    
    return {
        "api_url": api_url,
        "scraped_at": datetime.now().isoformat(),
        "endpoint_count": len(all_endpoints),
        "endpoints": all_endpoints
    }


def save_documentation(data: dict, output_path: Path):
    """Save scraped endpoints as documentation"""
    # Save JSON
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved JSON: {json_path}")
    
    # Generate Markdown documentation
    md_content = f"""# {data['api_url'].split('/')[-1]} API Endpoints

**Scraped:** {data['scraped_at']}  
**Total Endpoints:** {data['endpoint_count']}

## Endpoints

"""
    for ep in data['endpoints']:
        md_content += f"### {ep['method']} {ep['name']}\n\n"
        if ep.get('endpoint_path'):
            md_content += f"**Path:** `{ep['endpoint_path']}`\n\n"
        
        if ep.get('params'):
            md_content += "**Parameters:**\n\n"
            md_content += "| Name | Required | Example | Description |\n"
            md_content += "|------|----------|---------|-------------|\n"
            for p in ep['params']:
                req = "✓" if p.get('required') else ""
                md_content += f"| `{p['name']}` | {req} | {p.get('example', '')} | {p.get('description', '')[:50]} |\n"
            md_content += "\n"
        
        if ep.get('curl'):
            md_content += "**Example:**\n```bash\n"
            md_content += ep['curl'][:500]
            md_content += "\n```\n\n"
        
        md_content += "---\n\n"
    
    md_path = output_path.with_suffix('.md')
    with open(md_path, 'w') as f:
        f.write(md_content)
    print(f"📝 Saved Markdown: {md_path}")


def main():
    # Default to Instagram Scraper Stable API
    api_url = sys.argv[1] if len(sys.argv) > 1 else \
        "https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api"
    
    # Scrape endpoints
    data = scrape_all_endpoints(api_url)
    
    # Save documentation
    api_name = api_url.split('/')[-1]
    output_dir = Path(__file__).parent.parent / "docs" / "rapidapi"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{api_name}-endpoints"
    
    save_documentation(data, output_path)
    
    print(f"\n✅ Done! Scraped {data['endpoint_count']} endpoints")
    return data


if __name__ == "__main__":
    main()
