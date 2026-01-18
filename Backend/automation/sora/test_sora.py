#!/usr/bin/env python3
"""
Test script for Sora browser automation.

Run with: python -m automation.sora.test_sora
"""
import asyncio
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from automation.sora.sora_controller import SoraController
from automation.sora.pipeline import SoraPipeline


async def test_sora_launch():
    """Test 1: Launch Sora in Safari"""
    print("\n" + "="*60)
    print("TEST 1: Launch Sora in Safari")
    print("="*60)
    
    controller = SoraController()
    
    print("\n🚀 Launching Sora...")
    success = await controller.launch_sora()
    
    if success:
        print("✅ Safari launched with Sora")
    else:
        print("❌ Failed to launch Sora")
        return False
    
    await asyncio.sleep(2)
    return True


async def test_login_status():
    """Test 2: Check login status"""
    print("\n" + "="*60)
    print("TEST 2: Check Login Status")
    print("="*60)
    
    controller = SoraController()
    
    print("\n🔍 Checking login status...")
    status = await controller.check_login_status()
    
    print(f"   Logged in: {status.get('logged_in', False)}")
    print(f"   Has create UI: {status.get('has_create_ui', False)}")
    print(f"   URL: {status.get('url', 'N/A')}")
    
    if status.get('error'):
        print(f"   Error: {status.get('error')}")
    
    return status.get('logged_in', False)


async def test_page_state():
    """Test 3: Get page state"""
    print("\n" + "="*60)
    print("TEST 3: Get Page State")
    print("="*60)
    
    controller = SoraController()
    
    print("\n📊 Analyzing page...")
    state = await controller.get_page_state()
    
    print(f"   URL: {state.get('url', 'N/A')}")
    print(f"   Title: {state.get('title', 'N/A')}")
    print(f"   Has prompt input: {state.get('has_prompt_input', False)}")
    print(f"   Has generate button: {state.get('has_generate_button', False)}")
    print(f"   Video count: {state.get('video_count', 0)}")
    
    if state.get('error'):
        print(f"   Error: {state.get('error')}")
    
    return state.get('has_prompt_input', False)


async def test_prompt_input(prompt: str = "A serene lake at sunset with gentle ripples"):
    """Test 4: Input a prompt (without generating)"""
    print("\n" + "="*60)
    print("TEST 4: Input Prompt")
    print("="*60)
    
    controller = SoraController()
    
    print(f"\n📝 Entering prompt: '{prompt[:50]}...'")
    success = await controller.input_prompt(prompt)
    
    if success:
        print("✅ Prompt entered successfully")
    else:
        print("❌ Failed to enter prompt")
    
    return success


async def run_all_tests():
    """Run all Sora tests"""
    print("\n" + "#"*60)
    print("#" + " "*20 + "SORA AUTOMATION TESTS" + " "*17 + "#")
    print("#"*60)
    
    results = {}
    
    # Test 1: Launch
    results['launch'] = await test_sora_launch()
    
    if not results['launch']:
        print("\n❌ Cannot continue - Sora launch failed")
        return results
    
    await asyncio.sleep(3)
    
    # Test 2: Login status
    results['login'] = await test_login_status()
    
    # Test 3: Page state
    results['page_state'] = await test_page_state()
    
    # Test 4: Prompt input (only if logged in)
    if results['login']:
        results['prompt_input'] = await test_prompt_input()
    else:
        print("\n⚠️  Skipping prompt test - not logged in")
        results['prompt_input'] = None
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else ("⏭️ SKIP" if passed is None else "❌ FAIL")
        print(f"   {test}: {status}")
    
    passed = sum(1 for v in results.values() if v is True)
    total = sum(1 for v in results.values() if v is not None)
    print(f"\n   Total: {passed}/{total} tests passed")
    
    return results


async def interactive_mode():
    """Interactive mode for manual testing"""
    print("\n" + "#"*60)
    print("#" + " "*15 + "SORA INTERACTIVE MODE" + " "*16 + "#")
    print("#"*60)
    
    pipeline = SoraPipeline()
    
    print("\n1. Launching Sora...")
    await pipeline.controller.launch_sora()
    await asyncio.sleep(3)
    
    print("\n2. Checking login...")
    status = await pipeline.controller.check_login_status()
    
    if not status.get('logged_in'):
        print("\n⚠️  Not logged in! Please log in manually in Safari.")
        input("   Press Enter when ready...")
    
    print("\n3. Ready for commands!")
    print("   Commands: 'prompt <text>', 'generate', 'status', 'download', 'quit'")
    
    while True:
        try:
            cmd = input("\n> ").strip()
            
            if not cmd:
                continue
            
            if cmd.lower() in ['quit', 'exit', 'q']:
                break
            
            if cmd.startswith('prompt '):
                text = cmd[7:]
                print(f"   Entering prompt: {text[:50]}...")
                success = await pipeline.controller.input_prompt(text)
                print(f"   {'✅ Done' if success else '❌ Failed'}")
            
            elif cmd == 'generate':
                print("   Clicking generate...")
                success = await pipeline.controller.click_generate()
                print(f"   {'✅ Started' if success else '❌ Failed'}")
            
            elif cmd == 'status':
                status = await pipeline.controller.get_generation_status()
                print(f"   Status: {status.get('status', 'unknown')}")
                if status.get('progress_percent'):
                    print(f"   Progress: {status.get('progress_percent')}%")
                if status.get('video_src'):
                    print(f"   Video ready!")
            
            elif cmd == 'download':
                print("   Downloading...")
                path = await pipeline.downloader.download_current_video()
                if path:
                    print(f"   ✅ Downloaded: {path}")
                else:
                    print("   ❌ No video to download")
            
            elif cmd == 'state':
                state = await pipeline.controller.get_page_state()
                print(f"   URL: {state.get('url')}")
                print(f"   Has input: {state.get('has_prompt_input')}")
                print(f"   Has generate: {state.get('has_generate_button')}")
            
            else:
                print("   Unknown command. Try: prompt, generate, status, download, state, quit")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Sora browser automation")
    parser.add_argument('--interactive', '-i', action='store_true', help='Run in interactive mode')
    parser.add_argument('--test', '-t', type=str, help='Run specific test (launch, login, state, prompt)')
    args = parser.parse_args()
    
    if args.interactive:
        asyncio.run(interactive_mode())
    elif args.test:
        test_map = {
            'launch': test_sora_launch,
            'login': test_login_status,
            'state': test_page_state,
            'prompt': test_prompt_input,
        }
        if args.test in test_map:
            asyncio.run(test_map[args.test]())
        else:
            print(f"Unknown test: {args.test}")
            print(f"Available: {', '.join(test_map.keys())}")
    else:
        asyncio.run(run_all_tests())
