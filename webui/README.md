# Web UI sources

Edit the files in `src/`. `src/manifest.json` lists their assembly order: the HTML
shell and stylesheet, shared helpers, settings and the individual tabs. The
JavaScript pieces share the shell's closure, so function declarations can refer
to other tabs without adding browser module requests.

`index.html` is generated and committed. Run `python scripts/webui_source.py`
from the repository root to refresh it, or use `--check` to check it without
writing. PlatformIO, the Linux CMake target and the jsdom harness run this same
assembler. The firmware builder minifies the result and generates
`src/transport/http/WebUiAsset.h`; the TC002 bundle checks both generated files
before shipping the full gzip stream.

`src/generated/berry-api.js` comes from the device bindings on every assembly.
Regenerate `src/generated/timezones.js` with `python scripts/tz_data.py --inject`
after updating the pinned `tzdata` package. Neither generated fragment is edited
by hand. Keep the `//linux:begin` / `//linux:end` regions around Linux-only code;
they are removed from the ESP32 asset by `scripts/build_webui.py`.

## German and Chinese (this fork)

Upstream ships English only. This branch keeps its translations in files upstream
does not have, so `src/` can still be merged from upstream without conflicts:

| File | Holds |
| --- | --- |
| `src/shared/i18n-de.js`, `i18n-zh.js` | one entry per `STR` key in `shared/strings.js` |
| `src/shared/i18n-txt.js` | English literals used inside the views, plus `I18N_EN` for fork-only keys |
| `src/shared/i18n.js` | language choice, `t()` overlay, `tx()`, the header button |
| `src/settings/fields-local.js` | fork-only fields (`powerOffHour`, `randomAppOrder`, …) |

`t()` in `strings.js` reads `STR` on every call, so `i18n.js` only has to overwrite
`STR` with the active language; English is restored from a snapshot. Inline text
goes through `tx()`, which upstream code calls at a handful of choke points —
`actionRow` in `system/maintenance.js` covers every field label and help text,
`select`/`days` in `settings/widgets.js` cover option labels, and `toast()` in
`shared/dom.js` covers messages. A view that shows a literal without `tx()` stays
English; add the literal to `i18n-txt.js` instead of editing the view.

The language follows `?lang=de|zh`, then `localStorage.awtrixLang`, then
`navigator.language`. The `EN / DE / 中文` button in the header cycles through all
three and stores the choice. CJK costs three bytes per character and the UI is
embedded gzipped, so `BUDGET` in `scripts/build_webui.py` is 104 KB here; check it
after adding text. Keep Linux-only translations inside `//linux:` regions.

