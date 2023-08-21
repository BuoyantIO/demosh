# A Demo of `demosh`

This is the documentation - and executable code! - for demoing `demosh`
itself. The easiest way to use this file is, unsurprisingly, to execute it
with [demosh].

Things in Markdown comments are safe to ignore when reading this later. When
executing this with [demosh], things after the horizontal rule below (which
is just before a commented `@SHOW` directive) will get displayed.

[demosh]: https://github.com/BuoyantIO/demosh

The demo doesn't really have other external requirements, but it's intended to
be a Real Demo (if such a thing really exists), so it uses hooks and all that
jazz.

<!-- @hook show_editor EDITOR -->
<!-- @start_livecast -->
---
<!-- @SHOW -->

## Introducing `demosh`

This is `demosh`, the **Demo** **SH**ell. It can read Markdown files or shell
scripts, displaying commentary, typing commands out and then running them. It
lives at `https://github.com/BuoyantIO/demosh`.

When reading Markdown (like this file), `demosh` will display "normal text"
and execute commands in `bash` blocks, like so:

```bash
echo 'Hello, world!'
```

Commands really don't have to be as simple as that, of course: `demosh` can
manage fairly complex stuff:

```bash
now=$(date +"%Y-%m-%dT%H:%M:%S")

echo "The previous command ran at $now"
```

`demosh` also understands functions:

```bash
say_hello () {
    echo "Hello, world!"
}

say_hello
```

<!-- @wait_clear -->

As you would expect, variables and functions persist across blocks:

```bash
echo "The previous command ran at $now."
```

If we use curly braces for the variable substitution, demosh will
do the interpolation when typing the command.

```bash
echo "The previous command ran at ${now}."
```

Here's that function call again.

```bash
say_hello
```

<!-- @wait_clear -->

Another helpful thing that `demosh` can do is to let you back up and run
things again, by hitting `-`, or skip things by hitting `+`.

```bash
echo "DON'T RUN THIS COMMAND!!! back up and say hello again instead."
```

As you've seen, `demosh` pretends to type things out for you to make the demo
a little more realistic. For long commands, though, you can always skip to the
end with SPACE:

```bash
curl https://httpbin.org/ip \
    | grep origin \
    | cut -d: -f2 \
    | tr -d ' ' \
    | tr -d '"'
```

You can also skip to the end and immediately run it with RETURN:

```bash
curl https://httpbin.org/ip \
    | grep origin \
    | cut -d: -f2 \
    | tr -d ' ' \
    | tr -d '"'
```

<!-- @wait_clear -->

`demosh` also has macros and hooks that you can use, for example, to control
livecast setups. For example, let's flip over and look at the web browser
displaying the `demosh` repo.

<!-- @browser_then_terminal -->

That was using a macro to:

- use a hook to show the browser
- wait for a RETURN back in the `demosh` window
- use another hook to flip back to `demosh`

If the hooks aren't set, the macro will just make you hit RETURN to proceed,
rather than failing.

Put it all together and you can show the demo you're seeing now by running the
Markdown file we're going to show you next (assuming the hooks are working, of
course.)

```bash
#@wait
#@ifhook show_editor
  #@show_editor
  #@wait_clear
  #@show_terminal
#@endif
```

So that's the whirlwind tour of `demosh` -- hope you enjoyed it! We'll finish
by using a hook to go back to the slides.

<!-- @wait -->
<!-- @show_slides -->
