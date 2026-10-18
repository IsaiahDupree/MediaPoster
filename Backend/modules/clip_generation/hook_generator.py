"""
Hook Generator
Creates attention-grabbing text hooks using GPT-4
"""
import openai
from typing import Dict, List, Optional
from loguru import logger
from config import settings


class HookGenerator:
    """Generate viral hooks and text overlays using GPT-4"""
    
    HOOK_TYPES = [
        'question',        # "Want to know the secret?"
        'shock',          # "This changed everything"
        'teaser',         # "Wait for it..."
        'challenge',      # "Can you do this?"
        'revelation',     # "You won't believe what happened"
        'emotion',        # "This will make you cry"
        'tutorial',       # "How to [X] in 30 seconds"
        'comparison',     # "X vs Y - shocking results"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize hook generator
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key or settings.openai_api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        
        logger.info("Hook generator initialized")
    
    def generate_hooks(
        self,
        highlight_data: Dict,
        video_context: Dict,
        count: int = 5,
        hook_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Generate multiple hook options for a highlight
        
        Args:
            highlight_data: Highlight information
            video_context: Video metadata and content
            count: Number of hooks to generate
            hook_types: Specific hook types to generate
            
        Returns:
            List of hook options with text and metadata
        """
        logger.info(f"Generating {count} hooks")
        
        # Build prompt
        prompt = self._build_hook_prompt(
            highlight_data,
            video_context,
            count,
            hook_types
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a viral content expert specializing in creating attention-grabbing hooks for short-form videos (TikTok, Instagram Reels, YouTube Shorts). Your hooks should be concise, emotionally engaging, and optimized for maximum retention."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.9,  # High creativity
                max_tokens=500
            )
            
            # Parse response
            hooks_text = response.choices[0].message.content
            hooks = self._parse_hooks(hooks_text, hook_types or self.HOOK_TYPES)
            
            logger.success(f"✓ Generated {len(hooks)} hooks")
            return hooks
            
        except Exception as e:
            logger.error(f"Hook generation failed: {e}")
            # Return fallback hooks
            return self._generate_fallback_hooks(highlight_data, count)
    
    def _build_hook_prompt(
        self,
        highlight_data: Dict,
        video_context: Dict,
        count: int,
        hook_types: Optional[List[str]]
    ) -> str:
        """Build GPT prompt for hook generation"""
        
        types_str = ', '.join(hook_types or self.HOOK_TYPES[:4])
        
        prompt = f"""Generate {count} viral hooks for a short video clip.

VIDEO CONTEXT:
- Content Type: {video_context.get('content_type', 'unknown')}
- Key Topics: {', '.join(video_context.get('key_topics', [])[:5])}
- Duration: {highlight_data.get('duration', 0):.1f} seconds

CLIP DETAILS:
- Start: {highlight_data.get('start', 0):.1f}s
- Score: {highlight_data.get('composite_score', 0):.2f}
- Strengths: {', '.join(highlight_data.get('metadata', {}).get('strengths', ['engaging content'])[:3])}

HOOK TYPES TO USE: {types_str}

REQUIREMENTS:
- Maximum 60 characters per hook
- Use emojis strategically
- Create curiosity and urgency
- Match TikTok/Instagram viral style
- Each hook should stop the scroll

FORMAT:
1. [Hook Type] Hook Text 🔥
2. [Hook Type] Hook Text ⚡
...

Generate {count} diverse, attention-grabbing hooks:"""
        
        return prompt
    
    def _parse_hooks(
        self,
        gpt_response: str,
        hook_types: List[str]
    ) -> List[Dict]:
        """Parse GPT response into structured hooks"""
        
        hooks = []
        lines = gpt_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            
            # Remove numbering
            text = line.split('.', 1)[-1].strip()
            
            # Extract type if present
            hook_type = 'generic'
            if '[' in text and ']' in text:
                type_match = text[text.find('[')+1:text.find(']')]
                if type_match.lower() in hook_types:
                    hook_type = type_match.lower()
                text = text[text.find(']')+1:].strip()
            
            if text:
                hooks.append({
                    'text': text,
                    'type': hook_type,
                    'length': len(text),
                    'has_emoji': any(ord(c) > 127 for c in text)
                })
        
        return hooks
    
    def _generate_fallback_hooks(
        self,
        highlight_data: Dict,
        count: int
    ) -> List[Dict]:
        """Generate fallback hooks if GPT fails"""
        
        fallback_templates = [
            "Watch this 👀",
            "Wait for it... 🔥",
            "You won't believe this",
            "This is crazy ⚡",
            "POV: The moment when...",
        ]
        
        hooks = []
        for i, template in enumerate(fallback_templates[:count]):
            hooks.append({
                'text': template,
                'type': 'generic',
                'length': len(template),
                'has_emoji': True
            })
        
        return hooks
    
    def generate_cta(
        self,
        video_context: Dict,
        platform: str = 'tiktok'
    ) -> Dict:
        """
        Generate call-to-action text
        
        Args:
            video_context: Video metadata
            platform: Target platform
            
        Returns:
            CTA text and positioning
        """
        logger.info(f"Generating CTA for {platform}")
        
        prompt = f"""Generate a call-to-action for a {platform} video.

CONTEXT:
- Content: {video_context.get('content_type', 'video')}
- Platform: {platform}

Generate 3 CTA options:
1. Engagement CTA (like, comment, share)
2. Follow CTA (follow for more)
3. Action CTA (try this, learn more)

Keep each under 40 characters. Use emojis.
Format: one per line, no numbering."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a social media growth expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=200
            )
            
            ctas = [line.strip() for line in response.choices[0].message.content.split('\n') if line.strip()]
            
            return {
                'options': ctas,
                'recommended': ctas[0] if ctas else "Follow for more! 🚀"
            }
            
        except Exception as e:
            logger.error(f"CTA generation failed: {e}")
            return {
                'options': ["Follow for more! 🚀", "Like if you agree 💯", "Share this! ⚡"],
                'recommended': "Follow for more! 🚀"
            }
    
    def suggest_hashtags(
        self,
        video_context: Dict,
        platform: str = 'tiktok',
        count: int = 10
    ) -> List[str]:
        """
        Suggest relevant hashtags
        
        Args:
            video_context: Video metadata
            platform: Target platform
            count: Number of hashtags
            
        Returns:
            List of hashtags
        """
        logger.info(f"Generating {count} hashtags for {platform}")
        
        topics = video_context.get('key_topics', [])
        content_type = video_context.get('content_type', 'video')
        
        prompt = f"""Generate {count} trending hashtags for a {platform} video.

CONTENT:
- Type: {content_type}
- Topics: {', '.join(topics[:5])}

REQUIREMENTS:
- Mix of broad and niche hashtags
- Include platform-specific trending tags
- Mix of high-volume and low-competition
- No spaces in hashtags

Format: one hashtag per line, with # symbol."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a social media hashtag expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            hashtags = [
                line.strip() 
                for line in response.choices[0].message.content.split('\n')
                if line.strip().startswith('#')
            ]
            
            logger.success(f"✓ Generated {len(hashtags)} hashtags")
            return hashtags[:count]
            
        except Exception as e:
            logger.error(f"Hashtag generation failed: {e}")
            # Fallback hashtags
            return [
                '#fyp', '#foryou', '#viral', '#trending',
                f'#{content_type.lower()}', '#shorts'
            ][:count]
    
    def create_thumbnail_text(
        self,
        highlight_data: Dict,
        video_context: Dict
    ) -> Dict:
        """
        Generate thumbnail text overlay
        
        Args:
            highlight_data: Highlight info
            video_context: Video metadata
            
        Returns:
            Thumbnail text with styling
        """
        logger.info("Generating thumbnail text")
        
        prompt = f"""Create a thumbnail text for a video clip.

CLIP: {highlight_data.get('duration', 0):.1f} seconds
CONTENT: {video_context.get('content_type', 'video')}
STRENGTHS: {', '.join(highlight_data.get('metadata', {}).get('strengths', [''])[:2])}

Generate:
1. Main text (2-5 words, attention-grabbing)
2. Subtext (optional, under 8 words)

Make it BOLD, CLEAR, and CLICKABLE.
Use emojis if appropriate.

Format:
MAIN: [text]
SUB: [text]"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a thumbnail design expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=150
            )
            
            content = response.choices[0].message.content
            
            # Parse response
            main_text = ""
            sub_text = ""
            
            for line in content.split('\n'):
                if 'MAIN:' in line:
                    main_text = line.split('MAIN:')[-1].strip()
                elif 'SUB:' in line:
                    sub_text = line.split('SUB:')[-1].strip()
            
            return {
                'main': main_text or "WATCH THIS",
                'sub': sub_text,
                'style': {
                    'main_size': 72,
                    'sub_size': 36,
                    'color': 'white',
                    'outline': 'black',
                    'bold': True
                }
            }
            
        except Exception as e:
            logger.error(f"Thumbnail text generation failed: {e}")
            return {
                'main': "WATCH THIS",
                'sub': "You won't believe it",
                'style': {
                    'main_size': 72,
                    'sub_size': 36,
                    'color': 'white',
                    'outline': 'black',
                    'bold': True
                }
            }
    
    def optimize_hook_for_platform(
        self,
        hook: str,
        platform: str
    ) -> str:
        """
        Optimize hook text for specific platform
        
        Args:
            hook: Original hook text
            platform: Target platform
            
        Returns:
            Optimized hook
        """
        # Platform-specific optimizations
        if platform == 'tiktok':
            # TikTok loves emojis and trends
            if not any(ord(c) > 127 for c in hook):
                hook = hook + " 🔥"
        elif platform == 'youtube_shorts':
            # YouTube Shorts prefers cleaner text
            hook = hook.replace('🔥', '').replace('⚡', '').strip()
        elif platform == 'instagram':
            # Instagram likes aesthetic emojis
            hook = hook.replace('🔥', '✨')
        
        # Ensure length limits
        max_lengths = {
            'tiktok': 60,
            'instagram': 60,
            'youtube_shorts': 70
        }
        
        max_len = max_lengths.get(platform, 60)
        if len(hook) > max_len:
            hook = hook[:max_len-3] + '...'
        
        return hook


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("HOOK GENERATOR")
    print("="*60)
    print("\nThis module generates viral hooks using GPT-4.")
    print("Requires: OpenAI API key")
    print("\nFor end-to-end testing, use test_phase3.py")
