"""
Screenshot Analysis for Login Automation
Analyzes screenshots to extract automation patterns and login detection indicators.
"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger
import sys

try:
    from PIL import Image
    import cv2
    import numpy as np
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False
    logger.warning("PIL/OpenCV not available. Limited analysis.")


class ScreenshotAnalyzer:
    """Analyzes screenshots to extract login automation patterns."""
    
    def __init__(self, recording_file: Path, screenshots_dir: Path):
        self.recording_file = recording_file
        self.screenshots_dir = screenshots_dir
        self.recording_data = None
        self.screenshots = []
        
    def load_recording(self):
        """Load the recording JSON file."""
        try:
            with open(self.recording_file, 'r') as f:
                self.recording_data = json.load(f)
            logger.info(f"✅ Loaded recording: {self.recording_file.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load recording: {e}")
            return False
    
    def extract_screenshot_paths(self) -> List[Dict]:
        """Extract all screenshot paths from the recording."""
        screenshots = []
        
        if not self.recording_data:
            return screenshots
        
        for action in self.recording_data.get('actions', []):
            if action.get('type') == 'screenshot':
                path = action.get('details', {}).get('path', '')
                if path:
                    screenshots.append({
                        'path': Path(path),
                        'timestamp': action.get('timestamp'),
                        'relative_time': action.get('relative_time', 0),
                        'description': action.get('details', {}).get('description', '')
                    })
        
        # Also check for screenshots in the directory that match the recording time
        recording_time = datetime.fromisoformat(self.recording_data.get('recorded_at', ''))
        for screenshot_file in sorted(self.screenshots_dir.glob('*.png')):
            # Check if screenshot is from this recording session
            if screenshot_file.stat().st_mtime >= recording_time.timestamp() - 300:  # Within 5 min
                screenshots.append({
                    'path': screenshot_file,
                    'timestamp': None,
                    'relative_time': None,
                    'description': f'Detected: {screenshot_file.name}'
                })
        
        # Sort by relative time or filename
        screenshots.sort(key=lambda x: x.get('relative_time', 0) or 0)
        self.screenshots = screenshots
        return screenshots
    
    def analyze_visual_changes(self) -> List[Dict]:
        """Analyze visual changes between screenshots."""
        if not IMAGING_AVAILABLE or len(self.screenshots) < 2:
            return []
        
        changes = []
        prev_image = None
        
        for i, screenshot in enumerate(self.screenshots):
            try:
                current_image = cv2.imread(str(screenshot['path']))
                if current_image is None:
                    continue
                
                if prev_image is not None:
                    # Calculate difference
                    diff = cv2.absdiff(prev_image, current_image)
                    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                    change_percentage = (np.sum(gray_diff > 30) / gray_diff.size) * 100
                    
                    if change_percentage > 5:  # Significant change
                        changes.append({
                            'from': self.screenshots[i-1]['path'].name,
                            'to': screenshot['path'].name,
                            'change_percentage': round(change_percentage, 2),
                            'time_diff': screenshot.get('relative_time', 0) - self.screenshots[i-1].get('relative_time', 0) if screenshot.get('relative_time') else None
                        })
                
                prev_image = current_image
            except Exception as e:
                logger.debug(f"Error analyzing {screenshot['path']}: {e}")
        
        return changes
    
    def detect_login_indicators(self) -> Dict:
        """Detect visual indicators of login state."""
        indicators = {
            'login_form_detected': False,
            'logged_in_detected': False,
            'captcha_detected': False,
            'verification_code_detected': False,
            'url_patterns': []
        }
        
        if not self.recording_data:
            return indicators
        
        # Analyze URL patterns
        for action in self.recording_data.get('actions', []):
            if action.get('type') == 'url_change':
                url = action.get('details', {}).get('to', '')
                if 'login' in url.lower() or 'passport' in url.lower():
                    indicators['login_form_detected'] = True
                if 'tiktok.com' in url and 'login' not in url.lower() and 'passport' not in url.lower():
                    indicators['url_patterns'].append({
                        'url': url,
                        'time': action.get('relative_time', 0),
                        'indicator': 'possible_logged_in'
                    })
        
        # Check page state snapshots
        for action in self.recording_data.get('actions', []):
            if action.get('type') == 'page_state_snapshot':
                details = action.get('details', {})
                if details.get('has_login_form'):
                    indicators['login_form_detected'] = True
                if details.get('has_captcha'):
                    indicators['captcha_detected'] = True
                if details.get('has_code_input'):
                    indicators['verification_code_detected'] = True
        
        # Check final URL
        final_url = self.recording_data.get('final_url', '')
        if final_url and 'tiktok.com' in final_url and 'login' not in final_url.lower():
            indicators['logged_in_detected'] = True
        
        return indicators
    
    def generate_automation_steps(self) -> List[Dict]:
        """Generate automation steps based on recording analysis."""
        steps = []
        
        if not self.recording_data:
            return steps
        
        # Extract URL progression
        urls = []
        for action in self.recording_data.get('actions', []):
            if action.get('type') in ['navigation', 'url_change']:
                url = action.get('details', {}).get('url') or action.get('details', {}).get('to', '')
                if url:
                    urls.append({
                        'url': url,
                        'time': action.get('relative_time', 0),
                        'type': action.get('type')
                    })
        
        # Generate navigation steps
        for i, url_info in enumerate(urls):
            steps.append({
                'step': len(steps) + 1,
                'action': 'navigate',
                'target': url_info['url'],
                'description': f"Navigate to {url_info['url']}",
                'time_after_start': url_info['time']
            })
        
        # Extract form interactions (if available)
        for action in self.recording_data.get('actions', []):
            if action.get('type') in ['input_field_filled', 'js_input']:
                details = action.get('details', {})
                target = details.get('target', {})
                steps.append({
                    'step': len(steps) + 1,
                    'action': 'fill_input',
                    'target': target.get('id') or target.get('name') or target.get('placeholder', 'field'),
                    'description': f"Fill input field: {target.get('type', 'text')}",
                    'time_after_start': action.get('relative_time', 0)
                })
            
            elif action.get('type') in ['click', 'js_click']:
                details = action.get('details', {})
                target = details.get('target', {})
                steps.append({
                    'step': len(steps) + 1,
                    'action': 'click',
                    'target': target.get('selector') or target.get('id') or target.get('text', 'element'),
                    'description': f"Click: {target.get('text', 'element')[:50]}",
                    'time_after_start': action.get('relative_time', 0)
                })
        
        return steps
    
    def suggest_login_detection_methods(self) -> List[Dict]:
        """Suggest methods for detecting login success."""
        methods = []
        
        # URL-based detection
        methods.append({
            'method': 'url_check',
            'description': 'Check if URL contains tiktok.com but not login/passport',
            'implementation': "current_url = await browser.get_current_url()\nif 'tiktok.com' in current_url and 'login' not in current_url.lower():\n    return True",
            'confidence': 'medium'
        })
        
        # DOM element detection
        methods.append({
            'method': 'dom_element_check',
            'description': 'Look for profile icon or upload button',
            'implementation': "element = await page.query_selector('[data-e2e=\"profile-icon\"], [data-e2e=\"upload-icon\"]')\nreturn element is not None",
            'confidence': 'high'
        })
        
        # Visual detection (if screenshots available)
        if len(self.screenshots) > 0:
            methods.append({
                'method': 'visual_detection',
                'description': 'Compare current screenshot with known logged-in state',
                'implementation': 'Use image comparison to detect profile icon presence',
                'confidence': 'medium'
            })
        
        # Cookie-based detection
        methods.append({
            'method': 'cookie_check',
            'description': 'Check for authentication cookies',
            'implementation': "cookies = await browser.get_cookies()\nreturn any('session' in c.get('name', '').lower() for c in cookies)",
            'confidence': 'high'
        })
        
        return methods
    
    def generate_report(self) -> Dict:
        """Generate comprehensive analysis report."""
        if not self.load_recording():
            return {}
        
        screenshots = self.extract_screenshot_paths()
        visual_changes = self.analyze_visual_changes()
        indicators = self.detect_login_indicators()
        automation_steps = self.generate_automation_steps()
        detection_methods = self.suggest_login_detection_methods()
        
        report = {
            'recording_file': str(self.recording_file),
            'total_screenshots': len(screenshots),
            'visual_changes': visual_changes,
            'login_indicators': indicators,
            'automation_steps': automation_steps,
            'detection_methods': detection_methods,
            'summary': {
                'duration': self.recording_data.get('duration_seconds', 0),
                'total_actions': self.recording_data.get('total_actions', 0),
                'screenshots_captured': len(screenshots),
                'url_changes': len([a for a in self.recording_data.get('actions', []) if a.get('type') == 'url_change']),
                'significant_visual_changes': len([c for c in visual_changes if c.get('change_percentage', 0) > 10])
            }
        }
        
        return report


def main():
    """Main analysis function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze login recording screenshots')
    parser.add_argument('recording', type=int, nargs='?', default=1, help='Recording number to analyze (default: 1)')
    parser.add_argument('--output', type=str, help='Output JSON file for report')
    
    args = parser.parse_args()
    
    # Find recording file
    recordings_dir = Path(__file__).parent / "recordings"
    screenshots_dir = Path(__file__).parent / "screenshots"
    
    recordings = sorted(recordings_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not recordings:
        logger.error("No recordings found!")
        return
    
    if args.recording > len(recordings):
        logger.error(f"Recording {args.recording} not found. Available: 1-{len(recordings)}")
        return
    
    recording_file = recordings[args.recording - 1]
    
    logger.info(f"Analyzing recording: {recording_file.name}")
    
    analyzer = ScreenshotAnalyzer(recording_file, screenshots_dir)
    report = analyzer.generate_report()
    
    if not report:
        logger.error("Failed to generate report")
        return
    
    # Print report
    print("\n" + "=" * 80)
    print("📊 SCREENSHOT ANALYSIS REPORT")
    print("=" * 80)
    print(f"\n📁 Recording: {recording_file.name}")
    print(f"⏱️  Duration: {report['summary']['duration']:.1f}s")
    print(f"📸 Screenshots: {report['total_screenshots']}")
    print(f"🔄 URL Changes: {report['summary']['url_changes']}")
    print(f"✨ Visual Changes: {report['summary']['significant_visual_changes']}")
    
    print("\n" + "-" * 80)
    print("🔍 LOGIN INDICATORS")
    print("-" * 80)
    indicators = report['login_indicators']
    print(f"  Login Form Detected: {'✅' if indicators['login_form_detected'] else '❌'}")
    print(f"  Logged In Detected: {'✅' if indicators['logged_in_detected'] else '❌'}")
    print(f"  Captcha Detected: {'✅' if indicators['captcha_detected'] else '❌'}")
    print(f"  Verification Code: {'✅' if indicators['verification_code_detected'] else '❌'}")
    
    if indicators['url_patterns']:
        print(f"\n  URL Patterns:")
        for pattern in indicators['url_patterns']:
            print(f"    - {pattern['indicator']}: {pattern['url'][:60]}...")
    
    print("\n" + "-" * 80)
    print("🤖 AUTOMATION STEPS")
    print("-" * 80)
    if report['automation_steps']:
        for step in report['automation_steps'][:10]:  # Show first 10
            print(f"  {step['step']}. {step['action'].upper()}: {step['description']}")
        if len(report['automation_steps']) > 10:
            print(f"  ... and {len(report['automation_steps']) - 10} more steps")
    else:
        print("  No automation steps extracted (insufficient data)")
    
    print("\n" + "-" * 80)
    print("🎯 LOGIN DETECTION METHODS")
    print("-" * 80)
    for method in report['detection_methods']:
        confidence_emoji = {'high': '🟢', 'medium': '🟡', 'low': '🔴'}.get(method['confidence'], '⚪')
        print(f"\n  {confidence_emoji} {method['method'].upper()} ({method['confidence']} confidence)")
        print(f"     {method['description']}")
        if 'implementation' in method:
            print(f"     Code: {method['implementation'][:80]}...")
    
    print("\n" + "-" * 80)
    print("📈 VISUAL CHANGES")
    print("-" * 80)
    if report['visual_changes']:
        for change in report['visual_changes'][:5]:  # Show first 5
            print(f"  {change['from']} → {change['to']}")
            print(f"    Change: {change['change_percentage']}%")
            if change.get('time_diff'):
                print(f"    Time: {change['time_diff']:.1f}s")
    else:
        print("  No significant visual changes detected")
    
    print("\n" + "=" * 80)
    
    # Save report if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.success(f"✅ Report saved to: {output_path}")
    
    return report


if __name__ == "__main__":
    main()


