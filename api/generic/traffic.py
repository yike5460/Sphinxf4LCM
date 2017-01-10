import logging
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class Traffic(object):
    def __init__(self):
        pass

    @log_entry_exit(LOG)
    def configure(self, traffic_load, traffic_configuration_parameter):
        """
        This function applies the new traffic load and traffic configurations. If the traffic already flows, the
        parameters get applied at run time.

        :param traffic_load:                    Possible values: "LOW_TRAFFIC_LOAD", "NORMAL_TRAFFIC_LOAD",
                                                                 "MAX_TRAFFIC_LOAD", "INITIAL", "PERCENTAGE"
        :param traffic_configuration_parameter: Specific information required to run the traffic.
        :return:                                True if traffic load and configuration parameter were applied, False
                                                otherwise.
        """

        return True

    @log_entry_exit(LOG)
    def does_traffic_flow(self):
        """
        This function checks if packets are received. Dropped packets may occur, but are not considered as a negative
        outcome of the function. If all packets get dropped, the function fails.

        :return: True if traffic flow is detected, False otherwise
        """

        return True

    @log_entry_exit(LOG)
    def start(self, delay_time=0, return_when_emission_starts=True):
        """
        This function starts the traffic emission.

        :param delay_time:                  Time, in seconds, to wait until starting traffic.
        :param return_when_emission_starts: Flag influencing if the command should return back immediately or only when
                                            the emission actually started.
        :return:                            True if emission stared, False otherwise.
        """

        return True

    @log_entry_exit(LOG)
    def stop(self, delay_time=0, return_when_emission_stops=True):
        """
        This function stops the traffic emission.

        :param delay_time:                  Time, in seconds, to wait until stopping traffic.
        :param return_when_emission_stops:  Flag influencing if the command should return back immediately or only when
                                            the emission actually stopped.
        :return:                            True if emission stopped, False otherwise.
        """

        return True

    @log_entry_exit(LOG)
    def clear_counters(self):
        """
        This function clears all traffic counters.

        :return:                            True if all counters have been cleared, False otherwise.
        """

        return True
