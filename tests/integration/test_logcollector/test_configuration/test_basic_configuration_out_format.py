'''
copyright: Copyright (C) 2015-2024, Wazuh Inc.

           Created by Wazuh, Inc. <info@wazuh.com>.

           This program is free software; you can redistribute it and/or modify it under the terms of GPLv2

type: integration

brief: The 'wazuh-logcollector' daemon monitors configured files and commands for new log messages.
       Specifically, these tests will check if the logcollector detects invalid values for
       the 'out_format' tag and the Wazuh API returns the same values for the configured
       'localfile' section. Log data collection is the real-time process of making sense out
       of the records generated by servers or devices. This component can receive logs through
       text files or Windows event logs. It can also directly receive logs via remote syslog
       which is useful for firewalls and other such devices.

components:
    - logcollector

suite: configuration

targets:
    - agent

daemons:
    - wazuh-logcollector
    - wazuh-apid

os_platform:
    - linux

os_version:
    - Arch Linux
    - Amazon Linux 2
    - Amazon Linux 1
    - CentOS 8
    - CentOS 7
    - Debian Buster
    - Red Hat 8
    - Ubuntu Focal
    - Ubuntu Bionic

references:
    - https://documentation.wazuh.com/current/user-manual/capabilities/log-data-collection/index.html
    - https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html#out-format

tags:
    - logcollector_configuration
'''
import pytest, sys

from pathlib import Path

from wazuh_testing.constants.paths.logs import WAZUH_LOG_PATH
from wazuh_testing.constants.platforms import WINDOWS
from wazuh_testing.constants.daemons import LOGCOLLECTOR_DAEMON
from wazuh_testing.modules.logcollector import configuration as logcollector_configuration
from wazuh_testing.modules.logcollector import patterns
from wazuh_testing.modules.logcollector import utils
from wazuh_testing.tools.monitors import file_monitor
from wazuh_testing.utils import callbacks, configuration
from wazuh_testing.utils.services import control_service

from . import TEST_CASES_PATH, CONFIGURATIONS_PATH


# Marks
pytestmark = [pytest.mark.agent, pytest.mark.linux, pytest.mark.tier(level=0)]

# Configuration
cases_path = Path(TEST_CASES_PATH, 'cases_basic_configuration_out_format.yaml')
config_path = Path(CONFIGURATIONS_PATH, 'wazuh_basic_configuration_out_format.yaml')
local_internal_options = {logcollector_configuration.LOGCOLLECTOR_DEBUG: '2'}

test_configuration, test_metadata, test_cases_ids = configuration.get_test_cases_data(cases_path)

test_configuration = configuration.load_configuration_template(config_path, test_configuration, test_metadata)

# Test daemons to restart.
daemons_handler_configuration = {'all_daemons': True}


@pytest.mark.parametrize('test_configuration, test_metadata', zip(test_configuration, test_metadata), ids=test_cases_ids)
def test_configuration_out_format(test_configuration, test_metadata, set_wazuh_configuration, configure_local_internal_options, daemons_handler_module, stop_logcollector):
    '''
    description: Check if the 'wazuh-logcollector' daemon detects invalid settings for the 'out_format' tag.
                 For this purpose, the test will set a 'localfile' section using both valid and invalid values
                 for that tag. It also will set a 'socket' section to specify a custom socket. Finally, the
                 test will verify that the 'socket target' event is triggered when using a valid value or if
                 an error event is generated when using an invalid one.

    wazuh_min_version: 4.2.0

    tier: 0

    parameters:
        - test_configuration:
            type: data
            brief: Configuration used in the test.
        - test_metadata:
            type: data
            brief: Configuration cases.
        - set_wazuh_configuration:
            type: fixture
            brief: Configure a custom environment for testing.
        - configure_local_internal_options:
            type: fixture
            brief: Configure the Wazuh local internal options.
        - daemons_handler_module:
            type: fixture
            brief: Handler of Wazuh daemons.
        - stop_logcollector:
            type: fixture
            brief: Stop logcollector daemon.

    assertions:
        - Verify that the logcollector generates error events when using invalid values
          for the 'out_format' tag.
        - Verify that the logcollector generates 'socket target' events when using valid values
          for the 'out_format' tag.
        - Verify that the Wazuh API returns the same values for the 'localfile' section as the configured one.

    input_description: A configuration template (test_basic_configuration_out_format) is contained in an
                       external YAML file (wazuh_basic_configuration.yaml). That template is combined with
                       different test cases defined in the module. Those include configuration settings
                       for the 'wazuh-logcollector' daemon.

    expected_output:
        - r'DEBUG: Socket target for .* -> .*'
        - r'WARNING: Log target .* not found for the output format of localfile .*'

    tags:
        - invalid_settings
        - logs
    '''

    control_service('start', daemon=LOGCOLLECTOR_DAEMON)

    callback = None
    assert_error = None
    if test_metadata['valid_value']:
        callback=callbacks.generate_callback(patterns.LOGCOLLECTOR_SOCKET_TARGET_VALID, {
                              'location': test_metadata['location'],
                              'socket_name': test_metadata['target']
                          })
        assert_error = patterns.ERROR_TARGET_SOCKET
    else:
        callback=callbacks.generate_callback(patterns.LOGCOLLECTOR_LOG_TARGET_NOT_FOUND, {
                              'socket_name': test_metadata['target_out_format'],
                              'location': test_metadata['location']
                          })
        assert_error = patterns.ERROR_TARGET_SOCKET_NOT_FOUND

    wazuh_log_monitor = file_monitor.FileMonitor(WAZUH_LOG_PATH)
    wazuh_log_monitor.start(callback, timeout=10)

    assert wazuh_log_monitor.callback_result, assert_error


    if test_metadata['valid_value'] and sys.platform != WINDOWS:
        utils.check_logcollector_socket()
        utils.validate_test_config_with_module_config(test_configuration=test_configuration)
