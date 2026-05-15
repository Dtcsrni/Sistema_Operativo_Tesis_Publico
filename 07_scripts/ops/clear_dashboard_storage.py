from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:18789/"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(URL, wait_until='networkidle')
        page.evaluate("localStorage.clear(); sessionStorage.clear();")
        context.clear_cookies()
        page.reload(wait_until='networkidle')
        print(f"Storage cleared and page reloaded: {page.url}")
        browser.close()

if __name__ == '__main__':
    main()
