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

# wait_clear will wait for the user to hit RETURN, then
# clear the screen.

#@macro wait_clear
  echo "Waiting..."
  #@wait
  #@clear
#@end

# Neither of those macro definitions will actually show
# up when importing this file, of course, but they'll be
# usable after.
