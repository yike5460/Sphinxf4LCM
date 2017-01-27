import logging

from api.adapter import construct_adapter

LOG = logging.getLogger(__name__)


class Vim(object):
    """
    Generic VIM class.
    """
    def __init__(self, vendor=None, **kwargs):
        """
        Construct the VIM object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.vim_adapter = construct_adapter(vendor, module_type='vim', **kwargs)

    def __getattr__(self, attr):
        return getattr(self.vim_adapter, attr)
