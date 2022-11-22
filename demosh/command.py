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

from typing import Iterator, List, Optional, Union

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
    def __init__(self) -> None:
        self.cmdline = ""
        self.hidden = False
        self.type_command = True
        self.typeout = True
        self.wait_before = True
        self.wait_after = False
        self.explicit_wait = False

    def copy(self) -> 'Command':
        c2 = Command()
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

        return f"<CMD {S}{B}{A}{T}{H} {hrcmd}>"

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

        return self.cmdline.startswith("#!") or self.cmdline.startswith("##")

    def iscomment(self) -> bool:
        if not self.cmdline:
            return False

        return self.cmdline[0] == '#'

    def read_command(self, input: Iterator[str]) -> Optional[Union[RawSingleValue, RawMultiValue]]:
        buf = ''
        braces = 0

        for line in input:
            # This is to make mypy be quiet.
            assert line, "unexpected EOF"

            done = False
            # print(f'<<< {line.rstrip()}')

            if line.startswith("#@hook "):
                if buf:
                    raise Exception("Can't have a hook in a compound statement")

                # This is a hook function.
                _, hookname, hookvar = line.strip().split(" ", 2)

                return RawSingleValue("hook", hookname, hookvar)

            elif line.startswith("#@macro "):
                _, macroname = line.strip().split(" ", 1)

                macro: List[str] = []

                while True:
                    l2 = next(input)

                    if l2.rstrip() == "#@end":
                        break

                    macro.append(l2.lstrip())

                return RawMultiValue("macro", macroname, macro)

            elif line.startswith("#@import"):
                _, path = line.strip().split(" ", 1)

                return RawSingleValue("import", "import", path.strip())

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
                return RawSingleValue("cmd", "cmd", buf)

        return None
