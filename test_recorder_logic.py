import asyncio
from backend.agent.recorder_agent import recorder_agent
from backend.config.config_manager import config_manager

async def test():
    print("Testing Recorder Agent...")
    config_manager.save_config({"DEFAULT_URL": "about:blank", "INC_MODE": True})

    # Start session
    page = await recorder_agent.start_session()
    print("Session started")

    # Simulate an action from the browser
    await page.evaluate("""
        window.emitRecorderAction({
            action: 'CLICK',
            selector: 'button#test',
            text: 'Test Button',
            url: 'https://example.com'
        });
    """)
    print("Simulated action sent")

    # Wait for action to be processed
    await asyncio.sleep(2)

    # Stop session
    actions = await recorder_agent.stop_session()
    print(f"Captured actions: {len(actions)}")
    for a in actions:
        print(f" - {a['action']} at {a.get('url')}")

    if len(actions) > 0:
        print("✅ SUCCESS: Actions recorded!")
    else:
        print("❌ FAILURE: No actions recorded.")

if __name__ == "__main__":
    asyncio.run(test())
