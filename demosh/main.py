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
from .shellstate import ShellState, str2bool
from .demostate import DemoState


def main() -> None:
    parser = argparse.ArgumentParser(description=f'Demo SHell {__version__}: run shell scripts with commentary and pauses')

    parser.add_argument('--version', action='version', version=f"%(prog)s {__version__}")
    parser.add_argument('--debug', action='store_true', help="enable debug output")
    parser.add_argument('--no-builtins', action='store_true', help="don't load builtin functions")
    parser.add_argument('--no-init', action='store_true', help="don't run ~/.demoshrc on startup")
    parser.add_argument('--no-blurb', action='store_true', help="don't print the demosh blurb on startup")

    parser.add_argument('script', type=str, help="script to run")
    parser.add_argument('args', type=str, nargs=argparse.REMAINDER, help="optional arguments to pass to script")

    args = parser.parse_args()

    scriptname = args.script
    mode = "shell"

    if scriptname.lower().endswith(".md"):
        mode = "markdown"

    script = open(scriptname, "r")

    shellstate = ShellState(sys.argv[0], scriptname, args.args)
    demostate = DemoState(shellstate, mode, script,
                          debug=args.debug,
                          load_builtins=not args.no_builtins,
                          load_init=not args.no_init)

    demosh_no_blurb = str2bool(shellstate.env.get("DEMOSH_NO_BLURB", None))

    if not (args.no_blurb or demosh_no_blurb):
        print(f"demosh {__version__}: Interactive Demo SHell for Markdown and shell scripts")
        print("(c) 2022-2024 Buoyant, Inc.; Apache 2.0 License")
        print("https://github.com/BuoyantIO/demosh")
        print("")
        print("To exit, hit Q (capital Q!) when demosh is waiting for input.")
        print("To skip this message, use --no-blurb or set DEMOSH_NO_BLURB=true.")
        print("")
        print("Hit RETURN to continue, Q to quit")

        action = demostate.wait_to_proceed()

        if action == "quit":
            return

    try:
        demostate.run()
    finally:
        demostate.sane()


if __name__ == "__main__":
    main()
