# A360 Code Analysis Guide

**Skill companion file.** This document tells an agent **how to review an
A360 TaskBot** for quality, compliance, and maintainability. It combines
two inputs:

1. A **rule catalogue** (23 rules, each with a threshold, rationale, and a
   deterministic detection recipe against the JSON described in `SKILL.md`).
2. An **organizational RPA coding standard** — directory layout, variable
   naming, commenting, logging, and version-control conventions.

The two are integrated so that a single review pass can produce:

* per-rule violation counts,
* per-file and per-automation compliance metrics,
* objective code-quality metrics (cyclomatic complexity, Halstead volume,
  maintainability index, code churn, duplication, technology mix),
* a single subjective quality score in the range **1–100**.

---

## 0. Related documents

| File                    | Contents                                                            |
|-------------------------|---------------------------------------------------------------------|
| `SKILL.md`              | JSON schema, line-numbering algorithm, value type system, child-bot calls |
| `A360_PACKAGES.md`      | Per-package command reference (attribute names, enums, examples)    |
| `A360_FLATTEN.py`       | One-line-per-action listing tool (used by several detection recipes) |
| **`A360_ANALYSIS_GUIDE.md`** *(this file)* | Review rules, metrics, and scoring model         |

An agent asked to *analyze* / *review* / *audit* / *score* a TaskBot must
consult this file first, then use `SKILL.md` for JSON navigation and
`A360_PACKAGES.md` for command-level context.

---

## 1. Analysis workflow

Given one or more TaskBot `.json` files, do this in order:

1. **Parse.** Load each file into memory. Walk `nodes` depth-first (`SKILL.md`
   §2.2) to build a flat list of `(lineNumber, depth, node)` tuples for each
   bot. Total across all uploaded bots = "automation size".
2. **Build cross-references.**
   * Call graph: for every `runTask` node, record `callerBot → calleeBot`
     with the caller's editor line number.
   * Variable graph: for every variable, record where it is *written*
     (node `returnTo`) and *read* (`$var$` in an expression / attribute).
   * Credential graph: every `CREDENTIAL` value shape → its
     `lockerName`/`name`/`attributeName`.
3. **Run rules.** Evaluate every rule in §3 against every bot. Record each
   violation as `(ruleId, botFile, lineNumber, nodeUid, message)`.
4. **Compute metrics.** Apply §4 to each bot and to the whole automation.
5. **Score.** Apply §5 to get the overall subjective score.
6. **Report.** Use the template in §6.

---

## 2. Thresholds — configurable defaults

All numeric thresholds are configurable. **Bold** values are the defaults
used by this skill unless a user or a project override says otherwise. The
"Org standard" column shows an example value from a typical organizational
coding standard where it differs.

| Threshold                              | Default (this skill) | Org standard | Rule |
|----------------------------------------|:--------------------:|:------------:|:----:|
| Max actions per **automation**         | **5000**             | —                | R01  |
| Max actions per **task bot**           | **300**              | 800              | R02  |
| Max enabled actions per **Step**       | **50**               | 100              | R05  |
| Max **input + output** variables       | **15**               | 20               | R11  |
| Variable name **min length**           | **5**                | 5                | R09  |
| Variable name **max length**           | **25**               | 25               | R09  |

If the reviewing agent applies the org-standard numbers instead of
these defaults (e.g. when analysing legacy code), it must say so in the
report's "Configuration" section.

---

## 3. Rule catalogue

Each rule has:
* **ID** — stable identifier used in the report.
* **Rule** — one-sentence definition.
* **Severity** — `BLOCKER` (production risk), `MAJOR` (should fix),
  `MINOR` (style), `INFO` (advisory).
* **How to detect** — a deterministic recipe against the JSON structure
  documented in `SKILL.md`.
* **Notes** — false-positive traps.

### R01 · Automation size limit (BLOCKER)

* **Rule:** the total number of action nodes across every bot in the
  automation must not exceed **5000**.
* **Detect:**
  1. Flatten every uploaded bot using the algorithm in `SKILL.md` §2.2.
  2. `automationSize = Σ len(lines) for each bot`.
  3. Violation if `automationSize > 5000`.
* **Notes:** Comment nodes count. Branch headers (else/catch/finally) count.

### R02 · Task-bot size limit (MAJOR)

* **Rule:** no single bot's flattened line count may exceed **300**.
* **Detect:** per-bot line count from the walk in §2.2.
* **Notes:** If a bot is over the limit, propose split points at existing
  top-level `step` boundaries.

### R03 · Try / Catch coverage (BLOCKER)

* **Rule:** every non-comment action inside the automation logic must be
  inside a `try` block (directly or transitively).
* **Detect:**
  1. Walk each bot; carry a boolean `insideTry`.
  2. Enter `try` → set `insideTry = true` for its children.
  3. `catch` / `finally` branch children also count as "inside".
  4. Nodes to exempt from the rule (do **not** need to be inside a try):
     - `Comment.Comment`
     - `Step.step` itself (its *children* still must be inside a try)
     - The top-level `try` node itself
     - `TaskBot.runTask` **is** subject to the rule
  5. Violation for every action node with `insideTry == false`.
* **Notes:** A bot whose whole body is wrapped in one outer `try` at the
  top level passes trivially.

### R04 · No infinite loops (BLOCKER)

* **Rule:** loops must have a documented exit condition — either a bounded
  iterator (`times`, `forEachItemInList`, `forEachRowInCSVTXT`, …), or a
  `while` loop that contains a `loop.commands.break` guarded by a
  measurable condition.
* **Detect:**
  1. For every `loop.commands.start` node, inspect `iterator.value.iteratorName`.
  2. Safe iterators:
     `loop.iterators.times`,
     `loop.iterators.forEachItemInList`,
     `loop.iterators.forEachItemInDictionary`,
     `loop.iterators.forEachRowInCSVTXT`,
     `loop.iterators.forEachRowInDataTable`,
     `loop.iterators.forEachFileInFolder`.
  3. Unsafe iterator: `loop.iterators.condition` (while-style). Descend into
     the loop body; violation unless it contains at least one
     `loop.commands.break` **and** the break is inside an `if` whose
     condition references a counter/state variable that is being mutated
     inside the loop.
  4. Report every loop that has no reachable exit as a BLOCKER.
* **Notes:** Common false positive — retry loops that intentionally break
  on success (fine — flag only if no counter/state is mutated).

### R05 · Step action limit (MAJOR)

* **Rule:** the number of **enabled** actions **directly inside** a Step
  cannot exceed **50**.
* **Detect:**
  1. For each `Step.step` node: `count = |{c in step.children : c.disabled == false}|`.
  2. Violation if `count > 50`.
* **Notes:** Grandchildren (inside a nested try/if/loop inside the step)
  do NOT count toward the parent step's total. Only direct children.

### R06 · No disabled actions (MINOR)

* **Rule:** production bots must not contain nodes with `"disabled": true`.
* **Detect:** any node (or branch) with `disabled == true`.
* **Notes:** Common in development. Downgrade severity to INFO if the
  bot is flagged as `dev` (see §7.2 on dev-mode step).

### R07 · No empty control blocks (MAJOR)

* **Rule:** the following blocks must contain at least one non-Comment
  action: `try`, `catch`, `finally`, `if`, `elseIf`, `else`,
  `loop.commands.start`, `step`, and any Trigger Loop Handle block.
* **Detect:** for each such node/branch, check `children`. Violation if
  `children` is empty, or every child is `Comment.Comment`.
* **Notes:** Empty `else` branches are legal in A360 but count as a
  violation for this rule (they are code smell).

### R08 · Variable naming pattern (MAJOR)

* **Rule:** every variable name must match one of the naming patterns
  listed in §7.3 ("Variable naming pattern table"). Default patterns
  follow a common convention (`<abbreviation><name><typeSuffix?>`
  in camelCase).
* **Detect:**
  1. Load the type-abbreviation table from §7.3.
  2. For each variable, extract the leading lowercase letters
     (`^[a-z]+`).
  3. If the abbreviation does not match the variable's declared `type`
     (via §7.3 map), report a violation.
  4. Also violation if the name is one of the editor-generated defaults
     (`Window1`, `TableRow`, `Sample*`, `SampleString`, `SampleNumber`,
     `Browser1`, `Session1`, `CsvTxtRow` when not renamed, …).
* **Notes:** The two production bots we analysed use `str/nbr/bln/lst/ssn/
  file/dct/tbl/rec` prefixes; this is one accepted convention. The pattern
  table in §7.3 is authoritative and can be overridden per project.

### R09 · Variable name length (MINOR)

* **Rule:** variable names must be **≥ 5** and **≤ 25** characters.
* **Detect:** `len(name) < 5 or len(name) > 25`.
* **Notes:** The count includes the type-prefix.

### R10 · No unused variables (MAJOR)

* **Rule:** every variable declared in the bot must be either read or
  written by at least one action.
* **Detect:**
  1. Collect all variable names declared in `variables[]`.
  2. Scan every node for `returnTo.variableName` (write) and every value's
     `expression` string for `$name$` (read).
  3. Variables marked `input: true` count as *written* by the caller; still
     require at least one read inside the bot.
  4. Variables marked `output: true` count as *read* by the caller; still
     require at least one write inside the bot.
  5. Violation for any variable not touched.
* **Notes:** Constants (`constant: true`) are exempt from the "must be
  written" half of the check.

### R11 · Input + output variable limit (MAJOR)

* **Rule:** `count(input==true) + count(output==true) ≤ 15` per bot.
* **Detect:** count from `variables[]`.
* **Notes:** If exceeded, propose grouping related fields into a single
  DICTIONARY/RECORD variable.

### R12 · First action must be Comment (MINOR)

* **Rule:** the first node of the bot must be `Comment.Comment` — the
  header block that names the bot and describes its purpose.
* **Detect:** `nodes[0].commandName == "Comment"` and it is not disabled.
* **Notes:** Both reference bots (`COMMON_logger`, `COMMON_send_mail`) use
  a 6-line comment header. A single-line comment is enough to pass this
  rule but consider it MINOR to have < 3 lines.

### R13 · No hard-coded delay (MAJOR)

* **Rule:** the delay time in a `Delay` action must be set via a variable,
  never a literal number.
* **Detect:**
  1. For every node with `(packageName, commandName)` in
     `{("Delay", "delay"), ("Delay", "delayInSeconds")}` (or any package
     command whose primary attribute is `delayValue` / `delay`):
  2. Read the `delay` attribute. Violation if
     `value.type == "NUMBER" and "number" in value`
     (i.e. literal), pass if `"expression"` referencing a variable is used.

### R14 · No hard-coded file / folder path (MAJOR)

* **Rule:** file or folder paths passed to any command must be built from
  variables, not literal strings.
* **Detect:**
  1. Consider every attribute whose value type is `FILE`, or whose name is
     one of: `filePath`, `folderPath`, `parentPath`, `destinationFolder`,
     `sourceFile`, `taskbotFile`.
  2. Pass if the value is an `expression` containing at least one `$var$`
     token (e.g. `file://$strLogFilePath$`).
  3. Violation if the value is a bare literal string
     (e.g. `"file:///c:/temp/file.csv"`, `"C:\\Screenshots"`).
* **Notes:** Repository URIs (`repository:///…`) inside `runTask.taskbotFile`
  are exempt — they identify a Control Room artifact, not a runtime path.

### R15 · No hard-coded email address (MAJOR)

* **Rule:** no command attribute may contain a literal email address.
* **Detect:** for every value of type `STRING` (both `string` and
  `expression` payloads), match the regex
  `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b`. Violation on any
  hit that is **not** a config-value default in a `variables[]` entry.
* **Notes:** Empty-string defaults do not violate. Comments do not
  violate (opt-out).

### R16 · Catch block cannot be empty (BLOCKER)

* **Rule:** every `catch` branch must contain at least one non-Comment
  action.
* **Detect:** for each `try.branches[]` where `commandName == "catch"`,
  count non-Comment, non-disabled children.

### R17 · Mandatory catch logging (MAJOR) *(org standard)*

* **Rule:** every `catch` branch must contain a `LogToFile.logToFile`
  action **or** a `TaskBot.runTask` that calls the shared logger bot
  (`COMMON_logger` or `COMMON_db_rec`).
* **Detect:** descendants of the catch branch include at least one of
  the two patterns above.

### R18 · Mandatory catch line reference (MAJOR) *(org standard)*

* **Rule:** the catch's error variable-binding must capture the error
  line number.
* **Detect:** `catch.returns.errorLineNumber` is set and points to a
  NUMBER variable.

### R19 · Repository path hygiene (MINOR)

* **Rule:** `taskbotFile.string` in every `runTask` must start with
  `repository:///` — no local paths.
* **Detect:** trivial.

### R20 · No literal credentials (BLOCKER)

* **Rule:** password/secret attributes must use the `CREDENTIAL` value
  shape (`SKILL.md` §4.2), never inline strings.
* **Detect:** for attributes whose name is one of
  `password`, `secureText`, `userSecureText`, `clientCredSecret`,
  `apiKey`, `token`, `clientSecret`, `bearer`:
  * pass if `value.type == "CREDENTIAL"`,
  * violation otherwise.

### R21 · Loops must be named (MINOR) *(org standard)*

* **Rule:** every `loop.commands.start` should have an `anchor` label so
  nested `break` / `continue` unambiguously target it.
* **Detect:** `anchor` present, non-empty, and unique within the bot.

### R22 · Steps have descriptive uppercase titles (MINOR) *(org standard)*

* **Rule:** every `step` node's `title` attribute must be non-empty,
  fully UPPERCASE, and at least 5 characters.
* **Detect:** simple string check.

### R23 · dev-mode step present (INFO) *(org standard)*

* **Rule:** the bot should contain a `step` titled `DEV MODE` (or
  `DEV MODE - VARIABLE INITIALIZATION`) as its first executable step,
  wrapping literal test values, and disabled in production.
* **Detect:** locate a `step` whose title matches `^DEV[ _-]MODE`. Pass if
  present. This rule never blocks; it feeds the recommendations section.

---

## 4. Objective code-quality metrics

Each metric is computed **per bot** and **aggregated for the automation**.

### 4.1 Rule-based metrics

* **Violation count by rule.**
  For each ruleId → `Σ 1 for every violation`. Report as a table.

* **Violation-line ratio.**
  `distinctLinesWithAtLeastOneViolation / totalLines`.
  Reported as a percentage per bot and for the whole automation.

### 4.2 Cyclomatic complexity (CC)

Each **decision point** adds one path. In A360, decision points are:

| Node                              | Adds |
|-----------------------------------|:----:|
| `If.if`                           | 1    |
| `If.elseIf` (branch)              | 1    |
| `Loop.loop.commands.start`        | 1    |
| `ErrorHandler.catch` (branch)     | 1    |
| `Recorder.capture` used as an `If` predicate | 1 |
| Any `If` whose condition has boolean `AND`/`OR` sub-parts | +1 per extra operand |

`CC = 1 + Σ(decision points)`.
Report thresholds: `< 10 = simple`, `10–20 = moderate`, `20–50 = complex`,
`> 50 = untestable`.

### 4.3 Halstead metrics

* **Operators (n1 / N1)** — treat each unique `(packageName, commandName)`
  pair as one operator kind; count each occurrence.
* **Operands (n2 / N2)** — treat each distinct variable name and each
  distinct literal value (STRING/NUMBER) as one operand kind; count
  occurrences via `$var$` reads, `returnTo` writes, and literal attribute
  values.
* **Volume:** `V = (N1 + N2) * log2(n1 + n2)`.
* **Difficulty:** `D = (n1 / 2) * (N2 / n2)`.
* **Effort:** `E = D * V`.

Interpretation: report V as-is; flag if `V > 20000` for a single bot.

### 4.4 Maintainability index (MI)

Use the canonical SEI formula scaled to 0–100:

```
MI = max(0, (171 − 5.2 * ln(V) − 0.23 * CC − 16.2 * ln(LOC)) * 100 / 171)
```

where `LOC` is the flattened line count (§2.2). Bands:

| MI      | Verdict           |
|---------|-------------------|
| 85–100  | Highly maintainable |
| 65–84   | Moderate          |
| 40–64   | Poor              |
| < 40    | Very poor         |

### 4.5 Code churn (optional)

Requires **version-control history**. If a Control Room export of check-in
comments is available:

* `churn = Σ (linesAdded + linesRemoved) over the last N check-ins`
  (default `N = 20`).
* Report as absolute number and normalized `churn / LOC`.

If VC history is not accessible, mark this metric **N/A** in the report
and do not deduct points for it.

### 4.6 Code duplication

Detect the **same algorithm** — a multi-step block of logic — copied within
one bot or across the relevant bots. Copy-paste with only the variable names
changed still counts; incidental structural similarity between unrelated
boilerplate does **not**, and a single trivial line (e.g. the `$month$`
zero-pad) never counts.

> **Why the old structural fingerprint over-reported.** Hashing only
> `packageName + commandName + sortedAttrNames` ignored variable names *and*
> literal values, so RPA boilerplate that merely shares command *shape*
> (`Assign → If → Log …`) collided as "duplicate." Combined with a small
> `k = 5` window whose overlapping matches were each counted, ratios were
> inflated far past reality. The steps below fix all three causes.

**Step 1 — Normalize each node into a semantic token.**
For every flattened node build a token from:

* `packageName.commandName` — the operation itself;
* the operation's **semantic signature**: for `If` / `Loop` / decision nodes,
  the comparison operator(s) and boolean shape; for `Assign`, whether the RHS
  is an expression, a literal, or a plain variable copy; for `Loop`, the
  iterator kind; for `runTask`, the callee bot path;
* **operands normalized positionally**: replace each variable name with a slot
  (`$v1$`, `$v2$`, … assigned in first-seen order and reused consistently) and
  each literal with a *type* token (`STR`, `NUM`, `BOOL`, `DATE`) — never the
  value.

This way a block re-pasted with renamed variables collapses to the same token
stream, while two blocks that merely share a generic command (both `If` +
`Assign`) stay distinct because their signatures and operand patterns differ.

**Step 2 — Exclude boilerplate from seeding a clone.**
The following may not *start* a clone or *solely* constitute one: comments,
`step` header nodes, dev-mode blocks (R23), a lone `Log` / `LogToFile`, and a
single standalone `Assign`. A candidate clone must either contain at least one
decision / loop / `runTask` / data-transform node, **or** be ≥ `k` meaningful
nodes long.

**Step 3 — Find maximal repeated blocks (not fixed windows).**

1. Minimum block size **k = 6** consecutive *meaningful* (non-excluded)
   tokens — **or** ≥ 3 if the block contains a decision/loop node.
2. A block is a clone if its token sequence appears in ≥ 2 locations (same bot
   or different bots).
3. Extend every match to its **maximal** length, then **merge overlapping and
   adjacent matched windows into maximal clone regions** so one long repeated
   region is detected once, not once per shifted window.

**Step 4 — Count duplicated lines without double-counting.**

* For each clone region, keep the first occurrence as the *original*; every
  additional occurrence contributes its covered flattened lines to a
  `duplicatedLineSet`.
* `duplicatedLines = |duplicatedLineSet|` — a given line is counted **at most
  once**, even if it belongs to several clones.
* `duplicationRatio = duplicatedLines / totalMeaningfulLines`, where the
  denominator **excludes** comment and `step`-header lines.

**Report** the top clone regions — fingerprint, block size, occurrence count,
and each `bot:line` location — so the finding is actionable. The
recommendation for a genuine clone is *"extract to a child bot / reusable
step."* Single-line or sub-`k` snippets like the `$month$` zero-pad fall below
the floor and are reported nowhere.

Thresholds: `< 5% = clean`, `5–15% = review`, `> 15% = extract to
child bot`.

### 4.7 Technology mix

Detect embedded scripts / non-native technologies. For each bot:

| Signal                                           | Technology tag  |
|--------------------------------------------------|-----------------|
| `Python.python.commands.openScript`              | Python          |
| `Excel_MS.RunMacro` / `Excel_Advanced.macro`     | Excel VBA / macro |
| Any `RunScript` command with `.ps1` in the path  | PowerShell      |
| `.vbs` in a `filePath`                           | VBScript        |
| `.bat` / `.cmd` in a `filePath`                  | Batch           |
| `.sh` in a `filePath`                            | Bash            |
| `Database.*` commands                            | SQL             |
| `WebServices.*` / `REST*` / `SOAP*` commands     | Web API         |
| `SAP*` commands                                  | SAP scripting   |
| `AI` / `IQBot` / `DocumentAutomation` packages   | AI / OCR        |

`technologyCount = |distinct tags found|`. Report as a diversity indicator
— higher is not automatically worse, but ≥ 4 warrants a note about
integration risk.

---

## 5. Overall subjective score (1–100)

Start at **100** and deduct.

### 5.1 Deductions

Weight per severity:

| Severity | Points per violation |
|----------|---------------------:|
| BLOCKER  | −10                  |
| MAJOR    | −3                   |
| MINOR    | −1                   |
| INFO     | 0 (recommendation only) |

Cap the deduction per rule at **−20** to avoid a single systemic issue
dominating the score.

### 5.2 Adjustments (max ± 15)

Add or subtract based on metrics:

| Condition                                | Adjustment |
|------------------------------------------|:----------:|
| `MI ≥ 85`                                | +5         |
| `MI 65–84`                               | 0          |
| `MI 40–64`                               | −5         |
| `MI < 40`                                | −10        |
| Avg `CC ≤ 10` across bots                | +3         |
| Any bot with `CC > 50`                   | −5         |
| `duplicationRatio < 5%`                  | +2         |
| `duplicationRatio > 15%`                 | −5         |
| `violationLineRatio < 5%`                | +2         |
| `violationLineRatio > 25%`               | −5         |

### 5.3 Bands

| Score  | Verdict                                    |
|--------|--------------------------------------------|
| 90–100 | Excellent — production ready               |
| 75–89  | Good — minor polish recommended            |
| 60–74  | Fair — address MAJOR findings before go-live |
| 40–59  | Poor — significant rework required         |
| 1–39   | Fail — do not deploy                       |

---

## 6. Report output — HTML

The review is delivered as a **self-contained HTML report**, not a Markdown
file. The layout, styling, light/dark theme, and print rules are already built
— your job is only to supply the data, so every review comes out looking the
same and the reader gets a scannable dashboard (score dial, severity tiles,
metric meters, findings table, full rule catalogue) instead of a wall of text.

Two files under `assets/` do the work:

| File | Role |
|------|------|
| `assets/analysis_report_template.html` | The template. Contains `{{TOKENS}}` and `<!-- REPEAT: name -->…<!-- /REPEAT -->` blocks. Never edit it per-review — fill it. |
| `assets/render_report.py` | Fills the template from a JSON payload and writes the finished report. Prefer this over hand-substituting tokens. |
| `assets/analysis_report_sample.html` | A rendered example (the `COMMON_notify_users` review) so you can see the target output. |

### 6.1 Preferred path — build a JSON payload and run the renderer

Assemble the analysis results into a JSON object with the shape below, then run:

```
python assets/render_report.py <payload.json> -o <ReviewName>_review.html
```

The renderer escapes values, expands the repeat blocks, colours severity/band
by attribute, and fails loudly if a token is left unfilled — so you don't have
to touch the HTML. Payload shape (all keys shown; see the sample for realistic
values):

```jsonc
{
  "automation_name": "COMMON_notify_users",
  "review_date": "2026-07-28",
  "score": 54,                       // 0–100 (§5); drives the dial + its colour band
  "verdict_band": "Poor — significant rework required",   // §5.3
  "threshold_profile": "default (this skill)",            // or "org-standard" / "custom"
  "bots_analyzed_list": "COMMON_notify_users (9 lines)",
  "total_automation_size": 9,
  "config_overrides": "none",
  "counts": { "blocker": 7, "major": 3, "minor": 2, "info": 1 },
  "violation_line_ratio": 78,        // §4.1, percentage
  "mi": 64,                          // maintainability index, §4.4
  "duplication_ratio": 0,            // §4.6, percentage
  "metrics": [                       // one row per bot (§4)
    { "bot": "COMMON_notify_users", "lines": 9, "cc": 2,
      "halstead_v": "~146", "mi": 64, "duplication": 0,
      "tech_mix": "Native only (Outlook M365, CSV)" }
  ],
  "findings": [                      // only rules that fired (§3)
    { "rule_id": "R20", "rule_name": "No literal credentials",
      "severity": "blocker",         // blocker | major | minor | info
      "count": 1, "locations": "L6",
      "message": "clientSecret is a hard-coded literal — must use the Credential Vault." }
  ],
  "catalogue": [                     // ALL 23 rules, whether or not they fired (§3)
    { "rule_id": "R01", "rule_name": "Automation size limit", "severity": "blocker",
      "threshold": "≤5000 actions", "status": "pass", "count": 0 }
    // status: pass | fail | na   (na = not applicable, e.g. no catch blocks to check)
  ],
  "fixes": [                         // ordered, business-language (see below)
    "Secure the mailbox credentials — replace the typed-in client secret at line 6 with a Credential Vault lookup."
  ],
  "positives": [
    "The loop is a bounded CSV row iterator — no infinite-loop risk (R04 passes)."
  ]
}
```

### 6.2 Fallback — fill the template directly

If Python isn't available, open `assets/analysis_report_template.html`, replace
every `{{TOKEN}}`, and clone each `<!-- REPEAT: … -->` block once per row.
Severity colour is driven by `data-sev="blocker|major|minor|info|pass"` and
metric bands by `data-band="good|moderate|poor|bad"` — set the attribute and the
colour follows. Set the score dial's `--score-color` by band: `good` ≥90,
`--accent` 75–89, `warning` 60–74, `serious` 40–59, `critical` <40.

### 6.3 Content rules (unchanged by the format)

* The **fixes** list is business-facing — plain language, no rule IDs, each
  naming the concrete change and where (per SKILL.md's "Compare PDD ↔ bot"
  guidance). Technical detail lives in the findings table, not here.
* **Findings** lists only rules that fired; the **catalogue** lists all 23 so
  the reader can see what passed. Cite editor line numbers (§2.2) in
  `locations`.
* A status colour never stands alone — the template always pairs it with an
  icon and a text label, so leave those badges intact.

---

### Type-abbreviation map used by R08 detection:

| Variable type | Abbreviation prefix | Example                    |
|---------------|---------------------|----------------------------|
| STRING        | `str`               | `strHomeBank`              |
| NUMBER        | `num` or `nbr`      | `nbrCreditAmount`          |
| DATETIME      | `dt`                | `dtTransactionDate`        |
| BOOLEAN       | `bln`               | `blnFail`                  |
| FILE          | `file`              | `fileAttachmentXLSX`       |
| WINDOW        | `wnd`               | `wndSAPHome`               |
| CREDENTIAL    | `cred`              | `credPeopleSoftUser`       |
| LIST          | `lst`               | `lstTransactionRecords`    |
| DICTIONARY    | `dic` or `dct`      | `dicMonthNameStrings`      |
| RECORD        | `rec`               | `recInvoiceDetails`        |
| TABLE         | `tbl`               | `tblTransactions`          |
| SESSION       | `ssn`               | `ssnTransactionDB`         |
| ANY           | `any`               | `anyListItem`              |



### Action precedence (from high → low reliability)

When there is a choice, prefer this ordering:

```
1. API connections / direct DB queries       ← most reliable
2. Recorder with structured UI selectors
     (XPath for web; UI-Automation for desktop)
3. Native package commands (Excel_MS, Outlook M365, SharePoint, …)
4. Scripting (Python, PowerShell) — use when needed:
     Python for heavy data (large tables, transforms)
     PowerShell where AD / Azure / System packages lack functionality
5. Keystrokes / Mouse coordinates              ← last resort
```

An agent reviewing a bot should call out situations where a *lower*
precedence technique is used when a higher one would have worked (e.g.
`Mouse.mouseMove` where `Recorder.capture` would do).