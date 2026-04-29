# Bilim Günü Hikaye Makinesi — Briefing

You are joining a project that is already built and dialed in. Read this first; do not re-explore.

## What this is

A live vibecoding demo for **6-year-old kindergartners** on a science day. The user (Orsan) shows kids the terminal next to a browser. Kids verbally shout answers; he types prompts to you; you edit code; the page updates; a 4-panel comic story is generated. The point is for kids to see code change in real time and produce their story.

Audience: Turkish kindergartners. Stories are in Turkish. UI labels are in Turkish.

## How a demo session goes

1. User asks kids 4 questions verbally (character, setting, friend, activity).
2. Kids shout answers.
3. User tells you: "Update STORY_PAYLOAD: character = X, setting = Y, friend = Z, activity = W."
4. You edit `STORY_PAYLOAD` in [index.html](index.html) (the constant is in the script block).
5. Page auto-reloads (there's a poll-and-reload script in `index.html`).
6. User clicks the big button → story streams + 4 panels render.
7. Kids react, shout new ideas, loop.

The user is the one driving — kids never type anything. The interactivity IS the terminal.

## Architecture

Three files matter:

- **[serve.py](serve.py)** — Python http.server (port 8000). Reads `.env`, exposes:
  - `POST /api/story` → streams Anthropic SSE (Sonnet 4.6) for the Turkish story
  - `POST /api/scenes` → blocking Haiku call, takes the story text, returns 4 English image prompts as JSON
  - `POST /api/image` → fal.ai nano-banana. Without `reference_url`: text-to-image. With `reference_url`: nano-banana/edit (image-to-image)
  - Static file serving with `Last-Modified` header so browser auto-reloads on edit
- **[index.html](index.html)** — single page with the comic grid + story box + button. Auto-reload script polls every 800ms. The kids' answers live in `STORY_PAYLOAD`.
- **[.env](.env)** — `ANTHROPIC_API_KEY` and `FAL_KEY`. Already populated. Do not touch unless asked.

Other files: `DEMO-SCRIPT.md` (sequenced demo plan, mostly historical now), `README.md` (quickstart), `.gitignore`, `.env.example`.

## Dialed-in design decisions — DO NOT UNDO without asking

These were tuned across many iterations. A fresh instance must not "improve" them.

### Models
- **Story: `claude-sonnet-4-6`** — Haiku produced bad Turkish (e.g. "Ateşin" as a name, "yanardağ dağı" pleonasm). Sonnet handles Turkish morphology cleanly. Don't downgrade.
- **Scenes (story → image prompts): `claude-haiku-4-5-20251001`** — cheap, fast, fine for JSON formatting. Don't upgrade.
- **Images: `fal-ai/nano-banana` (panel 1) + `fal-ai/nano-banana/edit` (panels 2-4)** — earlier we used `flux/schnell`; characters had no consistency across panels. nano-banana edit mode references panel 1 to preserve character identity. Don't switch back to flux.

### Image flow
Panel 1 generates first (text-only, ~10s). Panels 2-4 fire in parallel, each passing panel 1's URL as `reference_url` so nano-banana edit mode preserves the character. Total: ~20-25s for all 4 panels.

The edit prompt explicitly says "use the reference ONLY for character appearance — do NOT copy composition, pose, framing, camera angle, background, or scene." This was added because earlier the panels looked like the same image redrawn. Keep that strict framing.

### Story prompt structure ([serve.py](serve.py) `build_story_prompt`)
- 4-act structure: Tanışma → Sorun → Çözüm → Mutlu Son. Each part marked **1.** **2.** **3.** **4.**
- Real science fact woven into the **resolution** (Çözüm), not tacked on at the end
- Science term + clarification pattern: "magma — yani yerin altındaki erimiş, sıcak kaya"
- 150-200 words total

### Turkish quality rules (CRITICAL)
The prompt enforces:
1. **No pleonasms** ("yanardağ dağı" type errors)
2. **Names are root forms, never inflected** ("Ateşin" / "Buzun" / "Karın" forbidden — these are possessives, not names). Pick roots like Volkan, Ateş, Pırıl, Toprak, Ada, Bulut.
3. **Natural Turkish syntax** — no translation-feel
4. **Age-6 vocabulary with science term clarifications**

### Tone (CRITICAL — `TON VE ATMOSFER` section)
Stories must feel like **children's fairy tales**, not adventure thrillers. Even when the kids pick a dramatic setting (volcano, storm, deep forest), the **story version** of that place is warm, magical, and curious — never threatening.

Banned sensory details: gray clouds, sulfur smell, smoke, ash, rumbling, shaking, scary shadows, "danger", "afraid", "shivered", "trembled".

Required sensory details: glowing colors, bird song, flower scent, warm bread smell, laughter, soft wind, bright sun, rainbows, sparkling rocks, dancing lights, whispering leaves.

Reframe: "kızgın lavlar" → "altın gibi parlayan ışıklı taşlar". "korkunç ağaçlar" → "yapraklarından ışık süzülen kocaman ağaçlar". The character must "merak etti" / "şaşırdı" / "gözleri parladı" — never "korktu" / "endişelendi".

Problems in act 2 are **mysteries to solve**, not **dangers to escape**.

### Locked illustration style
Single constant `ILLUSTRATION_STYLE` in [serve.py](serve.py) — warm watercolor children's storybook, no text/captions, age-appropriate. Appended to every image prompt. Don't fork this per-panel.

### Background theming (current state: volcano)
Body background, ember particles, button color, placeholder emoji, story-text color all match the current scene. Earlier we had ice (blue gradient + falling snowflakes). When the user changes the scene to something new, **also change the visual theme** to match — they will expect this. Look at how snow → volcano was done in the CSS (gradient + animated background particles + button gradient + accent colors).

## Common requests during demo

| User says | You do |
|---|---|
| "Kahraman X olsun" | Update `STORY_PAYLOAD.character` in [index.html](index.html) |
| "Y'de yaşıyor" | Update `setting` |
| "Arkadaşı Z" | Update `friend` |
| "Z yapıyorlar" | Update `activity` |
| "Sahneyi tamamen değiştir, [yer] olsun" | Update STORY_PAYLOAD AND swap the body background, particles, button colors, emoji to match |
| "Hikaye çok dramatik / korkutucu" | The TON VE ATMOSFER section in the story prompt isn't biting — strengthen it with more specific banned/preferred examples for that scenario |
| "Karakter farklı görünüyor panellerde" | Check that panels 2-4 are passing `reference_url`. Strengthen the "do NOT copy composition" language if scenes still look static |

## Restarting the server

The user runs `python serve.py` in one terminal. If you edit `serve.py`, **the change does not auto-reload** — Python http.server doesn't hot-reload code. You need to kill and restart.

To kill: `netstat -ano | grep :8000` to find the PID, then `taskkill /PID <pid> /F` (Windows) or via PowerShell `Stop-Process`.

`index.html` edits DO auto-apply because the browser polls for `Last-Modified` changes and reloads.

## API keys / secrets

In `.env`. Already configured. The user has explicitly said he won't `cat .env` during the demo. Don't print key values. Don't commit `.env` (it's in `.gitignore`).

## What NOT to do

- Do not propose refactors. The code is intentionally simple (single Python file + single HTML file).
- Do not add error handling beyond what exists. The demo runs once on a known machine; defensive code is noise.
- Do not add a build step, framework, npm, package.json, virtualenv, or anything else. Single Python stdlib server + single HTML file is the design.
- Do not split files. The HTML being one file is a feature — the user can show the kids one file changing.
- Do not add UI form fields for the kids. The interactivity is verbal + the terminal.
- Do not "improve" the Turkish prompt by removing the explicit rules. Every rule there is a fix for an actual error we've seen.
- Do not switch the image model. nano-banana is what works.
- Do not write planning, decision, or analysis docs. Edit code, restart server if needed, done.

## Cost note

Per story: ~$0.01 Sonnet + ~$0.001 Haiku scenes + 4× ~$0.04 nano-banana ≈ **$0.18**. A 30-minute demo with ~10 stories ≈ $2. Trivial.

## Quick mental model

- User in front of kids. Terminal on left. Browser on right.
- Kids shout. User types prompt to you. You edit `STORY_PAYLOAD` (and sometimes theme). Page reloads. Click button. Story + 4-panel comic renders in ~25-30s.
- Repeat with new payload until kids run out of energy.
