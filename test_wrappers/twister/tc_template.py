def twister_run(tc_module_name, tc_name):
    global _RESULT

    import importlib
    import json
    import logging

    from api.generic import constants
    from utils.logging_module import configure_logger

    tc_module = importlib.import_module(tc_module_name)
    tc_class = getattr(tc_module, tc_name)

    # Getting and configuring the RootLogger.
    root_logger = logging.getLogger()
    configure_logger(root_logger, console_level='INFO', propagate=True)

    # Logger for the current module.
    LOG = logging.getLogger('top_level_script')

    cfg_file = get_config(CONFIG[0], 'cfg_path/path')
    with open(cfg_file) as f:
        tc_input = json.load(f)

    LOG.info('Calling test case %s' % tc_name)
    tc_result = tc_class(tc_input).execute()

    set_details({'duration': tc_result['events']['instantiate_vnf']['duration']})

    if tc_result['overall_status'] == constants.TEST_PASSED:
        _RESULT = 'PASS'
    else:
        _RESULT = 'FAIL'
