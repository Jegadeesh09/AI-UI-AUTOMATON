import asyncio
from backend.agent.recorder_agent import recorder_agent
from backend.config.config_manager import config_manager

async def test():
    print("Testing Recorder Agent V2...")
    config_manager.save_config({"DEFAULT_URL": "about:blank", "INC_MODE": True})

    # We need to run this in a headless environment that supports evaluating JS
    # Since we can't run headed in the sandbox, we'll use headless=True for start_session
    # but we need to modify recorder_agent temporarily to allow headless for testing.
    # Actually, recorder_agent uses config.get("HEADLESS_AGENT", True) for harvester,
    # but start_session uses headless=False hardcoded.
    # Let's temporarily patch it for this test.

    import backend.agent.recorder_agent as ra
    ra.RECORD_SCRIPT_JS = ra.RECORD_SCRIPT_JS.replace("headless=False", "headless=True")

    # Patch start_session to use headless=True
    original_start = recorder_agent.start_session
    async def patched_start():
        from playwright.async_api import async_playwright
        recorder_agent.actions = []
        recorder_agent.status = "recording"
        recorder_agent.p = await async_playwright().start()
        recorder_agent.browser = await recorder_agent.p.chromium.launch(headless=True)
        recorder_agent.context = await recorder_agent.browser.new_context()
        await recorder_agent.context.expose_function("emitRecorderAction", recorder_agent._on_action)
        await recorder_agent.context.add_init_script(ra.RECORD_SCRIPT_JS)
        page = await recorder_agent.context.new_page()
        return page

    recorder_agent.start_session = patched_start

    page = await recorder_agent.start_session()
    print("Session started (Headless)")

    # 1. Test CLICK
    await page.evaluate("""
        window.emitRecorderAction({
            action: 'CLICK',
            selector: 'button#test',
            text: 'Test Button',
            url: 'https://example.com'
        });
    """)

    # 2. Test TYPE (Direct emission)
    await page.evaluate("""
        window.emitRecorderAction({
            action: 'TYPE',
            selector: 'input#name',
            value: 'John Doe',
            url: 'https://example.com'
        });
    """)

    print("Actions emitted")
    await asyncio.sleep(2)

    actions = await recorder_agent.stop_session()
    print(f"Captured actions: {len(actions)}")
    for a in actions:
        print(f" - {a['action']} at {a.get('url')}")

    if len(actions) >= 2:
        print("✅ SUCCESS: Actions recorded!")
    else:
        print("❌ FAILURE: Actions missing.")

if __name__ == "__main__":
    asyncio.run(test())
