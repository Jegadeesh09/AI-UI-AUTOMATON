import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        try:
            # Try to launch with --incognito
            browser = await p.chromium.launch(headless=True, args=["--incognito"])
            page = await browser.new_page()
            await page.goto("about:blank")
            # We can't really see the "incognito" icon in a screenshot of a page
            # unless we take a screenshot of the whole window, which is hard.
            # But we can check if it's a fresh session.
            print("Browser launched successfully with --incognito")
            await browser.close()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
