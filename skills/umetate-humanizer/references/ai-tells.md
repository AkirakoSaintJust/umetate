# AI tells

This is the reviewed detection reference for the umetate humanizer. The original
generic catalog had 55 patterns. This reference keeps the ones that matter for this
voice, adds the product self-description, article-drumbeat and wh-word heading
tells, and folds the rest into the main checklist. A pattern is a signal, not a
verdict. Read `voice.md` and the skill before you change a sentence.

## The patterns that matter

| ID | Tell | Fix |
| --- | --- | --- |
| P1 | Significance inflation: "stands as", "is a testament to", "pivotal moment", "underscores the importance", "evolving landscape" | State what the thing is or does. Cut the "represents" commentary. |
| P2 | Notability name-dropping: a list of publications with no claim | Pick one source and say what it reported, or cut it. |
| P3 | Superficial -ing clause: "highlighting", "underscoring", "ensuring", "reflecting", "showcasing" | Delete it or promote its information into a sourced sentence. |
| P4 | Promotional language: "vibrant", "breathtaking", "seamless", "robust", "world-class", "state-of-the-art" | Replace the adjective with the fact, setting, or sound that earns it. |
| P5 | Vague attribution: "experts argue", "research suggests", "industry reports", "it is widely believed" | Name the source and what it said, or cut the claim. |
| P6 | Formulaic challenge: "despite these challenges, it continues to thrive" | State the specific problem and what happened. |
| P8 | Copula avoidance: "serves as", "stands as", "acts as" when "is" is the word | Use "is" when it is the word. |
| P9 | Negative parallelism: "not just X, but Y", "not X, it's Y", "less X than Y" | State the positive, the cause, or the comparison. |
| P10 | Rule-of-three padding: three abstract nouns doing the work of one fact | List the real items. Two or four is fine. Concrete triads are content. |
| P31 | Elegant variation: "the visionary creator" after the name | Repeat the name or the pronoun. |
| P32 | Collaborative communication leaking: "In this article, we will explore" | Start with the thing the article says. |
| P33 | Placeholder text: "Dear [Recipient]" left in the draft | Fill it in or cut it. |
| P34 | Chatbot markup leaking: `citeturn0search1` | Remove it. |
| P35 | Tracking parameters in a cited URL | Strip the tracking parameters. |
| P36 | Sudden register shift: slang then "the aforementioned implementation" | Keep one register for the passage. |
| P37 | Overattribution: a list of outlets instead of a finding | Say what the source found. |
| P38 | Paragraph-reshuffling immunity: paragraphs with no causal order | Join the cause to the consequence, or cut the paragraph that only decorates. |
| P39 | "Whether" summary: "Whether you prefer X or Y, there is something for everyone" | End on one concrete detail. |
| P40 | Symbolic gloss: "the factory represents the decline of..." | Give the date, the jobs, the consequence. |
| P41 | Infomercial hook: "The brutal truth? They lack..." | State the finding and the evidence. |
| P42 | Erratic inline bold | Bold only a deliberate contrast, never a random phrase. |
| P43 | The treadmill effect: "In other words", "Put simply", "It performs well" | Say it once, with the number or the mechanism. |
| P44 | False agency: "the market rewards" | Name the actor and the action. The instrument can be the actor in a manual. |
| P45 | Narrator from a distance: "People tend to underestimate..." | Put the reader in the scene. |
| P46 | Diff-anchored writing: "This function was refactored to replace..." | Describe what the function does now. |
| P47 | Hyphenated-pair overuse | Use the hyphen where it is a compound modifier, and drop it where it is not. |
| P48 | Aphorism formula: "Data is the new oil" | Replace it with the concrete reason, instruction, or specific judgement. |
| P49 | Fragmented header: a heading followed by a sentence that repeats it | Make the first sentence say something new. |
| P50 | Passive or subjectless: "the cache is invalidated automatically" | Name the actor and the action. |
| P51 | Reasoning-chain artifact: "Let me break this down. Step 1..." | State the conclusion and the evidence. |
| P52 | Unicode obfuscation | Use plain characters. The goal is good writing, not evasion. |
| P53 | Hedged enumeration: "There are several ways... In general, it is a good idea to consider..." | Give the specific change and the result. |
| P54 | Argument residue: "While some might argue..." | State the claim and the evidence. |
| P55 | Leftover hedge debris: "To some extent, arguably, definitely" | Pick one hedge or commit. |
| P56 | Product self-description: a `what this is` section that restates the visible product and its specs | Cut the section. Use the space for the next action, the controls, or a real limit. |
| P57 | Article drumbeat: a list where every item starts with `The` | Drop the article, lead with the noun or the verb, or write the list as prose. |
| P58 | Wh-word nominal heading or label: `What to reach for first`, `How to move`, `What it does` | Use a noun phrase or an imperative: `Get started`, `Navigation`, `Functionality`. |

The patterns the original catalog had that are not listed here are covered by the
main checklist, or they are generic detector noise that does not fit this voice.
Do not turn the table into a score-chasing exercise.

## False positives and author-specific exceptions

Flag a cluster, not an isolated tell. A single em dash, a single "crucial", or one
three-item list is how humans write too.

- **Perfect grammar is not AI.** Clean spelling and consistent punctuation are
  signs of a careful writer.
- **Formal or non-native English is not AI.** A stiff register can be an honest
  second-language voice. Do not flag it on style alone.
- **Low sentence-length variance is not AI.** Some writers are naturally precise
  and low-variance. Look for the vocabulary and content tells too.
- **Quotes, titles, code, and examples are not yours to rewrite.** Leave them
  exactly as written. Mask code and block quotes before scanning.
- **Jargon and repetition can be correct.** Repeat `useEffect` or `set_param`.
  Do not vary a technical term for elegance.
- **Reference and manual sections are self-contained.** Do not force a transition
  between parameter sections.
- **A note next to a control is not a product description.** A line that explains
  what the control does belongs there. The tell is a standalone `what this is`
  section that describes the product instead of the task.
- **A table or parameter list can repeat a label.** That is a reference format. The
  tell is prose bullets where every item opens with `The` and the article adds
  nothing.
- **A real question in body prose is not a heading.** "What does the filter do?"
  can be a sentence. The tell is a heading or table label built from a wh-clause.
- **The instrument can be the actor.** "The filter removes" is correct in a manual.
- **Concrete triads and tip lists are content.** Three real settings are not
  padding.
- **"In order to", "whilst", "sort of", "probably", "and so on", and "(!)"** are
  voice in explanatory prose. Keep the ones doing work.
- **Deliberate contrast bold.** `**is**` and `**does**` in "not an emulation, but it
  **is** a DX-style synth" are voice.
- **A purpose clause.** "In order to" can set up a purpose. Shorten it only when
  the rhythm survives.
- **Calibrated hedges.** "I think", "kinda", "probably" can be voice. Cut a hedge
  only when it contradicts a claim the author wants to make.
- **UK tags and asides.** "innit", "kinda", "gal", "whatever", and "terminally
  online" are identity, not P41.
- **The parenthetical "(!)"** is a genuine surprise marker.
- **Factual "rather than just" contrasts** name both sides. They are not P9.
- **A slash in a scope label** is a compact category label.
- **A specific verdict is allowed.** "The K5000W is the least immediate additive
  instrument of the three" is a judgement, not an aphorism.

## Detect report

For `--mode detect`, output a short report:

```
## Voice report

**Tells found:** 6
**Voice gaps:** no first person, no contractions, uniform sentence length
**Aphorisms:** 1
**A, not B:** 2

| # | Tell | Text | Fix |
| --- | --- | --- | --- |
| 1 | Significance inflation | "stands as a testament" | State what it is. |
| 2 | Negative parallelism | "not just X, but Y" | State the positive. |
```

Keep the report short. Do not list every sentence. Do not score a sample under 40
words.

## Edit safety

Before editing a file in place, check that it is prose. Refuse source code,
configuration, and structured data. Extensions such as `.py`, `.js`, `.ts`, `.go`,
`.rs`, `.c`, `.h`, `.json`, `.yaml`, `.yml`, `.toml`, `.csv`, and `.lock` are out.
Markdown, plain text, and prose documents are fine.

Preserve the author's existing voice. Make targeted edits. Re-read the file after
the edit and check the facts.

## Honest limits

A pattern count is a signal, not a verdict. A model grading its own output inflates
the result. The real gate is a reader who knows the author, or a second pass with
the voice method. Short samples are unreliable. Do not claim a text is AI-generated
from a single tell.
