"""
SMS Verification Code Reader using AppleScript
Reads SMS codes from Messages.app on macOS.
"""
import asyncio
import subprocess
import re
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from loguru import logger


class SMSCodeReader:
    """Reads SMS verification codes from Messages.app."""
    
    def __init__(self):
        self.last_check_time = datetime.now()
        self.seen_codes: set = set()
    
    def _run_applescript(self, script: str) -> str:
        """Execute AppleScript and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.debug(f"AppleScript error: {e.stderr}")
            return ""
        except subprocess.TimeoutExpired:
            logger.warning("AppleScript timeout")
            return ""
    
    def get_recent_messages(self, minutes: int = 5) -> List[Dict]:
        """
        Get recent SMS messages from Messages.app.
        
        Args:
            minutes: How many minutes back to look
            
        Returns:
            List of message dictionaries
        """
        try:
            script = '''
            tell application "Messages"
                set recentMessages to {}
                repeat with chat in chats
                    repeat with message in messages of chat
                        set msgDate to date received of message
                        set timeDiff to (current date) - msgDate
                        if timeDiff < (5 * 60) then
                            set end of recentMessages to {text of message, msgDate, service of chat}
                        end if
                    end repeat
                end repeat
                return recentMessages
            end tell
            '''
            
            result = self._run_applescript(script)
            
            # Parse the result (AppleScript returns a list)
            # Format: {{"message text", date, "service"}, ...}
            messages = []
            if result:
                # Simple parsing - AppleScript list format
                # This is a simplified parser, may need adjustment
                lines = result.split('\n')
                for line in lines:
                    if line.strip() and '"' in line:
                        # Extract message text
                        match = re.search(r'"([^"]+)"', line)
                        if match:
                            messages.append({
                                "text": match.group(1),
                                "raw": line
                            })
            
            return messages
        except Exception as e:
            logger.debug(f"Error getting messages: {e}")
            return []
    
    def extract_verification_code(self, text: str) -> Optional[str]:
        """
        Extract verification code from text.
        Looks for 4-8 digit codes, common patterns.
        
        Args:
            text: Message text to search
            
        Returns:
            Verification code or None
        """
        # Common patterns for verification codes
        patterns = [
            r'\b(\d{6})\b',  # 6-digit code (most common)
            r'\b(\d{4})\b',  # 4-digit code
            r'\b(\d{5})\b',  # 5-digit code
            r'\b(\d{8})\b',  # 8-digit code
            r'code[:\s]+(\d{4,8})',  # "code: 123456"
            r'verification[:\s]+(\d{4,8})',  # "verification: 123456"
            r'(\d{4,8})[^\d]',  # Standalone digits
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                code = match.group(1)
                # Filter out obvious non-codes (years, phone numbers, etc.)
                if len(code) >= 4 and len(code) <= 8:
                    # Check if it's not a year (1900-2099)
                    if not (1900 <= int(code) <= 2099 and len(code) == 4):
                        return code
        
        return None
    
    async def wait_for_verification_code(
        self, 
        timeout: int = 120,
        check_interval: int = 2,
        keywords: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Wait for a verification code to arrive via SMS.
        
        Args:
            timeout: Maximum time to wait in seconds
            check_interval: How often to check for new messages
            keywords: Optional keywords to filter messages (e.g., ["TikTok", "verification"])
            
        Returns:
            Verification code or None if timeout
        """
        if keywords is None:
            keywords = ["tiktok", "verification", "code", "verify"]
        
        logger.info(f"Waiting for verification code (timeout: {timeout}s)...")
        logger.info(f"Watching for keywords: {', '.join(keywords)}")
        
        start_time = datetime.now()
        last_message_count = 0
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                # Get recent messages
                messages = self.get_recent_messages(minutes=5)
                
                # Check for new messages with keywords
                for msg in messages:
                    msg_text = msg.get("text", "").lower()
                    
                    # Check if message contains keywords
                    if any(keyword.lower() in msg_text for keyword in keywords):
                        # Extract code
                        code = self.extract_verification_code(msg.get("text", ""))
                        
                        if code and code not in self.seen_codes:
                            self.seen_codes.add(code)
                            logger.success(f"✅ Verification code found: {code}")
                            return code
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.debug(f"Error checking messages: {e}")
                await asyncio.sleep(check_interval)
        
        logger.warning("⏱️  Timeout waiting for verification code")
        return None
    
    async def get_latest_code(self, keywords: Optional[List[str]] = None) -> Optional[str]:
        """
        Get the most recent verification code from messages.
        
        Args:
            keywords: Optional keywords to filter messages
            
        Returns:
            Latest verification code or None
        """
        if keywords is None:
            keywords = ["tiktok", "verification", "code", "verify"]
        
        messages = self.get_recent_messages(minutes=10)
        
        # Sort by time (most recent first) - simplified
        for msg in reversed(messages):  # Check newest first
            msg_text = msg.get("text", "").lower()
            
            if any(keyword.lower() in msg_text for keyword in keywords):
                code = self.extract_verification_code(msg.get("text", ""))
                if code:
                    return code
        
        return None


async def test_sms_reader():
    """Test the SMS code reader."""
    reader = SMSCodeReader()
    
    logger.info("Testing SMS code reader...")
    
    # Try to get latest code
    code = await reader.get_latest_code()
    if code:
        logger.success(f"Found code: {code}")
    else:
        logger.info("No recent codes found")
    
    # Wait for new code
    logger.info("Waiting for new verification code...")
    code = await reader.wait_for_verification_code(timeout=30)
    if code:
        logger.success(f"Received code: {code}")
    else:
        logger.warning("No code received")


if __name__ == "__main__":
    import sys
    from loguru import logger
    
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    
    asyncio.run(test_sms_reader())

