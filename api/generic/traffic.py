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


import logging

from api.adapter import construct_adapter
from api.generic import ApiGenericError
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class TrafficGenericError(ApiGenericError):
    """
    A problem occurred in the VNF LifeCycle Validation traffic generic API.
    """
    pass


class Traffic(object):
    """
    Class of functions used to control the test traffic.
    """

    def __init__(self, vendor, adapter_config, **kwargs):
        self.vendor = vendor
        self.traffic_adapter = construct_adapter(vendor, module_type='traffic', **adapter_config)

    @log_entry_exit(LOG)
    def any_traffic_loss(self, delay_time=0, tolerance=0):
        """
        This function checks if any packets are dropped.

        :param delay_time:  Time, in seconds, to wait until polling for traffic.
        :param tolerance:   Acceptable percent of lost traffic.
        :return:            True if traffic flows with dropped packets, False otherwise
        """
        return self.traffic_adapter.any_traffic_loss(delay_time, tolerance)

    @log_entry_exit(LOG)
    def clear_counters(self):
        """
        This function clears all traffic counters.

        :return:    True if all counters have been cleared, False otherwise.
        """
        return self.traffic_adapter.clear_counters()

    @log_entry_exit(LOG)
    def config_traffic_load(self, traffic_load):
        return self.traffic_adapter.config_traffic_load(traffic_load)

    @log_entry_exit(LOG)
    def reconfig_traffic_dest(self, dest_addr_list):
        return self.traffic_adapter.reconfig_traffic_dest(dest_addr_list)

    @log_entry_exit(LOG)
    def configure(self, traffic_load, traffic_config):
        """
        This function applies the new traffic load and traffic configurations. If the traffic already flows, the
        parameters get applied at run time.

        :param traffic_load:    Possible values: 'LOW_TRAFFIC_LOAD', 'NORMAL_TRAFFIC_LOAD', 'MAX_TRAFFIC_LOAD',
                                                 'INITIAL', 'PERCENTAGE'
        :param traffic_config:  Specific information required to run the traffic.
        :return:                True if traffic load and configuration parameter were applied, False otherwise.
        """
        return self.traffic_adapter.configure(traffic_load, traffic_config)

    @log_entry_exit(LOG)
    def does_traffic_flow(self, delay_time=0):
        """
        This function checks if packets are received. Dropped packets may occur, but are not considered as a negative
        outcome of the function. If all packets get dropped, the function fails.

        :param delay_time:  Time, in seconds, to wait until polling for traffic.
        :return:            True if traffic flow is detected, False otherwise
        """
        return self.traffic_adapter.does_traffic_flow(delay_time)

    @log_entry_exit(LOG)
    def calculate_activation_time(self):
        return self.traffic_adapter.calculate_activation_time()

    @log_entry_exit(LOG)
    def calculate_deactivation_time(self):
        return self.traffic_adapter.calculate_deactivation_time()

    @log_entry_exit(LOG)
    def calculate_service_disruption_length(self):
        return self.traffic_adapter.calculate_service_disruption_length()

    @log_entry_exit(LOG)
    def start(self, delay_time=0, return_when_emission_starts=False):
        """
        This function starts the traffic emission.

        :param delay_time:                  Time, in seconds, to wait until starting traffic.
        :param return_when_emission_starts: Flag influencing if the command should return back immediately or only when
                                            the emission actually started.
        :return:                            True if emission stared, False otherwise.
        """
        return self.traffic_adapter.start(delay_time, return_when_emission_starts)

    @log_entry_exit(LOG)
    def stop(self, delay_time=0, return_when_emission_stops=True):
        """
        This function stops the traffic emission.

        :param delay_time:                  Time, in seconds, to wait until stopping traffic.
        :param return_when_emission_stops:  Flag influencing if the command should return back immediately or only when
                                            the emission actually stopped.
        :return:                            True if emission stopped, False otherwise.
        """
        return self.traffic_adapter.stop(delay_time, return_when_emission_stops)

    @log_entry_exit(LOG)
    def destroy(self):
        return self.traffic_adapter.destroy()
