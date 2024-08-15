import logging
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


class FacebookCrawler:
    DELAY_TIME_LOAD = 12
    PAGE_TIMEOUT = 75

    def __init__(self, logger: logging):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--enable-javascript")
        self.chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36"
        )

        self.logging = logger

    def get_latest_post(self, page_id):
        driver = webdriver.Chrome(options=self.chrome_options)

        page_url = f"https://www.facebook.com/{page_id}"

        try:
            return self._get_latest_post(driver, page_url)
        except Exception as ex:
            logging.error(f"Exception: {ex}")
            return None
        finally:
            driver.quit()

    def _get_latest_post(self, driver, page_url):
        try:
            driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36"
            })

            time.sleep(self.DELAY_TIME_LOAD)
            driver.get(page_url)

            wait = WebDriverWait(driver, self.PAGE_TIMEOUT)
            wait.until(ec.presence_of_element_located(
                (By.CSS_SELECTOR, "div[role='main']")))

            logging.info(f"Finding first post on page_url={page_url}")
            link_element = self.find_post_link(driver)

            if link_element is None:
                logging.error("Post link not found.")
                return None

            url = link_element.get_attribute("href")

            logging.info(f"Found URL: {url}")
            return self.clean_url(url)
        except Exception as ex:
            logging.error(f"Exception: {ex}")
            return None

    @staticmethod
    def find_post_link(driver):
        links = driver.find_elements(By.TAG_NAME, "a")
        regex = re.compile(r"https://www\.facebook\.com/[^/]+/posts/")

        for link in links:
            href = link.get_attribute("href")
            if regex.match(href):
                return link
        return None

    @staticmethod
    def clean_url(url):
        if not url:
            return url

        query_index = url.find('?')
        fragment_index = url.find('#')

        if query_index == -1 and fragment_index == -1:
            return url

        cutoff_index = min(query_index, fragment_index) if query_index != -1 and fragment_index != -1 else max(
            query_index, fragment_index)

        return url[:cutoff_index]
