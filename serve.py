"""
Tiny dev server for the Bilim Gunu demo.

Endpoints:
- POST /api/story  -> streaming Anthropic SSE, 4-act story for kids
- POST /api/scenes -> JSON: 4 image-ready scene descriptions matched to the story
- POST /api/image  -> JSON {url}: a single fal.ai illustration in a locked style

Run:  python serve.py
Open: http://localhost:8000
"""
import http.server
import json
import os
import socketserver
import urllib.request
from email.utils import formatdate

PORT = 8000
HERE = os.path.dirname(os.path.abspath(__file__))


def load_env():
    path = os.path.join(HERE, ".env")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FAL_KEY = os.environ.get("FAL_KEY", "")
if not API_KEY:
    print("UYARI: .env dosyasinda ANTHROPIC_API_KEY bulunamadi.")
if not FAL_KEY:
    print("UYARI: .env dosyasinda FAL_KEY bulunamadi.")


# Illustration style presets - parent picks one via STORY_PAYLOAD.style.
# A common suffix is appended to every preset so all panels stay safe and text-free.
ILLUSTRATION_STYLES = {
    "cartoon-2d": (
        "modern 2D cartoon illustration in the style of a children's animated TV show, "
        "flat vector art with bold clean outlines, bright saturated cel-shaded colors, "
        "expressive simplified character design, friendly cheerful mood"
    ),
    "watercolor": (
        "soft watercolor children's storybook illustration, hand-painted feel, "
        "gentle washes of color with visible paper texture, warm palette, "
        "light pencil-sketch outlines, dreamy and tender mood"
    ),
    "cartoon-3d": (
        "modern 3D rendered cartoon illustration like a contemporary children's animated film, "
        "soft global illumination, smooth sculpted character forms, "
        "rounded friendly proportions, warm cinematic lighting"
    ),
    "pixar": (
        "cinematic Pixar-style 3D illustration, expressive character faces with strong emotion, "
        "polished subsurface skin shading, rich depth of field, "
        "dramatic but warm lighting, theatrical composition"
    ),
    "anime": (
        "anime children's book illustration, soft cel-shaded coloring, "
        "expressive large eyes, clean linework, gentle pastel palette, "
        "Studio-Ghibli-like warmth"
    ),
    "crayon": (
        "crayon-and-paper children's drawing style, hand-drawn rough outlines, "
        "uneven crayon shading with visible strokes and paper grain, "
        "bright primary colors, playful and imperfect feel"
    ),
    "paper-cutout": (
        "paper-cutout collage children's book illustration, layered construction paper shapes, "
        "visible paper textures and soft drop shadows, simplified geometric forms, "
        "warm crafted feel"
    ),
}

ILLUSTRATION_STYLE_SUFFIX = (
    "age-appropriate for young children, no scary or violent elements, "
    "no text, no speech bubbles, no captions, no letters or writing in the image"
)


def resolve_style(payload):
    key = str(payload.get("style", "")).strip().lower()
    base = ILLUSTRATION_STYLES.get(key, ILLUSTRATION_STYLES["cartoon-2d"])
    return f"{base}, {ILLUSTRATION_STYLE_SUFFIX}"


def build_story_prompt(payload):
    character = str(payload.get("character", "")).strip() or "kahraman"
    setting = str(payload.get("setting", "")).strip()
    friend = str(payload.get("friend", "")).strip()
    activity = str(payload.get("activity", "")).strip()
    name = str(payload.get("name", "")).strip()
    topic = str(payload.get("topic", "")).strip()

    try:
        age = int(payload.get("age", 6))
    except (TypeError, ValueError):
        age = 6
    age = max(3, min(age, 14))

    if age <= 4:
        word_target = "100-130 words"
        reading_level = (
            f"a {age}-year-old who is just starting to follow stories. Use very short sentences "
            "(5-9 words). Repeat names instead of using pronouns when it helps. Avoid abstract "
            "concepts; everything must be something the child can see, hear, or touch. "
            "If you must mention a science term, give it a one-phrase plain-words explanation."
        )
    elif age <= 7:
        word_target = "150-200 words"
        reading_level = (
            f"a {age}-year-old. Use short, clear sentences (8-14 words). Concrete imagery, "
            "very few abstractions. When a real term appears (kernel, gravity, magma), follow it "
            "in the same sentence with a kid-friendly explanation."
        )
    elif age <= 10:
        word_target = "230-300 words"
        reading_level = (
            f"a {age}-year-old who reads independently. Sentences can be longer and slightly more "
            "varied (10-18 words, occasional compound sentences). The child can handle one real "
            "technical term per paragraph if it's followed by a clear one-line explanation. "
            "Don't talk down."
        )
    else:
        word_target = "350-450 words"
        reading_level = (
            f"a {age}-year-old. Treat them as a capable reader. Use varied sentence structure, "
            "real vocabulary, and don't over-explain. Technical terms can stand with a brief "
            "in-context clarification, not a baby-talk reframe. The story can be more layered, "
            "with subtler emotion."
        )

    parts = [f"Hero: {character}"]
    if name:
        parts.append(f"Hero's name: {name}")
    if setting:
        parts.append(f"Where they are: {setting}")
    if friend:
        parts.append(f"Their friend: {friend}")
    if activity:
        parts.append(f"What they're doing: {activity}")
    parts.append(f"Reader age: {age}")

    details = "\n".join(f"- {p}" for p in parts)

    if topic:
        lesson_block = f"""**3. Resolution:** The hero and their friend solve the problem. THE LESSON BELOW MUST DRIVE THE RESOLUTION — this concept should emerge naturally and be the key to solving the problem:

LESSON TO TEACH: {topic}

How to weave the lesson in:
- The hero must DISCOVER the idea, not have it narrated to them. The child should feel the "ohhh, so that's how it works!" moment alongside the hero.
- Even if the lesson and the setting feel mismatched (e.g. underwater + how Linux works), translate the lesson into the language of the scene — never break the fairy-tale world to teach. Example: instead of "Linux processes," say "tiny helpers, each doing one little job."
- Do NOT write flat exposition like "And so the hero learned that X..." The lesson must come through action and dialogue."""
    else:
        lesson_block = """**3. Resolution:** The hero and their friend solve the problem. The resolution must include a REAL science or nature fact that fits the setting or activity, woven in naturally as the key to solving the problem. (Example: in a restaurant, how yeast makes bread rise; in a forest, how trees pull water up to their leaves.) The hero must DISCOVER the idea, not have it narrated to them."""

    return f"""You are an experienced children's book writer. Write a short 4-part bedtime story in clear, warm English aimed at {reading_level}

STORY DETAILS:
{details}

STRUCTURE — four numbered parts. Pace each part however the story needs:

**1. Introduction:** Open us into the hero's world. Show us one specific, vivid thing only this scene would have — not a generic list of pretty details.

**2. Problem:** Something happens that pulls the hero in. Real stakes are fine — confusion, frustration, sadness, loneliness, urgency — as long as the overall arc lands somewhere comforting. Avoid actual horror imagery (gore, threats of harm, monsters that want to hurt the kid's hero).

{lesson_block}

**4. Happy Ending:** Land softly. Don't restate the moral; let the warmth do the work.

TONE:

The mood is warm and curious. The hero is allowed to feel things — confused, sad, determined, lonely, surprised, embarrassed, brave. A child can handle real emotion; what they can't handle is meanness or terror. So the story has feeling and stakes, but the world is never cruel and the ending always comforts.

WRITING STANDARDS:

1. **Be specific, not pretty.** Skip the menu of stock fairy-tale details (sparkling, glowing, dancing, whispering, twinkling, rainbows). Pick details no other writer would pick for *this exact* scene. A specific weird detail beats five poetic ones.

2. **Vary your verbs and your sensory channels.** Don't lean on color and light over and over. Use sound, smell, texture, weight, temperature, taste. One unexpected detail is worth more than three predictable ones.

3. **Plain, natural English.** Sound like a parent telling a bedtime story, not a writer trying to be lyrical. No "in a world where," no "little did they know," no piling adjectives.

4. **English names only.** All character names must be common English given names (e.g. Luna, Max, Oliver, Mia, Leo, Ruby, Finn, Ivy, Sam, Pip). Never use Turkish names or non-English names (no Pırıl, no Volkan, no Ateş). Never invent word-salad names. If the input gives a name in another language, replace it with an English name that fits the character.

GENERAL:
- Start each part with **1.**, **2.**, **3.**, **4.**
- Length: {word_target}. Let the story breathe within that range.
- The science/lesson must be REAL, not made up.
- Output the story only — no title, no commentary."""


def build_scenes_prompt(payload, story_text):
    character = str(payload.get("character", "")).strip() or "kahraman"
    setting = str(payload.get("setting", "")).strip()
    friend = str(payload.get("friend", "")).strip()

    anchor_parts = [character]
    if setting:
        anchor_parts.append(f"in {setting}")
    if friend:
        anchor_parts.append(f"with {friend}")
    anchor = " ".join(anchor_parts)

    return f"""You are a comic book artist storyboarding 6 panels for a children's storybook.

Here is the story (4 numbered parts):

\"\"\"
{story_text}
\"\"\"

Map the 4-part story onto 6 panels. Adapt this rhythm to what's actually in the text:

- Panel 1: open the world (Part 1 — Introduction)
- Panel 2: a beat inside Part 1 or the moment Part 2 begins — the friend appears, the activity starts, or the first hint of the problem
- Panel 3: the heart of Part 2 — the problem clearly visible
- Panel 4: the discovery moment in Part 3 — the character realizing or noticing the key idea
- Panel 5: the action of solving in Part 3 — characters using what they learned
- Panel 6: Part 4 — the warm landing, quieter and more intimate

REQUIREMENTS for each prompt:
- Capture the key moment of that panel.
- Always include the main character: {anchor}
- Repeat the SAME concrete character description across all 6 prompts (same hair, same clothes, same colors) so the character is recognizable as one person.
- 2-3 sentences max. Describe action + setting + camera angle + lighting.

LOCATION CONTINUITY (CRITICAL):
- Read the story carefully. Most stories happen in ONE main place. If the characters are in a spaceship cabin throughout, every panel must be in that same spaceship cabin — not a forest, not a cottage, not a different room.
- Only change location when the STORY TEXT explicitly says they move somewhere else. If the story never leaves the cabin, neither do the panels.
- You can vary which CORNER of the same room you show, what's framed in the window, what angle the camera takes — but the room itself stays the same room with the same furniture, same walls, same window, same light source.

EMOTION VARIETY (CRITICAL):
- Each panel MUST name a specific, distinct facial expression for the main character. Do NOT default to the same expression in every panel.
- Map roughly to the story beat:
  * Panel 1: calm, content, settled into the place
  * Panel 2: curious, leaning in, eyebrows up
  * Panel 3: puzzled or worried — brow furrowed, mouth slightly open
  * Panel 4: a wide-eyed "aha!" — eyes lit up, mouth in a small surprised O
  * Panel 5: focused and confident — slight smile, determined eyes
  * Panel 6: warm, soft smile, relaxed — eyes half-closed in contentment
- Write the expression EXPLICITLY in each prompt. Example: "Gandalf's eyes widen in delight, eyebrows raised, a small surprised smile."

CAMERA VARIETY:
- Each panel uses a DIFFERENT camera angle. Mix: wide establishing, medium, low angle, high angle, over-the-shoulder, close-up, two-shot. No two panels share the same framing.
- Panel 1 = widest establishing shot. Panel 6 = most intimate close-up.

NO text, captions, speech bubbles, or letters in the image.

Respond with ONLY a JSON array of 6 strings, no other text:
["prompt 1", "prompt 2", "prompt 3", "prompt 4", "prompt 5", "prompt 6"]"""


def call_anthropic_blocking(prompt, max_tokens=1024):
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    blocks = data.get("content") or []
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        try:
            path = self.translate_path(self.path)
            if os.path.isfile(path):
                mtime = os.path.getmtime(path)
                self.send_header("Last-Modified", formatdate(mtime, usegmt=True))
                self.send_header("Cache-Control", "no-store")
        except Exception:
            pass
        super().end_headers()

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return None

    def _send_json(self, status, obj):
        out = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        if self.path == "/api/story":
            self._handle_story()
        elif self.path == "/api/scenes":
            self._handle_scenes()
        elif self.path == "/api/image":
            self._handle_image()
        else:
            self.send_error(404, "Not Found")

    def _handle_story(self):
        if not API_KEY:
            self.send_error(500, "ANTHROPIC_API_KEY missing on server")
            return
        payload = self._read_json()
        if payload is None:
            return

        prompt = build_story_prompt(payload)

        body = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 1024,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        try:
            upstream = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"Anthropic hata {e.code}: {err_body}")
            self.send_error(502, f"Anthropic error {e.code}")
            return
        except Exception as e:
            print(f"Anthropic baglanti hatasi: {e}")
            self.send_error(502, "Upstream error")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            while True:
                chunk = upstream.read(1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            upstream.close()

    def _handle_scenes(self):
        if not API_KEY:
            self.send_error(500, "ANTHROPIC_API_KEY missing on server")
            return
        payload = self._read_json()
        if payload is None:
            return

        story_text = str(payload.get("story", "")).strip()
        if not story_text:
            self._send_json(400, {"error": "story field required"})
            return

        prompt = build_scenes_prompt(payload, story_text)
        try:
            text = call_anthropic_blocking(prompt, max_tokens=800)
        except Exception as e:
            print(f"scenes error: {e}")
            self.send_error(502, "Anthropic error")
            return

        scenes = self._parse_scenes_json(text)
        if not scenes:
            print(f"scenes parse failed, raw: {text[:300]}")
            self.send_error(502, "Could not parse scene descriptions")
            return

        self._send_json(200, {"scenes": scenes})

    def _parse_scenes_json(self, text):
        # Strip markdown code fences if present.
        s = text.strip()
        if s.startswith("```"):
            s = s.split("\n", 1)[1] if "\n" in s else s
            if s.endswith("```"):
                s = s[:-3]
            s = s.strip()
            # Drop optional language tag like "json"
            if s.lower().startswith("json"):
                s = s[4:].strip()
        # Find first [ and last ] in case of stray prose.
        start = s.find("[")
        end = s.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            arr = json.loads(s[start:end + 1])
        except json.JSONDecodeError:
            return None
        if not isinstance(arr, list):
            return None
        return [str(x) for x in arr if isinstance(x, str) and x.strip()]

    def _handle_image(self):
        if not FAL_KEY:
            self.send_error(500, "FAL_KEY missing on server")
            return
        payload = self._read_json()
        if payload is None:
            return

        scene = str(payload.get("scene", "")).strip()
        if not scene:
            character = str(payload.get("character", "")).strip() or "hero"
            topic = str(payload.get("topic", "")).strip() or "adventure"
            scene = f"A {character} exploring {topic}"

        reference_url = str(payload.get("reference_url", "")).strip()
        style = resolve_style(payload)

        if reference_url:
            prompt = (
                f"{scene}. {style}. "
                "Use the reference image ONLY to keep the character's IDENTITY consistent — "
                "same face shape, same hair color and length, same beard, same skin tone, "
                "same outfit, same colors. "
                "DO NOT copy the facial EXPRESSION from the reference — the expression must match "
                "what is described in this prompt (a different emotion, different mouth, different eyes). "
                "DO NOT copy the pose, body position, composition, framing, camera angle, "
                "background, or location from the reference. "
                "This panel shows a clearly different moment with a different feeling on the character's face."
            )
            endpoint = "https://fal.run/fal-ai/nano-banana/edit"
            body_obj = {
                "prompt": prompt,
                "image_urls": [reference_url],
                "image_size": "square_hd",
            }
        else:
            prompt = f"{scene}. {style}"
            endpoint = "https://fal.run/fal-ai/nano-banana"
            body_obj = {
                "prompt": prompt,
                "image_size": "square_hd",
            }

        body = json.dumps(body_obj).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Key {FAL_KEY}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as upstream:
                data = json.loads(upstream.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"fal hata {e.code}: {err_body}")
            self.send_error(502, f"fal error {e.code}")
            return
        except Exception as e:
            print(f"fal baglanti hatasi: {e}")
            self.send_error(502, "Upstream error")
            return

        images = data.get("images") or []
        url = images[0].get("url") if images else None
        if not url:
            self.send_error(502, "fal returned no image")
            return

        self._send_json(200, {"url": url})


with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
    httpd.allow_reuse_address = True
    print(f"Hikaye Makinesi http://localhost:{PORT} adresinde calisiyor")
    print("Durdurmak icin Ctrl+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatiliyor...")
