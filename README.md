<div align="center">

# shogun-speech-2-text

**Built by a shogun who gave up on Windows+H.**

Real-time speech-to-text powered by Deepgram Nova-3.
Speak into your mic, text appears in any app. That simple.

[![GitHub Stars](https://img.shields.io/github/stars/yohey-w/shogun-speech-2-text?style=social)](https://github.com/yohey-w/shogun-speech-2-text)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![v1.0.0](https://img.shields.io/badge/v1.0.0-Initial_Release-ff6600?style=flat-square)](https://github.com/yohey-w/shogun-speech-2-text/releases/tag/v1.0.0)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)

[English](README.md) | [日本語](README_ja.md)

</div>

<p align="center">
  <img src="docs/floating_window.png" alt="Floating window showing real-time speech recognition" width="480">
</p>

<p align="center"><i>Ctrl+Space → speak → text appears in your active window. $200 free credit included.</i></p>

---

## Quick Start

**Requirements:** Python 3.10+, Windows, Deepgram API key (free)

```bash
git clone https://github.com/yohey-w/shogun-speech-2-text.git
cd shogun-speech-2-text
install.bat          # Creates venv + installs dependencies
# Edit .env → set DEEPGRAM_API_KEY
start.bat            # Launch!
```

Press **Ctrl+Space**, speak, done.

> **First time?** Get your free API key below — takes 30 seconds.

---

## Why This Exists

| | Windows+H | shogun-speech-2-text |
|---|-----------|---------------------|
| **Accuracy** | Mediocre | Excellent |
| **Latency** | 2-3 sec delay | Near real-time |
| **Tech terms** | Butchered | Handled well |
| **Stability** | Random freezes | Auto-reconnect |
| **Cost** | Free | $200 free (effectively ∞) |
| **Interim results** | None | Live display while speaking |

---

## Features

- **Deepgram Nova-3** — State-of-the-art Japanese STT, far superior to Windows+H
- **Real-time** — Interim results displayed as you speak
- **Clipboard paste** — Finalized text auto-pasted via Ctrl+V (IME-safe)
- **Floating UI** — Ctrl+Space toggles a compact always-on-top overlay
- **Balance display** — Remaining Deepgram credits shown in the window
- **Auto-reconnect** — Recovers from WebSocket disconnections automatically
- **Watchdog** — Detects silent connection death (30s timeout)
- **Custom dictionary (Keyterm)** — Register technical terms for better accuracy (configured in `.env`)

---

## Get Your API Key (Free)

1. Go to [Deepgram Console](https://console.deepgram.com)
2. Sign up with **Google** ($200 free credit, no card required)
3. Create an API key — select **Admin** role for balance display
4. Paste into `.env`

<p align="center">
  <img src="docs/api_key_admin_role.png" alt="Select Admin role when creating API key" width="480">
</p>
<p align="center"><i>Select "Admin" under "4. Change role" to enable balance display.</i></p>

> How many Google accounts you have is between you and Google.

---

## Usage

### Floating Window (Recommended)

```bash
python floating_window.py
```

| Key | Action |
|-----|--------|
| **Ctrl+Space** | Toggle recognition ON/OFF |
| **Esc** | Stop & hide window |
| **Ctrl+C** | Quit |
| **Drag** | Move window |

### Tray Icon

```bash
python tray.py
```

### Console

```bash
python main.py
```

---

## Custom Dictionary (Keyterm Prompting)

Register technical terms to boost recognition accuracy (up to 90% improvement).

Add comma-separated terms to `.env`:

```bash
DEEPGRAM_KEYTERMS=deploy,WebSocket,API,GitHub,Claude
```

- Limit: 500 tokens per request (20-50 terms recommended)
- Best for: proper nouns, company names, industry jargon
- Leave empty to disable

---

## File Structure

```
shogun-speech-2-text/
├── floating_window.py  # Floating UI (recommended)
├── tray.py             # System tray version
├── main.py             # STT core + balance API
├── requirements.txt
├── .env.example
└── docs/
    └── floating_window.png
```

---

## Cost

| Item | Value |
|------|-------|
| Deepgram Nova-3 | $0.0059/min ($0.35/h) |
| Free credit | **$200 per Google account** |
| Hours included | ~571 hours |
| At 3h/day | ~190 days free |

---

## Troubleshooting

### pyaudio install fails

**Windows:**
```bash
pip install pipwin && pipwin install pyaudio
```

**Linux/WSL2:**
```bash
sudo apt-get install portaudio19-dev && pip install pyaudio
```

### Hotkey conflict with IME

Change `HOTKEY` in `floating_window.py`:
```python
HOTKEY = "<ctrl>+<alt>+<space>"  # or any combo you prefer
```

### WSL2

Clipboard paste requires running Python on Windows directly. Console-only mode works on WSL2.

---

## License

MIT

</div>
