#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Linux DAW acceptance: Ardour renders the VST3, Zrythm scans it.
#
# Usage: linux_daws.sh <vst3-bundle> [work-dir] [clap-binary]
set -eu

VST3=${1:?usage: linux_daws.sh <vst3-bundle> [work-dir] [clap-binary]}
WORK=${2:-"$(pwd)/linux-daws"}
CLAP=${3:-}

if [ ! -d "$VST3" ]; then
    echo "linux-daws: VST3 bundle not found: $VST3" >&2
    exit 1
fi
if [ -n "$CLAP" ] && [ ! -f "$CLAP" ]; then
    echo "linux-daws: CLAP binary not found: $CLAP" >&2
    exit 1
fi
case "$WORK" in
    /|"")
        echo "linux-daws: refusing unsafe work directory: $WORK" >&2
        exit 1
        ;;
esac

for tool in ardour8-new_session ardour8-lua ardour8-export zrythm \
            xvfb-run python3 timeout setsid readlink; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "linux-daws: missing $tool" >&2
        exit 1
    fi
done

rm -rf "$WORK"
mkdir -p "$WORK/home/.vst3" "$WORK/home/.clap" "$WORK/home/.config" \
         "$WORK/home/.local/share" "$WORK/ardour" "$WORK/zrythm"
cp -a "$VST3" "$WORK/home/.vst3/"
if [ -n "$CLAP" ]; then
    cp -a "$CLAP" "$WORK/home/.clap/"
fi

export HOME="$WORK/home"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export LANG=C.UTF-8

ARDOUR_UTIL="$(readlink -f "$(command -v ardour8-export)")"
ARDOUR_LIB_DIR="$(cd "$(dirname "$ARDOUR_UTIL")/.." && pwd)"
VST3_SCANNER="$ARDOUR_LIB_DIR/ardour-vst3-scanner"
if [ ! -x "$VST3_SCANNER" ]; then
    echo "linux-daws: missing $VST3_SCANNER" >&2
    exit 1
fi
LD_LIBRARY_PATH="$ARDOUR_LIB_DIR" "$VST3_SCANNER" \
    "$WORK/home/.vst3/$(basename "$VST3")" >"$WORK/ardour-scan.log" 2>&1

SESSION_DIR="$WORK/ardour/session"
SESSION_NAME="TypePFm1"
rm -rf "$SESSION_DIR"
ardour8-new_session -s 44100 "$SESSION_DIR" "$SESSION_NAME" \
    >"$WORK/ardour-new.log" 2>&1 || true
if [ ! -f "$SESSION_DIR/$SESSION_NAME.ardour" ]; then
    echo "linux-daws: Ardour did not create a session" >&2
    tail -20 "$WORK/ardour-new.log" >&2
    exit 1
fi

cat >"$WORK/add_track.lua" <<LUA
backend = AudioEngine:set_backend('None (Dummy)', '', '')
local f = io.open('$WORK/add_track.out', 'w')
local s = load_session('$SESSION_DIR', '$SESSION_NAME')
assert(s)
local info
for p in ARDOUR.LuaAPI.list_plugins():iter() do
  if p.name == 'Type P.fm1' then info = p end
end
f:write('plugin=' .. tostring(info) .. '\n')
assert(info, 'Type P.fm1 not found')
local list = s:new_midi_track(
  ARDOUR.ChanCount(ARDOUR.DataType('midi'), 1),
  ARDOUR.ChanCount(ARDOUR.DataType('audio'), 2),
  true, info, nil, nil, 1, 'Type P.fm1',
  ARDOUR.PresentationInfo.max_order, ARDOUR.TrackMode.Normal, true, false)
assert(list and not list:empty())
f:write('track=' .. list:front():name() .. '\n')
s:save_state('')
f:close()
LUA

timeout 60s xvfb-run -a ardour8-lua "$WORK/add_track.lua" \
    >"$WORK/ardour-lua.log" 2>&1 || true
if ! grep -q 'type="vst3"' "$SESSION_DIR/$SESSION_NAME.ardour"; then
    echo "linux-daws: Ardour did not save the VST3 track" >&2
    cat "$WORK/add_track.out" >&2
    tail -20 "$WORK/ardour-lua.log" >&2
    exit 1
fi

python3 - "$SESSION_DIR" "$SESSION_NAME" <<'PY'
import struct
import sys
from pathlib import Path

session_dir = Path(sys.argv[1])
session_name = sys.argv[2]
base = session_dir
midi_dir = base / "interchange" / session_dir.name / "midifiles"
midi_dir.mkdir(parents=True, exist_ok=True)


def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


track = b""
track += vlq(0) + bytes([0x90, 60, 100])
track += vlq(1920) + bytes([0x80, 60, 0])
track += vlq(0) + bytes([0xFF, 0x2F, 0x00])
data = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 960)
data += b"MTrk" + struct.pack(">I", len(track)) + track
(midi_dir / "Type P.fm1.mid").write_bytes(data)

path = base / (session_name + ".ardour")
text = path.read_text()
sources = (
    "<Sources>\n"
    '    <Source name="Type P.fm1.mid" type="midi" '
    'flags="Writable,CanRename" id="500" origin=""/>\n'
    "  </Sources>"
)
locations = (
    "<Locations>\n"
    '    <Location id="600" name="session" start="0" end="88200" '
    'flags="IsSessionRange" locked="no" position-lock-style="AudioTime"/>\n'
    '    <Location id="601" name="start" start="0" end="0" '
    'flags="IsMark,IsStart" locked="no" position-lock-style="AudioTime"/>\n'
    '    <Location id="602" name="end" start="88200" end="88200" '
    'flags="IsMark,IsEnd" locked="no" position-lock-style="AudioTime"/>\n'
    "  </Locations>"
)
text = text.replace("<Sources/>", sources)
text = text.replace("<Locations/>", locations)

region = (
    '      <Region locked="0" name="Type P.fm1" position="0" length="88200" '
    'stretch="1" muted="0" opaque="1" automatic="0" whole-file="0" '
    'import="0" external="0" sync-marked="0" left-of-split="0" '
    'right-of-split="0" hidden="0" position-locked="0" valid-transients="0" '
    'start="0" sync-position="0" ancestral-start="0" ancestral-length="0" '
    'shift="1" positional-lock-style="MusicTime" layering-index="0" '
    'start-beats="0" length-beats="4" id="501" type="midi" '
    'first-edit="nothing" bbt-position="1|1|0" source-0="500" '
    'master-source-0="500"/>\n'
)
marker = '<Playlist'
start = text.find(marker)
while start != -1:
    end = text.find("/>", start)
    if end == -1:
        break
    tag = text[start:end + 2]
    if 'type="midi"' in tag:
        opened = tag[:-2].rstrip() + ">\n"
        replacement = opened + region + "    </Playlist>"
        text = text[:start] + replacement + text[end + 2:]
        break
    start = text.find(marker, end + 2)
else:
    raise SystemExit("MIDI playlist not found")

path.write_text(text)
print("ardour session patched")
PY

timeout 120s ardour8-export -b 24 -s 44100 -o "$WORK/ardour.wav" \
    "$SESSION_DIR" "$SESSION_NAME" >"$WORK/ardour-export.log" 2>&1
if [ ! -f "$WORK/ardour.wav" ]; then
    echo "linux-daws: Ardour did not export audio" >&2
    tail -30 "$WORK/ardour-export.log" >&2
    exit 1
fi

python3 - "$WORK/ardour.wav" <<'PY'
import math
import struct
import sys
import wave

path = sys.argv[1]
with wave.open(path, "rb") as wav:
    frames = wav.getnframes()
    rate = wav.getframerate()
    channels = wav.getnchannels()
    width = wav.getsampwidth()
    data = wav.readframes(frames)

if width == 3:
    values = []
    for i in range(0, len(data), 3):
        value = data[i] | (data[i + 1] << 8) | (data[i + 2] << 16)
        if value & 0x800000:
            value -= 1 << 24
        values.append(value)
    scale = 8388608.0
elif width == 2:
    values = struct.unpack("<%dh" % (len(data) // 2), data)
    scale = 32768.0
else:
    raise SystemExit("unexpected WAV sample width %d" % width)

peak = max(abs(value) for value in values) / scale
rms = math.sqrt(sum((value / scale) ** 2 for value in values) / len(values))
print("ardour: frames=%d rate=%d channels=%d peak=%.6f rms=%.6f"
      % (frames, rate, channels, peak, rms))
if frames == 0 or peak <= 0.001:
    raise SystemExit("Ardour rendered silence")
PY

PLUGIN_CACHE="$XDG_DATA_HOME/Zrythm.org/Zrythm/known_plugins.xml"
rm -f "$PLUGIN_CACHE"
setsid timeout 20s xvfb-run -a zrythm --dummy \
    --new-project "$WORK/zrythm/TestProject" >"$WORK/zrythm.log" 2>&1 &
ZRYTHM_PID=$!
for _ in $(seq 1 40); do
    if [ -f "$PLUGIN_CACHE" ] &&
       grep 'name="Type P.fm1"' "$PLUGIN_CACHE" | grep -q 'format="VST3"'; then
        break
    fi
    sleep 0.5
done
kill -- -"$ZRYTHM_PID" 2>/dev/null || true
wait "$ZRYTHM_PID" 2>/dev/null || true

if [ ! -f "$PLUGIN_CACHE" ]; then
    echo "linux-daws: Zrythm did not write a plugin cache" >&2
    tail -30 "$WORK/zrythm.log" >&2
    exit 1
fi
if ! grep 'name="Type P.fm1"' "$PLUGIN_CACHE" | grep -q 'format="VST3"'; then
    echo "linux-daws: Zrythm did not scan Type P.fm1 as VST3" >&2
    tail -30 "$WORK/zrythm.log" >&2
    exit 1
fi
echo "zrythm: Type P.fm1 scanned as VST3"

if [ -n "$CLAP" ]; then
    if ! grep 'name="Type P.fm1"' "$PLUGIN_CACHE" | grep -q 'format="CLAP"'; then
        echo "linux-daws: Zrythm did not scan Type P.fm1 as CLAP" >&2
        tail -30 "$WORK/zrythm.log" >&2
        exit 1
    fi
    echo "zrythm: Type P.fm1 scanned as CLAP"
fi

echo "linux-daws: ok"
