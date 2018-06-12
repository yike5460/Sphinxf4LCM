#
# Copyright (c) 2018 by Spirent Communications Plc.
# All Rights Reserved.
#
# This software is confidential and proprietary to Spirent Communications Inc.
# No part of this software may be reproduced, transmitted, disclosed or used
# in violation of the Software License Agreement without the expressed
# written consent of Spirent Communications Inc.
#
#


import collections
import datetime
import functools

from threading import Lock


def generate_timestamp():
    """
    This function generates a timestamp.
    """

    return '{:%Y%m%d_%H%M%S}'.format(datetime.datetime.now())


def generate_name(name):
    """
    This function generates a unique name by adding a timestamp at the end of the provided name.
    """

    return '%s_%s' % (name, generate_timestamp())


def tee(iterable, n=2):
    """
    This function is based on the Python implementation of itertools.tee:
    https://docs.python.org/2/library/itertools.html#itertools.tee

    A lock was added for making it safe to use the teed iterators in separate threads.
    """
    it = iter(iterable)
    l = Lock()
    deques = [collections.deque() for i in range(n)]

    def gen(mydeque):
        while True:
            if not mydeque:  # when the local deque is empty
                with l:
                    newval = next(it)  # fetch a new value and
                for d in deques:  # load it to all the deques
                    d.append(newval)
            yield mydeque.popleft()

    return tuple(gen(d) for d in deques)


def recursive_map(func):
    @functools.wraps(func)
    def mapper(*args, **kwargs):
        data = kwargs.pop('data')

        if isinstance(data, dict):
            return {k: mapper(data=v, *args, **kwargs) for k, v in data.iteritems()}
        if isinstance(data, list):
            return map(lambda e: mapper(data=e, *args, **kwargs), data)
        return func(data=data, *args, **kwargs)

    return mapper
