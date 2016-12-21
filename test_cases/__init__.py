class TestExecutionError(Exception):
    pass


class TestCase(object):
    def __init__(self, tc_input):
        self.tc_input = tc_input
        self.tc_result = {}

    def initialize(self):
        pass

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

