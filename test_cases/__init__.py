import collections
import importlib

from api import ApiError
from api.generic import constants
from utils import reporting
from utils import timestamps

Function = collections.namedtuple('Function', 'function_reference function_args function_kwargs')


class TestExecutionError(Exception):
    """
    Generic exception for test execution.
    """
    def __init__(self, message, err_details=None):
        if err_details is None:
            err_details = message
        super(TestExecutionError, self).__init__(message)
        self.error_info = err_details


class TestSetupError(TestExecutionError):
    """
    A problem occurred during the test setup.
    """
    pass


class TestRunError(TestExecutionError):
    """
    A problem occurred during the test run.
    """
    pass


class TestCleanupError(TestExecutionError):
    """
    A problem occurred during the test cleanup.
    """
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
        self.tc_name = type(self).__name__
        self.tc_result = dict()
        self.tc_result['overall_status'] = constants.TEST_PASSED
        self.tc_result['error_info'] = 'No errors'
        self.tc_result['events'] = collections.OrderedDict()
        self.tc_result['resources'] = collections.OrderedDict()
        self.tc_result['scaling_out'] = dict()
        self.tc_result['scaling_in'] = dict()
        self.tc_result['scaling_up'] = dict()
        self.tc_result['scaling_down'] = dict()
        self.tc_result['timestamps'] = collections.OrderedDict()
        self.time_record = timestamps.TimeRecord()
        self.traffic = None
        self.em = None
        self.mano = None
        self.vim = None
        self.vnf = None
        self.vnf_instance_id = None
        self.ns_instance_id = None
        self.vnfm = None
        self.cleanup_registrations = list()

    # @classmethod
    # def initialize(cls):
    #     """
    #     This method configures the test case logger.
    #     """
    #     configure_logger(cls._LOG, file_level='DEBUG', console_level='INFO', override_parent=True)

    def check_requirements(self):
        """
        This method verifies that the test case instance tc_input dictionary contains all the required elements, if any.
        """
        try:
            for element in self.required_elements:
                if element not in self.tc_input.keys():
                    raise TestSetupError('Missing required element: %s' % element)
        except AttributeError:
            self._LOG.debug('No required elements for this test case')

    def setup(self):
        pass

    def run(self):
        pass

    def register_for_cleanup(self, function_reference, *args, **kwargs):
        """
        This method adds a "function" named tuple to the cleanup_registrations list.
        """
        self._LOG.debug('Registering function %s.%s for test cleanup'
                        % (function_reference.__module__, function_reference.__name__))
        if args:
            self._LOG.debug('Function will be called with arguments: (%s)' % ', '.join(map(str, args)))
        if kwargs:
            kv_args = list()
            for key, value in kwargs.iteritems():
                kv_args.append('%s=%s' % (key, value))
            self._LOG.debug('Function will be called with keyword arguments: (%s)' % ', '.join(map(str, kv_args)))
        new_function = Function(function_reference=function_reference, function_args=args, function_kwargs=kwargs)
        self.cleanup_registrations.append(new_function)

    def cleanup(self):
        """
        This method calls all the functions that were registered for cleanup in reverse order.
        """
        self._LOG.info('Starting main cleanup')
        for function in reversed(self.cleanup_registrations):
            try:
                function.function_reference(*function.function_args, **function.function_kwargs)
            except Exception as e:
                raise TestCleanupError(e.message)
        self._LOG.info('Finished main cleanup')

    def collect_timestamps(self):
        """
        This method copies all the timestamps that were recorded during the test in the tc_result dictionary.
        """
        self.tc_result['timestamps'].update(self.time_record.dump_data())

    def execute(self):
        """
        This method implements the test case execution logic.
        """
        try:
            self.check_requirements()
            self.setup()
            self.run()
        except TestSetupError as e:
            self._LOG.error('%s setup failed' % self.tc_name)
            self._LOG.debug(e.message)
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.error_info)
        except TestRunError as e:
            self._LOG.error('%s run failed' % self.tc_name)
            self._LOG.debug(e.message)
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.error_info)
        except ApiError as e:
            self._LOG.error('%s execution crashed' % self.tc_name)
            self.tc_result['overall_status'] = constants.TEST_ERROR
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.message)
            raise
        except Exception as e:
            self._LOG.error('%s execution crashed' % self.tc_name)
            self.tc_result['overall_status'] = constants.TEST_ERROR
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.message)
            raise
        finally:
            try:
                self.cleanup()
            except TestCleanupError as e:
                self._LOG.error('%s cleanup failed' % self.tc_name)
                self._LOG.debug('Exception message %s' % e.message)
            finally:
                self.collect_timestamps()
                self.report()
                return self.tc_result

    def report(self):
        reporting.report_test_case(self.tc_input, self.tc_result)
