import asyncio
from playwright.async_api import async_playwright


async def test():
    async with async_playwright() as p:
        try:
            b = await p.chromium.launch(headless=True)
            print("PLAYWRIGHT_OK")
            await b.close()
        except Exception as e:
            print(f"PLAYWRIGHT_FAIL: {e}")


asyncio.run(test())
