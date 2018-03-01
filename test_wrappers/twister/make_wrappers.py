#!/usr/bin/env python

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


import json
import shutil
import os

mapping_file_path = '../../test_cases/tc_mapping.json'
template_file_path = 'tc_template.py'
base_wrappers_dir = '.'
tc_mapping = None

with open(mapping_file_path, 'r') as mapping_file:
    tc_mapping = json.load(mapping_file)

for tc_name, tc_module in tc_mapping.items():
    wrappers_dir_path = tc_module.rsplit('.', 1)[0].replace('.', '/')
    full_wrappers_dir_path = os.path.join(base_wrappers_dir, wrappers_dir_path)

    try:
        os.makedirs(full_wrappers_dir_path)
    except OSError:
        print 'Not creating directory %s. Probably it already exists.' % full_wrappers_dir_path

    wrapper_file_path = os.path.join(full_wrappers_dir_path, tc_name + '.py')
    shutil.copy(template_file_path, wrapper_file_path)
