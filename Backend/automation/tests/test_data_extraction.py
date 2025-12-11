"""
TikTok Data Extraction Test
============================

Extract all data from a TikTok post:
- Video metadata (author, description, music)
- Engagement metrics (likes, comments, shares, saves)
- All comments with usernames and timestamps
"""

import pytest
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path


@pytest.fixture
def safari():
    """Safari helper."""
    class SafariHelper:
        def activate(self):
            subprocess.run(["osascript", "-e", 'tell application "Safari" to activate'], capture_output=True)
            time.sleep(0.3)
        
        def run_js(self, js_code: str) -> str:
            escaped_js = js_code.replace('"', '\\"').replace('\n', ' ')
            result = subprocess.run(
                ["osascript", "-e", f'tell application "Safari" to do JavaScript "{escaped_js}" in current tab of front window'],
                capture_output=True, text=True
            )
            return result.stdout.strip()
        
        def get_url(self) -> str:
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Safari" to return URL of current tab of front window'],
                capture_output=True, text=True
            )
            return result.stdout.strip()
        
        def navigate(self, url: str):
            subprocess.run(
                ["osascript", "-e", f'tell application "Safari" to set URL of current tab of front window to "{url}"'],
                capture_output=True
            )
            time.sleep(3)
    
    helper = SafariHelper()
    helper.activate()
    return helper


class TestDataExtraction:
    """Extract all data from TikTok posts."""
    
    def test_extract_video_metadata(self, safari):
        """Extract video metadata from current video."""
        safari.activate()
        
        print("\n=== VIDEO METADATA ===\n")
        
        # Get current URL
        url = safari.get_url()
        print(f"URL: {url}")
        
        # Extract author username
        username = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"browse-username\"]');"
            "if (!e) e = document.querySelector('[data-e2e=\"video-author-uniqueid\"]');"
            "e ? e.innerText : 'N/A';"
        )
        print(f"Author: @{username}")
        
        # Extract author nickname
        nickname = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"browser-nickname\"]');"
            "if (!e) e = document.querySelector('[data-e2e=\"video-author-nickname\"]');"
            "e ? e.innerText : 'N/A';"
        )
        print(f"Nickname: {nickname}")
        
        # Extract video description
        description = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"browse-video-desc\"]');"
            "if (!e) e = document.querySelector('[data-e2e=\"video-desc\"]');"
            "e ? e.innerText : 'N/A';"
        )
        print(f"Description: {description[:100]}..." if len(description) > 100 else f"Description: {description}")
        
        # Extract music info
        music = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"browse-music\"]');"
            "if (!e) e = document.querySelector('[data-e2e=\"video-music\"]');"
            "e ? e.innerText : 'N/A';"
        )
        print(f"Music: {music}")
        
        # Extract hashtags (get all links that contain /tag/)
        hashtag_count = safari.run_js(
            "document.querySelectorAll('a[href*=\"/tag/\"]').length;"
        )
        print(f"\nHashtags found: {hashtag_count}")
        
        if hashtag_count and hashtag_count != '0':
            num_tags = int(float(hashtag_count)) if hashtag_count.replace('.', '').isdigit() else 0
            hashtags = []
            for i in range(min(10, num_tags)):
                tag = safari.run_js(
                    "var tags = document.querySelectorAll('a[href*=\"/tag/\"]'); tags[" + str(i) + "] ? tags[" + str(i) + "].innerText : '';"
                )
                if tag:
                    hashtags.append(tag)
            print(f"Hashtags: {', '.join(hashtags)}")
    
    def test_extract_engagement_metrics(self, safari):
        """Extract engagement metrics from current video."""
        safari.activate()
        
        print("\n=== ENGAGEMENT METRICS ===\n")
        
        # Get each metric separately (simpler, more reliable)
        likes = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"like-count\"]'); e ? e.innerText : 'N/A';"
        )
        print(f"Likes: {likes}")
        
        comments = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"comment-count\"]'); e ? e.innerText : 'N/A';"
        )
        print(f"Comments: {comments}")
        
        shares = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"share-count\"]'); e ? e.innerText : 'N/A';"
        )
        print(f"Shares: {shares}")
        
        # Save count has different selectors
        saves = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"undefined-count\"]'); e ? e.innerText : 'N/A';"
        )
        print(f"Saves: {saves}")
    
    def test_extract_all_comments(self, safari):
        """Extract ALL top-level comments with scrolling to load more."""
        safari.activate()
        
        print("\n=== FULL COMMENT EXTRACTION ===\n")
        
        # Step 1: Detect and open comment panel
        panel_state = safari.run_js(
            "var footer = document.querySelector('[class*=\"DivCommentFooter\"]');"
            "var editor = document.querySelector('.public-DraftEditor-content');"
            "(footer || editor) ? 'OPEN' : 'CLOSED';"
        )
        print(f"Comment panel state: {panel_state}")
        
        if 'CLOSED' in panel_state:
            print("Opening comment panel...")
            safari.run_js(
                "var icon = document.querySelector('span[data-e2e=\"comment-icon\"]');"
                "if (icon) icon.click();"
            )
            time.sleep(2)
            print("Panel opened")
        
        # Step 2: Get total comment count from header (e.g. "Comments (128)")
        total_header = safari.run_js(
            "var h = document.querySelector('[class*=\"DivCommentListHeader\"]');"
            "if (!h) h = document.querySelector('[class*=\"CommentTitle\"]');"
            "h ? h.innerText : '';"
        )
        print(f"Comment header: {total_header}")
        
        # Also try getting count from the comment icon
        comment_count_display = safari.run_js(
            "var e = document.querySelector('[data-e2e=\"comment-count\"]'); e ? e.innerText : '';"
        )
        print(f"Comment count (from icon): {comment_count_display}")
        
        # Step 3: Find the scrollable comment container
        # TikTok uses a scrollable div for comments - find it
        container_info = safari.run_js(
            "var containers = document.querySelectorAll('[class*=\"CommentList\"], [class*=\"DivCommentContainer\"]');"
            "var result = [];"
            "for(var i=0; i<containers.length; i++) {"
            "  var c = containers[i];"
            "  result.push(c.className.substring(0,40) + ' scrollH:' + c.scrollHeight);"
            "}"
            "result.join(' | ');"
        )
        print(f"Comment containers: {container_info}")
        
        # Step 4: Scroll to load all comments
        print("\nScrolling comment panel to load all comments...")
        last_count = 0
        scroll_attempts = 0
        max_scrolls = 50  # Allow more scrolls for large comment sections
        
        while scroll_attempts < max_scrolls:
            # Get current loaded comment count
            current_count = safari.run_js(
                "document.querySelectorAll('[class*=CommentItem]').length;"
            )
            current_count = int(float(current_count)) if current_count.replace('.', '').isdigit() else 0
            
            print(f"  Loaded: {current_count} comments", end='\r')
            
            if current_count == last_count:
                scroll_attempts += 1
                if scroll_attempts >= 5:  # Wait longer for slow loading
                    print(f"\nNo new comments after 5 scroll attempts. Final: {current_count}")
                    break
            else:
                scroll_attempts = 0
                last_count = current_count
            
            # Scroll the comment container (try multiple selectors)
            safari.run_js(
                "var c = document.querySelector('[class*=\"DivCommentListContainer\"]');"
                "if (!c) c = document.querySelector('[class*=\"CommentListContainer\"]');"
                "if (!c) {"
                "  var all = document.querySelectorAll('div');"
                "  for(var i=0; i<all.length; i++) {"
                "    if(all[i].scrollHeight > all[i].clientHeight && all[i].className.includes('Comment')) {"
                "      c = all[i]; break;"
                "    }"
                "  }"
                "}"
                "if (c) { c.scrollTop = c.scrollHeight; }"
            )
            time.sleep(0.8)  # Wait for batch to load
        
        # Step 5: Try scrollIntoView on last comment to trigger load
        safari.run_js(
            "var items = document.querySelectorAll('[class*=CommentItem]');"
            "if(items.length > 0) items[items.length-1].scrollIntoView({block: 'end'});"
        )
        time.sleep(1)
        
        # Step 6: Check for and expand "View X replies" buttons
        reply_buttons = safari.run_js(
            "document.querySelectorAll('[class*=ReplyAction], p[class*=reply]').length;"
        )
        print(f"\nReply buttons found: {reply_buttons}")
        
        if reply_buttons and reply_buttons != '0':
            print("Expanding replies...")
            # Click all "View replies" buttons
            safari.run_js(
                "var btns = document.querySelectorAll('[class*=ReplyAction], p[class*=reply]');"
                "btns.forEach(function(b) { if(b.innerText.includes('View')) b.click(); });"
            )
            time.sleep(2)
        
        # Step 7: Get final count including replies
        final_count = safari.run_js(
            "document.querySelectorAll('[class*=CommentItem]').length;"
        )
        final_count = int(float(final_count)) if final_count.replace('.', '').isdigit() else 0
        print(f"\nTotal comments loaded (including replies): {final_count}")
        
        all_comments = []
        print(f"\nExtracting {final_count} comments...\n")
        
        for i in range(final_count):
            js_code = "var items = document.querySelectorAll('[class*=CommentItem]'); var item = items[" + str(i) + "]; item ? item.innerText : '';"
            comment_text = safari.run_js(js_code)
            
            if comment_text:
                lines = [l.strip() for l in comment_text.split('\n') if l.strip()]
                if len(lines) >= 2:
                    comment = {
                        'index': i + 1,
                        'username': lines[0],
                        'content': lines[1] if len(lines) > 1 else '',
                        'time': lines[2] if len(lines) > 2 else '',
                        'likes': lines[-1] if len(lines) > 3 and lines[-1].isdigit() else '0'
                    }
                    all_comments.append(comment)
                    
                    # Print all comments
                    if i < 30:
                        print(f"{i+1}. @{comment['username']}")
                        print(f"   {comment['content'][:70]}")
                        print(f"   Time: {comment['time']}")
                        print()
        
        if final_count > 30:
            print(f"... and {final_count - 30} more comments")
        
        print(f"\n=== EXTRACTION COMPLETE ===")
        print(f"Top-level + replies extracted: {len(all_comments)}")
        
        return all_comments
    
    def test_extract_full_post_data(self, safari):
        """Extract ALL data from current post into a single JSON object."""
        safari.activate()
        
        print("\n=== FULL POST DATA EXTRACTION ===\n")
        
        # Ensure comment panel is open
        safari.run_js("""
            var icon = document.querySelector('span[data-e2e="comment-icon"]');
            if (icon) icon.click();
        """)
        time.sleep(2)
        
        full_data = safari.run_js("""
            (function() {
                var data = {
                    extracted_at: new Date().toISOString(),
                    url: window.location.href,
                    author: {},
                    video: {},
                    metrics: {},
                    comments: []
                };
                
                // Author
                var author = document.querySelector('[data-e2e="video-author-uniqueid"]');
                var nickname = document.querySelector('[data-e2e="video-author-nickname"]');
                data.author.username = author ? author.innerText : null;
                data.author.nickname = nickname ? nickname.innerText : null;
                
                // Video
                var desc = document.querySelector('[data-e2e="video-desc"]');
                var music = document.querySelector('[data-e2e="video-music"]');
                data.video.description = desc ? desc.innerText : null;
                data.video.music = music ? music.innerText : null;
                
                // Hashtags
                var tags = document.querySelectorAll('[data-e2e="video-desc"] a[href*="/tag/"]');
                data.video.hashtags = [];
                tags.forEach(function(t) { data.video.hashtags.push(t.innerText); });
                
                // Metrics
                var likes = document.querySelector('[data-e2e="like-count"]');
                var comments = document.querySelector('[data-e2e="comment-count"]');
                var shares = document.querySelector('[data-e2e="share-count"]');
                data.metrics.likes = likes ? likes.innerText : null;
                data.metrics.comments = comments ? comments.innerText : null;
                data.metrics.shares = shares ? shares.innerText : null;
                
                // Comments (first 10)
                var items = document.querySelectorAll('[class*="DivCommentItemWrapper"]');
                items.forEach(function(item, idx) {
                    if (idx < 10) {
                        var username = item.querySelector('[class*="SpanUserNameText"]');
                        var content = item.querySelector('[class*="PCommentText"]');
                        var time = item.querySelector('[class*="SpanCreatedTime"]');
                        
                        data.comments.push({
                            username: username ? username.innerText : '',
                            content: content ? content.innerText : '',
                            time: time ? time.innerText : ''
                        });
                    }
                });
                
                return JSON.stringify(data, null, 2);
            })();
        """)
        
        print(full_data)
        
        # Save to file
        try:
            data = json.loads(full_data)
            output_dir = Path(__file__).parent / "extracted_data"
            output_dir.mkdir(exist_ok=True)
            
            filename = f"tiktok_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = output_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"\n✅ Saved to: {filepath}")
        except Exception as e:
            print(f"\nError saving: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
