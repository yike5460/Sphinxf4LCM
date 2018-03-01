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

from threading import Lock


def generate_name(name):
    """
    This function generates an unique name by adding a timestamp at the end of the provided name
    """

    new_name = str(name) + '_{:%Y_%m_%d_%H_%M_%S}'.format(datetime.datetime.now())
    return new_name


def tee(iterable, n=2):
    """
    This function is based on the Python implementation of itertools.tee:
    https://docs.python.org/2/library/itertools.html#itertools.tee

    A lock was added for making it safe to use the teed iterators in separate threads
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
