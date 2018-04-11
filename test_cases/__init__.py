#
# Copyright (c) 2018 by Spirent Communications Plc.
# All Rights Reserved.
#
# This software is confidential and proprietary to Spirent Communications Inc.
# No part of this software may be reproduced, transmitted, disclosed or used
# in violation of the Software License Agreement without the expressed
# written consent of Spirent Communications Inc.
#
#


import collections
import importlib

from api import ApiError
from api.generic import constants, construct_generic
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


class TestRequirementsError(TestExecutionError):
    """
    A problem occurred during the test initialization.
    """
    pass


class Step(object):
    index = 0

    @classmethod
    def generate_index(cls):
        cls.index += 1
        return cls.index

    def __init__(self, name, description):
        self.index = self.generate_index()
        self.name = name
        self.description = description
        self.status = 'SKIP'

    def __call__(self, run_func):
        self.run_func = run_func
        return self


class TestMeta(type):
    """
    Meta class that adds the logger object to the class dictionary of the class that is an instance of this meta class.
    """

    def __new__(meta, name, bases, class_dict):
        if bases != (object,):
            originating_module = importlib.import_module(class_dict['__module__'])
            class_dict['_LOG'] = originating_module.LOG

            steps = []
            for _, attr_value in class_dict.items():
                if isinstance(attr_value, Step):
                    steps.append(attr_value)
            steps.sort(key=lambda x: x.index)
            class_dict['steps'] = steps

        return type.__new__(meta, name, bases, class_dict)


class TestCase(object):
    """
    Test case class.
    """
    __metaclass__ = TestMeta

    REQUIRED_APIS = ()
    REQUIRED_ELEMENTS = ()
    TESTCASE_EVENTS = ()

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
        self.tc_result['scaling_to_level'] = dict()
        self.tc_result['scaling_from_level'] = dict()
        self.tc_result['timestamps'] = collections.OrderedDict()
        self.tc_result['steps'] = collections.OrderedDict()
        self.time_record = timestamps.TimeRecord()
        self.traffic = None
        self.em = None
        self.mano = None
        self.vim = None
        self.vnf = None
        self.vnf_instance_id = None
        self.ns_instance_id = None
        self.vnfm = None
        self.cleanup_registrations = dict()

    # @classmethod
    # def initialize(cls):
    #     """
    #     This method configures the test case logger.
    #     """
    #     configure_logger(cls._LOG, file_level='DEBUG', console_level='INFO', override_parent=True)

    def check_requirements(self):
        """
        This method verifies that the test case instance tc_input dictionary contains all the required items, if any.
        """
        required_items = self.REQUIRED_APIS + self.REQUIRED_ELEMENTS
        missing_items = list()
        for element in required_items:
            if element not in self.tc_input.keys():
                missing_items.append(element)
        if len(missing_items) > 0:
            raise TestRequirementsError('Missing required item(s) from test case input: %s' % missing_items)

    def build_apis(self):
        """
        This method creates the objects needed for test execution.
        """
        self._LOG.debug('Building objects for %s' % self.__class__.__name__)
        for element in self.REQUIRED_APIS:
            setattr(self, element, construct_generic(vendor=self.tc_input[element]['type'], module_type=element,
                                                     adapter_config=self.tc_input[element].get('adapter_config', {}),
                                                     generic_config=self.tc_input[element].get('generic_config', {})))

        self._LOG.debug('Finished building objects for %s' % self.__class__.__name__)

    def initialize_events(self):
        for event in self.TESTCASE_EVENTS:
            self.tc_result['events'][event] = dict()

    def setup(self):
        pass

    def run(self):
        for step in self.steps:
            self._LOG.info('Entering step %s' % step.name)
            try:
                step.run_func(self)
                step.status = 'PASS'
            except TestRunError as e:
                step.status = 'FAIL'
                raise e
            except Exception as e:
                step.status = 'ERROR'
                raise e
            finally:
                self._LOG.info('Exiting step %s' % step.name)

    def register_for_cleanup(self, index, function_reference, *args, **kwargs):
        """
        This method adds a "Function" named tuple to the cleanup_registrations dictionary as a value to the key
        indicated in the index (the index must be an integer).
        """
        if type(index) is not int:
            raise ValueError('Function register_for_cleanup "index" input must be an integer')
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
        self.cleanup_registrations[index] = new_function

    def unregister_from_cleanup(self, index):
        """
        This method removes the "Function" named tuple from the cleanup_registrations dictionary corresponding to key
        indicated in the index.
        """
        obsolete_function = self.cleanup_registrations.pop(index)
        function_reference = obsolete_function.function_reference
        self._LOG.debug('Unregistered function %s.%s from test cleanup'
                        % (function_reference.__module__, function_reference.__name__))

    def cleanup(self):
        """
        This method calls in reverse order all the functions that were registered for cleanup.
        """
        self._LOG.info('Starting main cleanup')
        for index in reversed(sorted(self.cleanup_registrations.keys())):
            function = self.cleanup_registrations[index]
            try:
                function.function_reference(*function.function_args, **function.function_kwargs)
            except Exception as e:
                self._LOG.exception(e)
                raise TestCleanupError(e.message)
        self._LOG.info('Finished main cleanup')

    def collect_timestamps(self):
        """
        This method copies all the timestamps that were recorded during the test in the tc_result dictionary.
        """
        self.tc_result['timestamps'].update(self.time_record.dump_data())

    def steps_summary(self):
        """
            This method creates a dict containing the summary of steps executions and stores it in tc_result
        """
        for step in self.steps:
            self.tc_result['steps'][step.name] = {
                'description': step.description,
                'status': step.status
            }

    def execute(self):
        """
        This method implements the test case execution logic.
        """
        try:
            self.check_requirements()
            self.build_apis()
            self.initialize_events()
            self.setup()
            self.run()
        except TestRequirementsError as e:
            self._LOG.error('%s missing requirements' % self.tc_name)
            self._LOG.exception(e)
            self.tc_result['overall_status'] = constants.TEST_ERROR
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.error_info)
        except TestSetupError as e:
            self._LOG.error('%s setup failed' % self.tc_name)
            self._LOG.exception(e)
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.error_info)
        except TestRunError as e:
            self._LOG.error('%s run failed' % self.tc_name)
            self._LOG.exception(e)
            self.tc_result['overall_status'] = constants.TEST_FAILED
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.error_info)
        except ApiError as e:
            self._LOG.error('%s execution crashed' % self.tc_name)
            self._LOG.exception(e)
            self.tc_result['overall_status'] = constants.TEST_ERROR
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.message)
        except Exception as e:
            self._LOG.error('%s execution crashed' % self.tc_name)
            self._LOG.exception(e)
            self.tc_result['overall_status'] = constants.TEST_ERROR
            self.tc_result['error_info'] = '%s: %s' % (type(e).__name__, e.message)
        finally:
            try:
                self.cleanup()
            except TestCleanupError as e:
                self._LOG.error('%s cleanup failed' % self.tc_name)
                self._LOG.exception(e)
            finally:
                self.collect_timestamps()
                self.steps_summary()
                self._LOG.info('RESULT: %s' % self.tc_result['overall_status'])
                return self.tc_result
