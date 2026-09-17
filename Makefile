NAME := steamroller
VERSION := $(shell tr -d '\n' < VERSION)

.PHONY: check source rpm

check:
	bash tests/static_checks.sh

source:
	mkdir -p build
	tar --exclude='./build' --transform='s,^.,$(NAME)-$(VERSION),' \
		-czf build/$(NAME)-$(VERSION).tar.gz .

rpm: source
	rpmbuild -ta build/$(NAME)-$(VERSION).tar.gz
