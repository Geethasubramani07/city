# Smart City Traffic Dashboard (Python version)

A live dashboard for a simulated 12-junction Bengaluru traffic network. The original HTML, CSS and browser JavaScript interface are retained; the backend has been converted from Node.js to Python using Flask.

## Run in VS Code

1. Install **Python 3.10 or newer** from https://www.python.org/downloads/ (on Windows, enable **Add Python to PATH**).
2. Extract this folder and open it in VS Code (`File > Open Folder`).
3. Open the VS Code terminal (`Terminal > New Terminal`).
4. Create a virtual environment:
   - Windows: `py -m venv .venv`
   - macOS/Linux: `python3 -m venv .venv`
5. Activate it:
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - Windows Command Prompt: `.venv\Scripts\activate.bat`
   - macOS/Linux: `source .venv/bin/activate`
6. Install dependencies: `python -m pip install -r requirements.txt`
7. Start the app: `python server.py`
8. Open **http://localhost:3000** in your browser.

Keep the terminal open while using the dashboard. Press `Ctrl+C` to stop it.

## Features

- 12 simulated Bengaluru junctions
- Live KPI cards, congestion map, junction table and incident feed
- Adaptive NS/EW signal timers
- Auto, Rush hour and Night scenarios
- Server-Sent Events for live browser updates

## API

- `GET /health`
- `GET /api/network`
- `GET /api/snapshot`
- `GET /api/history`
- `GET /api/stream` (Server-Sent Events)
- `POST /api/mode` with JSON body `{"mode":"auto|rush|night"}`

Traffic data is simulated; it is not connected to live road sensors.
