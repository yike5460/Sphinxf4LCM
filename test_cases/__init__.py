import importlib
import time
from utils.logging_module import configure_logger


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
        self.tc_result['time_record'] = {}

    @classmethod
    def initialize(cls):
        configure_logger(cls._LOG, file_level='DEBUG', console_level='INFO', override_parent=True)

    def setup(self):
        return True

    def run(self):
        return True

    def cleanup(self):
        return True

    def start_clock(self, label):
        if label not in self.tc_result['time_record']:
            self.tc_result['time_record'][label] = {}
        self.tc_result['time_record'][label]['start'] = time.time()

    def stop_clock(self, label):
        if label not in self.tc_result['time_record']:
            self.tc_result['time_record'][label] = {}
        self.tc_result['time_record'][label]['end'] = time.time()

    def check_time_records(self):
        for label in self.tc_result['time_record']:
            if 'start' not in self.tc_result['time_record'][label]:
                self._LOG.warning('No start time record for label %s' % label)
            if 'end' not in self.tc_result['time_record'][label]:
                self._LOG.warning('No end time record for label %s' % label)

    def execute(self):
        self.initialize()

        try:
            if not self.setup():
                raise TestExecutionError

            if not self.run():
                raise TestExecutionError

            self.check_time_records()

            if not self.cleanup():
                raise TestExecutionError
        except TestExecutionError:
            self.cleanup()

        return self.tc_result

