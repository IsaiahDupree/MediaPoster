"""
DOM Inspector for TikTok Comments
Inspects the live TikTok DOM to find correct selectors for comment extraction.
"""
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from tiktok_engagement import TikTokEngagement

async def inspect_comment_dom():
    """Inspect the TikTok DOM to find comment selectors."""
    engagement = TikTokEngagement(browser_type="safari")
    
    try:
        print("🔍 Starting DOM inspection for comments...")
        
        await engagement.start()
        print("✅ Safari started")
        
        # Navigate to FYP
        await engagement.navigate_to_fyp()
        await asyncio.sleep(3)
        print("📍 On FYP page")
        
        # Open comments
        await engagement.open_comments()
        await asyncio.sleep(3)
        print("💬 Comments panel should be open")
        
        # JavaScript to inspect the DOM and find comment elements
        inspect_js = """
        (function() {
            var results = {
                potential_comment_containers: [],
                data_e2e_elements: [],
                comment_text_candidates: []
            };
            
            // Find all elements with data-e2e attribute
            var e2eElements = document.querySelectorAll('[data-e2e]');
            e2eElements.forEach(function(el) {
                var attr = el.getAttribute('data-e2e');
                if (attr && (attr.includes('comment') || attr.includes('reply'))) {
                    results.data_e2e_elements.push({
                        'data-e2e': attr,
                        'tagName': el.tagName,
                        'className': el.className.substring(0, 100),
                        'children': el.children.length,
                        'textPreview': el.textContent.substring(0, 100)
                    });
                }
            });
            
            // Look for common comment container patterns
            var containers = document.querySelectorAll('[class*="Comment"], [class*="comment"]');
            containers.forEach(function(el, i) {
                if (i < 20) {  // Limit to first 20
                    results.potential_comment_containers.push({
                        'tagName': el.tagName,
                        'className': el.className.substring(0, 150),
                        'children': el.children.length
                    });
                }
            });
            
            // Look for comment text specifically
            var textCandidates = document.querySelectorAll('[class*="Text"], p, span');
            var commentPanel = document.querySelector('[class*="DivCommentListContainer"], [class*="CommentList"], [data-e2e="comment-list"]');
            if (commentPanel) {
                var textsInPanel = commentPanel.querySelectorAll('p, span, [class*="Text"]');
                textsInPanel.forEach(function(el, i) {
                    if (i < 30 && el.textContent.trim().length > 5 && el.textContent.trim().length < 300) {
                        results.comment_text_candidates.push({
                            'tagName': el.tagName,
                            'className': el.className ? el.className.substring(0, 100) : '',
                            'text': el.textContent.trim().substring(0, 100)
                        });
                    }
                });
            }
            
            // Find username links in comments
            var usernameLinks = document.querySelectorAll('a[href*="/@"]');
            results.username_links = [];
            usernameLinks.forEach(function(el, i) {
                if (i < 15) {
                    var parent = el.parentElement;
                    results.username_links.push({
                        'href': el.getAttribute('href'),
                        'text': el.textContent.trim(),
                        'parentClass': parent ? parent.className.substring(0, 80) : ''
                    });
                }
            });
            
            // Get the structure of the first few visible comment items
            results.dom_structure = [];
            var items = document.querySelectorAll('[class*="DivComment"], [class*="comment-item"]');
            items.forEach(function(item, i) {
                if (i < 5) {
                    results.dom_structure.push({
                        'tagName': item.tagName,
                        'className': item.className.substring(0, 150),
                        'innerHTML_preview': item.innerHTML.substring(0, 300)
                    });
                }
            });
            
            return JSON.stringify(results, null, 2);
        })();
        """
        
        print("🔍 Inspecting DOM...")
        result = await engagement._run_js(inspect_js)
        
        if result:
            print("\n" + "="*60)
            print("📋 DOM INSPECTION RESULTS")
            print("="*60)
            
            try:
                data = json.loads(result)
                
                print("\n🏷️ DATA-E2E COMMENT ELEMENTS:")
                for el in data.get('data_e2e_elements', []):
                    print(f"  - {el.get('data-e2e')}: {el.get('tagName')} ({el.get('children')} children)")
                    if el.get('textPreview'):
                        print(f"    Preview: {el.get('textPreview')[:60]}...")
                
                print("\n📦 POTENTIAL COMMENT CONTAINERS:")
                for el in data.get('potential_comment_containers', [])[:10]:
                    print(f"  - {el.get('tagName')}: {el.get('className')[:80]}...")
                
                print("\n💬 COMMENT TEXT CANDIDATES:")
                for el in data.get('comment_text_candidates', [])[:10]:
                    print(f"  - {el.get('tagName')}: \"{el.get('text')[:50]}...\"")
                    print(f"    Class: {el.get('className')[:60]}")
                
                print("\n👤 USERNAME LINKS:")
                for el in data.get('username_links', [])[:10]:
                    print(f"  - {el.get('text')} -> {el.get('href')}")
                
                print("\n🏗️ DOM STRUCTURE:")
                for el in data.get('dom_structure', []):
                    print(f"  - {el.get('className')[:100]}...")
                
                # Save full results to file
                output_file = Path(__file__).parent / "sessions" / "dom_inspection.json"
                output_file.parent.mkdir(exist_ok=True)
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"\n💾 Full results saved to: {output_file}")
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                print(f"Raw result: {result[:500]}")
        else:
            print("❌ No result from DOM inspection")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await engagement.cleanup()
        print("\n🧹 Cleanup complete")


if __name__ == "__main__":
    asyncio.run(inspect_comment_dom())
