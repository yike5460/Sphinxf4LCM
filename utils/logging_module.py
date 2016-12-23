import logging
import functools
import os

LOG_DIR = '/tmp/nfv'


def configure_logger(logger, file_level=None, console_level=None, propagate=False, override_parent=False):
    """
    This function configures a logger.

    :param logger:          Reference to the logger object.
    :param file_level:      Desired logging level of the logs that are to be written to file.
                            Possible values: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
                            Default value: 'DEBUG'
    :param console_level:   Desired logging level of the logs that are to be printed on the console
                            Possible values: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
                            Default value: None
    :param propagate:       Turn on/off propagation of messages.
                            Default value: "False" (message propagation is off).
    :param override_parent: Set to True to make the parent logger point to this logger.
    :return:                None
    """

    # create logger with the name specified by logger_name
    logger.setLevel(logging.DEBUG)

    # set the desired propagation for the logger
    logger.propagate = propagate

    if file_level:
        module_name = logger.name.rsplit('.', 1)[-1]
        log_file_path = os.path.join(LOG_DIR, module_name + ".log")

        try:
            os.stat(LOG_DIR)
        except:
            os.mkdir(LOG_DIR)

        # create file handler
        fh = logging.FileHandler(filename=log_file_path, mode="w")
        fh.setLevel(getattr(logging, str(file_level)))

        # create formatter and add it to the handlers
        fh_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
        fh.setFormatter(fh_formatter)

        # add the file handler to the logger
        logger.addHandler(fh)

    if console_level:
        # create file handler
        ch = logging.StreamHandler()
        ch.setLevel(getattr(logging, str(console_level)))

        # create formatter and add it to the handlers
        ch_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
        ch.setFormatter(ch_formatter)

        # add the file handler to the logger
        logger.addHandler(ch)

    if override_parent:
        # Set current logger as parent of the RootLogger.
        # logger.parent points to the RootLogger
        logger.parent.parent = logger

        # Making sure we avoid logging loops.
        logger.propagate = False


def log_entry_exit(LOG):
    def func_wrapper(func):
        @functools.wraps(func)
        def logger_wrapper(*args, **kwargs):
            LOG.debug("Entering function %s" % func.__name__)
            func_result = func(*args, **kwargs)
            LOG.debug("Exiting function %s" % func.__name__)
            return func_result
        return logger_wrapper
    return func_wrapper
