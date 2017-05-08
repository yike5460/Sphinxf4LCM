import logging

from api.adapter import construct_adapter
from utils.logging_module import log_entry_exit

# Instantiate logger
LOG = logging.getLogger(__name__)


class Vim(object):
    """
    Class of generic functions representing operations exposed by the VIM towards the NFVO as defined by 
    ETSI GS NFV-IFA 005 v2.1.1 (2016-04).
    """
    def __init__(self, vendor=None, **kwargs):
        """
        Construct the VIM object corresponding to the specified vendor.
        """
        self.vendor = vendor
        self.vim_adapter = construct_adapter(vendor, module_type='vim', **kwargs)

    @log_entry_exit(LOG)
    def query_compute_resource_quota(self, query_compute_quota_filter=None):
        """
        This function queries the VIM to get information about compute resources that the consumer has access to.

        This function was written in accordance with section 7.9.1.3 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param query_compute_quota_filter:  Query filter based on e.g. name, identifier, meta-data information or status
                                            information, expressing the type of information to be retrieved. It can also
                                            be used to specify one or more resources to be queried by providing their
                                            identifiers.

        :return:                            Element containing information about the quota resource. The cardinality can
                                            be 0 if no matching quota exists.
        """
        return self.vim_adapter.query_compute_resource_quota(query_compute_quota_filter)

    @log_entry_exit(LOG)
    def query_network_resource_quota(self, query_network_quota_filter=None):
        """
        This function queries the VIM to get information about network resources that the consumer has access to.

        This function was written in accordance with section 7.9.2.3 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param query_network_quota_filter:  Query filter based on e.g. name, identifier, meta-data information or status
                                            information, expressing the type of information to be retrieved. It can also
                                            be used to specify one or more resources to be queried by providing their
                                            identifiers.

        :return:                            Element containing information about the quota resource. The cardinality can
                                            be 0 if no matching quota exists.
        """
        return self.vim_adapter.query_network_resource_quota(query_network_quota_filter)

    @log_entry_exit(LOG)
    def query_storage_resource_quota(self, query_storage_quota_filter=None):
        """
        This function queries the VIM to get information about storage resources that the consumer has access to.

        This function was written in accordance with section 7.9.3.3 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param query_storage_quota_filter:  Query filter based on e.g. name, identifier, meta-data information or status
                                            information, expressing the type of information to be retrieved. It can also
                                            be used to specify one or more resources to be queried by providing their
                                            identifiers.

        :return:                            Element containing information about the quota resource. The cardinality can
                                            be 0 if no matching quota exists.
        """
        return self.vim_adapter.query_storage_resource_quota(query_storage_quota_filter)

    @log_entry_exit(LOG)
    def query_virtualised_compute_resource(self, query_compute_filter):
        """
        This function allows querying information about instantiated virtualised compute resources.

        This function was written in accordance with section 7.3.1.3 and 8.4.3 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param query_compute_filter:        Query filter based on e.g. name, identifier, meta-data information or status
                                            information.
        :return:                            Element containing information about the virtual compute resource(s)
                                            matching the filter.
        """

        return self.vim_adapter.query_virtualised_compute_resource(query_compute_filter)

    @log_entry_exit(LOG)
    def query_virtualised_network_resource(self, query_network_filter):
        """
        This function allows querying information about instantiated virtualised network resources.

        This function was written in accordance with section 7.4.1.3 and 8.4.5 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param query_network_filter:        Query filter based on e.g. name, identifier, meta-data information or status
                                            information.
        :return:                            Element containing information about the virtual network resource(s)
                                            matching the filter.
        """

        return self.vim_adapter.query_virtualised_network_resource(query_network_filter)

    @log_entry_exit(LOG)
    def query_virtualised_storage_resource(self, query_storage_filter):
        """
        This function allows querying information about instantiated virtualised storage resources.

        This function was written in accordance with section 7.5.1.3 and 8.4.7 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param query_storage_filter:        Query filter based on e.g. name, identifier, meta-data information or status
                                            information.
        :return:                            Element containing information about the virtual storage resource(s)
                                            matching the filter.
        """

        return self.vim_adapter.query_virtualised_storage_resource(query_storage_filter)
