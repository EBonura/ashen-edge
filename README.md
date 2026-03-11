# Aletha

A PICO-8 action-platformer set inside **The Hollowed Furnace** — a colossal ancient kiln that consumes the fire of the world.

You play as **Aletha**, a tempered figure born of the furnace itself, who returns to shut it down before it drains what's left. Fight constructs and vermin, extinguish ignition points, and descend toward the Heart of the Kiln.

## Controls

- Arrow keys: move / climb
- Up: jump
- Down: interact (switches, portals)
- O (Z): attack
- X: sweep attack

## Building

Requires [PICO-8](https://www.lexaloffle.com/pico-8.php) and a Rust toolchain.

```
make build     # Build the .p8 cart from source assets + Lua
make export    # Build + export to HTML (output in export/)
make count     # Show token/char/compressed usage
make minify    # Generate minified Lua
make edit      # Launch the level editor
```

The Rust build tool (`tools/build-cart/`) processes PNG sprite sheets into compressed animation data, encodes the level map, and assembles the final cart. HTML export is done natively (no PICO-8 binary needed) — it reads `pico8.dat` for the web player template.

## Project Structure

```
aletha.lua            Main game source (Lua)
music.p8              Music/SFX cart (composed in PICO-8 tracker)
level_editor.py       Tiled-style level editor (Python + pygame)
level_editor.html     Web-based level editor
minify.py             Lua minifier (token-aware)
count_tokens.py       PICO-8 token/char/compressed counter
tools/build-cart/     Rust build pipeline
assets/               Source sprite sheets and fonts
export/               HTML export (deployed to itch.io)
docs/                 Design document and data layout reference
```

## Deployment

Pushing changes to `export/` on `main` triggers a GitHub Actions workflow that deploys to itch.io via [Butler](https://itch.io/docs/butler/).

## Assets

All character/entity sprite sheets are from [Sci-Fi Platformer Dark Edition](https://penusbmic.itch.io/sci-fi-platformer-dark-edition) by penusbmic. Most have been tweaked or modified (recolored, resized, trimmed) to fit within PICO-8's constraints.

Tileset, title screen, UI elements, and font are original or heavily reworked derivatives.

## License

Game code is provided as-is for reference. Asset license follows the original pack's terms — see the [asset page](https://penusbmic.itch.io/sci-fi-platformer-dark-edition) for details.
