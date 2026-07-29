---
name: automation-anywhere-parser
description: Reference and toolkit for the JSON format of Automation Anywhere Automation 360 (A360) TaskBots exported/downloaded from the Control Room. Use this whenever you encounter an A360 bot `.json` file or a `.atmx`/`.bot` export, or are asked to read, explain, review, audit, score, lint, compare, refactor, document, map an editor line number to, translate to/from, or generate A360 bot code — even if the user just pastes bot JSON without naming the product. Also use it for questions about A360 commands, packages, variables, credential vault usage, child-bot (`runTask`) call graphs, or organizational RPA coding-standard compliance. Bundles a schema reference, a package/command reference, a 23-rule review-and-scoring guide, and a flattening script. (V2)
---

## 0. How to use this skill — routing

This skill is four files. SKILL.md (this file) is the entry point; the other
three are loaded **on demand** so you only pull in what the task needs. Figure
out which task you're doing, then read the file(s) called out below.

| If the task is…                                            | Read (in addition to this file)                     |
|------------------------------------------------------------|-----------------------------------------------------|
| Understand / explain / parse the JSON structure            | this file (§1–§9) is usually enough                 |
| Look up what a specific command/package does or how its attributes look | `A360_PACKAGES.md` — the command-level reference |
| Review / audit / score / lint a bot for quality or compliance | `A360_ANALYSIS_GUIDE.md` — 23 rules, metrics, 1–100 scoring model. **Deliver the review as HTML**, not Markdown: build the payload and run `assets/render_report.py` (template + renderer live in `assets/`; see §6) |
| Map an editor **line number** ↔ a JSON node, or produce a readable listing | run `A360_FLATTEN.py <bot.json>` (mirrors the editor's line numbering exactly); see §2.2 / §13 for the algorithm if you can't run it |
| Generate or refactor a bot                                 | this file (§4, §8, §11, §12) + `A360_PACKAGES.md` for the target commands |
| Build a call graph across multiple bots                    | this file §8–§9; flatten each bot to get call-site line numbers |

`A360_FLATTEN.py` is the fastest way to turn a bot into something you can read
and cite line numbers against — prefer running it over hand-walking the tree.
It falls back gracefully on commands it doesn't recognize, so it's safe on any
bot. When you can't execute it (no Python, or you only have a JSON snippet),
the depth-first walk in §2.2 reproduces the same line numbers by hand.

The companion files assume the vocabulary defined here (value types, the
line-numbering walk, the `runTask` shape). Skim §1–§4 first if a term in them
is unfamiliar.

---

## 1. Top-level schema

A TaskBot `.json` file is a single JSON object with exactly these keys:

```jsonc
{
  "triggers":            [ ... ],   // usually empty for callable child bots
  "nodes":               [ ... ],   // the ordered command tree (see §2)
  "variables":           [ ... ],   // bot-scope variables (see §5)
  "packages":            [ ... ],   // packages referenced, with versions (see §6)
  "properties":          { ... },   // bot-level settings (see §7)
  "workItemTemplateName": null       // set only if the bot binds to a queue template
}
```

Example:

```json
{
  "botCodeVersion": "7",
  "improvedNumberSupport": true,
  "timeout": "0s",
  "automationPriority": "PRIORITY_MEDIUM",
  "runInChildWindow": false,
  "runInChildWindowMode": "DESKTOP"
}
```

---

## 2. `nodes` — the command tree

`nodes` is an **ordered array**. Each element is a *command node* (one visible
statement in the editor). A command node may contain nested `children`
(the statements indented under it) and/or `branches` (else / catch / finally).

### 2.1 Generic node shape

```jsonc
{
  "uid":         "GUID",                 // stable node id, unique inside the bot
  "commandName": "assign",               // action name (camelCase, package-specific)
  "packageName": "String",               // package that owns the command (see §6)
  "disabled":    false,                  // true = "commented out" in the editor
  "attributes":  [ { ...attribute... } ],// parameters shown in the property panel
  "children":    [ ...nested nodes... ], // present on container commands
  "branches":    [ ...branch objects...],// present on if/try/switch/etc.
  "returnTo":    { ...variable ref... }, // present on commands that return a value
  "anchor":      "someLabel"             // present on loops (loop.commands.start)
}
```

Not every key is present on every node. Fields are omitted (not set to `null`)
when they don't apply.

### 2.2 How JSON structure maps to editor line numbers

The A360 editor numbers **every command node and every branch header** as one
line, in the order they appear in a depth-first walk of `nodes` →
`children`/`branches`.

Algorithm example to walk through and count lines:

```python
counter = 0
def walk(nodes, depth):
    for n in nodes:
        counter += 1;  emit(counter, depth, n)     # this node = 1 line
        walk(n.children,  depth+1)                  # normal nesting
        for b in n.branches:
            counter += 1;  emit(counter, depth, b)  # else / catch / finally headers count too
            walk(b.children, depth+1)
```

### 2.3 Container nodes (they have `children`)

| `commandName`            | `packageName`  | Meaning                                                       |
|--------------------------|----------------|---------------------------------------------------------------|
| `step`                   | `Step`         | Visual grouping. Attributes: `title` (STRING). No control flow. |
| `if`                     | `If`           | Conditional. `attributes[0]` is the `condition`. `branches` hold `else` / `else if`. |
| `try`                    | `ErrorHandler` | Error handler. `branches` hold `catch` and optional `finally`. |
| `loop.commands.start`    | `Loop`         | Loop root. `attributes` describe the iterator (see §2.6).      |

### 2.4 Branch objects (inside `branches`)

A branch has the same shape as a node, but represents a secondary path.

```jsonc
{
  "uid":         "GUID",
  "commandName": "catch",          // or "else", "elseIf", "finally"
  "packageName": "ErrorHandler",   // or "If"
  "children":    [ ... ],
  "attributes":  [ ... ],          // e.g. catch's exceptionType, elseIf's condition
  "returns":     { ... }           // e.g. catch's errorMessage/errorLineNumber bindings
}
```

Example — a `catch` branch that binds the exception into two bot variables:

```json
{
  "commandName": "catch",
  "packageName": "ErrorHandler",
  "attributes": [
    { "name": "exceptionType",
      "value": { "type": "EXCEPTION", "exceptionName": "BotException", "packageName": "ErrorHandler" } },
    { "name": "continueOnError",
      "value": { "type": "BOOLEAN", "boolean": false } }
  ],
  "returns": {
    "errorMessage":    { "type": "VARIABLE", "variableName": "strErrorMessageLocal" },
    "errorLineNumber": { "type": "VARIABLE", "variableName": "nbrErrorLine" }
  },
  "children": [ ... ]
}
```

### 2.5 `if` condition shape

An `if`'s condition is expressed as a single attribute of type `CONDITIONAL`:

```json
{
  "name": "condition",
  "value": { "type": "CONDITIONAL", "conditionalName": "numberVariable", "packageName": "Number" },
  "attributes": [
    { "name": "variable", "value": { "type": "NUMBER", "expression": "$nbrErrorLine$" } },
    { "name": "operator", "value": { "type": "STRING", "string": "EQ" } },
    { "name": "value",    "value": { "type": "NUMBER", "number": "0" } }
  ]
}
```

Common `operator` values: `EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `CONTAINS`,
`STARTS_WITH`, `ENDS_WITH`, `MATCHES_REGEX`. The `conditionalName` +
`packageName` pair identifies the *kind* of condition (string, number, file
exists, boolean, window exists, …).

Every packageName used in a conditional has it's own unique operator values.

### 2.6 Loops

```json
{
  "commandName": "loop.commands.start",
  "packageName": "Loop",
  "anchor": "ConnectRetry",              // optional label used by break/continue
  "attributes": [
    { "name": "loopType", "value": { "type": "STRING", "string": "ITERATOR" } },
    { "name": "iterator",
      "returnTo": { "type": "VARIABLE", "variableName": "nbrLoopCounter" },
      "attributes": [
        { "name": "times", "value": { "type": "NUMBER", "expression": "$nbrRetryThreshold$" } }
      ],
      "value": { "type": "ITERATOR", "iteratorName": "loop.iterators.times", "packageName": "Loop" }
    }
  ],
  "children": [ ... ]
}
```

`loop.commands.break` and `loop.commands.continue` are sibling command nodes
inside a loop; they carry an `anchor` attribute to target a specific outer loop.

### 2.7 Comments

Simple leaf nodes

```json
{ "commandName": "Comment", "packageName": "Comment",
  "attributes": [ { "name": "comment",
                    "value": { "type": "STRING",
                               "string": "This module is responsible for centralized exception handling..." } } ] }
```
---

## 3. `attributes` — parameter list

Every command exposes its inputs through an ordered `attributes` array.

```jsonc
{
  "name":  "logContent",          // parameter name (fixed per command)
  "value": { "type": "STRING",    // typed literal or expression (see §4)
             "string": "Timestamp,Runner machine,User,..." }
}
```

Commands that produce output add a sibling `returnTo` on the *node*, not the
attribute:

```json
"returnTo": { "type": "VARIABLE", "variableName": "strCurrentTime" }
```

---

## 4. Value objects — the type system

Every place a value can appear (attribute value, default value, condition
operand, dictionary entry) uses the same tagged-union shape:

```
{ "type": "<TYPE>", "<payloadKey>": <payload> [, "expression": "..."] }
```

`type` is one of A360's built-in data types. The payload key depends on the
type. When the value should be evaluated (variable references, formulas), the
payload key is replaced by `expression`.

| `type`       | Literal payload key | Notes                                                     |
|--------------|---------------------|-----------------------------------------------------------|
| `STRING`     | `string`            | `expression` variant supports `$var$` interpolation       |
| `NUMBER`     | `number` (as text!) | e.g. `"number": "3"`. `expression` variant also allowed   |
| `BOOLEAN`    | `boolean`           | true / false                                              |
| `DATETIME`   | —                   | Usually only `expression`, e.g. `$System:Date$`           |
| `FILE`       | —                   | Uses `expression: "file://$strScreenshotFile$"`           |
| `LIST`       | —                   | Referenced via `expression: "$lstAttachments$"`           |
| `DICTIONARY` | `dictionary`        | Array of `{ "key": ..., "value": { ... } }` entries        |
| `TABLE`      | (table payload)     | 2-D data structure                                        |
| `RECORD`     | (record payload)    | Named tuple / row                                         |
| `SESSION`    | —                   | Named handle: `expression: "$ssnOutlook$"`                 |
| `VARIABLE`   | `variableName`      | Direct reference (used by `returnTo` and `sourceList` etc.)|
| `CREDENTIAL` | `credential`        | Reference to Credential Vault (see §4.2)                  |
| `EXCEPTION`  | —                   | Uses `exceptionName` + `packageName`                      |
| `ITERATOR`   | —                   | Uses `iteratorName` + `packageName`                       |
| `CONDITIONAL`| —                   | Uses `conditionalName` + `packageName`                    |
| `TASKBOT`    | —                   | Child-bot reference (see §8)                              |
| `WINDOW `    | —                   | Used to store windows with window name and type           |

### 4.1 Variable interpolation inside strings

Any `STRING`/`NUMBER`/`FILE`/... value can be written as an **expression**
instead of a literal, and expressions embed variables with `$…$` syntax:

```
"file://$strLogFilePath$"
"$strBotID$ - ERROR - $strLogMessage$"
"Outlook 365 connection still failed after $nbrRetryThreshold.Number:toString$ tries - $strErrorMessage$"
```

Two special forms appear:

* `$System:Date$`, `$System:AATaskName$` — session/system variables provided
  by the runtime.
* `$var.Package:function$` — inline package function, e.g.
  `$nbrRetryThreshold.Number:toString$` casts a Number to a String.

### 4.2 Credential Vault references

Never inline credentials as strings. The correct value shape is:

```json
{
  "type": "CREDENTIAL",
  "credential": {
    "name":          "AZURE_CREDENTIALS_ATAWAY",
    "lockerName":    "Azure_Credentials_Ataway",
    "attributeName": "CLIENT_SECRET"
  }
}
```

`name` = credential name, `lockerName` = the locker holding it, `attributeName`
= the specific attribute (username, password, client_id, …). Any generator
must emit this shape for secrets.

---

## 5. `variables`

`variables` is an array of variable definitions scoped to the bot.

```jsonc
{
  "name":         "strLogFilePath",
  "description":  "",
  "type":         "STRING",          // any type from §4
  "readOnly":     false,
  "input":        true,              // if true exposed as input param when this bot is called
  "output":       false,             // if true returned to the caller
  "constant":     false,             // rarely set; makes it a constant
  "defaultValue": { "type": "STRING", "string": "" }
}
```

---

## 6. `packages`

Declares which A360 packages the bot uses, and pins their versions:

```json
{ "name": "Microsoft 365 Outlook", "version": "1.13.0", "settingsAttributes": [] }
```

> Do not invent package versions when generating bots. Either copy the version
> already present in a sibling bot, or omit and let the Control Room fill it
> in on import.

---

## 7. `properties`

Bot-level runtime settings.

| Key                    | Meaning                                                   |
|------------------------|-----------------------------------------------------------|
| `botCodeVersion`       | Schema version (currently `"7"`).                          |
| `improvedNumberSupport`| `true` on modern bots — enables higher-precision numbers.  |
| `timeout`              | Bot-wide timeout, e.g. `"0s"` = none.                      |
| `automationPriority`   | `PRIORITY_LOW` / `PRIORITY_MEDIUM` / `PRIORITY_HIGH`.      |
| `runInChildWindow`     | Run in isolated child window session.                      |
| `runInChildWindowMode` | `DESKTOP`, etc.                                            |

---

## 8. Calling another bot — `runTask` (child-bot invocation)

```jsonc
{
  "uid": "GUID",
  "commandName": "runTask",
  "packageName": "TaskBot",
  "attributes": [
    { "name": "taskbot",
      "value": {
        "type": "TASKBOT",
        "taskbotInput": {
          "type": "DICTIONARY",
          "dictionary": [
            { "key": "strLogFilePath",
              "value": { "type": "STRING", "expression": "$strLogFilePath$" } },
            { "key": "strLogMessageType",
              "value": { "type": "STRING", "expression": "$strLogMessageType$" } },
            { "key": "strLogMessage",
              "value": { "type": "STRING", "expression": "$strLogMessage$" } },
            { "key": "nbrErrorLine",
              "value": { "type": "NUMBER", "expression": "$nbrErrorLineNumber$" } },
            { "key": "strErrorMessage",
              "value": { "type": "STRING", "expression": "$strErrorMessage$" } },
            { "key": "strCallerBotName",
              "value": { "type": "STRING", "expression": "$strTaskName$" } },
            { "key": "strBotID",
              "value": { "type": "STRING", "expression": "$strBotID$" } }
          ]
        },
        "taskbotFile": {
          "type": "FILE",
          "string": "repository:///Automation Anywhere/Bots/Ataway/Public_Tasks/COMMON_logger"
        }
      }
    },
    { "name": "repeatOption",         "value": { "type": "STRING",  "string":  "DO_NOT_REPEAT" } },
    { "name": "delayNextRepetition",  "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "continueOnError",      "value": { "type": "BOOLEAN", "boolean": false } }
  ]
}
```

Key points for agents:

* `taskbotFile.string` is a **Control Room repository URI**
  (`repository:///…/BotName`, no `.json` extension). Spaces may be
  percent-encoded (`%20`) or left literal — both forms occur.
* `taskbotInput.dictionary` binds **caller variable → callee input variable**.
  Each `key` is the *callee's* variable name; the `value` is any expression
  from the caller's scope.
* If the callee has `output: true` variables, they can be captured with a
  `taskbotOutput` dictionary on the same node (analogous to `taskbotInput`).
* When mapping "the caller passes X to the callee", the *callee's* declared
  input variables (§5) are the authoritative list of allowed keys.

---

## 9. Cross-file references and dependency mapping

When multiple bot files are provided, an agent should build a
call-graph by scanning every `runTask` node:

1. For each bot file, find all descendants with `commandName == "runTask"`.
2. For each, read `attributes[name=taskbot].value.taskbotFile.string`.
3. The trailing segment of that repository path is the callee bot name — match
   it against other uploaded files (case-insensitively; strip `%20`).
4. Record the call site's editor line (see §2.2) so the map reads e.g.
   `COMMON_send_mail : 17,24,32,42,46,52 → COMMON_logger`.

Also worth cross-checking:

* Shared credential lockers (§4.2) — same `lockerName` used by multiple bots.
* Shared file paths — literal strings or common `$strLogFilePath$` input.
* Shared session names — e.g. both bots use `ssnOutlook` / `ssnGraphAPI` for
  the same Outlook Graph connection package.

---

## 10. Frequently seen commands (quick recognizer table)

| commandName            | packageName             | What it does (business view)                  |
|------------------------|-------------------------|-----------------------------------------------|
| `Comment`              | `Comment`               | Free-text note in the code                    |
| `step`                 | `Step`                  | Named grouping block                          |
| `if` / `else` / `elseIf` | `If`                  | Conditional branching                         |
| `try` / `catch` / `finally` | `ErrorHandler`     | Structured error handling                     |
| `throw`                | `ErrorHandler`          | Raise an exception (`BotException`, …)        |
| `loop.commands.start`  | `Loop`                  | Loop container (iterator/times/list/…)        |
| `loop.commands.break`  | `Loop`                  | Break out of loop (respects `anchor` label)   |
| `runTask`              | `TaskBot`               | Call another bot (see §8)                     |
| `assign`               | `String` / `Number` / `Boolean` / `File` / … | Set a variable      |
| `assignToNumber`       | `Number`                | Assign a numeric literal to a Number variable |
| `replace`              | `String`                | Find/replace, optionally regex                |
| `randomString`         | `String`                | Generate random text                          |
| `toString`             | `Datetime` / `Number`   | Format value as string                        |
| `systemInformation`    | `System`                | Read env info (`USERNAME`, machine, …)        |
| `createFolder`         | `Folder`                | Create a directory                            |
| `logToFile`            | `LogToFile`             | Append/write to a log file                    |
| `captureDesktop`       | `Screen`                | Take a screenshot to file                     |
| `addItem`              | `List`                  | Append to a list variable                     |
| `Connect` / `Disconnect` / `Send` | `Microsoft 365 Outlook` | Graph-API email connection & send |

---

## 11. Style guardrails when *generating* A360 JSON

1. Assign a fresh UUID (`uid`) to every node and branch.
2. Never inline credentials — always use the `CREDENTIAL` value shape (§4.2).
3. Wrap every business action in `try` / `catch`; in the `catch` bind
   `errorMessage` and `errorLineNumber` and call the `COMMON_logger` bot
   pattern shown in §8.
4. Prefix variable names by type (§5) and set `input`/`output` deliberately —
   these define the bot's public contract.
5. Keep `botCodeVersion` and package versions consistent with the target
   Control Room, ideally by copying from an existing bot in the same
   repository folder.
6. Emit meaningful `step` titles and `Comment` headers — the editor uses them
   as the readable structure for reviewers.
7. When embedding variables in text, prefer expressions
   (`"expression": "..$var$.."`) over string concatenation via `+`.
8. For loops, set an `anchor` label so nested `try` can `break` a specific
   outer loop unambiguously.

---

## 12. Minimal skeleton (safe starting template)

```json
{
  "triggers": [],
  "nodes": [
    { "uid": "REPLACE-UUID-1", "commandName": "Comment", "packageName": "Comment",
      "disabled": false,
      "attributes": [ { "name": "comment",
                        "value": { "type": "STRING", "string": "TODO: purpose of this bot" } } ] },
    { "uid": "REPLACE-UUID-2", "commandName": "step", "packageName": "Step",
      "disabled": false,
      "attributes": [ { "name": "title",
                        "value": { "type": "STRING", "string": "MAIN" } } ],
      "children": [] }
  ],
  "variables": [],
  "packages": [
    { "name": "Comment", "version": "2.17.0", "settingsAttributes": [] },
    { "name": "Step",    "version": "2.7.0",  "settingsAttributes": [] }
  ],
  "properties": {
    "botCodeVersion": "7",
    "improvedNumberSupport": true,
    "timeout": "0s",
    "automationPriority": "PRIORITY_MEDIUM",
    "runInChildWindow": false,
    "runInChildWindowMode": "DESKTOP"
  },
  "workItemTemplateName": null
}
```

---

## 13. Quick recipe: mapping "line N" to a JSON node

Given a bot JSON and a target editor line `N`:

```
counter = 0
def find(nodes):
    for n in nodes:
        counter += 1
        if counter == N: return n
        r = find(n.get('children', []))
        if r: return r
        for b in n.get('branches', []):
            counter += 1
            if counter == N: return b
            r = find(b.get('children', []))
            if r: return r
    return None
```
