# Third-party licence texts

These texts travel with the release. The source tree uses them, the publish tool
copies this folder when it stages plugin archives, and a plugin archive carries
them in `licences/`.

| File | Covers |
| --- | --- |
| `AGPL-3.0.txt` | JUCE 8.0.9, which the plugin binary links under its AGPL option. |
| `MIT-clap-juce-extensions.txt` | the CLAP wrapper at the pinned commit. |
| `MIT-CLAP.txt` | the CLAP headers and ABI. |
| `OFL-DotGothic16.txt` | the DotGothic16 font in the editor. |
| `OFL-ZenDots.txt` | the Zen Dots font in the editor. |
| `OFL-Terminus.txt` | the Terminus 8x16 screen font embedded in the firmware. |

The firmware's screen font is Terminus, generated into `firmware/gen/felucca_font.h`
from `ter-u16n.bdf`. Its OFL notice travels here with the firmware source and the
release page. The web app embeds the same firmware, so the notice covers it too.

The VST3 SDK is the copy bundled with JUCE 8.0.9 and is covered by the same
choice of GPLv3 or the Steinberg licence. The project itself is GPL-3.0-only,
see `../LICENSE`. The full attribution list is `../LICENSING.md`.
