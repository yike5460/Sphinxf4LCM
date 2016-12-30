import importlib
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
        self.tc_result = {}

    @classmethod
    def initialize(cls):
        configure_logger(cls._LOG, file_level='DEBUG', console_level='INFO', override_parent=True)

    def setup(self):
        return True

    def run(self):
        return True

    def cleanup(self):
        return True

    def execute(self):
        self.initialize()

        try:
            if not self.setup():
                raise TestExecutionError

            if not self.run():
                raise TestExecutionError

            if not self.cleanup():
                raise TestExecutionError
        except TestExecutionError:
            self.cleanup()

        return self.tc_result

