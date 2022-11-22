#!/bin/bash

## SPDX-FileCopyrightText: 2022 Buoyant, Inc.
## SPDX-License-Identifier: Apache-2.0

## This is a hidden comment.

clear
echo "This will run like a normal script."

# We can import things from other files.
#@import macros.sh

## The #@SHOW and #@HIDE tags control whether we're showing commands, waiting
## for the user to confirm proceeding, etc., or just running things like a
## normal script.
#@SHOW

# Welcome to our demo. Isn't it awesome?

# Let's try an assignment.
FOO="Hello world"
echo "$FOO"

# The $SHELL environment variable should be overwritten to be demosh itself.
echo "SHELL is $SHELL"

# Here's a function definition.
function hello() {
    echo "Hello, $1!"
}

# Can we run the function?
hello "world"

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

# cd is handled internally, so this should work.
cd /tmp
pwd


