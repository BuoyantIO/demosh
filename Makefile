all: install

install:
	flit install

uninstall:
	pip3 uninstall demosh

dev:
	pip3 uninstall --yes demosh
	flit install --symlink
