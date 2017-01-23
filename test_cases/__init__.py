import collections
import importlib

from utils.logging_module import configure_logger
from utils import timestamps


Function = collections.namedtuple('function', 'function_reference function_params')


class TestExecutionError(Exception):
    pass


class TestMeta(type):
    def __new__(meta, name, bases, class_dict):
        if bases != (object,):
            originating_module = importlib.import_module(class_dict['__module__'])
            class_dict['_LOG'] = originating_module.LOG
        return type.__new__(meta, name, bases, class_dict)


class TestCase(object):
    __metaclass__ = TestMeta

    def __init__(self, tc_input):
        self.tc_input = tc_input
        self.tc_result = dict()
        self.tc_result['timestamps'] = collections.OrderedDict()
        self.tc_result['durations'] = {}
        self.time_record = timestamps.TimeRecord()
        self.traffic = None
        self.vim = None
        self.vnf = None
        self.vnf_instance_id = None
        self.vnfm = None
        self.cleanup_registrations = list()

    @classmethod
    def initialize(cls):
        configure_logger(cls._LOG, file_level='DEBUG', console_level='INFO', override_parent=True)

    def setup(self):
        return True

    def run(self):
        return True

    def register_for_cleanup(self, function_reference, function_params=[]):
        new_function = Function(function_reference=function_reference, function_params=function_params)
        self.cleanup_registrations.append(new_function)

    def cleanup(self):
        self._LOG.info('Starting main cleanup')
        for function in reversed(self.cleanup_registrations):
            function.function_reference(*function.function_params)
        self._LOG.info('Finished main cleanup')
        return True

    def collect_timestamps(self):
        self.tc_result['timestamps'].update(self.time_record.dump_data())

    def execute(self):
        self.initialize()

        try:
            if not self.setup():
                raise TestExecutionError

            if not self.run():
                raise TestExecutionError

            self.collect_timestamps()

            if not self.cleanup():
                raise TestExecutionError
        except TestExecutionError:
            self.collect_timestamps()
            self.cleanup()

        return self.tc_result

