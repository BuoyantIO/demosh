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

from typing import Dict, List, Set, TYPE_CHECKING

import sys

import os
import re
import shlex
import signal
import subprocess

if TYPE_CHECKING:
    from .command import Command
    from .demostate import DemoState


# This is what the start of an assignment looks like to us...
reAssignment = re.compile(r"^\s*(export\s+)?([a-zA-Z0-9_]+)=")

# ...and this is what the first line of a function definition
# looks like to us.
reFunction = re.compile(r"^\s*(function\s+)?([a-zA-Z0-9_]+)\s*\(\)\s+\{")

def str2bool(v):
    return str(v).lower() in ("yes", "true", "t", "y", "1")


class ShellState:
    @staticmethod
    def ignore_signals() -> None:
        # print(f"Ignoring signals in {os.getpid()}")
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

    @staticmethod
    def allow_signals() -> None:
        # print(f"Allowing signals in {os.getpid()}")
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

    def __init__(self, argv0, script: str, args: List[str]) -> None:
        self.cwd = os.getcwd()
        self.env = os.environ.copy()
        self.functions: List[str] = []
        self.macros: Dict[str, 'DemoState'] = {}
        self.exit_on_failure = False
        self.quiet_failure = str2bool(os.environ.get("DEMOSH_QUIET_FAILURE", ""))
        self._hooks: Set[str] = set()

        self.shell = os.environ.get("SHELL", "/bin/sh")
        self.env["SHELL"] = os.path.abspath(argv0)

        self.env["0"] = os.path.abspath(script)
        # print(f">> set $0 = {self.env['0']}")

        i = 1
        for arg in args:
            self.env[str(i)] = arg
            # print(f">> set ${i} = {self.env[str(i)]}")
            i += 1

        ShellState.ignore_signals()

    def expand_env(self, s: str) -> str:
        for k in self.env.keys():
            bracketed = '${%s}' % k
            s = s.replace(bracketed, self.env[k])

        return s

    def subshell(self, demostate: 'DemoState') -> None:
        self.do_shell_command(demostate, f"{self.shell} -i")

    def run(self, demostate: 'DemoState', cmd: 'Command') -> int:
        cmdline = cmd.cmdline
        assert cmdline is not None, "how can cmdline be None?"

        if cmd.ismeta():
            cmdline = cmdline[2:]

        rc = 127

        # cmdline = self.expand_env(cmdline)
        # print(">> run << %s >>" % cmdline)

        m = reAssignment.match(cmdline)

        if m:
            var=m.group(2)
            value=cmdline[m.end(0):]
            # print(f"Assignment: {var} = {value}")
            return self.do_assign(demostate, var, value)

        m = reFunction.match(cmdline)

        if m:
            cmdline = f"{m.group(2)}() {{" + cmdline[m.end():]
            # print(f"Function: {cmdline}")

            self.functions.append(cmdline)
            return 0

        rc = self.run_command(demostate, cmdline)

        return rc

    def run_command(self, demostate: 'DemoState', cmdline: str) -> int:
        rc = 127

        try:
            fields = shlex.split(cmdline)
        except ValueError as e:
            print(f"could not parse line: {cmdline}")
            return rc

        first = fields[0]

        # Macro?
        if first in self.macros:
            # print(f"macro: {first}")
            self.macros[first].run()

            rc = 0
            # print(f"macro: {first} done")
        else:
            handler = getattr(self, "do_" + first, None)

            if not handler:
                handler = self.do_shell_command

            rc = handler(demostate, cmdline)

        # print(f"{first}: rc={rc}")
        return rc

    def do_wait(self, demostate: 'DemoState', cmd: str) -> int:
        # Nothing to do for this!
        return 0

    def do_print(self, demostate: 'DemoState', cmd: str) -> int:
        text = " ".join(shlex.split(cmd[6:]))

        text = self.expand_env(text)

        demostate.display(text, force=True)
        return 0

    def do_set(self, demostate: 'DemoState', cmd: str) -> int:
        # Handle "set". Currently we just honor set -e.
        fields = shlex.split(cmd)
        flags = fields[1]

        value = True

        if flags[0] == "-":
            value = True
        elif flags[0] == "+":
            value = False
        else:
            sys.stderr.write(f"Unknown set flag: {flags[0]}\n")
            sys.stderr.flush()
            return 1

        for flag in flags:
            if flag == "e":
                self.exit_on_failure = value

        return 0

    def do_cd(self, demostate: 'DemoState', cmd: str) -> int:
        proc = subprocess.Popen(["bash"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=self.cwd, env=self.env, close_fds=True)

        assert proc.stdin is not None   # hush, mypy
        proc.stdin.write(cmd.encode('utf-8'))
        proc.stdin.write("pwd\n".encode('utf-8'))

        stdout, stderr = proc.communicate()

        if proc.returncode == 0:
            self.cwd = stdout.decode('utf-8').strip()
            return 0

        print("cd failed: %s" % stderr.decode('utf-8'))
        return 1

    def do_assign(self, demostate: 'DemoState', name: str, value: str) -> int:
        i = 0

        while True:
            envvar = self.env.get(str(i), None)
            if envvar is None:
                break
            value = value.replace("$%d" % i, envvar)
            value = value.replace("${%d}" % i, envvar)

            i += 1

        # print(f"assign '{name}' = '{value}'")

        if name == "DEMOSH_QUIET_FAILURE":
            self.quiet_failure = str2bool(value.strip())
            # print(f"quiet_failure = {self.quiet_failure}")

        proc = subprocess.Popen(["bash"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=self.cwd, env=self.env, close_fds=True)

        assert proc.stdin is not None   # hush, mypy

        fn = "\n".join(self.functions) + "\n"
        c1 = f'{name}={value}'
        c2 = f'echo "${name}"'

        # print("assign c1: '%s'" % c1)
        # print("assign c2: '%s'" % c2)

        proc.stdin.write(fn.encode('utf-8'))
        proc.stdin.write(c1.encode('utf-8'))
        proc.stdin.write("\n".encode('utf-8'))
        proc.stdin.write(c2.encode('utf-8'))
        proc.stdin.write("\n".encode('utf-8'))

        stdout, stderr = proc.communicate()

        # print("assign rc: %d" % proc.returncode)
        # print("assign stdout: '%s'" % stdout.decode('utf-8'))
        # print("assign stderr: '%s'" % stderr.decode('utf-8'))

        if stderr:
            sys.stdout.write(stderr.decode('utf-8'))
            sys.stdout.flush()

        if proc.returncode == 0:
            self.env[name] = stdout.decode('utf-8').strip()
            # print("assign final: '%s' = '%s'" % (name, self.env[name]))
            return 0

        print("assignment failed!")
        return 1

    def do_shell_command(self, demostate: 'DemoState', cmd: str) -> int:
        allcmd = "\n".join(self.functions) + "\n" + cmd

        proc = subprocess.Popen(allcmd, shell=True,
                                cwd=self.cwd, env=self.env, close_fds=True, preexec_fn=ShellState.allow_signals)

        proc.wait()
        # print("proc finished: %d" % proc.returncode)
        return proc.returncode


