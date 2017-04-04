import logging

from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class OpenwrtVnfAdapter(object):
    def __init__(self):
        pass

    @log_entry_exit(LOG)
    def config_applied(self, **credentials):

        return True

    @log_entry_exit(LOG)
    def license_applied(self, **credentials):

        return True

    @log_entry_exit(LOG)
    def scale(self, vnf_instance_id, type, aspect_id, number_of_steps=1, additional_param=None):
        return None
