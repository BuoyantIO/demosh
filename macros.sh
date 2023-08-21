## SPDX-FileCopyrightText: 2022 Buoyant, Inc.
## SPDX-License-Identifier: Apache-2.0

# Let's set up a couple of macros.
#
# wait_then_date will wait for the user to hit RETURN,
# then run the date command.

#@macro wait_then_date
  #@echo "Waiting..."
  #@wait
  date
#@end

# This macro definitions won't actually show up when
# importing this file, of course, but it'll be usable after.
