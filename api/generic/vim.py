import logging
from api.adapter import construct_adapter

LOG = logging.getLogger(__name__)


class Vim(object):
    def __init__(self, vendor=None, **kwargs):
        self.vendor = vendor
        self.vim_adapter = construct_adapter(vendor, 'vim', **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vim_adapter, attr)
