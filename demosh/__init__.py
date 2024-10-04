#!/usr/bin/env python
#
# SPDX-FileCopyrightText: 2022 Buoyant, Inc.
# SPDX-License-Identifier: Apache-2.0
#
# Copyright 2022 Buoyant, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.  You may obtain
# a copy of the License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
demosh is a Demo SHell: it reads shell scripts or Markdown files and
executes shell commands from then. However, it also outputs commentary,
shows commands before running them, and pauses before (or after) running
each command. Pausing and what to show can be controlled by inline comments
in the script itself.

For more info, see README.md. If you've somehow found demosh without also
finding its repo, it's at github.com/BuoyantIO/demosh.
"""


# Flit reads this dynamically when building or publishing.
__version__ = "0.6.0"


import sys

from .main import main

