# diffseek

A tool for verifying and correcting manually transcribed strings across two devices using binary search.

## Use Cases

- Airgapped systems
- Low-privilege systems without email/clipboard access
- Any scenario requiring manual string transcription between devices (e.g., copying login links, tokens, or keys)

## How It Works

1. Run `diffseek` on both devices
2. Enter the reference string on device 1 (input is interactive to avoid shell history)
3. Enter your transcription on device 2
4. Compare hash-derived values (phrases, colors) displayed on each device
5. Binary search narrows down differences:
   - Matching hashes indicate error-free regions
   - Non-matching hashes indicate regions containing at least one error
   - At each step, the string is reprinted with color coding: orange (possibly mismatched), red (definitely mismatched), white (verified correct)

The tool uses breadth-first search when both strings have matching target lengths (to find all differences efficiently), and depth-first search when lengths differ (to find the first difference quickly).

## Usage

```bash
pip install diffseek
```

Then,

```bash
diffseek
# or
./diffseek.py
# or
python3 diffseek.py
```

## Disclosure

This tool was implemented by Claude Code from a specification I provided. I fixed minor bugs and verified it works for my use case. It is primarily AI-written code. You might not care, but if you do then now you know.

If you run into any problems, feel free to open an issue or a PR; these will be human-reviewed.
