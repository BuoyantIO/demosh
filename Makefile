all: install

install:
	flit install

uninstall:
	pip3 uninstall demosh

dev:
	pip3 uninstall --yes demosh
	flit install --symlink

mypy lint:
	mypy demosh

publish:
	FLIT_USERNAME="__token__" FLIT_PASSWORD=$$(cat $$HOME/.pypi-token) flit publish
