#!/usr/bin/env python3
"""
This module defines a Cache class and associated methods to interact with 
a Redis cache.
"""

import redis
from uuid import uuid4
from typing import Union, Callable, Optional
from functools import wraps


def count_calls(method: Callable) -> Callable:
    """
    Decorator to count the number of times a method of the Cache class is
    called.

    Args:
        method (Callable): The method to be decorated.

    Returns:
        Callable: Decorated method.
    """
    key = method.__qualname__

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        """
        Wrapper function to count calls and call the original method.

        Args:
            self: The instance of the Cache class.
            *args: Variable positional arguments.
            **kwargs: Variable keyword arguments.

        Returns:
            Any: Result of the original method.
        """
        self._redis.incr(key)
        return method(self, *args, **kwargs)

    return wrapper


def call_history(method: Callable) -> Callable:
    """
    Decorator to store the history of inputs and outputs for a specific
    function.

    Args:
        method (Callable): The method to be decorated.

    Returns:
        Callable: Decorated method.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        """
        Wrapper function to store input and output history and call the
        original method.

        Args:
            self: The instance of the Cache class.
            *args: Variable positional arguments.
            **kwargs: Variable keyword arguments.

        Returns:
            Any: Result of the original method.
        """
        input_str = str(args)
        self._redis.rpush(method.__qualname__ + ":inputs", input_str)

        output = str(method(self, *args, **kwargs))
        self._redis.rpush(method.__qualname__ + ":outputs", output)

        return output

    return wrapper


def replay(fn: Callable):
    """
    Display the history of calls for a specific function.

    Args:
        fn (Callable): The function for which the history will be
        displayed.
    """
    r = redis.Redis()
    func_name = fn.__qualname__
    call_count = int(r.get(func_name).decode("utf-8"))if r.exists(func_name) else 0

    print("{} was called {} times:".format(func_name, call_count))

    inputs = r.lrange("{}:inputs".format(func_name), 0, -1)
    outputs = r.lrange("{}:outputs".format(func_name), 0, -1)

    for inp, outp in zip(inputs, outputs):
        try:
            inp_str = inp.decode("utf-8")
        except UnicodeDecodeError:
            inp_str = "Unable to decode input"

        try:
            outp_str = outp.decode("utf-8")
        except UnicodeDecodeError:
            outp_str = "Unable to decode output"

        print("{}(*{}) -> {}".format(func_name, inp_str, outp_str))


class Cache:
    """
    The Cache class represents a cache using Redis.
    """

    def __init__(self):
        """
        Initializes an instance of the Cache class, connecting to Redis
        and flushing the database.
        """
        self._redis = redis.Redis(host='localhost', port=6379, db=0)
        self._redis.flushdb()

    @call_history
    @count_calls
    def store(self, data: Union[str, bytes, int, float]) -> str:
        """
        Stores the given data in Redis using a randomly generated key.

        Args:
            data (Union[str, bytes, int, float]): The data to be stored.

        Returns:
            str: The randomly generated key under which the data is stored.
        """
        random_key = str(uuid4())
        self._redis.set(random_key, data)
        return random_key

    def get(self, key: str, fn: Optional[Callable] = None) -> Union[str, bytes, int, float]:
        """
        Retrieves a value from Redis based on the provided key and optionally
        applies a conversion function.

        Args:
            key (str): The key for retrieving the value from Redis.
            fn (Optional[Callable]): A conversion function to be applied to
            the retrieved value. Defaults to None.

        Returns:
            Union[str, bytes, int, float]: The retrieved value, possibly
            converted by the provided function.
        """
        value = self._redis.get(key)
        if fn:
            value = fn(value)
        return value

    def get_str(self, key: str) -> str:
        """
        Retrieves a value as a string from Redis based on the provided key.

        Args:
            key (str): The key for retrieving the value from Redis.

        Returns:
            str: The retrieved value as a string.
        """
        value = self._redis.get(key)
        return value.decode("utf-8")

    def get_int(self, key: str) -> int:
        """
        Retrieves a value as an integer from Redis based on the provided
        key.

        Args:
            key (str): The key for retrieving the value from Redis.

        Returns:
            int: The retrieved value as an integer.
        """
        value = self._redis.get(key)
        try:
            value = int(value.decode("utf-8"))
        except (ValueError, TypeError):
            value = 0
        return value
