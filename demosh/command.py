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

from typing import Generator, Iterator, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .demostate import DemoState

class RawSingleValue:
    def __init__(self, type: str, name: str, value: str) -> None:
        self.type = type
        self.name = name
        self.value = value

    def __str__(self) -> str:
        return f"<SINGLE {self.type} {self.name} = {self.value}>"

class RawMultiValue:
    def __init__(self, type: str, name: str, value: List[str]) -> None:
        self.type = type
        self.name = name
        self.value = value

    def __str__(self) -> str:
        return f"<MULTI {self.type} {self.name} = {self.value}>"


class Command:
    def __init__(self, cmdline: str, comment: Optional[bool]=False,
                 markdown: Optional[bool]=False, conditional: Optional[str]=None,
                 demostate: Optional['DemoState']=None) -> None:
        self.cmdline = cmdline
        self.comment = comment
        self.markdown = markdown
        self.conditional = conditional
        self.demostate = demostate
        self.hidden = False
        self.type_command = True
        self.typeout = True
        self.wait_before = True
        self.wait_after = False
        self.explicit_wait = False

    def copy(self) -> 'Command':
        c2 = Command(self.cmdline, comment=self.comment, markdown=self.markdown,
                     conditional=self.conditional, demostate=self.demostate)
        c2.cmdline = self.cmdline
        c2.hidden = self.hidden
        c2.type_command = self.type_command
        c2.typeout = self.typeout
        c2.wait_before = self.wait_before
        c2.wait_after = self.wait_after
        c2.explicit_wait = self.explicit_wait

        return c2

    def __str__(self) -> str:
        S = "S" if self.type_command else " "
        B = "B" if self.wait_before else " "
        A = "A" if self.wait_after else " "
        T = "T" if self.typeout else " "
        H = "H" if self.hidden else " "

        hrcmd = self.cmdline.rstrip()

        kind = "CMD"

        if self.comment:
            kind = "#M#" if self.markdown else "###"

        cond = f" {self.conditional}" if self.conditional else ""

        return f"<{kind} {S}{B}{A}{T}{H}{cond} {hrcmd}>"

    def __bool__(self) -> bool:
        return bool(self.cmdline)

    def ishidden(self) -> bool:
        return self.hidden

    def isblank(self) -> bool:
        if not self.cmdline:
            return True

        return len(self.cmdline.strip()) == 0

    def ismeta(self) -> bool:
        if not self.cmdline:
            return False

        return self.cmdline.startswith("#@")

    def ishiddencomment(self) -> bool:
        if not self.cmdline:
            return False

        if self.markdown:
            return False

        return self.cmdline.startswith("#!") or self.cmdline.startswith("##")

    def iscomment(self) -> bool:
        if self.comment:
            return True

        if not self.cmdline:
            return False

        return self.cmdline[0] == '#'

    def isconditional(self) -> bool:
        return bool(self.conditional)

class InputReader:
    def __init__(self, mode: str, input: Iterator[str]) -> None:
        self.mode = mode
        self.markdown_allowed = (mode == "markdown")
        self.input = input

    def parse_directive(self, line: str) -> Union[RawSingleValue, RawMultiValue]:
        if line.startswith("#@hook "):
            # This is a hook function.
            _, hookname, hookvar = line.strip().split(" ", 2)

            return RawSingleValue("hook", hookname, hookvar)

        elif line.startswith("#@macro "):
            _, macroname = line.strip().split(" ", 1)

            macro: List[str] = []

            while True:
                l2 = next(self.input)

                if l2.rstrip() == "#@end":
                    break

                macro.append(l2.lstrip())

            return RawMultiValue("macro", macroname, macro)

        elif line.startswith("#@import"):
            _, path = line.strip().split(" ", 1)

            return RawSingleValue("import", "import", path.strip())

        elif line.startswith("#@ifhook"):
            _, hookname = line.strip().split(" ", 1)

            body: List[str] = []

            while True:
                l2 = next(self.input)

                if l2.rstrip() == "#@endif":
                    break

                body.append(l2.lstrip())

            return RawMultiValue("ifhook", hookname, body)

        else:
            # If it's not a special directive, meh, just return it
            # as a command.
            return RawSingleValue("cmd", "cmd", line)

    def read_element(self) -> Generator[Union[RawSingleValue, RawMultiValue], None, None]:
        buf = ''
        braces = 0

        for line in self.input:
            # print(f'<<< {self.mode[0].upper()}: {line.rstrip()}')

            # if buf:
            #     print(f'    B: {buf}')

            if self.mode == "shell":
                done = False

                if (line.startswith("#@hook ") or
                    line.startswith("#@macro ") or
                    line.startswith("#@import ") or
                    line.startswith("#@ifhook ")):
                    if buf:
                        raise Exception("Can't have a directive in a compound statement")

                    rawcmd = self.parse_directive(line.strip())
                    yield rawcmd
                    continue

                if line.strip() == "```":
                    # This is the end of a bash block in Markdown, and it's
                    # not allowed in one of our shell-script inputs.
                    if self.markdown_allowed:
                        self.mode = "markdown"
                        continue

                    done = True
                    break

                buf += line
                stripped = line.rstrip()

                if stripped:
                    c = stripped[-1]
                else:
                    c = '\n'

                if c == '\\':
                    pass
                elif c == '{':
                    braces += 1
                elif c == '}':
                    braces -= 1

                    if braces <= 0:
                        done = True
                        braces = 0
                elif braces <= 0:
                    done = True

                # print(f'{done} {ord(c)} {braces} {line}')

                if done:
                    if buf.startswith("#"):
                        yield RawSingleValue("comment", "shell", buf)
                    else:
                        yield RawSingleValue("cmd", "cmd", buf)

                    buf = ""
                    continue

            elif self.mode == "markdown":
                # If we see "```bash" or "```sh", we switch to shell mode.
                if line.startswith("```bash") or line.startswith("```sh"):
                    if buf:
                        yield RawSingleValue("comment", "markdown", buf)
                        buf = ""

                    self.mode = "shell"
                    continue

                # OK, not a bash block. Is it a directive in a Markdown comment?
                if line.startswith("<!-- @"):
                    if buf:
                        yield RawSingleValue("comment", "markdown", buf)
                        buf = ""

                    line = line.replace("<!-- @", "#@")
                    line = line.replace("-->", "")

                    rawcmd = self.parse_directive(line.strip())
                    # print(f"markdown directive: {rawcmd}")
                    yield rawcmd
                    continue

                # Not a bash block, not a directive. Save it.
                buf += line

        if buf:
            if self.mode == "shell":
                if buf.startswith("#"):
                    yield RawSingleValue("comment", "shell", buf)
                else:
                    yield RawSingleValue("cmd", "cmd", buf)
            else:
                yield RawSingleValue("comment", "markdown", buf)
