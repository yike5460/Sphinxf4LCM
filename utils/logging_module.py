import datetime
import functools
import logging
import os
import sys

LOG_DIR = '/var/log/vnflcv'


def configure_logger(logger, file_level=None, log_filename=None, console_level=None, propagate=False,
                     override_parent=False):
    """
    This function configures a logger.

    :param logger:          Reference to the logger object.
    :param file_level:      Desired logging level of the logs that are to be written to file.
                            Possible values: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
                            Default value: 'DEBUG'
    :param log_filename:    Name of the file to dump logs to.
    :param console_level:   Desired logging level of the logs that are to be printed on the console
                            Possible values: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
                            Default value: None
    :param propagate:       Turn on/off propagation of messages.
                            Default value: "False" (message propagation is off).
    :param override_parent: Set to True to set current logger as parent of the RootLogger.
    :return:                None
    """

    # create logger with the name specified by logger_name
    logger.setLevel(logging.DEBUG)

    # set the desired propagation for the logger
    logger.propagate = propagate

    if file_level is not None:
        # Generate unique logging file name
        new_log_file_name = '{:%Y_%m_%d_%H_%M_%S}_'.format(datetime.datetime.now()) + str(log_filename)
        log_file_path = os.path.join(LOG_DIR, new_log_file_name + ".log")

        try:
            os.stat(LOG_DIR)
        except:
            os.mkdir(LOG_DIR)

        # Create file handler
        fh = logging.FileHandler(filename=log_file_path, mode="w")
        fh.setLevel(getattr(logging, str(file_level)))

        # Create formatter and add it to the handlers
        fh_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
        fh.setFormatter(fh_formatter)

        # Add the file handler to the logger
        logger.addHandler(fh)

    if console_level is not None:
        # Create file handler
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(getattr(logging, str(console_level)))

        # Create formatter and add it to the handlers
        ch_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
        ch.setFormatter(ch_formatter)

        # Add the file handler to the logger
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
