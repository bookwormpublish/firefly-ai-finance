#!/usr/bin/env python3
"""
Monday Brief Generator — auto-prepares everything you need to write your book.

Cron setup (runs every Sunday at 8pm):
  crontab -e
  Add: 0 20 * * 0 cd /path/to/kids-books && python monday_brief.py >> briefs/cron.log 2>&1

Usage:
  python monday_brief.py                 # auto-select best book for this week
  python monday_brief.py --preview       # show which book would be selected, no generation
  python monday_brief.py --book P1-PB-002  # force a specific book by ID
  python monday_brief.py --force         # overwrite if a brief already exists this week
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import anthropic

SCRIPT_DIR = Path(__file__).parent
BACKLOG_FILE = SCRIPT_DIR / "backlog.json"
CHARACTER_BIBLE_FILE = SCRIPT_DIR / "character_bible.json"
VOICE_GUIDE_FILE = SCRIPT_DIR / "voice_guide.json"
BRIEFS_DIR = SCRIPT_DIR / "briefs"

SEASONAL_TOPICS = {
    1: ["winter", "new_year"],
    2: ["friendship", "kindness", "valentines"],
    3: ["spring", "nature"],
    4: ["nature", "growth", "spring"],
    5: ["adventure", "independence", "spring", "summer"],
    6: ["summer", "courage"],
    7: ["summer", "back_to_school_prep"],
    8: ["back_to_school", "new_beginnings"],
    9: ["fall", "new_school_year", "back_to_school"],
    10: ["fall", "feelings"],
    11: ["gratitude", "family"],
    12: ["winter", "giving"],
}

AGE_BAND_SPECS = {
    "board_book": {
        "words": "50-150",
        "spreads": "6-8",
        "default_spreads": 7,
        "reading_level": "1 noun or phrase per page",
        "read_aloud_time": "under 1 minute",
    },
    "picture_book": {
        "words": "400-800",
        "spreads": "12-16",
        "default_spreads": 14,
        "reading_level": "Simple sentences",
        "read_aloud_time": "3–5 minutes",
    },
    "early_reader": {
        "words": "1500-3000",
        "spreads": "20-30",
        "default_spreads": 24,
        "reading_level": "Short chapters",
        "read_aloud_time": "15–20 minutes",
    },
}


def load_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: dict | list) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_monday_of_week(today: date) -> date:
    return today - timedelta(days=today.weekday())


def pick_next_book(backlog_data: dict, today: date, verbose: bool = False) -> dict:
    """Score queued books and return the best pick for this week."""
    queued = [b for b in backlog_data["books"] if b["status"] == "Queued"]
    if not queued:
        print("ERROR: No queued books in backlog. Add more entries to backlog.json.")
        sys.exit(1)

    month = today.month
    seasonal = set(SEASONAL_TOPICS.get(month, []))
    last_pillar = backlog_data.get("last_published", {}).get("pillar")

    scores = []
    for book in queued:
        score = 0
        reasons = []

        book_tags = set(book.get("season_tags", []))
        seasonal_overlap = book_tags & seasonal
        if seasonal_overlap:
            score += 5
            reasons.append(f"+5 seasonal tags match: {seasonal_overlap}")

        if book.get("publish_month") == month:
            score += 10
            reasons.append(f"+10 exact publish month match: {month}")

        if last_pillar and book["pillar"] == last_pillar:
            score -= 10
            reasons.append(f"-10 same pillar as last book: {last_pillar}")

        scores.append((score, book, reasons))

    scores.sort(key=lambda x: x[0], reverse=True)

    if verbose:
        print("\nBook selection scores:")
        for s, b, r in scores[:5]:
            print(f"  [{s:+3d}] {b['id']} — {b['title_idea']}")
            for reason in r:
                print(f"         {reason}")

    return scores[0][1]


def build_system_prompt(character_bible: dict, voice_guide: dict) -> str:
    return f"""You are a world-class children's book author and SEO strategist. You write books that parents buy and children love — books that solve real parenting pain points while delivering genuine emotional resonance.

You know:
- The difference between a book that sits on the shelf and one that gets read at bedtime for a year
- How to write at a child's emotional level without talking down to them
- How to layer meaning so parents catch their breath at the last page
- How SEO titles work on Amazon and how to write metadata that converts

Your output will be used directly on Monday morning. The author will sit down, open your brief, and write. Every section must be ready to use — not notes to think about, but scaffolding to build on.

## Voice Guide
{json.dumps(voice_guide["rules"], indent=2)}

## Character Bible
{json.dumps(character_bible["series"], indent=2)}

## Age Band Specifications
{json.dumps(AGE_BAND_SPECS, indent=2)}

Always follow the voice guide rules strictly. When a book uses a named series character (Mia, Max & Sam), use the character bible details exactly — same visual description, same signature item, same art style. For standalone books, create a new character using the standalone template structure."""


def build_user_prompt(book: dict, today: date) -> str:
    specs = AGE_BAND_SPECS[book["age_band"]]
    series_note = (
        f"Series character: **{book['series']}** (use the character bible entry exactly)"
        if book.get("series")
        else "This is a standalone book — create a new character following the standalone template structure in the character bible."
    )

    return f"""Generate a complete Monday Brief for this week's book.

## Book Details
- **ID**: {book["id"]}
- **Pillar**: {book["pillar"]} — {book["pillar_name"]}
- **Age Band**: {book["age_band"]} ({book["age_range"]} years)
- **Topic**: {book["topic"]}
- **Working Title**: {book["title_idea"]}
- **Target Words**: {book["target_words"]}
- **Target Spreads**: {book["target_spreads"]}
- **Hook**: {book["hook"]}
- {series_note}
- **Today's Date**: {today.strftime("%B %d, %Y")}

---

Generate ALL SIX sections below. Be specific, be ready-to-use, be excellent.

---

## SECTION 1: SEO PACKAGE

Generate a complete, ready-to-publish metadata package:

**Primary Title**: [SEO formula: Age + Emotion/Topic + Format + Hook — under 60 characters]
**Subtitle**: [Secondary keyword phrase — under 100 characters]
**Amazon Description** (250 words minimum):
Write a full parent-facing description. Open with the pain point the parent feels. Show how this book helps. Close with a call to action. Weave in the 7 keywords naturally.

**7 Amazon Keywords** (exact-match search terms parents type):
1.
2.
3.
4.
5.
6.
7.

**BISAC Codes**:
- Primary:
- Secondary:

**Pinterest/Google SEO Tags** (10 tags, comma-separated):

---

## SECTION 2: STORY BLUEPRINT

Fill every field:

**Final Title**: [The one you'd actually publish]
**Tagline**: [1 sentence — the line on the cover below the title]
**Core Concept** (1 sentence): [What the child learns or feels]
**Protagonist**: [Name, age, 1 defining trait, 1 visual signature]
**Opening Problem** (spread 1–2): [The specific situation — be concrete, not general]
**3 Attempts / Escalation** (spreads 3–5): [What the character tries, why it doesn't work yet]
**Turning Point** (spread 6): [The moment the character shifts internally — not solved, but changed]
**Resolution** (spread 7–8): [How it resolves — must come from the character, not an adult fixing it]
**Takeaway Line** (final spread): [The exact line. Warm + concrete + hopeful. Under 12 words.]
**Refrain**: [The phrase that repeats 2–4 times through the book]
**Parent Note** (back matter, 2 sentences): [What parents can say or do after reading — practical, warm]

---

## SECTION 3: SPREAD-BY-SPREAD OUTLINE

For each spread, provide exactly:
- **Scene**: [What is physically happening]
- **Character Action**: [What the protagonist does or feels]
- **Text (draft)**: [The actual words — ready to use, under 12 words per sentence]

Generate all {book["target_spreads"]} spreads. Number them clearly.

---

## SECTION 4: ILLUSTRATION PROMPTS

For each spread, write a complete AI image generation prompt using this structure:

**Spread [N] — [Emotion/Scene Label]**
- **Style**: [art style — must match series or standalone decision]
- **Scene**: [what's happening, 1 sentence]
- **Character**: [protagonist + emotion + body posture]
- **Background**: [setting, time of day, 2–3 key elements]
- **Color Palette**: [warm/cool, 3 descriptors or hex codes]
- **Mood**: [the feeling this image must convey]
- **Text Space**: [top / bottom / left / right / full-bleed no text]
- **Full Prompt**: [The complete prompt string ready to paste into Midjourney or Firefly]

Generate prompts for all {book["target_spreads"]} spreads.

---

## SECTION 5: VOICE REMINDERS

Write 5 specific reminders for THIS book — not generic rules, but targeted to the topic, character, and age band of this specific story:

1.
2.
3.
4.
5.

Then flag any voice traps specific to this topic (e.g., "Anger books often have adults solving the problem — resist this").

---

## SECTION 6: SOCIAL CONTENT PLAN

**Reel Script (60 seconds)**:
Write the full voiceover script for a 60-second reel. Format:
- Hook line (0–3s): [the scroll-stopper]
- Problem setup (3–15s): [the parent pain point]
- Book reveal (15–40s): [3-page flip narration — what they'd see]
- CTA (40–60s): [where to get it]

**Post 1 — Takeaway Quote Card**:
- Visual description: [what the card looks like]
- Quote: [the exact takeaway line, formatted for a typographic card]
- Caption: [full Instagram caption with hook, problem, solution, CTA, 3 hashtags]

**Post 2 — Behind the Scenes**:
- Visual description: [spread layout or character sketch]
- Caption: [full caption — process-focused, builds authority]

**Post 3 — Parent Tip**:
- Tip: [1 actionable parenting tip related to the book's topic]
- Caption: [full caption — educational, builds trust, soft CTA]

**3 Hashtags for all posts**:
#[topic]booksfortoddlers #[ageBand]reads #[emotion]books"""


def generate_brief(book: dict, character_bible: dict, voice_guide: dict, today: date) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("Set it with: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(character_bible, voice_guide)
    user_prompt = build_user_prompt(book, today)

    print(f"\nGenerating Monday Brief for: {book['id']} — {book['title_idea']}")
    print(f"Model: claude-opus-4-7 | Thinking: adaptive | Effort: high")
    print("=" * 70)

    full_response = ""

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=12000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text

    final = stream.get_final_message()
    usage = final.usage
    print(f"\n\n{'=' * 70}")
    print(f"Tokens — Input: {usage.input_tokens:,} | Output: {usage.output_tokens:,}", end="")
    if hasattr(usage, "cache_read_input_tokens") and usage.cache_read_input_tokens:
        print(f" | Cache read: {usage.cache_read_input_tokens:,}", end="")
    if hasattr(usage, "cache_creation_input_tokens") and usage.cache_creation_input_tokens:
        print(f" | Cache write: {usage.cache_creation_input_tokens:,}", end="")
    print()

    return full_response


def save_brief(content: str, book: dict, today: date) -> Path:
    BRIEFS_DIR.mkdir(exist_ok=True)
    monday = get_monday_of_week(today)
    filename = f"monday_{monday.strftime('%Y_%m_%d')}_{book['id'].lower().replace('-', '_')}.md"
    filepath = BRIEFS_DIR / filename

    header = f"""# Monday Brief — {monday.strftime('%B %d, %Y')}

| Field | Value |
|-------|-------|
| Book ID | `{book["id"]}` |
| Pillar | {book["pillar"]} — {book["pillar_name"]} |
| Age Band | {book["age_band"]} ({book["age_range"]} yrs) |
| Working Title | {book["title_idea"]} |
| Target Words | {book["target_words"]} |
| Target Spreads | {book["target_spreads"]} |
| Series | {book.get("series", "Standalone")} |
| Generated | {today.isoformat()} |

---

{content}
"""

    filepath.write_text(header, encoding="utf-8")
    return filepath


def update_backlog_status(backlog_file: Path, book_id: str, today: date) -> None:
    data = load_json(backlog_file)
    for book in data["books"]:
        if book["id"] == book_id:
            book["status"] = "In Progress"
            book["brief_generated"] = today.isoformat()
            data["last_published"]["pillar"] = book["pillar"]
            data["last_published"]["age_band"] = book["age_band"]
            data["last_published"]["book_id"] = book_id
            data["last_published"]["date"] = today.isoformat()
            break
    save_json(backlog_file, data)


def brief_exists_this_week(today: date) -> Path | None:
    """Return path to existing brief if one was already generated this week."""
    monday = get_monday_of_week(today)
    prefix = f"monday_{monday.strftime('%Y_%m_%d')}_"
    for path in BRIEFS_DIR.glob(f"{prefix}*.md"):
        return path
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate Monday Brief — your complete book-writing kit for the week."
    )
    parser.add_argument(
        "--book",
        metavar="ID",
        help="Force a specific book by ID (e.g. P1-PB-002). Skips auto-selection.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show which book would be selected and its scores — no generation.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing brief if one already exists this week.",
    )
    args = parser.parse_args()

    today = date.today()

    # Check if brief already exists this week
    if not args.force and not args.preview:
        existing = brief_exists_this_week(today)
        if existing:
            print(f"Brief already exists for this week: {existing}")
            print("Use --force to regenerate, or --book <ID> --force to pick a different book.")
            sys.exit(0)

    # Load data files
    for path, label in [(BACKLOG_FILE, "backlog.json"), (CHARACTER_BIBLE_FILE, "character_bible.json"), (VOICE_GUIDE_FILE, "voice_guide.json")]:
        if not path.exists():
            print(f"ERROR: {label} not found at {path}")
            sys.exit(1)

    backlog_data = load_json(BACKLOG_FILE)
    character_bible = load_json(CHARACTER_BIBLE_FILE)
    voice_guide = load_json(VOICE_GUIDE_FILE)

    # Select book
    if args.book:
        matches = [b for b in backlog_data["books"] if b["id"] == args.book]
        if not matches:
            print(f"ERROR: Book ID '{args.book}' not found in backlog.json")
            print("Available IDs:", [b["id"] for b in backlog_data["books"]])
            sys.exit(1)
        book = matches[0]
        print(f"Using specified book: {book['id']} — {book['title_idea']}")
    else:
        book = pick_next_book(backlog_data, today, verbose=args.preview or True)

    if args.preview:
        print(f"\nSelected book for week of {get_monday_of_week(today).strftime('%B %d, %Y')}:")
        print(f"  ID:    {book['id']}")
        print(f"  Title: {book['title_idea']}")
        print(f"  Topic: {book['topic']}")
        print(f"  Band:  {book['age_band']} ({book['age_range']} yrs)")
        print(f"  Words: {book['target_words']}")
        print(f"\nRun without --preview to generate the full brief.")
        sys.exit(0)

    # Generate
    content = generate_brief(book, character_bible, voice_guide, today)

    # Save
    brief_path = save_brief(content, book, today)
    update_backlog_status(BACKLOG_FILE, book["id"], today)

    print(f"\nBrief saved to: {brief_path}")
    print(f"Backlog updated: {book['id']} → In Progress")
    print(f"\nYou're ready for Monday. Open {brief_path.name} and write.")


if __name__ == "__main__":
    main()
