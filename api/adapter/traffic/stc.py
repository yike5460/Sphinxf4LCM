import logging
import time
from threading import Lock, Thread

from stcrestclient import resthttp, stchttp

from api.adapter.traffic import TrafficAdapterError
from api.generic import constants
from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class StcTrafficAdapterError(TrafficAdapterError):
    """
    A problem occurred in the VNF LifeCycle Validation STC traffic adapter API.
    """
    pass


class StcTrafficAdapter(object):
    def __init__(self, lab_server_addr, user_name, session_name):
        try:
            self.stc = stchttp.StcHttp(lab_server_addr)
            self.session = self.stc.new_session(user_name=user_name, session_name=session_name, kill_existing=True)
            self.project = self.stc.create(object_type='project')
        except Exception as e:
            raise StcTrafficAdapterError(e.message)
        self.tx_results = None
        self.rx_results = None
        self.tx_port = None
        self.rx_port = None
        self.stream_block = None
        self.arp_needed = None

        self._attempt_to_start_traffic = False
        self._traffic_attempt_lock = Lock()

        self._emission_started = False
        self._emission_lock = Lock()

        self._service_disruption_length = None
        self._service_disruption_lock = Lock()

    @property
    def attempt_to_start_traffic(self):
        with self._traffic_attempt_lock:
            return self._attempt_to_start_traffic

    @attempt_to_start_traffic.setter
    def attempt_to_start_traffic(self, value):
        with self._traffic_attempt_lock:
            self._attempt_to_start_traffic = value

    @property
    def emission_started(self):
        with self._emission_lock:
            return self._emission_started

    @emission_started.setter
    def emission_started(self, value):
        with self._emission_lock:
            self._emission_started = value

    @property
    def service_disruption_length(self):
        with self._service_disruption_lock:
            return self._service_disruption_length

    @service_disruption_length.setter
    def service_disruption_length(self, value):
        with self._service_disruption_lock:
            self._service_disruption_length = value

    @log_entry_exit(LOG)
    def create_port(self, port_location):
        try:
            port = self.stc.create(object_type='port', under=self.project)
            self.stc.config(handle=port, location=port_location)
            self.stc.apply()
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

        return port

    @log_entry_exit(LOG)
    def create_eth_ipv4_host_iface(self, address, plen, gw, affiliated_port):
        try:
            host = self.stc.create(object_type='host', under=self.project)
            self.stc.config(handle=host, affiliatedPort=affiliated_port)

            eth_iface = self.stc.create(object_type='EthIIIf', under=host, useDefaultPhyMac='TRUE')
            ipv4_iface = self.stc.create(object_type='Ipv4If', under=host, address=address, prefixLength=plen,
                                         usePortDefaultIpv4Gateway=False, gateway=gw, resolveGatewayMac=True)

            self.stc.config(handle=ipv4_iface, stackedOn=eth_iface)
            self.stc.config(handle=host, topLevelIf=ipv4_iface)
            self.stc.config(handle=host, primaryIf=ipv4_iface)

            self.stc.apply()
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

        return ipv4_iface

    @log_entry_exit(LOG)
    def create_ipv4_stream(self, source_port, source_ipv4_iface, dest_ipv4_iface):
        try:
            stream_block = self.stc.create(object_type='streamBlock', under=source_port)
            self.stc.config(handle=stream_block, frameConfig='')
            self.stc.create(object_type='ethernet:EthernetII', under=stream_block)
            self.stc.create(object_type='ipv4:IPv4', under=stream_block)
            self.stc.config(handle=stream_block, srcBinding=source_ipv4_iface, dstBinding=dest_ipv4_iface)

            self.stc.apply()
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

        return stream_block

    @log_entry_exit(LOG)
    def create_raw_stream(self, source_port, source_ipv4_addr, dest_ipv4_addr, dest_mac_addr):
        try:
            stream_block = self.stc.create(object_type='streamBlock', under=source_port)
            self.stc.config(handle=stream_block, frameConfig='')
            self.stc.create(object_type='ethernet:EthernetII', under=stream_block, name='RAW_STREAM_ETH',
                            dstMac=dest_mac_addr)
            self.stc.create(object_type='ipv4:IPv4', under=stream_block, sourceAddr=source_ipv4_addr,
                            destAddr=dest_ipv4_addr)

            self.stc.apply()
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

        return stream_block

    @log_entry_exit(LOG)
    def config_port_rate(self, port_name, port_rate):
        try:
            generator = self.stc.get(port_name, 'children-Generator')
            generator_config = self.stc.get(generator, 'children-GeneratorConfig')
            self.stc.config(handle=generator_config, DurationMode='CONTINUOUS', LoadMode='FIXED',
                            FixedLoad=port_rate,
                            LoadUnit='PERCENT_LINE_RATE', SchedulingMode='PORT_BASED')
            self.stc.apply()
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

    @log_entry_exit(LOG)
    def config_traffic_load(self, traffic_load):
        self.config_port_rate(self.tx_port, constants.traffic_load_percent_mapping[traffic_load])

    @log_entry_exit(LOG)
    def config_traffic_stream(self, dest_mac_addr_list):
        # Delete existing modifiers, if any.
        try:
            existing_modifiers = self.stc.get(self.stream_block, 'children-TableModifier')
            self.stc.delete(existing_modifiers)
        except resthttp.RestHttpError:
            LOG.debug('No modifiers to delete')

        # Create new modifier with the provided destination MAC address list.
        try:
            modifier = self.stc.create(object_type='TableModifier', under=self.stream_block)
            self.stc.config(handle=modifier, Data=dest_mac_addr_list, RepeatCount=0,
                            OffsetReference='RAW_STREAM_ETH.dstMac')
            self.stc.apply()
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

    @log_entry_exit(LOG)
    def configure(self, traffic_load, traffic_config):
        l_port = self.create_port(port_location=traffic_config['left_port_location'])
        self.tx_port = l_port

        l_ipv4_iface = self.create_eth_ipv4_host_iface(address=traffic_config['left_traffic_addr'],
                                                       plen=traffic_config['left_traffic_plen'],
                                                       gw=traffic_config['left_traffic_gw'],
                                                       affiliated_port=l_port)

        r_port = self.create_port(port_location=traffic_config['right_port_location'])
        self.rx_port = r_port

        r_ipv4_iface = self.create_eth_ipv4_host_iface(address=traffic_config['right_traffic_addr'],
                                                       plen=traffic_config['right_traffic_plen'],
                                                       gw=traffic_config['right_traffic_gw'],
                                                       affiliated_port=r_port)

        dest_mac_addr = traffic_config.get('left_traffic_gw_mac')
        if dest_mac_addr is None:
            self.arp_needed = True
            self.stream_block = self.create_ipv4_stream(source_port=l_port, source_ipv4_iface=l_ipv4_iface,
                                                        dest_ipv4_iface=r_ipv4_iface)
        else:
            self.arp_needed = False
            self.stream_block = self.create_raw_stream(source_port=l_port,
                                                       source_ipv4_addr=traffic_config['left_traffic_addr'],
                                                       dest_ipv4_addr=traffic_config['right_traffic_addr'],
                                                       dest_mac_addr=dest_mac_addr)

        self.config_traffic_load(traffic_load)

        try:
            self.stc.perform('AttachPorts')
            self.stc.perform('DevicesStartAll')

            self.stc.perform(command='ResultsSubscribe', parent=self.project, ConfigType='StreamBlock',
                             ResultType='TxStreamResults')
            self.stc.perform(command='ResultsSubscribe', parent=self.project, ConfigType='StreamBlock',
                             ResultType='RxStreamSummaryResults')

            self.tx_results = self.stc.get(self.stream_block, 'children-TxStreamResults')
            self.rx_results = self.stc.get(self.stream_block, 'children-RxStreamSummaryResults')
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

    @log_entry_exit(LOG)
    def start(self, delay_time, return_when_emission_starts):
        self.attempt_to_start_traffic = True

        def traffic_starter():
            if self.arp_needed is True:
                resolution_status = 'NOT_STARTED'
                while resolution_status != 'SUCCESSFUL':
                    if not self.attempt_to_start_traffic:
                        LOG.debug('Aborting attempt to start traffic')
                        return

                    LOG.debug('Address resolution status: %s. Will retry.' % resolution_status)
                    try:
                        resolution_status = self.stc.perform(command='ArpNdStart')['ArpNdState']
                    except Exception as e:
                        raise StcTrafficAdapterError(e.message)
                LOG.debug('Address resolution status: %s' % resolution_status)

            if delay_time > 0:
                LOG.debug('Sleeping %s seconds before starting emission' % delay_time)
                time.sleep(delay_time)

            try:
                self.stc.perform(command='StreamBlockStart')
            except Exception as e:
                raise StcTrafficAdapterError(e.message)
            self.emission_started = True

            LOG.debug('Emission successfully started')

        def service_disruption_calculation_loop():
            self.service_disruption_length = 0

            # Sleep for 5 seconds to make sure first packets have been received.
            time.sleep(5)

            last_timestamp = time.time()

            while self.attempt_to_start_traffic:
                try:
                    rx_results = self.stc.get(self.rx_results)
                    rx_frame_rate = int(rx_results['FrameRate'])
                    rx_dropped_frame_rate = int(rx_results['DroppedFrameRate'])

                    current_timestamp = time.time()

                    LOG.debug('RX frame rate: %s' % rx_frame_rate)
                    LOG.debug('RX dropped frame rate: %s' % rx_dropped_frame_rate)

                    if rx_dropped_frame_rate > 0 or rx_frame_rate == 0:
                        self.service_disruption_length += current_timestamp - last_timestamp
                        LOG.debug('Service disruption length: %s' % self.service_disruption_length)

                    last_timestamp = current_timestamp
                except RuntimeError:
                    LOG.debug('STC RX results are not ready to be subscribed to')

                time.sleep(1)

        traffic_starter_thread = Thread(target=traffic_starter)
        traffic_starter_thread.start()

        service_disruption_calculation_thread = Thread(target=service_disruption_calculation_loop)
        service_disruption_calculation_thread.start()

        if return_when_emission_starts:
            traffic_starter_thread.join()

    @log_entry_exit(LOG)
    def stop(self, delay_time, return_when_emission_stops):
        self.attempt_to_start_traffic = False

        def traffic_stopper():
            if self.emission_started:
                if delay_time > 0:
                    LOG.debug('Sleeping %s seconds before stopping emission' % delay_time)
                    time.sleep(delay_time)

                try:
                    self.stc.perform(command='StreamBlockStop')
                except Exception as e:
                    raise StcTrafficAdapterError(e.message)
                self.emission_started = False

            LOG.debug('Emission successfully stopped')

        traffic_stopper_thread = Thread(target=traffic_stopper)
        traffic_stopper_thread.start()

        if return_when_emission_stops:
            traffic_stopper_thread.join()

    @log_entry_exit(LOG)
    def does_traffic_flow(self, delay_time):
        if delay_time > 0:
            LOG.debug('Sleeping %s seconds before polling traffic rate' % delay_time)
            time.sleep(delay_time)

        try:
            rx_frame_rate = int(self.stc.get(self.rx_results)['FrameRate'])
        except Exception as e:
            raise StcTrafficAdapterError(e.message)
        LOG.debug('RX frame rate is: %d' % rx_frame_rate)
        return rx_frame_rate > 0

    @log_entry_exit(LOG)
    def any_traffic_loss(self, delay_time, tolerance):
        if delay_time > 0:
            LOG.debug('Sleeping %s seconds before polling traffic rate' % delay_time)
            time.sleep(delay_time)

        try:
            tx_results = self.stc.get(self.tx_results)
            rx_results = self.stc.get(self.rx_results)
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

        tx_frame_count = int(tx_results['FrameCount'])
        rx_frame_count = int(rx_results['FrameCount'])

        tx_frame_rate = int(tx_results['FrameRate'])
        rx_frame_rate = int(rx_results['FrameRate'])

        rx_frames_dropped = int(rx_results['DroppedFrameCount'])
        # DroppedFramePercent shows the percent of dropped frames since the stream was started.
        # It is not an instantaneous value.
        rx_dropped_frame_percent = float(rx_results['DroppedFramePercent'])

        LOG.debug('TX frame - count: %s; rate: %s' % (tx_frame_count, tx_frame_rate))
        LOG.debug('RX frame - count: %s; rate: %s' % (rx_frame_count, rx_frame_rate))

        if rx_frames_dropped > tolerance * tx_frame_count:
            LOG.debug('Dropped frames: count = %d; rate = %.2f%%' % (rx_frames_dropped, rx_dropped_frame_percent))
            return True
        else:
            # If no dropped frames detected, it means that either:
            LOG.debug('No dropped frames detected')
            # 1. emission was not started => no traffic loss
            if tx_frame_count == 0:
                LOG.debug('No traffic emitted, so no traffic loss')
                return False

            # 2. 100% traffic loss from the beginning => all traffic lost
            if rx_frame_count == 0:
                LOG.debug('Traffic emitted, but nothing received, so assuming all traffic is lost')
                return True

            # 3. 0% traffic loss followed by 100% traffic loss (happening now) => some traffic lost
            if rx_frame_rate == 0:
                # 3a. Still emitting traffic
                if tx_frame_rate > 0:
                    LOG.debug('Emitting traffic, but not receiving, so assuming all traffic is momentarily dropped')
                    return True

                # 3b. Traffic emission stopped. Expecting RX count == TX count
                if rx_frame_count < (1 - tolerance) * tx_frame_count:
                    LOG.debug('Traffic stopped. Not all emitted traffic was received')
                    return True

            LOG.debug('No traffic loss detected')
            return False

    @log_entry_exit(LOG)
    def calculate_activation_time(self):
        LOG.debug('Activation time is calculated per RFC 6201 Frame-Loss Method')

        try:
            tx_results = self.stc.get(self.tx_results)
            rx_results = self.stc.get(self.rx_results)
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

        rx_frame_count = float(rx_results['FrameCount'])
        tx_frame_count = float(tx_results['FrameCount'])
        tx_frame_rate = float(tx_results['FrameRate'])

        return (tx_frame_count - rx_frame_count) / tx_frame_rate

    @log_entry_exit(LOG)
    def calculate_deactivation_time(self):
        LOG.debug('Deactivation time is calculated per RFC 6201 Frame-Loss Method')
        LOG.debug('Make sure counters were cleared at the time of calling DUT termination')

        try:
            tx_results = self.stc.get(self.tx_results)
            rx_results = self.stc.get(self.rx_results)
        except Exception as e:
            raise StcTrafficAdapterError(e.message)

        rx_frame_count = float(rx_results['FrameCount'])
        tx_frame_rate = float(tx_results['FrameRate'])

        return rx_frame_count / tx_frame_rate

    @log_entry_exit(LOG)
    def calculate_service_disruption_length(self):
        return self.service_disruption_length

    @log_entry_exit(LOG)
    def clear_counters(self):
        try:
            self.stc.perform(command='ResultsClearAll')
        except Exception as e:
            raise StcTrafficAdapterError(e.message)
        self.service_disruption_length = 0

    @log_entry_exit(LOG)
    def destroy(self):
        try:
            self.stc.perform(command='DetachPorts')
            self.stc.perform(command='ResetConfig')
            self.stc.delete(handle=self.project)
            self.stc.end_session(end_tcsession=self.session)
        except Exception as e:
            raise StcTrafficAdapterError(e.message)
