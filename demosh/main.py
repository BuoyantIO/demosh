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

import argparse

from . import __version__
from .shellstate import ShellState
from .demostate import DemoState


def main() -> None:
    parser = argparse.ArgumentParser(description='Demo SHell: run shell scripts with commentary and pauses')

    parser.add_argument('--version', action='version', version=f"%(prog)s {__version__}")
    parser.add_argument('--debug', action='store_true', help="enable debug output")

    parser.add_argument('script', type=str, help="script to run")
    parser.add_argument('args', type=str, nargs=argparse.REMAINDER, help="optional arguments to pass to script")

    args = parser.parse_args()

    scriptname = args.script
    mode = "shell"

    if scriptname.lower().endswith(".md"):
        mode = "markdown"

    script = open(scriptname, "r")

    shellstate = ShellState(sys.argv[0], scriptname, args.args)
    demostate = DemoState(shellstate, mode, script, debug=args.debug)

    try:
        demostate.run()
    finally:
        demostate.sane()


if __name__ == "__main__":
    main()
