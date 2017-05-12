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
    def query_compute_capacity(self, zone_id=None, compute_resource_type_id=None, resource_criteria=None,
                               attribute_selector=None, time_period=None):
        """
        This function retrieves capacity information for the various types of consumable virtualised compute resources
        available in the Virtualised Compute Resources Information Management Interface.

        This function was written in accordance with section 7.3.4.3 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param zone_id:                     When specified this parameter identifies the resource zone for which the
                                            capacity is requested.
        :param compute_resource_type_id:    Identifier of the resource type for which the issuer wants to know the
                                            available, total, reserved and/or allocated capacity.
        :param resource_criteria:           Input capacity computation parameter for selecting the virtual memory,
                                            virtual CPU and acceleration capabilities for which the issuer wants to know
                                            the available, total, reserved and/or allocated capacity.
        :param attribute_selector:          Input parameter for selecting which capacity information (i.e. available,
                                            total, reserved and/or allocated capacity) is queried.
        :param time_period:                 The time interval for which capacity is queried.
        :return:                            Element containing the capacity during the requested time period.
        """
        return self.vim_adapter.query_compute_capacity(zone_id, compute_resource_type_id, resource_criteria,
                                                       attribute_selector, time_period)

    @log_entry_exit(LOG)
    def query_storage_capacity(self, zone_id=None, storage_resource_type_id=None, resource_criteria=None,
                               attribute_selector=None, time_period=None):
        """
        This function retrieves capacity information for the various types of consumable virtualised storage resources
        available in the Virtualised Storage Resources Information Management Interface.

        This function was written in accordance with section 7.5.4.2 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param zone_id:                     When specified this parameter identifies the resource zone for which the
                                            capacity is requested.
        :param storage_resource_type_id:    Identifier of the resource type for which the issuer wants to know the
                                            available, total, reserved and/or allocated capacity.
        :param resource_criteria:           Input capacity computation parameter for selecting the characteristics of
                                            the virtual storage for which the issuer wants to know the available, total,
                                            reserved and/or allocated capacity.
        :param attribute_selector:          Input parameter for selecting which capacity information (i.e. available,
                                            total, reserved and/or allocated capacity) is queried.
        :param time_period:                 The time interval for which capacity is queried.
        :return:                            Element containing the capacity during the requested time period.
        """
        return self.vim_adapter.query_storage_capacity(zone_id, storage_resource_type_id, resource_criteria,
                                                       attribute_selector, time_period)

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

        This function was written in accordance with section 7.3.1.3 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

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

        This function was written in accordance with section 7.4.1.3 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

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

        This function was written in accordance with section 7.5.1.3 of ETSI GS NFV-IFA 005 v2.1.1 (2016-04).

        :param query_storage_filter:        Query filter based on e.g. name, identifier, meta-data information or status
                                            information.
        :return:                            Element containing information about the virtual storage resource(s)
                                            matching the filter.
        """

        return self.vim_adapter.query_virtualised_storage_resource(query_storage_filter)

    @log_entry_exit(LOG)
    def create_compute_resource_reservation(self, resource_group_id, compute_pool_reservation=None,
                                            virtualisation_container_reservation=None, affinity_constraint=None,
                                            anti_affinity_constraint=None, start_time=None, end_time=None,
                                            expiry_time=None, location_constraints=None):
        """
        This operation allows requesting the reservation of virtualised compute resources as indicated by the consumer
        functional block.

        This function was written in accordance with section 7.8.1.2 of ETSI NFV-IFA 005 v2.1.1 (2016-04).

        :param compute_pool_reservation:                Amount of compute resources that need to be reserved, e.g.
                                                        {"cpu_cores": 90, "vm_instances": 10, "ram": 10000}.
        :param virtualisation_container_reservation:    Virtualisation containers that need to be reserved (e.g.
                                                        following a specific compute "flavour").
        :param affinity_constraint:                     Element with affinity information of the virtualised compute
                                                        resources to reserve. For the resource reservation at resource
                                                        pool granularity level, identifies the affinity information of
                                                        the virtual compute pool resources to reserve. For the resource
                                                        reservation at virtual container granularity level, it defines
                                                        the affinity information of the virtualisation container(s) to
                                                        reserve.
        :param anti_affinity_constraint:                Element with anti-affinity information of the virtualised
                                                        compute resources to reserve. For the resource reservation at
                                                        resource pool granularity level, it defines the anti-affinity
                                                        information of the virtual compute pool resources to reserve.
                                                        For the resource reservation at virtual container granularity
                                                        level, it defines the anti-affinity information of the
                                                        virtualisation container(s) to reserve.
        :param start_time:                              Timestamp indicating the earliest time to start the consumption
                                                        of the resources. If the time value is 0, resources are reserved
                                                        for immediate use.
        :param end_time:                                Timestamp indicating the end time of the reservation (when the
                                                        issuer of the request expects that the resources will no longer
                                                        be needed) and used by theVIM to schedule the reservation. If
                                                        not present, resources are reserved for unlimited usage time.
        :param expiry_time:                             Timestamp indicating the time the VIM can release the
                                                        reservation in case no allocation request against this
                                                        reservation was made.
        :param location_constraints:                    If present, it defines location constraints for the resource(s)
                                                        is (are) requested to be reserved, e.g. in what particular
                                                        Resource Zone.
        :param resource_group_id:                       Unique identifier of the "infrastructure resource group",
                                                        logical grouping of virtual resources assigned to a tenant
                                                        within an Infrastructure Domain.
        :return: reservation_data:                      Element containing information about the reserved resource.
        """
        return self.vim_adapter.create_compute_resource_reservation(resource_group_id, compute_pool_reservation,
                                                                    virtualisation_container_reservation,
                                                                    affinity_constraint, anti_affinity_constraint,
                                                                    start_time, end_time, expiry_time,
                                                                    location_constraints)

    @log_entry_exit(LOG)
    def terminate_compute_resource_reservation(self, reservation_id):
        """
        This operation allows terminating one or more issued compute resource reservation(s). When the operation is done
        on multiple ids, it is assumed to be best-effort, i.e. it can succeed for a subset of the ids, and fail for the
        remaining ones.

        This function was written in accordance with section 7.8.1.5 of ETSI NFV-IFA 005 v2.1.1 (2016-04).

        :param reservation_id:      Identifier of the resource reservation(s) to terminate.
        :return: reservation_id:    Identifier of the resource reservation(s) successfully terminated.
        """

        return self.vim_adapter.terminate_compute_resource_reservation(reservation_id)

    @log_entry_exit(LOG)
    def create_network_resource_reservation(self, network_reservation, resource_group_id, start_time=None,
                                            end_time=None, expiry_time=None, affinity_constraint=None,
                                            anti_affinity_constraint=None, location_constraints=None):
        """
        This operation allows requesting the reservation of virtualised network resources as indicated by the consumer
        functional block.

        This function was written in accordance with section 7.8.2.2 of ETSI NFV-IFA 005 v2.1.1 (2016-04).

        :param network_reservation:         Type and configuration of virtualised network resources that need to be
                                            reserved, e.g. {"PublicIPs": 20}.
        :param resource_group_id:           Unique identifier of the "infrastructure resource group", logical grouping
                                            of virtual resources assigned to a tenant within an Infrastructure Domain.
        :param start_time:                  Timestamp to start the consumption of the resources. If the time value is 0,
                                            resources are reserved for immediate use.
        :param end_time:                    Timestamp indicating the end time of the reservation (when the issuer of the
                                            request expects that the resources will no longer be needed) and used by the
                                            VIM to schedule the reservation. If not present, resources are reserved for
                                            unlimited usage time.
        :param expiry_time:                 Timestamp indicating the time the VIM can release the reservation in case no
                                            allocation request against this reservation was made.
        :param affinity_constraint:         Element with affinity information of the virtual network resources to
                                            reserve.
        :param anti_affinity_constraint:    Element with anti-affinity information of the virtual network resources to
                                            reserve.
        :param location_constraints:        If present, it defines location constraints for the resource(s) is (are)
                                            requested to be reserved, e.g. in what particular Resource Zone.
        :return: reservation_data:          Element containing information about the reserved resource.
        """

        return self.vim_adapter.create_network_resource_reservation(self, network_reservation, resource_group_id,
                                                                    start_time, end_time, expiry_time,
                                                                    affinity_constraint, anti_affinity_constraint,
                                                                    location_constraints)

    @log_entry_exit(LOG)
    def terminate_network_resource_reservation(self, reservation_id):
        """
        This operation allows terminating one or more issued network resource reservation(s). When the operation is done
        on multiple ids, it is assumed to be best-effort, i.e. it can succeed for a subset of the ids, and fail for the
        remaining ones.

        This function was written in accordance with section 7.8.2.5 of ETSI NFV-IFA 005 v2.1.1 (2016-04).

        :param reservation_id:      Identifier of the resource reservation(s) to terminate.
        :return: reservation_id:    Identifier of the resource reservation(s) successfully terminated.
        """

        return self.vim_adapter.terminate_network_resource_reservation(reservation_id)

    @log_entry_exit(LOG)
    def create_storage_resource_reservation(self, storage_pool_reservation, resource_group_id, start_time=None,
                                            end_time=None, expiry_time=None, affinity_constraint=None,
                                            anti_affinity_constraint=None, location_constraints=None):
        """
        This operation allows requesting the reservation of virtualised storage resources as indicated by the consumer
        functional block.

        This function was written in accordance with section 7.8.3.2 of ETSI NFV-IFA 005 v2.1.1 (2016-04).

        :param storage_pool_reservation:    Type and configuration of virtualised storage that need to be reserved. E.g.
                                            amount of storage resources that need to be reserved, e.g. {"gigabytes":
                                            1000, "snapshots": 10, "volumes": 10}.
        :param resource_group_id:           Unique identifier of the "infrastructure resource group", logical grouping
                                            of virtual resources assigned to a tenant within an Infrastructure Domain.
        :param start_time:                  Timestamp to start the consumption of the resources. If the time values is
                                            0, resources are reserved for immediate use.
        :param end_time:                    Timestamp indicating the end time of the reservation (when the issuer of
                                            the request expects that the resources will no longer be needed) and used
                                            by the VIM to schedule the reservation. If not present, resources are
                                            reserved for unlimited usage time.
        :param expiry_time:                 Timestamp indicating the time the VIM can release the reservation in case
                                            no allocation request against this reservation was made.
        :param affinity_constraint:         Element with affinity information of the virtual storage resources to
                                            reserve.
        :param anti_affinity_constraint:    Element with anti-affinity information of the virtual storage resources to
                                            reserve.
        :param location_constraints:        If present, it defines location constraints for the resource(s) is (are)
                                            requested to be reserved, e.g. in what particular Resource Zone.
        :return: reservation_data:          Element containing information about the reserved resource.
        """

        return self.create_storage_resource_reservation(self, storage_pool_reservation, resource_group_id, start_time,
                                                        end_time, expiry_time, affinity_constraint,
                                                        anti_affinity_constraint, location_constraints)

    @log_entry_exit(LOG)
    def terminate_storage_resource_reservation(self, reservation_id):
        """
        This operation allows terminating one or more issued storage resource reservation(s). When the operation is
        done on multiple ids, it is assumed to be best-effort, i.e. it can succeed for a subset of the ids, and fail
        for the remaining ones.

        This function was written in accordance with section 7.8.3.5 of ETSI NFV-IFA 005 v2.1.1 (2016-04).

        :param reservation_id:      Identifier of the resource reservation(s) to terminate.
        :return: reservation_id:    Identifier of the resource reservation(s) successfully terminated.
        """

        return self.vim_adapter.terminate_storage_resource_reservation(reservation_id)
