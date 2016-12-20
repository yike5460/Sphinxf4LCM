from utils.logging_module import configure_logger

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

    def launch(self):
        self.initialize()

        try:
            if not self.setup():
                raise RuntimeError

            if not self.run():
                raise RuntimeError

            if not self.cleanup():
                raise RuntimeError
        except:
            self.cleanup()

        return self.tc_result

