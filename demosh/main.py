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
#
#--------------------------------------
#
# For more info, see README.md. If you've somehow found demosh without also
# finding its repo, it's at github.com/BuoyantIO/demosh.

import sys

import os

from .shellstate import ShellState
from .demostate import DemoState


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: %s script [arg [arg [...]]]" % os.path.basename(sys.argv[0]))
        sys.exit(1)

    scriptname = sys.argv[1]
    script = open(scriptname, "r")

    shellstate = ShellState(scriptname, sys.argv[2:])
    demostate = DemoState(shellstate, script)

    try:
        demostate.run()
    finally:
        demostate.sane()


if __name__ == "__main__":
    main()