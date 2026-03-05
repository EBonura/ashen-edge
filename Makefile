build:
	cargo run --release --manifest-path tools/build-cart/Cargo.toml

count:
	python3 count_tokens.py

minify:
	python3 minify.py

edit:
	python3 level_editor.py
