import os
import time
from typing import List

import requests


class APIClient:
    def __init__(
        self,
        methods: List[str] | None = None,
        zenrows_key: str | None = None,
        scraperapi_key: str | None = None,
        pause_duration: int = 600,
        max_retries: int = 5,
    ):
        """
        zenrows_key: API key for Zenrows API.
        scraperapi_key: API key for ScraperAPI.
        pause_duration: Time to wait (in seconds) before retrying after all methods fail.
        max_retries: Maximum number of retries before giving up.
        """
        self.zenrows_key = (
            zenrows_key if zenrows_key is not None else os.environ.get("ZENROWS_KEY")
        )
        self.scraperapi_key = (
            scraperapi_key
            if scraperapi_key is not None
            else os.environ.get("SCRAPERAPI_KEY")
        )
        self.pause_duration = pause_duration
        self.max_retries = max_retries
        self.methods = methods if methods is not None else ["zenrows_api", "scraperapi"]
        self.method_success_rates = {
            method: {"success": 0, "total": 0} for method in self.methods
        }

    def update_success_rate(self, method_name, success):
        """
        Update the success rate for a given method.
        """
        if method_name in self.method_success_rates:
            self.method_success_rates[method_name]["total"] += 1
            if success:
                self.method_success_rates[method_name]["success"] += 1

    def sort_methods_by_success_rate(self):
        """
        Sort API methods by success rate (highest first).
        """

        def success_rate(method):
            stats = self.method_success_rates[method]
            return stats["success"] / stats["total"] if stats["total"] > 0 else 0

        self.methods.sort(key=success_rate, reverse=True)

    def make_api_request(self, url: str, headers=None, cookies=None, **kwargs):
        """
        Tries each specified API method and pauses if all fail, then retries.
        """
        available_methods = {
            "zenrows_api": self.zenrows_api,
            "scraperapi": self.scraperapi,
            "generic": self.generic,
        }

        retries = 0
        while retries < self.max_retries:
            self.sort_methods_by_success_rate()
            for method_name in self.methods:
                api_method = available_methods.get(method_name)
                if not api_method:
                    print(f"API method {method_name} not found.")
                    continue

                try:
                    response = api_method(
                        url, headers=headers, cookies=cookies, **kwargs
                    )
                    if response.status_code == 200:
                        self.update_success_rate(
                            method_name, response.status_code == 200
                        )
                        return response
                    else:
                        print(
                            f"API method {method_name} failed with status code {response.status_code}"
                        )
                except Exception as e:
                    self.update_success_rate(method_name, False)
                    print(f"Error with API method {method_name}: {e}")

            retries += 1
            if retries < self.max_retries:
                print(
                    f"All API methods failed. Pausing for {self.pause_duration / 60} minutes before retrying... Attempt {retries}/{self.max_retries}"
                )
                time.sleep(self.pause_duration)
            else:
                print("Maximum retries reached. No more attempts will be made.")

        return None

    def zenrows_api(self, url, headers=None, cookies=None, **kwargs):
        payload = {
            "apikey": self.zenrows_key,
            "url": url,
            "original_status": "true",
            "custom_headers": "true",
            **kwargs,
        }
        return requests.get(
            "https://api.zenrows.com/v1/",
            params=payload,
            headers=headers,
            cookies=cookies,
        )

    def scraperapi(self, url, headers=None, cookies=None, **kwargs):
        payload = {
            "api_key": self.scraperapi_key,
            "url": url,
            "keep_headers": "true",
            **kwargs,
        }
        return requests.get(
            "https://api.scraperapi.com/",
            params=payload,
            headers=headers,
            cookies=cookies,
        )

    def generic(self, url, headers=None, cookies=None, **kwargs):
        return requests.get(url, headers=headers, cookies=cookies, params=kwargs)
