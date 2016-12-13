import logging


class LoggingClass:
    """
    Class used for logging

    :param logger_name:     The name of the logger
    :param log_file_name:   The name of the file to write logs to; Example "log.txt"
    :param file_level:      The desired logging level of the logs that are to be written to file
                            Possible values: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
                            Default value: 'DEBUG'
    :param console_level:   The desired logging level of the logs that are to be printed on the console
                            Possible values: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
                            Default value: 'INFO'
    :param propagate:       Turn on/off propagation of messages
                            Default value: "TRUE" (message propagation is on)
    """
    def __init__(self, logger_name, log_file_name, file_level="DEBUG", console_level="INFO", propagate=True):

        # create logger with the name specified by logger_name
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)

        # set the desired propagation for the logger ()
        self.logger.propagate = propagate

        # create file handler
        fh = logging.FileHandler(filename=log_file_name, mode="w")
        fh.setLevel(getattr(logging, str(file_level)))

        # create formatter and add it to the handlers
        fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(fh_formatter)

        # add the file handler to the logger
        self.logger.addHandler(fh)

        # create console handler
        ch = logging.StreamHandler()
        ch.setLevel(getattr(logging, str(console_level)))

        # create formatter and add it to the handlers
        ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(ch_formatter)

        # add the console handler to the logger
        self.logger.addHandler(ch)

    def write_critical(self, message):
        if self.logger.propagate is True:
            self.logger.critical(message)

    def write_error(self, message):
        if self.logger.propagate is True:
            self.logger.error(message)

    def write_warning(self, message):
        if self.logger.propagate is True:
            self.logger.warning(message)

    def write_info(self, message):
        if self.logger.propagate is True:
            self.logger.info(message)

    def write_debug(self, message):
        if self.logger.propagate is True:
            self.logger.debug(message)

    def close_handlers(self):
        handlers = self.logger.handlers
        for handler in handlers:
            self.logger.removeHandler(handler)
            handler.close()
