import logging
import time

from api.adapter.traffic import TrafficAdapterError
from utils.net import ping

LOG = logging.getLogger(__name__)


class PingTrafficAdapterError(TrafficAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation Ping traffic adapter API.
    """
    pass


class PingTrafficAdapter(object):
    def __init__(self):
        self.dest_addr_list = []
        self.traffic_started = False

    def configure(self, *args, **kwargs):
        pass

    def start(self, *args, **kwargs):
        self.traffic_started = True

    def stop(self, *args, **kwargs):
        self.traffic_started = False

    def reconfig_traffic_dest(self, dest_addr_list):
        self.dest_addr_list = dest_addr_list.split(' ')[:-1]

    def destroy(self, *args, **kwargs):
        pass

    def does_traffic_flow(self, delay_time):
        time.sleep(delay_time)
        if self.traffic_started:
            for dest_addr in self.dest_addr_list:
                if not ping(dest_addr):
                    return False
            return True
        else:
            return False

    def any_traffic_loss(self, delay_time, tolerance):
        for dest_addr in self.dest_addr_list:
            if not ping(dest_addr):
                return True
        return False

    def clear_counters(self):
        pass
