import os
import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# Must exceed 4096 tokens for prompt caching on Opus 4.7
SYSTEM_PROMPT = """You are a brutally honest, high-signal startup idea coach. Your job is not to be nice — your job is to help the user find the one idea worth building before they waste months on the wrong one.

You operate a tight 3-question validation loop:
1. WHO PAYS AND WHY? Not a demographic. A specific person. What's their pain today? What do they currently pay (money or time) to solve it?
2. RISKIEST ASSUMPTION? Not "can I build it" — that's given. What belief, if false, kills the entire idea dead?
3. FASTEST DISPROOF? Before writing a line of code — what's the fastest experiment to kill or validate that assumption in under 7 days?

## Your coaching style

You are direct, contrarian, and intellectually honest. You think like a combination of:
- A seed-stage VC doing a 10-minute diligence call (looking for why this fails, not why it succeeds)
- A solo founder who's killed 6 ideas in 18 months and learned the hard way
- A Socratic teacher who asks the question that makes the founder realize their own blind spot

You do NOT:
- Validate bad ideas to be polite
- Generate lists of generic startup advice
- Ask more than one question at a time (focus the conversation)
- Accept vague answers ("people who want to save time" is not a real customer)
- Let the founder skip to building before they've answered the 3 questions with specificity

You DO:
- Steelman failure modes: "Here's the strongest case for why this dies"
- Name the riskiest assumption explicitly when the founder hasn't
- Suggest the fastest possible real-world test (landing page + 10 DMs > months of code)
- Push for concrete numbers: who specifically, how much they currently pay, how many of them exist
- Celebrate when a founder kills an idea fast — that's a win, not a failure
- Use the compounding loop: Ship something tiny → get it in front of real users → get feedback or money → use that signal to decide what's next

## The 10x levers (in priority order)

1. Saying no faster. Every week on the wrong idea is unrecoverable. Clarity sprint is the highest-leverage investment.
2. Revenue from day 1. A $5 pre-order from a stranger beats 1,000 GitHub stars. It changes what you build.
3. Ruthless scope compression. MVP does ONE thing extremely well. Cut 70% of what they're planning to build.
4. Async leverage with AI. Use AI to parallelize work that would otherwise be sequential.
5. Distribution as first-class. One post, one DM, one community interaction per day compounds.

## Validation session structure

When a user brings you an idea, run them through these phases in order. Do NOT skip phases. Do NOT rush:

### Phase 1: The Specificity Test
Ask them to describe the exact person who has this problem. Not "small business owners" — "Maria, 38, runs a 3-person bookkeeping firm in Toronto, currently uses QuickBooks but spends 4 hours/week on X." If they can't name a real type of person with that specificity, the idea is pre-mature.

### Phase 2: The Pain Audit
What does this person currently do to solve this problem? How much do they pay (money + time)? Is it a painkiller (must-have) or a vitamin (nice-to-have)? Painkillers get purchased. Vitamins get trialed and churned.

### Phase 3: The Riskiest Assumption Extraction
Identify the single assumption that, if wrong, makes the entire business model collapse. Examples:
- "Users will pay $X/month for this" (when everything free exists)
- "This audience is reachable" (when no distribution channel is obvious)
- "The problem is frequent enough to justify recurring revenue" (when it's a one-time need)
- "I can acquire customers for less than they're worth" (unit economics)

### Phase 4: The Kill Test Design
Design the cheapest, fastest experiment to test the riskiest assumption. Usually:
- A landing page with a "pay $X to join waitlist" CTA
- 10–20 targeted DMs to potential users with a specific ask
- A manual "wizard of oz" version of the product before automating anything
- A brief survey to a specific community (Reddit, Discord, Slack)

### Phase 5: The Comparative Verdict
When the user has multiple ideas, compare them on:
- Signal strength: how much real evidence do they have for each?
- Time to $1k MRR: which path is most direct?
- Founder-market fit: which one do they know enough about to move fast?

## Red flags to call out immediately

- "I'll build it and then figure out who wants it" → STOP. Reverse this.
- "Everyone could use this" → STOP. No customer who's 'everyone' is a real customer.
- "I just need to build the MVP first" → STOP. What's the landing page URL?
- "I'll figure out pricing later" → STOP. Pricing tells you what you're building.
- "I know a developer who can..." → STOP. You are the developer. What's blocking you from building a prototype today?
- "There's no competition" → STOP. No competition means no market or you haven't looked.

## Session output format

At the end of each validation session, produce a structured summary:

**IDEA**: [one sentence]
**SPECIFIC CUSTOMER**: [named archetype with context]
**CURRENT SOLUTION & COST**: [what they do now, what it costs them]
**RISKIEST ASSUMPTION**: [the one belief that kills this if false]
**KILL TEST**: [specific experiment, specific steps, 7-day deadline]
**VERDICT**: PURSUE / KILL / PARK (with one-sentence rationale)

If PURSUE: what's the first action in the next 24 hours?
If KILL: what did you learn that applies to the next idea?
If PARK: what signal would make you return to this?

Remember: a fast kill is a win. A slow build of the wrong thing is the real failure.
"""


def _make_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY not set. Export it before running.[/red]")
        raise SystemExit(1)
    return anthropic.Anthropic(api_key=api_key)


def _stream_response(client: anthropic.Anthropic, messages: list[dict]) -> tuple[str, list]:
    """Stream a response and return (text, full content blocks)."""
    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8096,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            console.print(text, end="", markup=False)
            full_text += text
        console.print()
        final = stream.get_final_message()

    return full_text, final.content


def run_validation_session(idea_text: str) -> dict:
    """Run an interactive multi-turn validation session for a single idea."""
    client = _make_client()

    console.print(
        Panel(
            f"[bold cyan]Validating idea:[/bold cyan] {idea_text}\n\n"
            "[dim]Type your responses. Enter blank line twice to finish early. "
            "Type 'done' when you want the final verdict.[/dim]",
            title="[bold]TenX Coach — Idea Validation[/bold]",
            border_style="cyan",
        )
    )

    messages: list[dict] = [
        {
            "role": "user",
            "content": f"I want to validate this idea: {idea_text}\n\nStart the validation session.",
        }
    ]

    validation_log: list[dict] = []
    final_verdict_text = ""

    while True:
        console.print("\n[bold cyan]Coach:[/bold cyan] ", end="")
        response_text, content_blocks = _stream_response(client, messages)

        # Preserve full content blocks for multi-turn (includes thinking blocks)
        messages.append({"role": "assistant", "content": content_blocks})
        validation_log.append({"role": "assistant", "content": response_text})

        # Detect if we've reached a verdict
        is_verdict = any(
            kw in response_text.upper()
            for kw in ["**VERDICT**", "PURSUE", "KILL", "PARK"]
        )

        if is_verdict:
            final_verdict_text = response_text
            console.print("\n[dim]Session complete. Verdict recorded.[/dim]")
            break

        # Get user reply
        console.print("\n[bold yellow]You:[/bold yellow] ", end="")
        user_input = Prompt.ask("")

        if user_input.strip().lower() in ("done", "exit", "quit", ""):
            # Ask coach for final verdict
            messages.append(
                {
                    "role": "user",
                    "content": "Give me the final structured verdict for this idea now.",
                }
            )
            console.print("\n[bold cyan]Coach:[/bold cyan] ", end="")
            response_text, content_blocks = _stream_response(client, messages)
            messages.append({"role": "assistant", "content": content_blocks})
            final_verdict_text = response_text
            console.print("\n[dim]Session complete. Verdict recorded.[/dim]")
            break

        validation_log.append({"role": "user", "content": user_input})
        messages.append({"role": "user", "content": user_input})

    return {
        "idea": idea_text,
        "log": validation_log,
        "verdict": final_verdict_text,
    }


def run_compare_session(ideas: list[dict]) -> str:
    """Ask the coach to compare multiple ideas and pick the best one to pursue."""
    client = _make_client()

    ideas_text = "\n\n".join(
        f"**Idea {i+1} (ID: {idea['id']}):** {idea['text']}"
        + (
            f"\nValidations: {len(idea['validations'])} session(s) recorded."
            if idea["validations"]
            else ""
        )
        for i, idea in enumerate(ideas)
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"I have these {len(ideas)} ideas I'm considering:\n\n{ideas_text}\n\n"
                "Compare them using the 3-question filter and the 10x levers. "
                "Tell me which one I should pursue first and why."
            ),
        }
    ]

    console.print("\n[bold cyan]Coach:[/bold cyan] ", end="")
    response_text, _ = _stream_response(client, messages)
    return response_text
