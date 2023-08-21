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

script = '''
# wait_clear is a macro that just waits before clearing the terminal. We
# do this a lot.

#@macro wait_clear
  #@wait
  #@clear
#@end

# browser_then_terminal, if we're livecasting, will wait, then switch the
# view for the livestream to the browser, then wait again, then clear the
# terminal before switching the view back to the terminal. There are a lot
# of places in the demo where we want to present stuff in the terminal, then
# flip to the browser to show something, then flip back to the terminal.
#
# If you're _not_ livecasting, so the hooks aren't doing anything... uh...
# you'll be stuck hitting RETURN twice to clear the screen and get to the
# next step. Working on that...

#@macro _b_t_t_internal
  #@ifhook show_terminal
    #@wait
    #@show_browser
    #@wait
    #@clear
    #@show_terminal
  #@endif
#@end

#@macro browser_then_terminal
  #@ifhook show_browser
    #@_b_t_t_internal
  #@endif
#@end

# start_livecast is a macro for starting a livecast. It assumes that the demo
# hooks are working, and uses them to display slides at first while putting a
# cue to hit RETURN on the terminal. Once the user hits RETURN, it clears the
# terminal before showing it, so that the stuff after the macro call is front
# and center.

#@macro _s_t_internal
  #@ifhook show_terminal
    #@show_slides

    clear
    echo Waiting...

    #@wait_clear
    #@show_terminal
  #@endif
#@end

#@macro start_livecast
  #@ifhook show_slides
    #@_s_t_internal
  #@endif
#@end
'''