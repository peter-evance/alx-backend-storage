#!/usr/bin/env python3
"""
This module defines a web cache and tracker using Redis.
"""

import requests
import redis
from functools import wraps

# Connect to the Redis store
store = redis.Redis()


def count_url_access(method):
    """
    Decorator to count how many times a URL is accessed and cache its
    content.

    Args:
        method: The function to be decorated.

    Returns:
        function: Decorated function.
    """
    @wraps(method)
    def wrapper(url):
        """
        Wrapper function to count URL accesses, cache content, and call
        the original method.

        Args:
            url (str): The URL to be accessed.

        Returns:
            str: HTML content of the URL.
        """
        cached_key = "cached:" + url
        cached_data = store.get(cached_key)

        if cached_data:
            return cached_data.decode("utf-8")

        count_key = "count:" + url
        html = method(url)

        store.incr(count_key)
        store.set(cached_key, html)
        store.expire(cached_key, 10)  # Cache the content for 10 seconds

        return html

    return wrapper


@count_url_access
def get_page(url: str) -> str:
    """
    Retrieves the HTML content of a given URL.

    Args:
        url (str): The URL to fetch.

    Returns:
        str: HTML content of the URL.
    """
    res = requests.get(url)
    return res.text
