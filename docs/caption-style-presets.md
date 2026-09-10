# Caption style presets (ASS)

Reference specs for burned-in captions, adapted for this toolkit's ffmpeg +
ASS pipeline (`ass=captions.ass` filter). Sourced from a skill-discovery
audit (2026-09-10) of two external Claude Code skills —
[AgriciDaniel/claude-shorts](https://github.com/AgriciDaniel/claude-shorts)
(Remotion-rendered) and
[6missedcalls/video-editing-skill](https://github.com/6missedcalls/video-editing-skill)
(ffmpeg/Whisper-based) — with their exact numbers translated from
Remotion/CSS units into ASS `[V4+ Styles]` fields so they can be dropped
into a project's `build_captions_*.py` without re-deriving specs from
scratch each time. Font sizes assume a 1080×1920 canvas; scale
proportionally for other resolutions.

Every preset below pairs with the toolkit's existing `\t` pop-in transform
pattern (see `projects/*/build_captions_*.py` for worked examples) for the
entrance animation — the "spring config" column is the Remotion equivalent,
included so the *feel* (how bouncy, how fast) can be matched even though ASS
has no physics-based springs of its own; approximate with two-stage `\t`
scale keyframes (overshoot then settle).

## Bold (claude-shorts) — business / education / "guru" content

| Property | Value |
|---|---|
| Font | Noto Sans CJK JP Bold (or Montserrat Bold for latin) |
| Size | ~72px equiv → ASS Fontsize 60-64 at 1080-wide canvas |
| Case | UPPERCASE (latin only — no case concept in JP) |
| Words/page | 2-3 |
| Color | White text, **active word/phrase in Yellow `&H0000D7FF&`** |
| Outline | 3px solid black, all sides — ASS `Outline: 3`, `OutlineColour: &H00000000&` |
| Position | Bottom, `MarginV: 350` (px from bottom edge) |
| Entrance | Pop-in, spring `{mass:1, damping:12, stiffness:200}` → ASS: `\fscx55\fscy55` → `\t(0,120,\fscx112\fscy112)` → `\t(120,200,\fscx100\fscy100)` (slight overshoot, settles ~0.3s) |

## Bounce (claude-shorts) — entertainment / reactions / high-energy

| Property | Value |
|---|---|
| Font | Bangers (OFL, Google Fonts) or a heavy display JP font |
| Size | ~84px equiv → ASS Fontsize 70-76 |
| Words/page | 1-2 |
| Color | Rotates per page: Cyan `&H00FFFF00&` → Magenta `&H00FF00FF&` → Lime `&H0000FF00&` → Yellow `&H0000FFFF&` → Orange `&H000066FF&` → Hot Pink `&H006600FF&` (cycle) |
| Outline | 4px solid black |
| Entrance | Very bouncy, spring `{damping:8, stiffness:180}`, scale 0.7→1.2→1.0 → ASS: `\fscx70\fscy70` → `\t(0,90,\fscx125\fscy125)` → `\t(90,180,\fscx100\fscy100)` |

## Clean (claude-shorts) — professional / interviews / calm

| Property | Value |
|---|---|
| Font | Noto Sans CJK JP (Regular/Medium — not Bold) |
| Size | ~56px equiv → ASS Fontsize 46-50 |
| Case | Original (no uppercase) |
| Words/page | 3-5 |
| Color | White, active word Light gray `&H00E0E0E0&` |
| Shadow | Soft: ASS `Shadow: 3` (blurred via `ScaledBorderAndShadow: yes`), no hard outline |
| Entrance | Fade-in only, opacity 0→1 over 200ms — ASS `\fad(200,0)`, no scale/transform |

## Hormozi (video-editing-skill) — word-by-word big impact

The "Alex Hormozi style" seen across fitness/business creator shorts: one or
two words on screen at a time, huge, centered, high-contrast — built for
watching muted with the sound off.

| Property | Value |
|---|---|
| Font | Very heavy weight — Noto Sans CJK JP Black, or a condensed impact font |
| Size | Large — ASS Fontsize 80-100 (dominant element of the frame) |
| Words/page | 1 (word-by-word swap, not phrase chunks) |
| Color | White fill, thick black outline, optional yellow/green flash on emphasis words |
| Outline | Heavy — `Outline: 6-8` |
| Position | Centered (`Alignment: 5`), not bottom-anchored |
| Timing | Each word's own Dialogue line, synced to word-level ASR timestamps (needs Whisper or VOICEVOX phoneme timing, not sentence-level) |

Word-level timing is the hard part for this style — sentence-level TTS
duration (what `manifest_*.json` gives you in this toolkit) isn't granular
enough; either run the synthesized narration back through Whisper for word
timestamps, or approximate by splitting each sentence's duration evenly
across its word count (rougher, but workable for short exclamations).

## Standard (video-editing-skill) — traditional bottom subtitles

| Property | Value |
|---|---|
| Font | Noto Sans CJK JP |
| Size | ASS Fontsize 40-46 |
| Background | Semi-transparent box behind text — ASS `BorderStyle: 3`, `BackColour: &H80000000&` (50% black) |
| Position | Bottom, standard subtitle placement |

This is what most of this toolkit's existing amber-pop-in captions
(`entp-love-talk/v3`, `v4`) already approximate — listed here for
completeness / as the "when in doubt" fallback.

## Minimal (video-editing-skill) — unobtrusive lower-third

| Property | Value |
|---|---|
| Font | Noto Sans CJK JP |
| Size | ASS Fontsize 32-36 (small) |
| Style | No background box, thin outline only |
| Position | Lower-third, small margin |

## Two-card "info box" style (reverse-engineered from a 都市伝説/雑学 short, 2026-09-10)

Not from either audited skill — this is the format documented directly from
a sample video in `projects/entp-love-talk/v5/` (see that project's
`build_captions_urban.py` for the full working implementation): opaque
white card, black bold text, split across a card ABOVE and a card BELOW a
centered boxed still, no glow/highlight. Worth keeping here since it's a
distinct, validated preset alongside the others:

| Property | Value |
|---|---|
| Font | Noto Sans CJK JP Bold |
| Size | ASS Fontsize 44-46 |
| Color | Black text `&H00101010&` on near-opaque white card `&H08F5F5F5&` (BackColour alpha near `00`, **not** `F0` — a common mistake, see pitfall below) |
| BorderStyle | 3 (opaque box), `Outline: 18` (box padding, not a text outline) |
| Position | Two styles: `Alignment: 8` (top, MarginV ~150) and `Alignment: 2` (bottom, MarginV ~470) |

**Pitfall (hit and fixed in v5):** ASS `BackColour`/`OutlineColour` alpha is
inverted — `00` = fully opaque, `FF` = fully transparent. A near-`F0` alpha
looks like a "mostly transparent white" was intended but actually renders as
a barely-there gray wash, not a solid card. For a solid opaque card, alpha
must be close to `00` (e.g. `&H08F5F5F5&`, not `&HF0F5F5F5&`).

**Pitfall (hit and fixed in v5):** when building multi-line dialogue text
with `\N` line breaks programmatically, escape each line's raw text
*individually* before joining with the literal `\N` separator — never join
first and then escape the whole string, since a blanket backslash-escape
pass will double-escape the `\N` you just inserted (`\N` → `\\N`), which
libass renders as a literal stray backslash instead of a line break.
