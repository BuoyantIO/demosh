# `demosh`

## Installing `demosh` for Development

To install `demosh` from source, you'll need Python 3.8.10 or higher,
[`flit`](https://flit.pypa.io/en/stable/), and `make`.

- Install `flit`, most likely with `python3 -m pip install flit`.
- Run `make dev`. This will install `demosh` using symlinks, so that further
  changes you make will be reflected in your installed `demosh`.

## Shipping a New Version

- **Make sure that `make lint` runs clean before releasing a new version.**
- Edit `demosh/__init__.py` to change the version. **THIS IS VERY IMPORTANT.**
  - Note that `demosh` uses [semantic versioning](https://semver.org/).
- Commit and push.
- Tag the pushed commit with the same version that's contained in
  `__init__.py`, with a leading `v`.
- Make sure you have a valid PyPI token in `$HOME/.pypi-token`.
- Run `make publish`.
