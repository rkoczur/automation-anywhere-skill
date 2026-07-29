# Automation Anywhere A360 Analysis Skill

A Claude skill and toolkit for reading, reviewing, scoring, and documenting
**Automation Anywhere Automation 360 (A360) TaskBots** exported from the
Control Room. Point Claude at one or more bot `.json` files and it will parse
the structure, map editor line numbers, check them against a 23-rule coding
standard, compute quality metrics, and produce a self-contained HTML review.

---

## What's in this folder

| File | Purpose |
|------|---------|
| [SKILL.md](SKILL.md) | Entry point. The A360 JSON schema, value type system, `runTask` call graphs, line-numbering walk, and generation guardrails. |
| [A360_PACKAGES.md](A360_PACKAGES.md) | Command-level reference — what each package/command does and how its attributes look. |
| [A360_ANALYSIS_GUIDE.md](A360_ANALYSIS_GUIDE.md) | The review engine: 23 rules, objective metrics (complexity, Halstead, maintainability, **duplication** — §4.6), and the 1–100 scoring model. |
| [A360_FLATTEN.py](A360_FLATTEN.py) | Turns a bot `.json` into a one-line-per-action listing that mirrors the editor's line numbers exactly. |
| [assets/render_report.py](assets/render_report.py) | Fills the HTML report template from a JSON analysis payload. |
| [assets/analysis_report_template.html](assets/analysis_report_template.html) | The report design (you supply data, this supplies layout/styling). |
| [assets/analysis_report_sample*.html/json](assets/) | A worked example — payload + rendered report. |
| [evals/](evals/) | Fixtures and expectations used to test the skill. |

---

## 1. Exporting bots from the Control Room

The skill reads the **JSON form** of a bot, not the binary `.bot` package.

### Preferred: download the source JSON

1. In the Control Room, open the folder holding the bot(s).
2. Select the TaskBots as a normal export flow → **⋮ (Actions)** → (**Export**).
3. Unzip the downloaded file
4. The bot files has no extensions → rename them, so they will be .JSON files
5. Use the files in VS Code or Claude CLI with this skill

### Export the whole automation, not just the entry bot

A "real" automation is usually a **parent bot plus the child bots it calls**
via `runTask`. To analyze it properly, export **every bot in the call graph**:

> If you only have a snippet pasted into chat, the skill still works on it —
> but metrics that span bots (call graph, cross-bot duplication) need the full
> set of files.

---

## 2. Naming and organizing the files

Keep the Control Room bot name and use it as the filename:

```
<Automation>/
  MAIN_process_invoices.json
  COMMON_logger.json
  COMMON_send_mail.json
  SUB_validate_record.json
```

Guidelines:

- **One `.json` per bot**, named after the bot as it appears in the repository
  (the trailing segment of its `repository:///…/<BotName>` path). This is how
  `runTask` callees are matched to files — see [SKILL.md §9](SKILL.md).
- Don't rename in a way that loses the callee name — e.g. `COMMON_logger.json`
  must stay recognizable as `COMMON_logger`, or the call graph won't link.
- Spaces in names are fine; the skill handles literal spaces and `%20`.

---

## 3. Using the skill with Claude

Once the files are in the folder, just ask. The skill auto-triggers on A360
bot JSON. Typical requests:

- **Explain** — *"What does `MAIN_process_invoices.json` do?"*
- **Flatten / cite lines** — *"Show me a line-numbered listing"* or
  *"What's on line 42?"*
- **Review / audit / score** — *"Review this automation against the coding
  standard"* → produces the HTML report.
- **Call graph** — *"Map which bots call which"* across the folder.
- **Compare / refactor / document / generate** — *"Extract the repeated
  retry block into a child bot,"* *"Generate a skeleton logger bot."*

Claude loads only the reference file each task needs (routing table at the top
of [SKILL.md](SKILL.md)), so you don't have to specify which doc to read.

---

## 4. The command-line tools

Both scripts are plain Python 3, no dependencies. Run from this folder.

### Flatten a bot to a readable listing

```bash
python A360_FLATTEN.py path/to/bot.json                 # writes ./<bot>.flat.txt + prints
python A360_FLATTEN.py path/to/bot.json -o out.txt      # custom output path
python A360_FLATTEN.py path/to/bot.json --quiet         # file only, no stdout
python A360_FLATTEN.py path/to/bot.json --max-str 60    # truncate long literals
```

Line numbers match the A360 web editor exactly (every command node and every
branch header — `else` / `elseIf` / `catch` / `finally` — is one line).
Unknown commands fall back to a generic `Package: command k=v` line, so it's
safe on packages the script has never seen.

## 5. What the analysis reports

Per bot and aggregated for the whole automation
(full detail in [A360_ANALYSIS_GUIDE.md](A360_ANALYSIS_GUIDE.md)):

- **23 coding-standard rules** (BLOCKER / MAJOR / MINOR / INFO) — try/catch
  coverage, no infinite loops, no literal credentials, named loops, descriptive
  step titles, size limits, and more, including configurable organizational standards.
- **Cyclomatic complexity** — decision-point count per bot (§4.2).
- **Halstead volume / difficulty / effort** (§4.3).
- **Maintainability index** (0–100, §4.4).
- **Code duplication** — the *same multi-line algorithm* reused within or
  across bots, using semantic tokens with positionally-normalized operands so
  copy-paste-with-renamed-variables is caught while incidental boilerplate and
  trivial one-liners are not (§4.6).
- **Technology mix** — embedded Python/VBA/PowerShell/SQL/API/SAP signals (§4.7).
- **Overall score (1–100)** with a verdict band and a prioritized findings list.

---