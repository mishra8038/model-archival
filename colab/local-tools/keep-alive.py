"""
Colab session keep-alive — runs on your LOCAL machine.

Keeps a Google Colab browser session alive by periodically clicking
the "Run cell" button using Selenium. Useful when Pro+ background
execution is unreliable or you're on the free tier.

Requirements (on your local dev machine):
    pip install selenium webdriver-manager

Usage:
    python colab/local-tools/keep-alive.py --url "https://colab.research.google.com/drive/YOUR_NOTEBOOK_ID"

The script:
1. Opens Chrome to the Colab URL
2. Waits for you to sign in (60-second window)
3. Clicks "Connect" if not already connected
4. Every N minutes, scrolls the page and executes a no-op cell to reset idle timer
5. Logs activity to keep-alive.log

Stop with Ctrl+C.

NOTE: This is a last resort. Colab Pro+ with background execution enabled
is more reliable. Use this only if background execution is not available.
"""

import argparse
import logging
import time
import sys
from datetime import datetime
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, WebDriverException
    )
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install selenium webdriver-manager")
    sys.exit(1)

# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("keep-alive.log"),
    ],
)
log = logging.getLogger("keep-alive")

PING_INTERVAL_MINUTES = 10    # How often to ping Colab (minutes)
LOGIN_TIMEOUT_SECONDS = 90    # How long to wait for manual login
CONNECT_TIMEOUT = 30          # How long to wait for runtime connection


def build_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    # Use a persistent profile so Google login is remembered
    profile_dir = Path.home() / ".colab-keepalive-profile"
    profile_dir.mkdir(exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_dir}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def wait_for_login(driver: webdriver.Chrome, timeout: int) -> bool:
    """Wait until the notebook iframe is present (indicates successful login)."""
    log.info("Waiting for login / page load (up to %ds)...", timeout)
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "colab-connect-button, .codecell-input-area")
            )
        )
        return True
    except TimeoutException:
        return False


def click_connect(driver: webdriver.Chrome) -> bool:
    """Click the Connect button if the runtime is disconnected."""
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "colab-connect-button")
        status = btn.get_attribute("data-status") or ""
        if "connected" not in status.lower():
            log.info("Clicking Connect button...")
            btn.click()
            time.sleep(5)
            return True
    except NoSuchElementException:
        pass
    return False


def ping(driver: webdriver.Chrome) -> None:
    """
    Execute a lightweight no-op in the notebook to reset the idle timer.
    Finds the first code cell and executes it via keyboard shortcut.
    """
    try:
        # Scroll to top of notebook
        driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(1)

        # Try to find and click a cell to focus it
        cells = driver.find_elements(By.CSS_SELECTOR, ".codecell-input-area")
        if cells:
            cells[0].click()
            time.sleep(0.5)

        # Execute via Colab's toolbar API (more reliable than keyboard shortcuts)
        driver.execute_script("""
            try {
                // Reset idle timeout by interacting with the notebook
                const event = new MouseEvent('mousemove', {bubbles: true});
                document.dispatchEvent(event);
            } catch(e) {}
        """)
        log.info("Pinged at %s", datetime.now().strftime("%H:%M:%S"))
    except WebDriverException as e:
        log.warning("Ping failed: %s", e)


def run_keepalive(url: str, interval_minutes: int, headless: bool) -> None:
    log.info("Starting keep-alive for: %s", url)
    log.info("Ping interval: %d minutes", interval_minutes)

    driver = build_driver(headless=headless)

    try:
        driver.get(url)
        log.info("Opened notebook. Please sign in if prompted (you have %ds).", LOGIN_TIMEOUT_SECONDS)

        if not wait_for_login(driver, LOGIN_TIMEOUT_SECONDS):
            log.error("Could not detect notebook after %ds. Exiting.", LOGIN_TIMEOUT_SECONDS)
            return

        log.info("Notebook loaded.")
        click_connect(driver)
        time.sleep(10)

        log.info("Keep-alive running. Press Ctrl+C to stop.")
        interval_seconds = interval_minutes * 60

        while True:
            ping(driver)
            # Check connection status
            try:
                click_connect(driver)  # reconnects if dropped
            except Exception:
                pass
            log.info("Sleeping %d minutes until next ping...", interval_minutes)
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        log.info("Stopped by user.")
    except Exception as e:
        log.error("Unexpected error: %s", e)
    finally:
        driver.quit()
        log.info("Browser closed.")


def main():
    parser = argparse.ArgumentParser(
        description="Keep a Google Colab session alive from your local machine."
    )
    parser.add_argument(
        "--url", required=True,
        help='Full Colab notebook URL, e.g. "https://colab.research.google.com/drive/ABC123"'
    )
    parser.add_argument(
        "--interval", type=int, default=PING_INTERVAL_MINUTES,
        help=f"Minutes between pings (default: {PING_INTERVAL_MINUTES})"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run Chrome headless (no window). NOTE: Google may block headless login."
    )
    args = parser.parse_args()
    run_keepalive(args.url, args.interval, args.headless)


if __name__ == "__main__":
    main()
