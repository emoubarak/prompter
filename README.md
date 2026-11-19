# prompter

Turn a Markdown script into a full-screen teleprompter on your second monitor, with one command.

```
prompter episode-1.md
```

![prompter on a 1920x1080 monitor](docs/screenshot.png)

Made for recording voice-overs and talking-head videos with a small monitor placed above or below
the main screen. No app to install, no account: a single Python file that opens a dedicated browser
window, full screen, on the right monitor.

## What it does

- **Cleans the script for reading.** Headings, cue lines such as `**[Intro]**` or `[B-roll]`, and the
  prep notes above the first `---` are removed. Bold, links and code marks are stripped. Each sentence
  gets its own line, paragraphs are spaced for breathing, and a faint `• • •` marks each new section.
  The words you read are exactly the words of your script.
- **Opens on the right screen.** It finds your external monitor (GNOME through Mutter, other X11
  desktops through `xrandr`) and opens a full-screen window there. Pick another one with
  `--screen DP-2` or by model name, `--screen ARZOPA`.
- **Scrolls at your speaking pace.** Speed is set in words per minute, not in pixels, so it stays
  right when you change the text size. The time left is shown on demand.
- **Stays out of the way.** Black background, a reading line marked by two arrows, text already read
  dims, the cursor hides itself, the screen does not go to sleep. Speed and text size are remembered
  per script.

## Keys

| Key | Action |
| --- | --- |
| Space or click | Play / pause, with a 3 second countdown before it starts |
| ↑ / ↓ | Faster / slower (10 words per minute per step) |
| ← / → | Previous / next paragraph, handy to redo a take |
| Mouse wheel | Scroll by hand |
| + / − | Text size |
| Home / End | Start / end of the script |
| M | Mirror (for a beam-splitter glass) |
| N | Narrow column: 3 or 4 words a line, reading line near the top, so your eyes barely move |
| V | Follow the voice / timed scroll (when a transcription server is set) |
| F | Toggle full screen |
| H | Show or hide the help |

Close the window with Alt+F4.

## Install

Needs Python 3.10+ and a Chromium-based browser (Brave, Chromium, Chrome or Edge). Linux only for now.

```
git clone https://github.com/emoubarak/prompter.git
cd prompter
./install.sh          # links prompter into ~/.local/bin
```

## Options

```
prompter script.md                  open on the external monitor
prompter script.md --screen DP-1    pick a monitor (connector or model name)
prompter script.md --wpm 140        starting speed
prompter script.md --narrow        narrow column near the lens
prompter script.md --stt ws://…    follow the voice through a streaming transcription server
prompter script.md --no-stt        timed scroll only
prompter script.md --text           also write the cleaned script to script.prompter.txt
prompter script.md --no-open        only build the page
prompter script.md --lang fr        interface in French (or set PROMPTER_LANG=fr)
prompter script.md -- --kiosk       extra flags passed to the browser
```

`PROMPTER_BROWSER` picks the browser command. The page and the browser profile live in
`~/.local/share/prompter/`, apart from your usual browser profile.

## Follow the voice

With a streaming transcription server, the text follows what you say instead of a fixed speed: it moves on
when you speak, waits when you pause or improvise, and keeps the line you are reading on the reading line.
Space starts and pauses, V switches between voice and timed scroll, ← → and the wheel re-place you after a retake.

The page sends the microphone (16 kHz PCM) to a WebSocket that speaks the OpenAI realtime transcription events
(`session.update`, then `*.delta` text pieces), such as `nemo-speech serve` from
[NeMo-Speech.cpp](https://github.com/NVIDIA/NeMo-Speech.cpp) with a Nemotron streaming model. Each heard word is
matched against the next words of the script, with room for misheard and skipped words.

Run the server on the machine that records if you can: a busy remote server lags behind, a local one keeps up.
`~/.config/prompter/config.json` sets it once; servers are tried in order, and `stt_server` starts a local one
with the window and stops it when the last prompter window closes. `screen` names the monitor to prefer when it
is plugged in. The microphone is allowed once in the prompter's own browser profile, so it never asks:

```json
{
  "screen": "ARZOPA",
  "stt": ["ws://127.0.0.1:8097/v1/audio/transcriptions/realtime",
          "ws://other-machine:8093/v1/audio/transcriptions/realtime"],
  "stt_lang": "fr-FR",
  "stt_server": ["nemo-speech", "serve", "--no-ui", "--threads", "4", "--host", "127.0.0.1", "--port", "8097",
                 "--device", "cpu", "--asr-model", "/path/to/nemotron-3.5-asr-streaming-0.6b.q8_0.gguf"]
}
```

## Writing a script

See [examples/sample.md](examples/sample.md). Anything above the first `---` (if it comes in the
first 15 lines) is treated as notes to yourself. Put a cue on its own line in brackets to mark a
section for the edit: it is hidden from the prompter and becomes a section break.

```markdown
# Episode 1

Notes for me: B-roll list is in the shot doc.

---

**[Hook]**

You spent a whole weekend on your first video. Twelve people watched it.
```

## Notes on Wayland

Wayland does not let an app choose where its window goes, so on a Wayland session prompter starts
the browser through Xwayland (`--ozone-platform=x11`), which does. It also avoids flicker on some
60 Hz USB-C monitors placed next to a high refresh rate laptop screen.

## Tests

```
python3 -m unittest discover -s tests
```

## License

MIT
