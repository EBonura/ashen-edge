.PHONY: build export count minify edit

build:
	cargo run --release --manifest-path tools/build-cart/Cargo.toml

export:
	cargo run --release --manifest-path tools/build-cart/Cargo.toml -- --export

count:
	python3 tools/scripts/count_tokens.py

minify:
	python3 tools/scripts/minify.py

edit:
	python3 levels/server.py
