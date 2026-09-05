from playwright.async_api import async_playwright
import base64

class Browser:
    def __init__(self):
        self._pw = None
        self._browser = None
        self.page = None

    async def start(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        self.page = await self._browser.new_page(viewport={"width": 1280, "height": 800})

    async def navigate(self, url):
        await self.page.goto(url, timeout=30000)
        return await self.snapshot()

    async def click(self, selector):
        await self.page.click(selector, timeout=10000)
        await self.page.wait_for_timeout(500)
        return await self.snapshot()

    async def type_text(self, selector, text):
        await self.page.fill(selector, text, timeout=10000)
        await self.page.wait_for_timeout(300)
        return await self.snapshot()

    async def extract(self):
        title = await self.page.title()
        text = await self.page.evaluate("() => document.body.innerText")
        url = self.page.url
        return {"title": title, "text": text[:3000], "url": url}

    async def scroll(self, direction, pixels=500):
        if direction == "down":
            await self.page.evaluate(f"window.scrollBy(0, {pixels})")
        else:
            await self.page.evaluate(f"window.scrollBy(0, -{pixels})")
        await self.page.wait_for_timeout(300)
        return await self.snapshot()

    async def back(self):
        await self.page.go_back()
        await self.page.wait_for_timeout(500)
        return await self.snapshot()

    async def snapshot(self):
        png = await self.page.screenshot()
        b64 = base64.b64encode(png).decode()
        url = self.page.url
        elements = await self.page.evaluate("""() =>
            Array.from(document.querySelectorAll('a,button,input,textarea,select,[role="button"],[onclick]'))
                .filter(el => el.offsetParent !== null)
                .slice(0, 30)
                .map((el, i) => ({
                    i,
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || el.value || el.placeholder || '').trim().slice(0, 60),
                    selector: el.id ? `#${el.id}` : (el.className ? `.${el.className.split(' ')[0]}` : el.tagName.toLowerCase())
                }))
        """)
        return {"screenshot": b64, "elements": elements, "url": url}

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
