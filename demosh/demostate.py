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

from typing import Any, Dict, Iterator, List, Optional, Set, TYPE_CHECKING

import sys

import curses
import os
import random
import select
import termios
from .builtins import script as builtin_script

from .command import RawSingleValue, RawMultiValue, Command, InputReader

if TYPE_CHECKING:
    from .shellstate import ShellState


def chardelay() -> float:
    return random.uniform(0.01, 0.1)


class DemoState:
    Standalones = {
        "checkfor",
        "print",
    }

    def __init__(self, shellstate: 'ShellState', mode: str, script: Iterator[str],
                 parent: Optional['DemoState']=None,
                 debug: Optional[bool]=False,
                 load_builtins: Optional[bool]=True,
                 load_init: Optional[bool]=True) -> None:
        self._level: int = parent._level + 1 if parent else 0
        self.debug = False

        if debug:
            self.debug = True
        elif parent:
            self.debug = parent.debug

        self.parent = parent
        self.mode = mode
        self.skipping = False
        self.showing = False
        self.echo_blanks = False
        self.shellstate = shellstate
        self._end_color: Optional[str] = None
        self._colors: Dict[str, str] = {}
        self._sane: Optional[List[Any]] = None
        self._cbreak: Optional[List[Any]] = None
        self._raw: Optional[List[Any]] = None

        self._overrides: Dict[str, bool] = {}

        self.reader = InputReader(mode, script)

        self._action_chars = {
            # 'q':  "quit",
            'Q':  "quit",
            ' ':  "fast-forward",
            '\n': "run",
            '-':  "repeat",
            '+':  "skip",
        }

        self.fd = sys.stdin.fileno()

        if self.parent is not None:
            # We have a parent. Copy its termios settings...
            self._sane = self.parent._sane
            self._cbreak = self.parent._cbreak
            self._raw = self.parent._raw
        else:
            # No parent. Actually set termios stuff ourselves...
            self.setup_termios()

            # ...and initialize curses -- not for whole-hog screen
            # management, just for terminfo access.
            curses.setupterm()

        self.commands: List[Command] = []

        if load_builtins and not parent:
            if self.debug:
                print("Loading builtins...")

            self.read_commands(shellstate, InputReader("shell", iter(builtin_script.split("\n"))))

            if self.debug:
                print("End of builtins...")

        if load_init and not parent:
            init_file = None
            init_path = None
            init_mode = "shell"

            for path, mode in [
                ( ".demoshrc", "shell" ),
                ( ".demoshrc.md", "markdown" ),
                ( os.path.expanduser("~/.demoshrc"), "shell" ),
                ( os.path.expanduser("~/.demoshrc.md"), "markdown" ),
            ]:
                try:
                    init_file = open(path, "r")
                except FileNotFoundError:
                    continue

                init_path = path
                init_mode = mode
                break

            if init_file:
                if self.debug:
                    print(f"Loading {init_path} as {init_mode}...")

                self.read_commands(shellstate, InputReader(init_mode, init_file))

                if self.debug:
                    print("End of ~/.demoshrc...")

                init_file.close()

        self.read_commands(shellstate, InputReader(self.mode, script))

    def read_commands(self, shellstate: 'ShellState', reader: Optional[InputReader]) -> None:
        if reader is None:
            reader = self.reader

        for rawcmd in reader.read_element():
            if self.debug:
                print(f"{self._level}: CMD {rawcmd}")

            if rawcmd.type == "cmd":
                assert isinstance(rawcmd, RawSingleValue)
                cmd = Command(rawcmd.value)
                self.commands.append(cmd)

            elif rawcmd.type == "comment":
                assert isinstance(rawcmd, RawSingleValue)
                cmd = Command(rawcmd.value, comment=True, markdown=(rawcmd.name == "markdown"))
                self.commands.append(cmd)

            elif rawcmd.type == "import":
                assert isinstance(rawcmd, RawSingleValue)

                imode = "shell"

                if rawcmd.value.lower().endswith(".md"):
                    imode = "markdown"

                ireader = InputReader(imode, open(rawcmd.value, "r"))
                self.read_commands(shellstate, ireader)

            elif rawcmd.type == "hook":
                assert isinstance(rawcmd, RawSingleValue)
                varname = f"DEMO_HOOK_{rawcmd.value}"

                value = self.shellstate.env.get(varname, None)

                if value:
                    self.shellstate._hooks.add(rawcmd.name)
                else:
                    value = ":;"

                shellstate.functions.append("\n".join([
                    "%s() {" % rawcmd.name,
                    value,
                    "}"
                ]))

            elif rawcmd.type == "macro":
                if self.debug:
                    print(f"{self._level}: processing macro {rawcmd.name}")

                assert isinstance(rawcmd, RawMultiValue)
                macro_ds = DemoState(self.shellstate, "shell", iter(rawcmd.value), parent=self)

                if self.debug:
                    print(f"{self._level}: saving DemoState for macro {rawcmd.name}")

                self.shellstate.macros[rawcmd.name] = macro_ds

            elif rawcmd.type == "ifhook":
                if self.debug:
                    print(f"{self._level}: processing ifhook {rawcmd.name}")

                assert isinstance(rawcmd, RawMultiValue)
                ifhook_ds = DemoState(self.shellstate, "shell", iter(rawcmd.value), parent=self)

                if self.debug:
                    print(f"{self._level}: pushing DemoState for ifhook {rawcmd.name}")

                cmd = Command(rawcmd.name, conditional="ifhook", demostate=ifhook_ds)
                self.commands.append(cmd)

    def handlemeta(self, cmd: Command) -> bool:
        # Make mypy shut up
        assert (len(cmd.cmdline) > 2) and (cmd.cmdline[0] == "#")

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
        elif cs in DemoState.Standalones:
            # This is a standalone command, not a modifier for the next command.
            self._overrides['wait_before'] = False
            self._overrides['wait_after'] = True
            self._overrides['type_command'] = False
            return False
        elif cs == "wait":
            # This is a standalone command, not a modifier for the next command.
            self._overrides['wait_before'] = False
            self._overrides['wait_after'] = True
            self._overrides['type_command'] = False
            self._overrides['explicit_wait'] = True
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
        elif cs == "notypeout":
            self._overrides['typeout'] = False
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

    def get_cap(self, capname: str) -> str:
        cstr = self._colors.get(capname, None)

        if cstr is None:
            cstr = ""
            cap = curses.tigetstr(capname)

            if cap:
                cstr = cap.decode('utf-8')

            self._colors[capname] = cstr

        return cstr

    def start_bold(self) -> str:
        return self.get_cap("smso")

    def end_bold(self) -> str:
        return self.get_cap("rmso")

    def start_underline(self) -> str:
        return self.get_cap("smul")

    def end_underline(self) -> str:
        return self.get_cap("rmul")

    def color(self, text: str) -> str:
        if not text:
            return ""

        if text[0] == "#":
            return self.start_color(1)
        # elif text[0] == '$':
        #     return self.start_color(3)

        return ""

    def markdownify(self, text: str) -> str:
        states = [ "LineStart" ]
        dchars = { "`", "_" }
        colors: List[str] = []
        decorations: List[str] = []

        output = ""
        hc = 0

        idx = 0

        while idx < len(text):
            c = text[idx]
            idx += 1

            state = states[-1]

            if state == "LineStart":
                if c == '#':
                    # Header!
                    hc = 1
                    states.append("Header")
                else:
                    if not colors:
                        cstr = self.start_color(1)
                        colors.append(cstr)
                        output += cstr

                    states.append("Normal")
                    idx -= 1

            elif state == "Header":
                if c == '#':
                    hc += 1
                else:
                    if hc == 1:
                        output += self.start_bold()

                    cstr = self.start_color(2)
                    colors.append(cstr)
                    output += cstr
                    output += self.start_underline()
                    output += '#' * hc
                    idx -= 1
                    states.append("Normal")

            elif state == "Normal":
                if c == "\n":
                    states.pop()

                    if states[-1] == "Header":
                        output += self.end_underline()
                        output += self.end_bold()
                        output += self.end_color()
                        colors = []

                        states.pop()
                        assert states[-1] == "LineStart", "Popped Header and didn't get LineStart?"

                elif c == "*":
                    # Asterisk is weird because "**" and "*" are both valid
                    # decorations, and because "*" can also mark a list item.
                    states.append("Asterisk")
                    continue

                elif c == "`":
                    # It's important to realize that we'll never have "```" at this point
                    # (it will have become a command) and also that we don't want to do
                    # formatting inside backticks. So switch to a new state.

                    states.append("Backtick")

                    # Switch to color 4.
                    cstr = self.start_color(4)
                    colors.append(cstr)
                    output += cstr

                    continue

                elif c in dchars:
                    # XXX Kind of leftover code: the only decoration we can see here is
                    # an underscore, so this can probably be simplified now.
                    if decorations and (c == decorations[-1]):
                        decorations.pop()
                        colors.pop()
                        output += colors[-1]
                        continue
                    else:
                        color = 5

                        if c == '`':
                            color = 4
                        elif c == '_':
                            color = 4

                        cstr = self.start_color(color)
                        colors.append(cstr)
                        output += cstr

                        decorations.append(c)
                        continue

                output += c

            elif state == "Asterisk":
                # We're not going to stay in the Asterisk
                # state no matter what.
                states.pop()

                if c == '*':
                    # Two asterisks is its very own kind of decoration.
                    if decorations and ("**" == decorations[-1]):
                        decorations.pop()
                        colors.pop()
                        output += colors[-1]
                        continue

                    cstr = self.start_color(5)
                    colors.append(cstr)
                    output += cstr
                    decorations.append("**")
                elif (decorations and ("*" == decorations[-1])):
                    # This is the end of a single asterisk decoration.
                    decorations.pop()
                    colors.pop()
                    output += colors[-1] + c
                    continue
                elif not (c.isalnum() or (c == "\n")):
                    # This is just a plain old asterisk, not the start of
                    # anything.
                    output += "*" + c
                else:
                    # One asterisk is a decoration.
                    if decorations and ("*" == decorations[-1]):
                        decorations.pop()
                        colors.pop()
                        output += colors[-1]
                        continue

                    cstr = self.start_color(5)
                    colors.append(cstr)
                    output += cstr + c
                    decorations.append("*")

            elif state == "Backtick":
                if c == "`":
                    # Done with backticks!
                    states.pop()
                    colors.pop()
                    output += colors[-1]
                    continue

                output += c

        output += self.end_color()

        return output

    def display(self, text: str, newline: bool=True, force: bool=False, markdown: bool=False) -> None:
        if self.showing or force:
            if text == "":
                if not (self.echo_blanks or force):
                    return

            if not markdown:
                sys.stdout.write(self.color(text))
                sys.stdout.write(text)
                sys.stdout.write(self.end_color())
            else:
                sys.stdout.write(self.markdownify(text))

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
        if self._sane:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self._sane)

    def cbreak(self) -> None:
        if self._cbreak:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self._cbreak)

    def raw(self) -> None:
        if self._raw:
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

            if self.debug:
                print(f"--{self.skipping and '#' or '-'} {self.cmd_index}: {cmd}")

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
                        self.display(self.shellstate.expand_env(cmd.cmdline.rstrip()),
                                     markdown=bool(cmd.markdown))
                    continue

            if cmd.isconditional():
                if cmd.conditional == "ifhook":
                    if self.debug:
                        ispresent = '' if (cmd.cmdline in self.shellstate._hooks) else ' not'
                        print(f"Hook {cmd.cmdline}{ispresent} present")

                    if cmd.cmdline in self.shellstate._hooks:
                        assert isinstance(cmd.demostate, DemoState)
                        cmd.demostate.run()
                else:
                    print(f"Invalid conditional type {cmd.conditional}")

                continue

            # If we're here, it's meant to be executed. First, apply overrides.
            cmd = cmd.copy()

            for k, v in self._overrides.items():
                setattr(cmd, k, v)

            # Clear the overrides.
            self._overrides = {}

            if self.debug:
                print(f"--> {self.cmd_index}: {cmd}")

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

                        if cmd.wait_before or (not typeout):
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

            if (not action or
                ((action != "subshell") and (action != "skip") and (action != "quit"))):
                rc = self.shellstate.run(self, cmd)

                if (rc != 0) and self.shellstate.exit_on_failure:
                    if not self.shellstate.quiet_failure:
                        print(f"{self.start_color(5)}...exiting due to failure.{self.end_color()}")
                    break

                if self.showing and cmd.wait_after:
                    action = self.wait_to_proceed()

            if action == "subshell":
                # Repeat this same command when back from the subshell.
                self.cmd_index -= 1
                self.shellstate.subshell(self)
                continue

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


