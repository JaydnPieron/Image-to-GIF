import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_default_input_folder(base_dir):
    candidate_folders = [
        base_dir / "my_images",
        Path.cwd() / "my_images",
        base_dir.parent / "my_images",
    ]
    return next((path for path in candidate_folders if path.exists()), candidate_folders[0])


def pngs_to_gif(image_folder, output_path, duration=33, loop=0):
    image_folder = Path(image_folder).resolve()
    output_path = Path(output_path).resolve()

    if not image_folder.exists() or not image_folder.is_dir():
        raise FileNotFoundError(f"Input folder does not exist: {image_folder}")

    image_paths = sorted(
        path for path in image_folder.iterdir() if path.is_file() and path.suffix.lower() == ".png"
    )
    if not image_paths:
        raise ValueError(f"No PNG images found in: {image_folder}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_paths[0]) as first_frame:
        frames = []
        for image_path in image_paths[1:]:
            with Image.open(image_path) as frame:
                frames.append(frame.copy())

        first_frame.save(
            output_path,
            format="GIF",
            append_images=frames,
            save_all=True,
            duration=duration,
            loop=loop,
        )

    return len(image_paths), output_path


def run_cli(input_folder, output_path, duration, loop):
    frame_count, output_file = pngs_to_gif(
        image_folder=input_folder,
        output_path=output_path,
        duration=duration,
        loop=loop,
    )
    print(f"Loaded {frame_count} PNG files from: {Path(input_folder).resolve()}")
    print(f"Successfully saved animated GIF to: {output_file}")


def _ps_escape(value):
    return str(value).replace("'", "''")


def _run_powershell(script):
    encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-EncodedCommand", encoded_script],
        capture_output=True,
        text=True,
    )
    return result


def show_message_box(title, message, icon):
    if sys.platform != "win32":
        return

    script = f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show(
    '{_ps_escape(message)}',
    '{_ps_escape(title)}',
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::{icon}
) | Out-Null
"""
    _run_powershell(script)


def ask_gui_settings(default_input, default_output):
    if sys.platform != "win32":
        raise RuntimeError("GUI mode is only supported on Windows.")

    default_output = Path(default_output).resolve()
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

$folderDialog = New-Object System.Windows.Forms.FolderBrowserDialog
$folderDialog.Description = 'Select folder containing PNG files'
$folderDialog.SelectedPath = '{_ps_escape(Path(default_input).resolve())}'
if ($folderDialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {{ exit 2 }}

$saveDialog = New-Object System.Windows.Forms.SaveFileDialog
$saveDialog.Filter = 'GIF files (*.gif)|*.gif|All files (*.*)|*.*'
$saveDialog.Title = 'Choose output GIF file'
$saveDialog.AddExtension = $true
$saveDialog.DefaultExt = 'gif'
$saveDialog.OverwritePrompt = $true
$saveDialog.InitialDirectory = '{_ps_escape(default_output.parent)}'
$saveDialog.FileName = '{_ps_escape(default_output.name)}'
if ($saveDialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {{ exit 2 }}

$duration = [Microsoft.VisualBasic.Interaction]::InputBox(
    'Frame duration in milliseconds',
    'GIF Settings',
    '33'
)
if ($duration -eq '') {{ exit 2 }}

$loop = [Microsoft.VisualBasic.Interaction]::InputBox(
    'Loop count (0 means infinite)',
    'GIF Settings',
    '0'
)
if ($loop -eq '') {{ exit 2 }}

[PSCustomObject]@{{
    input = $folderDialog.SelectedPath
    output = $saveDialog.FileName
    duration = $duration
    loop = $loop
}} | ConvertTo-Json -Compress
"""

    result = _run_powershell(script)
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "PowerShell GUI prompt failed."
        raise RuntimeError(details)

    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError("Failed to parse GUI input.") from exc


def launch_gui(default_input, default_output):
    settings = ask_gui_settings(default_input, default_output)
    if settings is None:
        return

    try:
        duration = int(str(settings["duration"]).strip())
        loop = int(str(settings["loop"]).strip())
    except (KeyError, ValueError) as exc:
        raise ValueError("Duration and loop must be whole numbers.") from exc

    if duration <= 0:
        raise ValueError("Duration must be greater than 0.")
    if loop < 0:
        raise ValueError("Loop must be 0 or greater.")

    output_path = Path(settings["output"])
    if output_path.suffix.lower() != ".gif":
        output_path = output_path.with_suffix(".gif")

    frame_count, saved_path = pngs_to_gif(
        image_folder=settings["input"],
        output_path=output_path,
        duration=duration,
        loop=loop,
    )

    show_message_box(
        "Conversion Complete",
        f"Loaded {frame_count} PNG files and saved:\\n{saved_path}",
        "Information",
    )


if __name__ == "__main__":
    base_dir = get_base_dir()
    default_input = find_default_input_folder(base_dir)
    default_output = base_dir / "your_gif.gif"

    parser = argparse.ArgumentParser(description="Convert a folder of PNG files into an animated GIF.")
    parser.add_argument("--nogui", action="store_true", help="Run conversion in the console.")
    parser.add_argument("--input", default=str(default_input), help="Path to the folder containing PNG files.")
    parser.add_argument("--output", default=str(default_output), help="Path for the output GIF file.")
    parser.add_argument("--duration", type=int, default=33, help="Frame duration in milliseconds.")
    parser.add_argument("--loop", type=int, default=0, help="GIF loop count (0 means infinite).")
    args = parser.parse_args()

    if args.nogui:
        run_cli(args.input, args.output, args.duration, args.loop)
    else:
        try:
            launch_gui(default_input=args.input, default_output=args.output)
        except Exception as exc:
            show_message_box("Conversion Failed", str(exc), "Error")
            print(f"Conversion failed: {exc}")
            sys.exit(1)
