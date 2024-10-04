#!/bin/bash

## SPDX-FileCopyrightText: 2022 Buoyant, Inc.
## SPDX-License-Identifier: Apache-2.0

## This is a hidden comment.

clear
echo "This will run like a normal script."

# We can import things from other files.
#@import macros.sh

# We can define hooks too.
#@hook show_browser BROWSER
#@hook nonexistant NONEXISTANT

## The #@SHOW and #@HIDE tags control whether we're showing commands, waiting
## for the user to confirm proceeding, etc., or just running things like a
## normal script.
#@SHOW

# Welcome to our demo. Isn't it awesome?

# You can use the `@print` directive to produce colorized output:

#@print This will be ordinary black text.
#@print # This will be red like a comment.

# Next, let's check for hooks. If you've set DEMO_HOOK_BROWSER to a nonempty
# value, you should see "we have a browser hook!" here.

#@ifhook show_browser
#@immed
echo "We have a browser hook!"
#@endif

# As long as you haven't set DEMO_HOOK_NONEXISTANT to a nonempty
# value, you should not see "we have a nonexistant hook?" here.

#@ifhook nonexistant
#@immed
echo 'We have a nonexistant hook?'
#@endif

## Hit RETURN to continue (this is the wait directive).
#@wait

# Let's try an assignment.
FOO="Hello world"
echo "$FOO"

# exported assignments work too. (The word export itself is a noop in demosh,
# to be clear: variables are always exported.)

export BAR="Exported hello world"
echo "$BAR"

# The $SHELL environment variable should be overwritten to be demosh itself.
echo "SHELL is $SHELL"

# Here's a function definition with the "function" keyword...
function hello() {
    echo "Hello, $1!"
}

# ...and here's one without it.
hello2 () {
    echo "Hello again, $1!"
}

# Can we run the functions?
hello "world"
hello2 "world"

# Assignments persist across blocks, of course.

echo $FOO
echo $BAR

# cd is handled internally, so this should work.
cd /tmp
pwd

# Let's test a macro.
wait_clear

# How about an immediate macro call?
#@wait_then_date

# Here, we'll need to hit RETURN to run our command.
echo "Waiting only before"

# This is an immediate command: no waiting at all.
#@immed
echo "No waiting."

# Here we wait before and after.
#@waitafter
echo "Waiting before and after"

#@waitafter
#@nowaitbefore
echo "Waiting only after"

# Let's try the function again.
hello "world again"

# Let's test signal handling. You should be able to hit
# Ctrl-C to interrupt the sleep.

sleep 120

# And that's the whole `demosh` shell-script demo!!
