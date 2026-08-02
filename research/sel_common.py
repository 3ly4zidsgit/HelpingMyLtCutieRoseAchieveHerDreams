from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, random

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

def driver(headless=True):
    o = Options()
    if headless:
        o.add_argument("--headless=new")
    o.add_argument("--window-size=1920,1080")
    o.add_argument(f"--user-agent={UA}")
    o.add_argument("--lang=fr-FR,fr")
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--disable-gpu")
    o.add_argument("--log-level=3")
    o.add_argument("--blink-settings=imagesEnabled=false")
    o.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    o.add_experimental_option("useAutomationExtension", False)
    # 'eager' returns as soon as the DOM is interactive: these job pages keep
    # loading trackers/ads forever and would otherwise burn the full timeout.
    o.page_load_strategy = "eager"
    o.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    })
    d = webdriver.Chrome(options=o)
    d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """
        Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
        Object.defineProperty(navigator,'languages',{get:()=>['fr-FR','fr','en-US','en']});
        Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
        window.chrome = {runtime:{}};
    """})
    d.set_page_load_timeout(22)
    return d

def get(d, url, wait_css=None, timeout=20, settle=2.0):
    try:
        d.get(url)
    except Exception:
        pass
    if wait_css:
        try:
            WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_css)))
        except Exception:
            pass
    time.sleep(settle + random.uniform(0, 0.8))
    return d.page_source
