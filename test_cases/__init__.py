import collections
import importlib

from utils.logging_module import configure_logger
from utils import reporting
from utils import timestamps


Function = collections.namedtuple('Function', 'function_reference function_args function_kwargs')


class TestExecutionError(Exception):
    pass


class TestMeta(type):
    """
    Meta class that adds the logger object to the class dictionary of the class that is an instance of this meta class.
    """
    def __new__(meta, name, bases, class_dict):
        if bases != (object,):
            originating_module = importlib.import_module(class_dict['__module__'])
            class_dict['_LOG'] = originating_module.LOG
        return type.__new__(meta, name, bases, class_dict)


class TestCase(object):
    """
    Test case class.
    """
    __metaclass__ = TestMeta

    def __init__(self, tc_input):
        self.tc_input = tc_input
        self.tc_result = dict()
        self.tc_result['durations'] = collections.OrderedDict()
        self.tc_result['resources'] = collections.OrderedDict()
        self.tc_result['scaling_out'] = dict()
        self.tc_result['scaling_in'] = dict()
        self.tc_result['scaling_up'] = dict()
        self.tc_result['scaling_down'] = dict()
        self.tc_result['timestamps'] = collections.OrderedDict()
        self.time_record = timestamps.TimeRecord()
        self.traffic = None
        self.vim = None
        self.vnf = None
        self.vnf_config = None
        self.vnf_instance_id = None
        self.vnfm = None
        self.cleanup_registrations = list()

    @classmethod
    def initialize(cls):
        """
        This method configures the test case logger.
        """
        configure_logger(cls._LOG, file_level='DEBUG', console_level='INFO', override_parent=True)

    def setup(self):
        return True

    def run(self):
        return True

    def register_for_cleanup(self, function_reference, *args, **kwargs):
        """
        This method adds a "function" named tuple to the cleanup_registrations list.
        """
        new_function = Function(function_reference=function_reference, function_args=args, function_kwargs=kwargs)
        self.cleanup_registrations.append(new_function)

    def cleanup(self):
        """
        This method calls all the functions that were registered for cleanup in reverse order.
        """
        self._LOG.info('Starting main cleanup')
        for function in reversed(self.cleanup_registrations):
            function.function_reference(*function.function_args, **function.function_kwargs)
        self._LOG.info('Finished main cleanup')
        return True

    def collect_timestamps(self):
        """
        This method copies all the timestamps that were recorded during the test in the tc_result dictionary.
        """
        self.tc_result['timestamps'].update(self.time_record.dump_data())

    def execute(self):
        """
        This method implements the test case execution logic.
        """
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

        self.report()

        return self.tc_result

    def report(self):
        reporting.report_test_case(self.tc_input, self.tc_result)
