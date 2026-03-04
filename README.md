# DeskClock

Small local GTK4 clock app built with PyGObject.

## Features

- Live clock (`HH:MM:SS`) with current date
- Lock mode that switches to a centered, translucent circular display
- Header/title controls hidden while locked
- Unlock by double-clicking the clock (when locked)

## Ubuntu dependencies

Install system GTK/PyGObject packages:

```bash
sudo apt update
sudo apt install -y python3 python3-gi gir1.2-gtk-4.0
```

If using a virtual environment, keep system GI packages installed and add build deps:

```bash
sudo apt install -y libgirepository-2.0-dev libcairo2-dev pkg-config python3-dev
```

## Run

From project root, use the provided script:

```bash
./run.sh
```

This activates `.venv` and starts the app via `dbus-run-session`.

Alternative direct run:

```bash
python -m lin_test_app
```

## Controls

- Click lock icon to toggle lock/unlock
- `Ctrl+L` to toggle lock/unlock
- Double-click clock to unlock (while locked)
- `Esc` to quit

## Code layout

- Main UI and lock behavior: `lin_test_app/app.py`
- App entry point: `lin_test_app/main.py`
