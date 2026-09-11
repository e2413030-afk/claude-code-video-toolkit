# Reference-video format analysis via Gemini (browser)

When cloning the editing format of a reference short (TikTok/Reels/YouTube
Shorts) — cut timing, transitions, caption specs, BGM/SE, tone — this
toolkit's own tools can't watch or listen to an arbitrary video. This
procedure hands that job to Gemini through the browser (`claude-in-chrome` or
the built-in browser), which *can* do real multimodal video+audio analysis —
but only when used correctly. Validated 2026-09-11 against a real 20s TikTok
clip; see the three-tier comparison below for what actually works.

## The three tiers (cheapest to most capable — and least to most reliable)

1. **Bare YouTube/TikTok link pasted into Gemini's chat.** Looks great at
   first — confident answers about aspect ratio, duration, BGM mood, layout.
   **Don't trust it.** Gemini does NOT watch the video this way; it pulls the
   auto-caption transcript plus general knowledge about the genre/creator and
   writes plausible-sounding fiction. Proven by directly asking it afterward
   "did you actually listen to the audio for that BGM answer?" — it admitted
   the BGM/mood answer was pure inference from the title and transcript
   text, not real listening. Treat every claim from this tier as a guess
   until cross-checked.
2. **A real frame image uploaded as a file** (grab one with `ffmpeg -ss
   <t> -frames:v 1 out.jpg` from a downloaded/recorded clip, or use a
   YouTube thumbnail fraction endpoint `i.ytimg.com/vi/<id>/{0,1,2,3}.jpg`
   when you don't have the file). This is genuine image analysis — pixel-
   level layout percentages, hex-ish colors, line counts came back
   measurably different (and more useful) than the tier-1 guesses. But it
   can still confidently state something visually wrong: it called a clearly
   bold gothic caption font "明朝体" (serif) — caught only by looking at the
   same image myself. **Spot-check every "measured" claim against the image
   yourself, especially anything font/typography-related** — that specific
   judgment seems weak even when everything else about the analysis is
   accurate.
3. **An actual video file uploaded** (the user's own screen recording, or
   any clip you have rights to — see consent note below). This is the tier
   that's actually worth the setup. A single real upload produced: a full
   timestamped cut list, the actual transition techniques in play (flash/
   distortion/zoom synced to the beat, not just "hard cut"), per-segment
   caption text with font/color/position, BGM genre+tempo+a specific
   song-title guess, and an explicit, correct observation that there was
   *no* separate SE track — everything was synced to the music's own beat.
   Independently re-verified 3 of its timestamped claims by pulling frames
   at those exact seconds with ffmpeg — all matched exactly (caption text,
   effect type, end-card). The specific song-ID guess is a strong lead, not
   a confirmed fact — verify by ear.

## Procedure

1. Get an actual video file — the reference creator's own download feature,
   or (most reliable, works for any platform) **have the person screen-record
   themselves playing it** on their own device. This sidesteps YouTube's
   bot-detection wall entirely (downloading via `yt-dlp` from this sandbox is
   IP-blocked — confirmed, multiple extractor-arg workarounds tried and
   failed) without resorting to sketchy "youtube-to-mp4" converter sites,
   which this toolkit's operator will not drive (they're a bot-detection
   bypass by another name, and a real malware-risk category besides).
2. In Chrome (`claude-in-chrome` tools; `ToolSearch` for
   `mcp__claude-in-chrome__*` if deferred), open `gemini.google.com/app`,
   switch the model to **3.1 Pro** (or whichever is the "advanced reasoning"
   tier that session offers — Flash-Lite/Flash give shallower answers),
   click the `+`/"アップロードとツール" button, then use `find` to locate the
   now-visible hidden `input[type=file]` and `file_upload` the video path
   directly — do NOT click the upload menu item yourself (it opens a native
   OS file picker the automation can't drive).
3. **A rights/consent dialog appears on video upload** ("アップロードする
   コンテンツの権利を所有していること...を確認ください"). This is a real
   attestation, not a cookie banner — only click through it for content the
   person actually has the rights/permission to use for this purpose. Get
   explicit confirmation of that before agreeing, every time; don't assume
   it from an earlier session.
4. Ask one dense, single-line message covering everything you need —
   timestamped cut list, per-cut transition technique, caption timing/font/
   color/position, BGM genre/tempo/identification, SE timestamps,
   narration/tone — and explicitly demand it separate 事実 (confirmed by
   actually looking/listening) from 推測 (inferred). **Avoid literal newlines
   in the typed message** — Gemini's composer submits on Enter (not
   Shift+Enter), so a `\n` mid-type fires the message early with only the
   first line sent. Use ①②③ markers instead of a numbered list with real
   line breaks, or explicit `key: shift+Return` actions between lines.
5. Cross-check 2-3 of the concrete, falsifiable claims (exact caption text,
   an effect at a specific second) by pulling real frames yourself
   (`ffmpeg -ss <t> -frames:v 1`) before trusting the rest of the answer.

## Why not just feed it the bare link and call it done

Because it will answer anyway, confidently, and the answer will look exactly
as detailed as the real thing until you push on one specific claim. The
"grill it, don't accept the first confident answer" approach is what
surfaced the tier-1 BGM admission — worth doing as a matter of course before
trusting any single-shot analysis of a reference video.
