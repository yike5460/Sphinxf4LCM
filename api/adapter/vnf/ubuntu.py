import logging

from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class UbuntuVnfAdapter(object):
    def __init__(self):
        pass

    @log_entry_exit(LOG)
    def config_applied(self, **credentials):

        return True

    @log_entry_exit(LOG)
    def license_applied(self, **credentials):

        return True
