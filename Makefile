.PHONY: build export count minify edit

build:
	cargo run --release --manifest-path tools/build-cart/Cargo.toml

export:
	cargo run --release --manifest-path tools/build-cart/Cargo.toml -- --export

count:
	python3 count_tokens.py

minify:
	python3 minify.py

edit:
	python3 level_editor.py
