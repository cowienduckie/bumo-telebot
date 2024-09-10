import logging
import re
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


class FacebookCrawler:
    DELAY_TIME_LOAD = 12
    PAGE_TIMEOUT = 75

    def __init__(self, logger: logging):
        self.logging = logger

        self._setup_Chrome()

    def _setup_Chrome(self):
        """
        Setup Chrome options
        """
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--enable-javascript")
        self.chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36"
        )

    def get_latest_post(self, page_id: str) -> Optional[str]:
        """
        Get the latest post from a Facebook page
        """
        driver = webdriver.Chrome(options=self.chrome_options)
        page_url = f"https://www.facebook.com/{page_id}"
        latest_post_url = None

        try:
            driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36"
                },
            )

            # time.sleep(self.DELAY_TIME_LOAD)
            driver.get(page_url)

            wait = WebDriverWait(driver, self.PAGE_TIMEOUT)
            wait.until(
                ec.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
            )

            logging.info(f"Finding first post on page_url={page_url}")
            link_element = self.find_post_link(driver)

            if link_element is None:
                logging.error("Post link not found.")
                return None

            url = link_element.get_attribute("href")

            logging.info(f"Found URL: {url}")
            latest_post_url = self.clean_url(url)
        except Exception as ex:
            logging.error(f"Exception: {ex}")
        finally:
            driver.quit()
            return latest_post_url

    @staticmethod
    def find_post_link(driver) -> Optional[str]:
        """
        Find the first post link among all anchor tags
        """
        # Find all anchor tags
        anchors = driver.find_elements(By.TAG_NAME, "a")

        # Regular expression to match Facebook post URLs
        fb_post_regex = re.compile(r"https://www\.facebook\.com/[^/]+/posts/")
        for anchor in anchors:
            href = anchor.get_attribute("href")
            if fb_post_regex.match(href):
                return anchor

        return None

    @staticmethod
    def clean_url(url: str) -> str:
        """
        Clean the URL by removing the query string and fragment
        """
        # Find the indices of the query string and fragment
        query_index = url.find("?")
        fragment_index = url.find("#")

        # If neither the query string nor the fragment is found, return the URL as is
        if query_index == -1 and fragment_index == -1:
            return url

        # Find the cutoff index
        cutoff_index = (
            min(query_index, fragment_index)
            if query_index != -1 and fragment_index != -1
            else max(query_index, fragment_index)
        )

        return url[:cutoff_index]
