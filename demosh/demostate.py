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

from typing import Dict, Iterator, List, Optional, TYPE_CHECKING

import sys

import curses
import os
import random
import select
import termios

from .command import RawSingleValue, RawMultiValue, Command

if TYPE_CHECKING:
    from .shellstate import ShellState


def chardelay() -> float:
    return random.uniform(0.01, 0.1)


class DemoState:
    def __init__(self, shellstate: 'ShellState', script: Iterator[str], parent: Optional['DemoState']=None) -> None:
        self.parent = parent
        self.skipping = False
        self.showing = False
        self.echo_blanks = False
        self.shellstate = shellstate
        self._end_color: Optional[str] = None
        self._colors: Dict[str, str] = {}

        self._overrides: Dict[str, bool] = {}

        self._action_chars = {
            # 'q':  "quit",
            'Q':  "quit",
            ' ':  "fast-forward",
            '\n': "run",
            '-':  "repeat",
            '+':  "skip",
        }

        self.fd = sys.stdin.fileno()

        if self.parent:
            # We have a parent. Copy its termios settings...
            self._sane = parent._sane
            self._cbreak = parent._cbreak
            self._raw = parent._raw
        else:
            # No parent. Actually set termios stuff ourselves...
            self.setup_termios()

            # ...and initialize curses -- not for whole-hog screen
            # management, just for terminfo access.
            curses.setupterm()

        self.commands: List[Command] = []

        self.read_commands(shellstate, script)

    def read_commands(self, shellstate: 'ShellState', script: Iterator[str]) -> None:
        while True:
            cmd = Command()

            rawcmd = cmd.read_command(script)

            if not rawcmd:
                break

            if rawcmd.type == "cmd":
                assert isinstance(rawcmd, RawSingleValue)
                cmd.cmdline = rawcmd.value
            elif rawcmd.type == "import":
                assert isinstance(rawcmd, RawSingleValue)
                self.read_commands(shellstate, open(rawcmd.value))
                continue
            elif rawcmd.type == "hook":
                assert isinstance(rawcmd, RawSingleValue)
                varname = f"DEMO_HOOK_{rawcmd.value}"

                value = self.shellstate.env.get(varname, None)

                if not value:
                    value = ":;"

                shellstate.functions.append("\n".join([
                    "function %s () {" % rawcmd.name,
                    value,
                    "}"
                ]))
                continue
            elif rawcmd.type == "macro":
                assert isinstance(rawcmd, RawMultiValue)
                macro_ds = DemoState(self.shellstate, iter(rawcmd.value), parent=self)

                self.shellstate.macros[rawcmd.name] = macro_ds
                continue

            self.commands.append(cmd)
            # print(f"<<<: {cmd}")

    def handlemeta(self, cmd: Command) -> bool:
        # Make mypy shut up
        assert cmd.cmdline and (len(cmd.cmdline) > 2) and (cmd.cmdline[0] == "#")

        cs = cmd.cmdline[2:].strip()

        if cs == "SKIP":
            self.skipping = True
            return True
        elif cs == "SHOW":
            self.showing = True
            return True
        elif cs == "HIDE":
            self.showing = False
            return True
        elif cs == "wait":
            # This is a standalone command, not a modifier for the next command.
            self._overrides['wait_before'] = False
            self._overrides['wait_after'] = True
            self._overrides['type_command'] = False
            self._overrides['explicit_wait'] = True
            return False
        elif cs == "print":
            # This is a standalone command, not a modifier for the next command.
            self._overrides['wait_before'] = False
            self._overrides['wait_after'] = True
            self._overrides['type_command'] = False
            return False
        elif cs == "waitafter":
            self._overrides['wait_after'] = True
            return True
        elif cs == "nowaitbefore":
            self._overrides['wait_before'] = False
            return True
        elif cs == "noshow":
            self._overrides['type_command'] = False
            return True
        else:
            self._overrides['wait_before'] = False
            self._overrides['wait_after'] = False
            self._overrides['type_command'] = False

            if (cs == "immed") or (cs == "immediate"):
                return True

        return False

    def start_color(self, color: int) -> str:
        cstr = self._colors.get(str(color), None)

        if not cstr:
            af = curses.tigetstr("setaf")
            cstr = ""

            if af:
                cstr = curses.tparm(af, color).decode('utf-8')

            self._colors[str(color)] = cstr

        return cstr

    def end_color(self) -> str:
        if self._end_color is None:
            sgr0 = curses.tigetstr("sgr0")
            decoded = ""

            if sgr0:
                decoded = sgr0.decode('utf-8')

            self._end_color = decoded

        return self._end_color

    def color(self, text: str) -> str:
        if not text:
            return ""

        if text[0] == "#":
            return self.start_color(1)
        # elif text[0] == '$':
        #     return self.start_color(3)

        return ""

    def display(self, text: str, newline: bool=True, force: bool=False) -> None:
        if self.showing or force:
            if text == "":
                if not (self.echo_blanks or force):
                    return

            sys.stdout.write(self.color(text))
            sys.stdout.write(text)

            sys.stdout.write(self.end_color())

            if newline:
                sys.stdout.write("\n")

            sys.stdout.flush()

            self.echo_blanks = not (text == "")

    def display_slowly(self, prefix: str, text: str, suffix: str, strip_leading_comments: bool=True) -> Optional[str]:
        ch = ""

        sys.stdout.write(self.color(prefix))
        sys.stdout.write(prefix)
        sys.stdout.flush()

        if strip_leading_comments:
            text = text.replace("\n#", "\n")

        try:
            self.raw()

            for i in range(len(text)):
                sys.stdout.write(text[i])
                sys.stdout.flush()

                # We're using select() here both to check for early input
                # _and_ for the intercharacter delay.
                keypressed, _, _ = select.select([self.fd], [], [], chardelay())

                if keypressed:
                    # Early input! Read it and rush to the end of the command.
                    ch = os.read(self.fd, 1).decode('utf-8')

                    if ch in self._action_chars:
                        if self._action_chars[ch] != "quit":
                            if i < len(text):
                                sys.stdout.write(text[i+1:])
                        break

            if suffix:
                sys.stdout.write(suffix)
                sys.stdout.flush()
        finally:
            sys.stdout.write(self.end_color())
            sys.stdout.flush()
            self.sane()

        action = self._action_chars.get(ch, None)
        # print(f"DS returning {action}")
        return action

    def setup_termios(self) -> None:
        LFLAG = 3
        CC = 6

        self._sane = termios.tcgetattr(self.fd)

        self._cbreak = termios.tcgetattr(self.fd)
        self._cbreak[LFLAG] = self._cbreak[LFLAG] & ~termios.ICANON & ~termios.ECHO

        self._raw = termios.tcgetattr(self.fd)
        self._raw[LFLAG] = self._raw[LFLAG] & ~termios.ICANON & ~termios.ECHO
        self._raw[CC][termios.VMIN] = 0
        self._raw[CC][termios.VTIME] = 0

    def sane(self) -> None:
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self._sane)

    def cbreak(self) -> None:
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self._cbreak)

    def raw(self) -> None:
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self._raw)

    def find_previous_command(self, delta: int) -> Optional[int]:
        idx = self.cmd_index - delta

        while idx >= 0:
            cmd = self.commands[idx]

            if not cmd.ishidden() and not cmd.iscomment() and not cmd.isblank():
                # print(f"-landed on {idx}: {cmd}")
                return idx

            # print(f"-continue past on {idx}: {cmd}")
            idx -= 1

        return None

    def run(self) -> None:
        self.cmd_index = 0

        while True:
            if self.cmd_index >= len(self.commands):
                break

            cmd = self.commands[self.cmd_index]

            if not self.showing:
                cmd.hidden = True

            # print(f"--{self.skipping and '#' or '-'} {self.cmd_index}: {cmd}")

            self.cmd_index += 1

            if self.skipping:
                if cmd.cmdline.strip() == "#@SHOW":
                    self.skipping = False
                else:
                    continue

            if cmd.isblank():
                self.display("")
                continue

            if cmd.iscomment():
                if cmd.ishiddencomment():
                    continue

                show = True

                if cmd.ismeta():
                    show = False

                    if self.handlemeta(cmd):
                        continue

                if show:
                    if cmd.cmdline.startswith("#$"):
                        self.display_slowly("$ ", cmd.cmdline[2:].strip(), "\n")
                    else:
                        self.display(self.shellstate.expand_env(cmd.cmdline.rstrip()))
                    continue

            # If we're here, it's meant to be executed. First, apply overrides.
            cmd = cmd.copy()

            for k, v in self._overrides.items():
                setattr(cmd, k, v)

            # Clear the overrides.
            self._overrides = {}

            # print(f"--> {self.cmd_index}: {cmd}")

            action = None
            typeout = cmd.typeout

            while True:
                if self.showing:
                    if cmd.type_command:
                        text = self.shellstate.expand_env(cmd.cmdline.rstrip())

                        if typeout:
                            action = self.display_slowly("$ ", text, "" if cmd.wait_before else "\n")
                        else:
                            self.display("$ " + text, newline=False)
                            action = None

                        if not action or (action == "fast-forward"):
                            if cmd.wait_before:
                                action = self.wait_to_proceed()

                        if cmd.wait_before:
                            sys.stdout.write("\n")
                            sys.stdout.flush()
                elif cmd.explicit_wait:
                    # The #@wait command _always_ executes, showing or not.
                    action = self.wait_to_proceed()

                if action == "repeat":
                    # We _don't_ want to execute this command; we want the previous
                    # command.
                    prev_idx = self.find_previous_command(2)

                    if prev_idx is None:
                        print(f"{self.start_color(5)}...nothing earlier to repeat!{self.end_color()}")
                        typeout = False
                        continue

                    # Found something good here.
                    self.cmd_index = prev_idx
                    self._overrides = {
                        "type_command": True,
                        "typeout": False,
                        "wait_before": True,
                    }

                # Not repeat, so we're finished repeating.
                break

            if action == "repeat":
                continue

            self.echo_blanks = True

            if not action or ((action != "skip") and (action != "quit")):
                rc = self.shellstate.run(self, cmd)

                if (rc != 0) and self.shellstate.exit_on_failure:
                    break

                if self.showing and cmd.wait_after:
                    action = self.wait_to_proceed()

            if action == "skip":
                print(f"{self.start_color(5)}...skipping{self.end_color()}")

            if action == "quit":
                break

            if action == "repeat":
                # We _don't_ want to execute this command; we want the previous
                # command.
                prev_idx = self.find_previous_command(1)

                if prev_idx is None:
                    print(f"{self.start_color(5)}...nothing earlier to repeat!{self.end_color()}")
                    typeout = False
                    continue

                # Found something good here.
                self.cmd_index = prev_idx
                self._overrides = {
                    "type_command": True,
                    "typeout": False,
                    "wait_before": True,
                }

    def wait_to_proceed(self) -> Optional[str]:
        # print("Waiting to proceed...")

        ch = None

        try:
            self.cbreak()

            while True:
                ch = os.read(self.fd, 1).decode('utf-8')

                if ch in self._action_chars:
                    break
        finally:
            self.sane()

        action = self._action_chars.get(ch, None)
        # print(f"WP returning {action}")
        return action


