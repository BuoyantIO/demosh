# `demosh`

**tl;dr:** `demosh` can run shell scripts or Markdown files in a very
interactive way, showing commentary in between running commands, and waiting
for you to hit RETURN to proceed before running commands. It was created as
a tool for doing live demos of relatively complex things. See `testing.md`
and `testing.sh` for examples.

**To exit `demosh`, hit `Q` (capital `Q`).** `demosh` deliberately ignores
signals and won't respond to `control-C` or `control-D`, so that the commands
it runs don't get confused.

<!--
SPDX-FileCopyrightText: 2022-2023 Buoyant, Inc.
SPDX-License-Identifier: Apache-2.0
-->

**To install `demosh`:** just run `pip install demosh`! or see
[`INSTALLING.md`](INSTALLING.md) if you want to install from source.

**To use `demosh` to demo itself:** see [`demo/DEMO.md`](demo/DEMO.md).

**To work on `demosh` itself:** see [`DEVELOPING.md`](DEVELOPING.md).


----

`demosh` is a **D**emo **SH**ell: it reads shell scripts or Markdown files and
executes shell commands from them. However, it can also output commentary from
the script, show commands before running them, and pause before (or after)
running each command. Pausing and what to show can be controlled by inline
comments in the script itself. See `testing.md` and `testing.sh` for examples.

## Running

Run `demosh path-to-script [arg [arg [...]]]` as if `demosh` were itself the
shell.

**`demosh` starts out _not_ showing commentary and _not_ being interactive**,
so that the script can do initialization quietly. Use the `@SHOW` directive
to switch into the fully-interactive mode (and use `@HIDE` to go back).

### Init Scripts and Builtins

On startup, `demosh` will search for one of four startup files to read:

- `.demoshrc` in the current directory
- `.demoshrc.md` in the current directory
- `$HOME/.demoshrc`
- `$HOME/.demoshrc.md`

These files are checked in the order above; if any are present, the first one
found will be loaded, with `.demoshrc` files treated as shell scripts and
`.demoshrc.md` files treated as Markdown. The `--no-init` flag prevents this
behavior.

The startup file is treated _exactly_ the same as files supplied on the
command line. In particular, `@SHOW` directives will cause them to go
interactive (as discussed below), and anything they define will be available
for files on the command line to use.

`demosh` will also load a set of builtin definitions on startup, unless the
`--no-builtins` flag is present on the command line. Builtins are discussed
below with other directives.

### Executing and Waiting

When `demosh` has a command to execute in interactive mode, it will:

- Optionally type the command slowly
- Optionally wait for a RETURN
- Run the command
- Optionally wait for a RETURN

By default, typing the command and waiting for RETURN _before_ execution are
enabled, and waiting for RETURN after executing the command is disabled.

While "waiting for RETURN", there are several things you can actually type:

- Hitting `space` while the command is being typed will type the rest of
  the command immediately.

- Hitting `RETURN` while the command is being typed will type the rest of
  the command immediately and then execute it immediately.

- Hitting `Q` will quit `demosh`. This must be a capital `Q`; lowercase `q`
  will do nothing.

- Hitting `-` will repeat the previous command (note that this currently
  doesn't work well when executing a macro).

- Hitting `+` will skip to the next command _without_ executing this one
  (note that this currently doesn't work well when executing a macro).

<!--
(! isn't currently implemented!)

- Hitting `!` will spawn a subshell with all the environment variables
  defined in the script intact.

   - **NOTE WELL**: the subshell will not, at present, include functions
     defined in the script. -->

When `demosh` has a command to execute in noninteractive mode, it just
executes it.

## Directives

When reading from shell scripts, `demosh` directives look like comments:

```bash
#@SHOW
#@HIDE
```

etc. **There must not be any spaces between `#` and `@` -- only `#@` can
start a directive.**

When reading Markdown, directives can still be in comments in `bash` blocks,
but most of the time it works better to put them in Markdown comments:

```markdown
<!-- @SHOW -->
<!-- @HIDE -->
```

etc. **Note that there is no leading `#` in this case.**

### Valid directives:

- `@SHOW`: start showing commentary, displaying commands before running them,
   waiting for the user to hit RETURN before running things, etc. This is
   `demosh`'s fully-interactive-during-a-demo mode.

- `@HIDE`: the inverse of `@SHOW`. Just run commands without showing comments
   or waiting. `demosh` starts in this mode.

- `@SKIP`: don't do _anything_ until an `@SHOW` directive -- don't show
   commentary and don't run commands. This is mostly a debugging aid: when
   working out what a demo should contain, it's very handy to have an easy
   way to skip sections entirely and focus in on the parts that aren't
   working so smoothly.

- `@wait`: wait for RETURN before proceeding. This can be useful for e.g.
   pausing while showing longer blocks of commentary.

- `@waitafter`: wait _after_ running the next command, as well as before.

- `@nowaitbefore`: do _not_ wait before running the next command.

- `@noshow`: do not display the next command.

- `@notypeout`: don't slowly type the next command, just spit it out all at
  once.

- `@immed` or `@immediate`: don't display the next command and don't wait
   before or after it. This is a way to run a command inline without showing
   it to the viewers.

- `@print arg [arg [...]]`: like the shell's `echo` command, but it colorizes
   the output as appropriate. For example:

   ```
   #@print # This will be colorized like a comment
   ```

   will output text that's red like an inline comment. Also, since `@print`
   has to be a directive, it will never produce output when running the
   script using the normal shell.

- `@import`: see "Imports" below.

- `@macro`: see "Macros" below.

- `@hook`: see "Hooks" below.

- `@ifhook`: see "Hooks" below.

Some "directives" are actually macros defined as builtins:

- `@wait_clear` waits for RETURN, then clears the screen.

- `@browser_then_terminal` tries to use hooks named `show_browser` and
  `show_terminal` to wait, show a browser, then return to the terminal. Both
  must be defined for the macro to have any effect.

- `@start_livecast`, likewise, tries to use hooks named `show_slides` and
  `show_terminal` to show a slide deck, wait, clear the terminal screen, and
  show the terminal. Again, both hooks must be defined for the macro to have
  any effect.

Finally, any other directive will be interpreted as an immediate command, so
(in shell mode):

```bash
#@foobar
```

is exactly like

```bash
#@immed
foobar
```

meaning that it will immediately run `foobar` as a shell command: no command
display, no waiting. The main difference is that the one-line version looks
like a comment if you're executing the script _without_ `demosh`, so if
you're running your script with `bash` it will _not_ run `foobar` at all. The
two-line version leaves the `foobar` command looking like a command even when
running without `demosh`.

### Imports

The `@import <pathname>` directive reads the given pathname and inserts its
contents into the input stream. This is mostly a way of getting annoying
setup code out of the main script, to make the main script easier for others
to read.

You can import Markdown into shell scripts and vice-versa: `@import` will
read its argument as Markdown if the pathname ends in `.md`, or as shell
otherwise.

### Macros

Macros allow giving groups of commands simpler names. They are **very**
simple: running a macro is the moral equivalent of just inserting the macro's
contents into the script in place of the macro. They don't take arguments and
they don't have any dynamic behavior.

The syntax is as follows:

```bash
#@macro macro-name
  #@command1
  #@command2
  ...
#@end
```

Then, later:

```bash
#@macro-name
```

will run `command1`, `command2`, etc.

It's not technically necessary to have every command in a macro start with
`#@`; likewise, it's not strictly necessary to invoke the macro with a
leading `#@`. It is usually a good idea, though, since it means that all
macros will be no-ops when running the script without `demosh`.

### Hooks

Hooks are a special kind of macro-ish thing that create functions based on
environment variables whose names start with `DEMO_HOOK_`.

```bash
#@hook do_the_thing THING
```

will cause `do_the_thing` to execute the contents of `DEMO_HOOK_THING` if
that variable is present in the environment, or to be a no-op if it's not
set. This provides a simple mechanism to e.g. control a livestreaming setup
by setting environment variables, and still have a working script if they're
not set.

Note that hooks can appear in macros, and that, again, it's a good idea to
only invoke hooks with the `#@` prefix so that the calls are ignored if you
run the script without `demosh`.

There is also a special form, `@ifhook`, for hooks:

```bash
#@ifhook hookname
  #@command1
  #@command2
  ...
#@endif
```

in which the commands enclosed between `@ifhook` and `@endif` will be run only
if the named hook is not a no-op. This permits, for example, skipping a
sequence with multiple `@wait`s if it's not going to have any useful effect,
so that the user doesn't have to press RETURN multiple times to continue.

## Limitations

`demosh` has some serious limitations, mostly stemming from two things:

1. Shell syntax is _terrifyingly_ complex. `demosh` doesn't even try to be a
   full shell parser.

2. `demosh` executes commands one at a time, rather than messing about with
   trying to have a persistent shell process.

## Parsing

`demosh` doesn't even try to fully parse the insanity of shell syntax.
Instead, it does things more simply:

### When reading shell scripts

- Lines starting with `#` are considered commentary, and will be displayed in
  interactive mode. Blank lines are considered commentary, too, but multiple
  blanks are folded into one.

- Once `demosh` sees a line that doesn't look like a comment, it reads lines
  until an unescaped newline that's not inside curly braces is found. This
  forms a single command.

- "Unescaped" means that the newline is not preceded by a backslash. The
  curly-brace thing is for shell functions. We do _NOT_ parse quoted
  strings at present; I don't see the benefit for demo scripts.

### When reading Markdown

- Anything outside a code block is considered commentary. Multiple blank
  lines will be folded into one.

- Within a code block marked as either `bash` or `sh`, lines get parsed as if
  `demo` were reading a shell script.

## Processing

Since `demosh` executes commands in independent subshells, it has to do some
complex stuff to make things appear to be a single shell session.

1. `demosh` keeps track of environment variables on its own. Immediately
   after reading a command, anything of the form `${VARNAME}` is
   interpolated with the value from `demosh`'s environment.

   **NOTE WELL**: _only_ the curly-brace form is interpolated. The unbraced
   form `$FOO` and complex forms like `${FOO:-default}` or the like are _not_
   handled, because that way lies madness without a _lot_ more work in the
   parser.

   Also note that positional variables (`$1` etc) will be taken from
   `demosh`'s command line itself: see below for more.

2. If the command looks like an environment variable assignment, we update
   `demosh`'s environment internally. This is the environement passed to each
   command being executed.

   "Looks like an assignment" means that it has optional whitespace, then
   an identifier followed immediately by an equals sign, then optional
   content.

3. If the command looks like a shell function definition, we save the line
   and prepend it to all subsequent shell commands. Again, separate
   subshells. `demosh` does _not_ prepend functions to the `cd` command or
   variable assignments.

   Only the `identifier () {` and `function identifer () {` forms of
   function definitions are supported.

4. If the first word of the command is `cd`, we handle that in the `demosh`
   itself.

Assignments and `cd` are both handled by running the command in a new shell
and then having the shell echo the result back to us, so that the shell can
manage more complex variable expansions, etc.

Why do things like this? Because it's pretty simple and it generally works
for demos. An alternative would be to use a single shell and drive it using
a `pty` and multiple threads, but signal handling is _much_ harder in that
world.

### Environment variables

`demosh` maintains the environment passed to each command. When `demosh`
starts, it saves its own command line in this enviroment as the positional parameters:

- `$0` is the script passed to `demosh`;
- `$1` etc. are command-line parameters after the script; and
- `$SHELL` is `demosh` itself (as a fully-qualified path).

### Signal Handling

When executing a command, you can use `INTR` (usually control-C) as usual to
interrupt the command. `demosh` ignores `SIGINT` and `SIGTERM` so that you
can't accidentally interrupt `demosh` itself.

## License and Copyright

`demosh` is copyright 2022 Buoyant, Inc., and is licensed under the Apache
License Version 2.0. For more information see the `LICENSE` file.
