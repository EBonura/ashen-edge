#!/usr/bin/env python3
"""Convert audio stems (via basic-pitch MIDI extraction) to PICO-8 music.p8 format.

Usage:
  python3 stems2pico.py [--start SEC] [--end SEC] [--speed N] [--bpm N]

Requires: basic-pitch (pip install basic-pitch)
Input: stems_midi.json (pre-extracted) or audio files in STEMS_DIR
Output: music.p8 in the same directory as this script
"""

import json, os, sys, argparse
from collections import defaultdict

DIR = os.path.dirname(os.path.abspath(__file__))
MIDI_JSON = "/tmp/audio2pico/stems_midi.json"
MUSIC_P8 = os.path.join(DIR, "music.p8")

# PICO-8 constants
MAX_SFX = 31          # slots 0-30 available
MAX_PATTERNS = 64
NOTES_PER_SFX = 32
MIDI_TO_PICO_OFFSET = 48  # PICO-8 pitch 0 = MIDI 48
PICO_PITCH_MIN = 0
PICO_PITCH_MAX = 63

# Channel config: stem_name -> (waveform, default_volume, effect, midi_offset)
# Waveforms: 0=sine, 1=saw, 2=sq50, 3=sq25, 4=pulse, 5=organ, 6=noise, 7=tri
# midi_offset: PICO-8 pitch = MIDI pitch - midi_offset
CHANNEL_CONFIG = {
    "synth": {"wave": 0, "vol": 5, "eff": 5, "midi_offset": 48},  # sine, slide
    "bass":  {"wave": 1, "vol": 5, "eff": 0, "midi_offset": 24},  # saw, transposed up 2 oct
    "drums": {"wave": 6, "vol": 5, "eff": 5, "midi_offset": 48},  # noise, slide
    "other": {"wave": 7, "vol": 4, "eff": 0, "midi_offset": 24},  # triangle, transposed up 2 oct
}

# Channel order in PICO-8 music patterns
CHANNEL_ORDER = ["synth", "bass", "drums", "other"]


def load_midi_data():
    """Load pre-extracted MIDI data from JSON."""
    with open(MIDI_JSON) as f:
        return json.load(f)


def quantize_channel(notes, start_time, end_time, step_dur, midi_offset=48, monophonic=True):
    """Quantize notes to a fixed grid.

    Returns list of (pico_pitch, velocity) or None for each grid step.
    For monophonic: picks highest velocity note at each step.
    """
    window_notes = [n for n in notes if n['end'] > start_time and n['start'] < end_time]

    num_steps = int((end_time - start_time) / step_dur)
    grid = [None] * num_steps

    for n in window_notes:
        closest_step = round((n['start'] - start_time) / step_dur)
        closest_step = max(0, min(num_steps - 1, closest_step))

        pico_pitch = n['pitch'] - midi_offset
        if pico_pitch < PICO_PITCH_MIN or pico_pitch > PICO_PITCH_MAX:
            continue

        if monophonic:
            if grid[closest_step] is None or n['vel'] > grid[closest_step][1]:
                grid[closest_step] = (pico_pitch, n['vel'])
        else:
            grid[closest_step] = (pico_pitch, n['vel'])

    return grid


def quantize_drums(notes, start_time, end_time, step_dur):
    """Quantize drum hits - map to fixed pitch range for noise channel."""
    window_notes = [n for n in notes if n['end'] > start_time and n['start'] < end_time]

    num_steps = int((end_time - start_time) / step_dur)
    grid = [None] * num_steps

    for n in window_notes:
        closest_step = round((n['start'] - start_time) / step_dur)
        closest_step = max(0, min(num_steps - 1, closest_step))

        # Map drum hits to noise pitches based on original pitch
        # Low drums (kick) -> low noise pitch, hi-hat/cymbal -> high noise pitch
        midi_pitch = n['pitch']
        if midi_pitch < 40:
            pico_pitch = 8   # low thump
        elif midi_pitch < 50:
            pico_pitch = 16  # mid hit
        elif midi_pitch < 60:
            pico_pitch = 24  # snare-ish
        else:
            pico_pitch = 32  # hi-hat-ish

        pico_pitch = max(PICO_PITCH_MIN, min(PICO_PITCH_MAX, pico_pitch))

        if grid[closest_step] is None or n['vel'] > grid[closest_step][1]:
            grid[closest_step] = (pico_pitch, n['vel'])

    return grid


def grid_to_sfx_lines(grid, wave, vol, eff, speed):
    """Convert a quantized grid to PICO-8 SFX hex lines.

    Returns list of (sfx_hex_line, is_empty) tuples, one per 32-note chunk.
    """
    sfx_lines = []

    for chunk_start in range(0, len(grid), NOTES_PER_SFX):
        chunk = grid[chunk_start:chunk_start + NOTES_PER_SFX]

        # Pad to 32 notes if needed
        while len(chunk) < NOTES_PER_SFX:
            chunk.append(None)

        # Build hex line
        # Header: editor_mode(1) speed(1) loop_start(1) loop_end(1)
        header = f"01{speed:02x}0000"

        note_hex = ""
        is_empty = True
        for note in chunk:
            if note is None:
                note_hex += "00000"
            else:
                pitch, velocity = note
                # Scale velocity (0-127) to PICO-8 volume (0-7)
                note_vol = max(1, min(7, int(velocity / 127 * 7)))
                # Waveform hex: wave(3 bits) | custom(1 bit) << 3
                wf_hex = wave & 0x7
                note_hex += f"{pitch:02x}{wf_hex:01x}{note_vol:01x}{eff:01x}"
                is_empty = False

        sfx_lines.append((header + note_hex, is_empty))

    return sfx_lines


def sfx_pitch_signature(hex_line):
    """Extract just the pitch sequence from an SFX hex line for fuzzy matching."""
    notes_hex = hex_line[8:]  # skip header
    pitches = []
    for i in range(NOTES_PER_SFX):
        s = notes_hex[i*5:(i+1)*5]
        if s == "00000":
            pitches.append(-1)
        else:
            pitches.append(int(s[0:2], 16))
    return tuple(pitches)


def deduplicate_sfx(all_sfx, fuzzy=True):
    """Find duplicate SFX lines and return deduplicated list + index mapping.

    If fuzzy=True, matches by pitch pattern only (ignoring volume/effect differences).
    """
    unique = []
    seen = {}       # key -> index in unique list
    mapping = {}    # original index -> unique index

    for orig_idx, (hex_line, is_empty) in enumerate(all_sfx):
        if is_empty:
            mapping[orig_idx] = None
            continue

        key = sfx_pitch_signature(hex_line) if fuzzy else hex_line

        if key in seen:
            mapping[orig_idx] = seen[key]
        else:
            new_idx = len(unique)
            seen[key] = new_idx
            unique.append(hex_line)
            mapping[orig_idx] = new_idx

    return unique, mapping


def build_music_p8(channel_sfx, patterns_per_channel, speed):
    """Build the final music.p8 file content."""
    # Collect all SFX from all channels with their channel assignment
    all_sfx_flat = []  # (hex_line, is_empty, channel_idx, local_sfx_idx)

    for ch_idx, ch_name in enumerate(CHANNEL_ORDER):
        if ch_name in channel_sfx:
            for local_idx, (hex_line, is_empty) in enumerate(channel_sfx[ch_name]):
                all_sfx_flat.append((hex_line, is_empty, ch_idx, local_idx))

    # Deduplicate across all channels
    unique_sfx, global_mapping = deduplicate_sfx(
        [(h, e) for h, e, _, _ in all_sfx_flat]
    )

    print(f"Unique SFX before cap: {len(unique_sfx)}")
    if len(unique_sfx) > MAX_SFX:
        print(f"WARNING: {len(unique_sfx)} unique SFX needed, but only {MAX_SFX} slots available!")
        print(f"  Consider shortening the clip or reducing channels.")
        unique_sfx = unique_sfx[:MAX_SFX]

    print(f"SFX slots used: {len(unique_sfx)}/{MAX_SFX}")

    # Build per-channel SFX index sequences
    # For each channel, map local SFX index -> global unique SFX slot
    ch_slot_sequences = {}
    flat_idx = 0
    for ch_idx, ch_name in enumerate(CHANNEL_ORDER):
        if ch_name in channel_sfx:
            ch_slots = []
            for local_idx in range(len(channel_sfx[ch_name])):
                global_slot = global_mapping.get(flat_idx)
                if global_slot is not None and global_slot < MAX_SFX:
                    ch_slots.append(global_slot)
                else:
                    ch_slots.append(None)
                flat_idx += 1
            ch_slot_sequences[ch_name] = ch_slots
        else:
            ch_slot_sequences[ch_name] = []

    # Build music patterns
    # Each pattern references 4 SFX (one per channel)
    max_pattern_count = max(len(seq) for seq in ch_slot_sequences.values()) if ch_slot_sequences else 0
    max_pattern_count = min(max_pattern_count, MAX_PATTERNS)

    music_lines = []
    for pat_idx in range(max_pattern_count):
        channels = []
        for ch_name in CHANNEL_ORDER:
            seq = ch_slot_sequences.get(ch_name, [])
            if pat_idx < len(seq) and seq[pat_idx] is not None:
                channels.append(seq[pat_idx])
            else:
                channels.append(0x41)  # no SFX (bit 6 set = channel disabled)

        # Flags: bit 0 = loop start, bit 1 = loop end, bit 2 = stop
        flag = 0
        if pat_idx == max_pattern_count - 1:
            flag = 1  # loop back (set loop end... actually let's just set stop for now)
            # For looping: flag=3 (bits 0+1) on last pattern means loop back to pattern with flag bit 0
            # Simpler: just use flag=1 on first, flag=2 on last for a loop

        music_lines.append(f"{flag:02x} {channels[0]:02x}{channels[1]:02x}{channels[2]:02x}{channels[3]:02x}")

    # Set loop flags: first pattern flag bit 0, last pattern flag bit 1
    if len(music_lines) > 0:
        parts = music_lines[0].split(" ")
        flag = int(parts[0], 16) | 1  # set loop start
        music_lines[0] = f"{flag:02x} {parts[1]}"

        parts = music_lines[-1].split(" ")
        flag = int(parts[0], 16) | 2  # set loop end
        music_lines[-1] = f"{flag:02x} {parts[1]}"

    # Build .p8 file
    lines = [
        "pico-8 cartridge // http://www.pico-8.com",
        "version 43",
        "__lua__",
        "-- ashen edge music cart",
        f"-- auto-generated: {len(unique_sfx)} sfx, {len(music_lines)} patterns",
        f"-- speed {speed}",
        "",
        "__sfx__",
    ]

    for sfx_hex in unique_sfx:
        lines.append(sfx_hex)

    lines.append("")
    lines.append("__music__")
    for ml in music_lines:
        lines.append(ml)
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Convert audio stems to PICO-8 music")
    parser.add_argument("--start", type=float, default=0, help="Start time in seconds")
    parser.add_argument("--end", type=float, default=0, help="End time in seconds (0=auto)")
    parser.add_argument("--speed", type=int, default=41, help="PICO-8 SFX speed (1-255)")
    parser.add_argument("--bpm", type=float, default=0, help="Override BPM (0=auto from speed)")
    parser.add_argument("--channels", type=str, default="synth,bass,drums,other",
                       help="Comma-separated channel names to include")
    parser.add_argument("--preview", action="store_true", help="Print note grid preview instead of writing")
    args = parser.parse_args()

    print("Loading MIDI data...")
    data = load_midi_data()

    # Determine time range
    all_notes = [n for stem in data.values() for n in stem]
    max_time = max(n['end'] for n in all_notes) if all_notes else 0

    start_time = args.start
    end_time = args.end if args.end > 0 else max_time

    # Step duration from speed
    step_dur = args.speed / 120.0  # PICO-8: note duration = speed/120 seconds

    duration = end_time - start_time
    total_steps = int(duration / step_dur)
    total_sfx_per_ch = (total_steps + NOTES_PER_SFX - 1) // NOTES_PER_SFX

    active_channels = [ch.strip() for ch in args.channels.split(",")]

    print(f"Time range: {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)")
    print(f"Speed: {args.speed} ({step_dur*1000:.0f}ms per note)")
    print(f"Total steps: {total_steps}, SFX per channel: {total_sfx_per_ch}")
    print(f"Channels: {', '.join(active_channels)}")
    print(f"Estimated SFX needed (before dedup): {total_sfx_per_ch * len(active_channels)}")
    print()

    # Quantize each channel
    channel_sfx = {}
    for ch_name in active_channels:
        if ch_name not in data:
            print(f"  Skipping {ch_name} (no data)")
            continue

        cfg = CHANNEL_CONFIG.get(ch_name, {"wave": 0, "vol": 5, "eff": 0})

        midi_offset = cfg.get("midi_offset", MIDI_TO_PICO_OFFSET)
        print(f"  Quantizing {ch_name} (midi_offset={midi_offset})...")
        if ch_name == "drums":
            grid = quantize_drums(data[ch_name], start_time, end_time, step_dur)
        else:
            grid = quantize_channel(data[ch_name], start_time, end_time, step_dur, midi_offset=midi_offset)

        # Count non-empty steps
        filled = sum(1 for g in grid if g is not None)
        print(f"    {filled}/{len(grid)} steps filled ({100*filled/max(1,len(grid)):.0f}%)")

        if args.preview:
            note_names = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
            print(f"    First 64 notes:")
            for i, g in enumerate(grid[:64]):
                if g:
                    p, v = g
                    nn = note_names[p % 12] + str(p // 12)
                    print(f"      {i:3d}: {nn} v{v}")
                else:
                    print(f"      {i:3d}: ---")

        sfx_lines = grid_to_sfx_lines(grid, cfg["wave"], cfg["vol"], cfg["eff"], args.speed)
        channel_sfx[ch_name] = sfx_lines
        print(f"    Generated {len(sfx_lines)} SFX chunks")

    if args.preview:
        print("\nPreview mode - not writing output.")
        return

    # Build and write output
    print("\nBuilding music.p8...")
    p8_content = build_music_p8(channel_sfx, total_sfx_per_ch, args.speed)

    with open(MUSIC_P8, "w") as f:
        f.write(p8_content)

    print(f"Written to {MUSIC_P8}")


if __name__ == "__main__":
    main()
