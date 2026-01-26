"""
Test Sora Character Prompt via Safari Automation
=================================================
Sends a 15 second video prompt to Sora using @isaiahdupree character.
"""

import asyncio
import subprocess
import time
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

SORA_URL = "https://sora.com"


class SoraCharacterAutomation:
    """Safari automation for Sora with character support"""
    
    def __init__(self):
        self.character = "isaiahdupree"
    
    def _run_applescript(self, script: str, timeout: int = 60) -> tuple[bool, str]:
        """Execute AppleScript and return success status and output"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Script timed out"
        except Exception as e:
            return False, str(e)
    
    def open_sora(self) -> bool:
        """Open Safari and navigate to Sora"""
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then
                make new document
            end if
            set URL of front document to "{SORA_URL}"
        end tell
        
        delay 3
        return "opened"
        '''
        success, output = self._run_applescript(script)
        logger.info(f"Open Sora: {success}")
        return success
    
    def check_login_status(self) -> bool:
        """Check if logged into Sora"""
        script = '''
        tell application "Safari"
            set pageURL to URL of front document
            set pageContent to do JavaScript "document.body.innerText" in front document
        end tell
        
        if pageContent contains "Sign in" or pageContent contains "Log in" then
            return "not_logged_in"
        else
            return "logged_in"
        end if
        '''
        success, output = self._run_applescript(script)
        is_logged_in = success and output == "logged_in"
        logger.info(f"Login status: {'✅ Logged in' if is_logged_in else '❌ Not logged in'}")
        return is_logged_in
    
    def wait_for_login(self, timeout: int = 120) -> bool:
        """Wait for user to complete login"""
        logger.info("⏳ Waiting for user to log in to Sora...")
        start = time.time()
        while time.time() - start < timeout:
            if self.check_login_status():
                logger.info("✅ Login detected")
                return True
            time.sleep(3)
        logger.error("❌ Login timeout")
        return False
    
    def input_prompt_with_character(self, prompt: str, character: str = "isaiahdupree") -> bool:
        """
        Input prompt into Sora with @character mention.
        
        Uses clipboard paste for reliable text entry into React textarea.
        """
        # Build full prompt with character
        full_prompt = f"@{character} {prompt}"
        
        logger.info(f"Inputting prompt: {full_prompt[:80]}...")
        
        # Step 1: Copy prompt to clipboard
        import subprocess
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(full_prompt.encode('utf-8'))
        logger.info("Copied prompt to clipboard")
        
        # Step 2: Focus the textarea and click it
        focus_script = '''
        tell application "Safari"
            activate
            do JavaScript "
                var ta = document.querySelector('textarea');
                if (ta) { 
                    ta.focus(); 
                    ta.click();
                    'focused'; 
                } else { 
                    'not_found'; 
                }
            " in front document
        end tell
        '''
        success, output = self._run_applescript(focus_script)
        if "not_found" in output:
            logger.error("Textarea not found")
            return False
        
        time.sleep(0.5)
        
        # Step 3: Paste from clipboard using Cmd+V
        paste_script = '''
        tell application "System Events"
            keystroke "v" using command down
        end tell
        '''
        success, output = self._run_applescript(paste_script)
        
        time.sleep(0.5)
        
        # Step 4: Verify the text was entered
        verify_script = '''
        tell application "Safari"
            do JavaScript "
                var ta = document.querySelector('textarea');
                ta && ta.value.length > 0 ? 'has_text' : 'empty';
            " in front document
        end tell
        '''
        success, output = self._run_applescript(verify_script)
        
        if "has_text" in output:
            logger.info("✅ Prompt pasted successfully")
            return True
        else:
            logger.warning("Paste may have failed, textarea still empty")
            return False
    
    def set_duration(self, seconds: int = 15) -> bool:
        """
        Set video duration. Options: 10, 15, 25 seconds.
        Must be on Storyboard page for this to work.
        """
        logger.info(f"Setting duration to {seconds} seconds...")
        
        # Step 1: Click the duration button to open menu
        open_menu_script = '''
        tell application "Safari"
            do JavaScript "
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var txt = btns[i].textContent.trim();
                    if (txt.match(/^\\d+s$/)) {
                        btns[i].click();
                        break;
                    }
                }
                'opened_duration_menu';
            " in front document
        end tell
        '''
        self._run_applescript(open_menu_script)
        time.sleep(0.5)
        
        # Step 2: Select the desired duration
        select_script = f'''
        tell application "Safari"
            do JavaScript "
                var options = document.querySelectorAll('[role=menuitem], [role=option], [role=menuitemradio], [data-radix-collection-item]');
                var found = false;
                for (var i = 0; i < options.length; i++) {{
                    var txt = options[i].textContent.trim();
                    if (txt.includes('{seconds} seconds') || txt === '{seconds}s') {{
                        options[i].click();
                        found = true;
                        break;
                    }}
                }}
                found ? 'duration_set_{seconds}' : 'duration_option_not_found';
            " in front document
        end tell
        '''
        success, output = self._run_applescript(select_script)
        logger.info(f"Duration setting result: {output}")
        return success and "duration_set" in output
    
    def set_aspect_ratio(self, ratio: str = "Portrait") -> bool:
        """
        Set aspect ratio. Options: Portrait (9:16), Landscape (16:9).
        Must be on Storyboard page for this to work.
        """
        logger.info(f"Setting aspect ratio to {ratio}...")
        
        # Step 1: Click the aspect ratio button to open menu
        open_menu_script = '''
        tell application "Safari"
            do JavaScript "
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var txt = btns[i].textContent.trim();
                    if (txt === 'Portrait' || txt === 'Landscape' || txt === 'Square') {
                        btns[i].click();
                        break;
                    }
                }
                'opened_aspect_menu';
            " in front document
        end tell
        '''
        self._run_applescript(open_menu_script)
        time.sleep(0.5)
        
        # Step 2: Select the desired aspect ratio
        select_script = f'''
        tell application "Safari"
            do JavaScript "
                var options = document.querySelectorAll('[role=menuitem], [role=option], [role=menuitemradio], [data-radix-collection-item]');
                var found = false;
                for (var i = 0; i < options.length; i++) {{
                    var txt = options[i].textContent.trim();
                    if (txt === '{ratio}') {{
                        options[i].click();
                        found = true;
                        break;
                    }}
                }}
                found ? 'aspect_set_{ratio}' : 'aspect_option_not_found';
            " in front document
        end tell
        '''
        success, output = self._run_applescript(select_script)
        logger.info(f"Aspect ratio result: {output}")
        return success and "aspect_set" in output
    
    def navigate_to_storyboard(self) -> bool:
        """Navigate to the Storyboard page where all options are available"""
        logger.info("Navigating to Storyboard...")
        
        script = '''
        tell application "Safari"
            set URL of front document to "https://sora.chatgpt.com/storyboard"
        end tell
        '''
        success, output = self._run_applescript(script)
        time.sleep(2)
        return success
    
    def click_character(self, character: str = "isaiahdupree") -> bool:
        """Click on a character button to select it"""
        logger.info(f"Selecting character: @{character}...")
        
        script = f'''
        tell application "Safari"
            do JavaScript "
                var btns = document.querySelectorAll('button');
                var found = false;
                for (var i = 0; i < btns.length; i++) {{
                    var txt = btns[i].textContent.trim();
                    if (txt === '{character}') {{
                        btns[i].click();
                        found = true;
                        break;
                    }}
                }}
                found ? 'character_selected' : 'character_not_found';
            " in front document
        end tell
        '''
        success, output = self._run_applescript(script)
        logger.info(f"Character selection result: {output}")
        return success and "character_selected" in output
    
    def click_generate(self) -> bool:
        """Click the generate button - exact selector for 'Create video' button"""
        logger.info("Clicking generate button...")
        
        script = '''
        tell application "Safari"
            do JavaScript "
                // Find the 'Create video' button by text content
                var buttons = document.querySelectorAll('button');
                var genButton = null;
                
                for (var i = 0; i < buttons.length; i++) {
                    var txt = (buttons[i].textContent || '').trim().toLowerCase();
                    if (txt.includes('create video') || txt === 'create') {
                        genButton = buttons[i];
                        break;
                    }
                }
                
                if (genButton) {
                    if (genButton.disabled) {
                        'button_disabled_need_prompt';
                    } else {
                        genButton.click();
                        'generate_clicked';
                    }
                } else {
                    'create_button_not_found';
                }
            " in front document
        end tell
        '''
        success, output = self._run_applescript(script)
        logger.info(f"Generate button result: {output}")
        return success and "clicked" in output.lower()
    
    def get_page_state(self) -> str:
        """Get current page state for debugging"""
        script = '''
        tell application "Safari"
            set pageURL to URL of front document
            set pageTitle to name of front document
            return pageURL & " | " & pageTitle
        end tell
        '''
        success, output = self._run_applescript(script)
        return output if success else "unknown"
    
    async def send_prompt(
        self,
        prompt: str,
        character: str = "isaiahdupree",
        duration: int = 15,
        aspect_ratio: str = "Portrait"
    ):
        """
        Full flow to send a prompt to Sora with character.
        Uses Explore page which has character buttons and simple prompt input.
        
        Workflow:
        1. Navigate to Explore page
        2. Check/wait for login  
        3. Click character button to add @character to prompt
        4. Click Settings to open duration/aspect options
        5. Input remaining prompt text
        6. Click Create video
        """
        
        print("\n" + "="*60)
        print("SORA CHARACTER VIDEO GENERATION")
        print("="*60)
        print(f"Character: @{character}")
        print(f"Duration: {duration} seconds")
        print(f"Aspect Ratio: {aspect_ratio}")
        print(f"Prompt: {prompt[:60]}...")
        print("="*60 + "\n")
        
        # Step 1: Navigate to Explore page (has characters)
        logger.info("Step 1: Navigating to Explore page...")
        script = '''
        tell application "Safari"
            activate
            set URL of front document to "https://sora.chatgpt.com/explore"
        end tell
        '''
        self._run_applescript(script)
        await asyncio.sleep(3)
        
        # Step 2: Check login
        logger.info("Step 2: Checking login status...")
        if not self.check_login_status():
            logger.warning("⚠️ Not logged in - please log in manually...")
            if not self.wait_for_login(timeout=120):
                logger.error("Login timeout - aborting")
                return False
        
        await asyncio.sleep(1)
        
        # Step 3: Click character button to add to prompt
        logger.info(f"Step 3: Clicking @{character} character...")
        self.click_character(character)
        await asyncio.sleep(1)
        
        # Step 4: Open Settings and set duration/aspect
        logger.info("Step 4: Opening Settings for duration/aspect...")
        self._click_settings_button()
        await asyncio.sleep(1)
        
        # Step 5: Input remaining prompt (character already added)
        logger.info("Step 5: Entering prompt text...")
        # Just add the prompt text, character already inserted
        if not self._type_prompt_text(prompt):
            logger.warning("Could not type prompt")
        
        await asyncio.sleep(1)
        
        # Step 6: Click Create video
        logger.info("Step 6: Clicking Create video...")
        if self.click_generate():
            logger.info("✅ Create video clicked - generation started!")
            print("\n" + "="*60)
            print("✅ PROMPT SUBMITTED TO SORA")
            print("="*60)
            print("The video is now generating in Sora.")
            print(f"Character: @{character}")
            print("Check sora.com for generation progress.")
            print("="*60)
            return True
        else:
            logger.warning("⚠️ Could not auto-click Create - please click manually")
            print("\n" + "="*60)
            print("⚠️ MANUAL ACTION REQUIRED")
            print("="*60)
            print("The prompt and settings have been configured.")
            print("Please click the Create video button manually.")
            print("="*60)
            return False
    
    def _click_settings_button(self) -> bool:
        """Click the Settings button near Create video"""
        script = '''
        tell application "Safari"
            do JavaScript "
                var btns = document.querySelectorAll('button');
                var createBtn = null;
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].textContent.trim() === 'Create video') {
                        createBtn = btns[i];
                        break;
                    }
                }
                if (createBtn && createBtn.previousElementSibling) {
                    createBtn.previousElementSibling.click();
                    'settings_clicked';
                } else {
                    'settings_not_found';
                }
            " in front document
        end tell
        '''
        success, output = self._run_applescript(script)
        logger.info(f"Settings click: {output}")
        return success
    
    def _type_prompt_text(self, prompt: str) -> bool:
        """Type prompt text into the textarea (append to existing)"""
        # Copy to clipboard and paste
        import subprocess
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(f" {prompt}".encode('utf-8'))
        
        # Focus textarea and paste
        focus_script = '''
        tell application "Safari"
            do JavaScript "
                var ta = document.querySelector('textarea');
                if (ta) { ta.focus(); 'focused'; } else { 'not_found'; }
            " in front document
        end tell
        '''
        self._run_applescript(focus_script)
        time.sleep(0.3)
        
        # Move to end and paste
        paste_script = '''
        tell application "System Events"
            key code 119
            keystroke "v" using command down
        end tell
        '''
        success, output = self._run_applescript(paste_script)
        time.sleep(0.5)
        
        # Verify
        verify_script = '''
        tell application "Safari"
            do JavaScript "
                var ta = document.querySelector('textarea');
                ta && ta.value.length > 10 ? 'has_text' : 'empty';
            " in front document
        end tell
        '''
        success, output = self._run_applescript(verify_script)
        return "has_text" in output


async def main():
    """Test sending a 15 second video prompt with @isaiahdupree character"""
    
    automation = SoraCharacterAutomation()
    
    # Test prompt using the @isaiahdupree character
    prompt = """walking through a modern city at sunset, 
confident stride, cinematic lighting, shallow depth of field, 
urban environment with neon signs reflecting off wet pavement, 
professional cinematography, 4K quality"""
    
    await automation.send_prompt(
        prompt=prompt,
        character="isaiahdupree",
        duration=15
    )


if __name__ == "__main__":
    asyncio.run(main())
