# Image-to-GIF

A small Python tool that converts a folder of `.png` images into an animated GIF.

## What it does

- Loads all PNG files from a selected/input folder
- Sorts frames by filename order
- Builds and saves an animated `.gif`
- Lets you control:
  - frame duration (milliseconds)
  - loop count (`0` = infinite loop)

## Modes

- **GUI mode (default, Windows only):**
  - Folder picker for PNG input
  - Save dialog for GIF output
  - Prompts for duration and loop
  - Success/failure message boxes
- **CLI mode (`--nogui`):**
  - Full command-line control for input, output, duration, and loop

## Requirements

- Python 3
- [Pillow](https://pypi.org/project/Pillow/)

Install dependency:

```bash
pip install pillow
```

## Usage

Run with GUI (Windows):

```bash
python convert.py
```

Run in terminal mode:

```bash
python convert.py --nogui --input ./my_images --output ./your_gif.gif --duration 33 --loop 0
```

## CLI options

- `--nogui` Run conversion in the console
- `--input` Path to folder containing PNG files
- `--output` Output GIF path
- `--duration` Frame duration in ms (default: `33`)
- `--loop` GIF loop count (default: `0`)

## Default behavior

- The script looks for a `my_images` folder in common locations
- Default output file is `your_gif.gif` in the script/executable directory
- Creates output directories if they do not exist

## Packaging

A PyInstaller spec file (`convert.spec`) is included for building a standalone executable.