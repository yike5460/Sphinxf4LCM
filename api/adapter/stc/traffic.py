import logging
import time
from threading import Lock, Thread

from stcrestclient import stchttp

from utils.logging_module import log_entry_exit

LOG = logging.getLogger(__name__)


class TrafficStcAdapter(object):
    def __init__(self, lab_server_addr, user_name, session_name):
        self.stc = stchttp.StcHttp(lab_server_addr)
        self.session = self.stc.new_session(user_name=user_name, session_name=session_name, kill_existing=True)
        self.project = self.stc.create(object_type='project')
        self.tx_results = None
        self.rx_results = None

        self._attempt_to_start_traffic = False
        self._traffic_attempt_lock = Lock()
        self._emission_started = False
        self._emission_lock = Lock()

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

    @log_entry_exit(LOG)
    def create_port(self, port_location):
        port = self.stc.create(object_type='port', under=self.project)
        self.stc.config(handle=port, location=port_location)
        self.stc.apply()

        return port

    @log_entry_exit(LOG)
    def create_eth_ipv4_host_iface(self, address, plen, gw, affiliated_port):
        host = self.stc.create(object_type='host', under=self.project)
        self.stc.config(handle=host, affiliatedPort=affiliated_port)

        eth_iface = self.stc.create(object_type='EthIIIf', under=host, useDefaultPhyMac='TRUE')
        ipv4_iface = self.stc.create(object_type='Ipv4If', under=host, address=address, prefixLength=plen,
                                     usePortDefaultIpv4Gateway=False, gateway=gw, resolveGatewayMac=True)

        self.stc.config(handle=ipv4_iface, stackedOn=eth_iface)
        self.stc.config(handle=host, topLevelIf=ipv4_iface)
        self.stc.config(handle=host, primaryIf=ipv4_iface)

        self.stc.apply()

        return ipv4_iface

    @log_entry_exit(LOG)
    def create_ipv4_stream(self, source_port, source_ipv4_iface, dest_ipv4_iface):
        stream_block = self.stc.create(object_type='streamBlock', under=source_port)
        self.stc.config(handle=stream_block, frameConfig='')
        eth_header = self.stc.create(object_type='ethernet:EthernetII', under=stream_block)
        ip_header = self.stc.create(object_type='ipv4:IPv4', under=stream_block)
        self.stc.config(handle=stream_block, srcBinding=source_ipv4_iface, dstBinding=dest_ipv4_iface)

        self.stc.apply()

        return stream_block

    @log_entry_exit(LOG)
    def config_traffic_load(self, generator_port, traffic_load):
        traffic_load_percent_mapping = {'LOW_TRAFFIC_LOAD': 10,
                                        'NORMAL_TRAFFIC_LOAD': 50,
                                        'MAX_TRAFFIC_LOAD': 100}

        generator = self.stc.get(generator_port, 'children-Generator')
        generator_config = self.stc.get(generator, 'children-GeneratorConfig')
        self.stc.config(handle=generator_config, DurationMode='CONTINUOUS', LoadMode='FIXED',
                        FixedLoad=traffic_load_percent_mapping[traffic_load],
                        LoadUnit='PERCENT_LINE_RATE', SchedulingMode='PORT_BASED')
        self.stc.apply()

    @log_entry_exit(LOG)
    def configure(self, traffic_load, traffic_config):
        l_port = self.create_port(port_location=traffic_config['left_port_location'])

        l_ipv4_iface = self.create_eth_ipv4_host_iface(address=traffic_config['left_traffic_addr'],
                                                       plen=traffic_config['left_traffic_plen'],
                                                       gw=traffic_config['left_traffic_gw'],
                                                       affiliated_port=l_port)

        r_port = self.create_port(port_location=traffic_config['right_port_location'])

        r_ipv4_iface = self.create_eth_ipv4_host_iface(address=traffic_config['right_traffic_addr'],
                                                       plen=traffic_config['right_traffic_plen'],
                                                       gw=traffic_config['right_traffic_gw'],
                                                       affiliated_port=r_port)

        stream_block = self.create_ipv4_stream(source_port=l_port, source_ipv4_iface=l_ipv4_iface,
                                               dest_ipv4_iface=r_ipv4_iface)

        self.config_traffic_load(generator_port=l_port, traffic_load=traffic_load)

        self.stc.perform('AttachPorts')
        self.stc.perform('DevicesStartAll')

        self.stc.perform(command='ResultsSubscribe', parent=self.project, ConfigType='StreamBlock',
                         ResultType='TxStreamResults')
        self.stc.perform(command='ResultsSubscribe', parent=self.project, ConfigType='StreamBlock',
                         ResultType='RxStreamSummaryResults')

        self.tx_results = self.stc.get(stream_block, 'children-TxStreamResults')
        self.rx_results = self.stc.get(stream_block, 'children-RxStreamSummaryResults')

        return True

    @log_entry_exit(LOG)
    def start(self, delay_time, return_when_emission_starts):
        self.attempt_to_start_traffic = True

        def traffic_starter():
            resolution_status = 'NOT_STARTED'
            while resolution_status != 'SUCCESSFUL':
                if not self.attempt_to_start_traffic:
                    LOG.debug('Aborting attempt to start traffic')
                    return

                LOG.debug('Address resolution status: %s. Will retry.' % resolution_status)
                resolution_status = self.stc.perform(command='ArpNdStart')['ArpNdState']
            LOG.debug('Address resolution status: %s' % resolution_status)

            if delay_time > 0:
                LOG.debug('Sleeping %s seconds before starting emission' % delay_time)
                time.sleep(delay_time)

            self.stc.perform(command='StreamBlockStart')
            self.emission_started = True

            LOG.debug('Emission successfully started')

        traffic_starter_thread = Thread(target=traffic_starter)
        traffic_starter_thread.start()

        if return_when_emission_starts:
            traffic_starter_thread.join()

        return self.emission_started

    @log_entry_exit(LOG)
    def stop(self, delay_time, return_when_emission_stops):
        self.attempt_to_start_traffic = False

        def traffic_stopper():
            if self.emission_started:
                if delay_time > 0:
                    LOG.debug('Sleeping %s seconds before stopping emission' % delay_time)
                    time.sleep(delay_time)

                self.stc.perform(command='StreamBlockStop')
                self.emission_started = False

            LOG.debug('Emission successfully stopped')

        traffic_stopper_thread = Thread(target=traffic_stopper)
        traffic_stopper_thread.start()

        if return_when_emission_stops:
            traffic_stopper_thread.join()

        return not self.emission_started

    @log_entry_exit(LOG)
    def does_traffic_flow(self, delay_time):
        if delay_time > 0:
            LOG.debug('Sleeping %s seconds before polling traffic rate' % delay_time)
            time.sleep(delay_time)

        rx_frame_rate = int(self.stc.get(self.rx_results)['FrameRate'])
        LOG.debug('RX frame rate is: %d' % rx_frame_rate)
        return rx_frame_rate > 0

    @log_entry_exit(LOG)
    def any_traffic_loss(self, delay_time):
        if delay_time > 0:
            LOG.debug('Sleeping %s seconds before polling traffic rate' % delay_time)
            time.sleep(delay_time)

        tx_results = self.stc.get(self.tx_results)
        rx_results = self.stc.get(self.rx_results)

        tx_frame_count = int(tx_results['FrameCount'])
        rx_frame_count = int(rx_results['FrameCount'])

        tx_frame_rate = int(tx_results['FrameRate'])
        rx_frame_rate = int(rx_results['FrameRate'])

        rx_frames_dropped = int(rx_results['DroppedFrameCount'])
        rx_dropped_frame_percent = float(rx_results['DroppedFramePercent'])

        LOG.debug('TX frames - count: %s; rate: %s' % (tx_frame_count, tx_frame_rate))
        LOG.debug('RX frames - count: %s; rate: %s' % (rx_frame_count, rx_frame_rate))

        if rx_frames_dropped > 0:
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

                # 3b. Traffic emission stopped. Expecting TX count == RX count
                if tx_frame_count != rx_frame_count:
                    LOG.debug('Traffic stopped. Not all emitted traffic was received')
                    return True

            LOG.debug('No traffic loss detected')
            return False

    @log_entry_exit(LOG)
    def calculate_deactivation_time(self):
        LOG.debug('Deactivation time is calculated per RFC 6201 Frame-Loss Method')
        LOG.debug('Make sure counters were cleared at the time of calling DUT termination')

        tx_results = self.stc.get(self.tx_results)
        rx_results = self.stc.get(self.rx_results)

        rx_frame_count = float(rx_results['FrameCount'])
        tx_frame_rate = float(tx_results['FrameRate'])

        return rx_frame_count / tx_frame_rate

    @log_entry_exit(LOG)
    def clear_counters(self):
        self.stc.perform(command='ResultsClearAll')
        return True

    @log_entry_exit(LOG)
    def destroy(self):
        self.stc.perform(command='DetachPorts')
        self.stc.perform(command='ResetConfig')
        self.stc.delete(handle=self.project)
        self.stc.end_session(end_tcsession=self.session)
