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
        return await self.snapshot()

    async def type_text(self, selector, text):
        await self.page.fill(selector, text, timeout=10000)
        return await self.snapshot()

    async def extract(self):
        title = await self.page.title()
        text = await self.page.evaluate("() => document.body.innerText")
        return {"title": title, "text": text[:3000]}

    async def snapshot(self):
        png = await self.page.screenshot()
        b64 = base64.b64encode(png).decode()
        elements = await self.page.evaluate('''() =>
            Array.from(document.querySelectorAll('a,button,input,textarea,select'))
                .slice(0, 25)
                .map((el, i) => ({i, tag: el.tagName.toLowerCase(), text: (el.innerText || '').trim().slice(0, 60), placeholder: el.placeholder || ''}))
        ''')
        return {"screenshot": b64, "elements": elements}

    async def close(self):
        if self._browser: await self._browser.close()
        if self._pw: await self._pw.stop()