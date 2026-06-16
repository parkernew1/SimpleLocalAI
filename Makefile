.PHONY: test chat doctor apple-helper

test:
	python3 -m unittest discover -s tests

chat:
	python3 -m simplelocalai chat

doctor:
	python3 -m simplelocalai doctor

apple-helper:
	mkdir -p build
	swiftc scripts/apple-foundation-helper.swift -o build/apple-foundation-helper

