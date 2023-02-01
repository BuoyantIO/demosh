# demosh -- demo shell

`demosh` can display Markdown while also running code contained in `bash`
or `sh` blocks in the Markdown file.

When running this Markdown file with `demosh`, we start out _not_ displaying
things, because we haven't seen a SHOW directive yet. So this block will
be readable in the Markdown file, but it won't be shown when feeding this
file to `demosh`.

## This is a header, but it won't be shown when running the demo.

```bash
clear
echo "This will run like a normal script."
```

The bash above will run even though we're still not showing anything yet.

We can import things from other files. Note that directives to `demosh` need
to either be in Markdown comments, or in bash blocks. We'll use a Markdown
comment here.
<!-- @import macros.sh -->

The `@SHOW` and `@HIDE` directives control whether we're showing commands,
waiting for the user to confirm proceeding, etc., or just reading through
things non-interactively. The `@SHOW` directive below (in a comment, so you
won't see it in the Markdown preview) tells `demosh` to start doing its thing.

<!-- @SHOW -->

# Welcome to our demo!

## Since these are headers, `demosh` will colorize them.

Kind of, anyway. It's kind of a best-effort sort of thing.

Here's some more Markdown. _Underscores_ are highlighted.
So are `backticks` and *asterisks* and **doubled asterisks**.
But, also, e.g. 5 * 4 == 20.  How about *4* or *44
45 46*?

How about *hello
world* for emphasis?

* Asterisks can also be list items.
- So can dashes.

### Assignments and functions

Let's try an assignment.

```bash
FOO="Hello world"
echo "$FOO"
```

The `$SHELL` environment variable should be overwritten to be `demosh` itself.

```bash
echo "SHELL is $SHELL"
```

Here's a function definition with the `function` keyword...

```bash
function hello() {
    echo "Hello, $1!"
}
```

...and here's one without it.

```bash
hello2 () {
    echo "Hello again, $1!"
}
```

Can we run the functions?

```bash
hello "world"
hello2 "world"
```

### `cd`

`cd` is handled internally, because it has to be.

```bash
cd /tmp
pwd
```

### Macros

Let's test macro calls. While we're at it, let's show that we can have
comments in `bash` blocks too.

```bash
wait_clear

# How about an immediate macro call?
#@wait_then_date
```

### Waiting (or not)

Here, we'll need to hit RETURN to run our command.

```bash
echo "Waiting only before"
```

This is an immediate command: no waiting at all.

```bash
#@immed
echo "No waiting."
```

Here we wait before and after.

```bash
#@waitafter
echo "Waiting before and after"
```

```bash
#@waitafter
#@nowaitbefore
echo "Waiting only after"
```

Let's try the function again.

```bash
hello "world again"
```

### Signal Handling

Let's test signal handling. You should be able to hit
Ctrl-C to interrupt the sleep.

```bash
sleep 120
```

And that's the whole `demosh` Markdown demo!!
