# A360 Package Reference

**Companion to `SKILL.md`.**
`SKILL.md` describes the *file-level* JSON schema of an A360 TaskBot
(`nodes`, `variables`, `packages`, value types, line-number algorithm,
`runTask` shape, credential vault, …). **This document is the *command-level*
reference**: for each frequently used package, what commands exist, what
attributes they take, what they return, and how the JSON looks in practice.

---

## 0. Cross-cutting conventions

### 0.1 Session-based packages

Packages that hold an external connection (Excel, CsvTxt, Outlook,
SharePoint, ActiveDirectory, Python, …) always follow the same three-step
pattern:

```
Open / Connect / Authenticate  →  do work (session=...)  →  Close / Disconnect / Revoke
```

The **session handle** is either a plain string name (`"Default"`) or a
`SESSION` variable returned via `returnTo`. Every subsequent command in that
session takes the same handle as its `session` attribute.

Two on-disk shapes are both valid and interchangeable:

```jsonc
// Named session (most packages)
{ "name": "session", "value": { "type": "STRING", "string": "Default" } }

// Session object (session-typed variable)
{ "name": "session",
  "value": { "type": "SESSION",
             "sessionName": { "type": "STRING", "string": "Default" } } }

// Reference to a SESSION variable produced by an earlier "open" command
{ "name": "session",
  "value": { "type": "SESSION", "expression": "$sessionVariable$" } }
```

`returnTo` on an "open" command uses this session-return shape:

```jsonc
"returnTo": {
  "type": "SESSION",
  "sessionName":  { "type": "STRING", "string": "Default" },
  "sessionTarget": "LOCAL"
}
```

### 0.2 `WINDOW` values

UI-automation commands (`Window`, `Wait`, `Keystrokes`, `Browser`) accept a
window either by preset, by literal descriptor, or by variable.

```jsonc
// The currently active window
{ "type": "WINDOW",
  "window": { "type": "WINDOW", "presetType": "CURRENTLY_ACTIVE" } }

// Reference to a Window variable
{ "type": "WINDOW", "expression": "$Window1$" }

// Literal window descriptor (typical in variable default values)
{ "type": "WINDOW",
  "window": {
    "name": "Mail*Outlook",           // supports * wildcard
    "path": "C:\\Program Files\\...\\OUTLOOK.EXE",
    "className": "rctrl_renwnd32",
    "type":  "WINDOW"
  } }
```

### 0.3 `UIOBJECT` (Recorder captures)

A UI element captured with Recorder / AI-sensor is a large value carrying an
opaque `blob` plus a `criteria` map. Only the criteria entries with
`enabled: true` are matched at runtime — the others are stored as fallbacks.

```jsonc
{ "type": "UIOBJECT",
  "uiObject": {
    "blob": "eyJvYmpOb2RlIjp7...",              // base64 tree, do not edit
    "controlType": "BUTTON",
    "technologyType": "MS_UI_AUTOMATION",       // or BROWSER / WEB / JAVA
    "browserType": "UNKNOWN_BROWSER",
    "criteria": {
      "Name":  { "enabled": true,  "value": { "type": "STRING", "string": "Read / Unread" } },
      "ID":    { "enabled": true,  "value": { "type": "STRING", "string": "buttonId" } },
      "Class Name": { "enabled": false, "value": { "type": "STRING", "string": "…" } }
    },
    "isElevated": false
  } }
```

### 0.4 `COORDINATE` values (Mouse)

```jsonc
{ "type": "COORDINATE",
  "coordinate": {
    "x": { "type": "NUMBER", "number": "1175" },
    "y": { "type": "NUMBER", "number": "257"  },
    "capture": { "screenshotPoint": {"x":1175,"y":257}, "…": "…" }
  } }
```

### 0.5 `OAUTHCONNECTION` (Control-Room OAuth pool)

Used by SharePoint and other cloud packages:

```jsonc
{ "type": "OAUTHCONNECTION",
  "oauthConnection": { "connectionName": "SharePointOnlineV2", "isShared": true } }
```

`connectionName` is defined once in Control Room → Administration → OAuth
connections and reused across bots.

### 0.6 Where structural packages are documented

The following packages are documented in `SKILL.md` and are **not** repeated
here:

| Package         | See                          |
|-----------------|------------------------------|
| `Comment`       | SKILL.md §2.7                |
| `Step`          | SKILL.md §2.3                |
| `If`            | SKILL.md §2.3, §2.5          |
| `Loop`          | SKILL.md §2.6                |
| `ErrorHandler`  | SKILL.md §2.3, §2.4          |
| `TaskBot`       | SKILL.md §8                  |

Also, credential access uses the `CREDENTIAL` value shape from SKILL.md
§4.2. Never write literal passwords into a package attribute.

---

## 1. String — text manipulation

`packageName: "String"`. All commands return their result via node
`returnTo`.

| Command          | Purpose                                         |
|------------------|-------------------------------------------------|
| `assign`         | Copy/build a string (supports `$var$` expression)|
| `trim`           | Strip leading/trailing whitespace               |
| `length`         | Character count → Number                        |
| `replace`        | Find/replace (optional regex, case flag, range) |
| `randomString`   | Random alphanumeric of given length             |
| `find`           | Position of a substring → Number                |
| `subString`      | Extract by start index + length                 |
| `split`          | Split on a delimiter → LIST                     |
| `beforeAfter`    | Extract text before/after marker string(s)      |
| `compare`        | Equality test → Boolean                         |
| `uppercase` / `lowercase` / `reverse` | Case / order transforms   |
| `toNumber`       | Parse to Number                                 |
| `toBoolean`      | Parse to Boolean                                |
| `toLocaleNumber` | Locale-aware numeric parse                      |
| `toString`       | (numbers/dates use `Number.toString` / `Datetime.toString`) |

### assign

```json
{ "commandName": "assign", "packageName": "String",
  "attributes": [
    { "name": "sourceString",
      "value": { "type": "STRING", "expression": "$CsvTxtRow{username}$" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "vUserName" } }
```

Notes:
* Access a Record field by name inside an expression: `$rec{fieldName}$`.
* Access a Table cell by row index (1-based): `$tbl[1]$` (whole row) or
  `$tbl[1][2]$` (row 1, column 2).

### trim

```json
{ "commandName": "trim", "packageName": "String",
  "attributes": [
    { "name": "sourceString",  "value": { "type": "STRING", "expression": "$vUserName$" } },
    { "name": "trimAtBeginning","value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "trimAtEnd",     "value": { "type": "BOOLEAN", "boolean": true } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "vUserName" } }
```

### length

```json
{ "commandName": "length", "packageName": "String",
  "attributes": [
    { "name": "sourceString", "value": { "type": "STRING", "expression": "$vUserName$" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nUserNameCharacterLength" } }
```

### replace

```json
{ "commandName": "replace", "packageName": "String",
  "attributes": [
    { "name": "sourceString",       "value": { "type": "STRING", "expression": "$vUserName$" } },
    { "name": "find",               "value": { "type": "STRING", "string": "@corning.com" } },
    { "name": "isCaseSensitive",    "value": { "type": "STRING", "string": "false" } },
    { "name": "isRegularExpression","value": { "type": "STRING", "string": "false" } },
    { "name": "startIndex",         "value": { "type": "NUMBER", "number": "1"  } },
    { "name": "count",              "value": { "type": "NUMBER", "number": "-1" } },
    { "name": "replaceWith",        "value": { "type": "STRING", "string": "@na.corning.com" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "vUsernameWithPlace" } }
```

Notes:
* `isCaseSensitive` and `isRegularExpression` are STRING booleans
  (`"true"` / `"false"`), *not* real BOOLEAN — quirk of this package.
* `count = -1` means "replace all occurrences from `startIndex`".
* For regex, remember JSON needs backslashes escaped twice
  (`"^(.*[\\\\\\/])"` matches `^(.*[\\\/])`).

### randomString

```json
{ "commandName": "randomString", "packageName": "String",
  "attributes": [
    { "name": "randomStringLength", "value": { "type": "NUMBER", "number": "3" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strRND" } }
```

### find

```json
{ "commandName": "find", "packageName": "String",
  "attributes": [
    { "name": "sourceString",       "value": { "type": "STRING", "expression": "$strPersonName$" } },
    { "name": "find",               "value": { "type": "STRING", "string": "Kovacs" } },
    { "name": "isCaseSensitive",    "value": { "type": "STRING", "string": "true" } },
    { "name": "isRegularExpression","value": { "type": "STRING", "string": "false" } },
    { "name": "startIndex",         "value": { "type": "NUMBER", "number": "1" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrPosKovacs" } }
```

Returns the 1-based index of the match, or 0 if not found. Like `replace`,
`isCaseSensitive` / `isRegularExpression` are **string** booleans.

### subString

```json
{ "commandName": "subString", "packageName": "String",
  "attributes": [
    { "name": "sourceString",              "value": { "type": "STRING", "expression": "$strPath$" } },
    { "name": "startIndex",                "value": { "type": "NUMBER", "number": "1" } },
    { "name": "subStringLength",           "value": { "type": "NUMBER", "number": "5" } },
    { "name": "returnBlankIfRangeNotFound","value": { "type": "BOOLEAN", "boolean": true } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strChunk" } }
```

### split (→ LIST)

```json
{ "commandName": "split", "packageName": "String",
  "attributes": [
    { "name": "sourceString",    "value": { "type": "STRING", "expression": "$strGroupName$" } },
    { "name": "delimiter",       "value": { "type": "STRING", "string": "|" } },
    { "name": "isCaseSensitive", "value": { "type": "STRING", "string": "false" } },
    { "name": "substrings",      "value": { "type": "STRING", "string": "ALL" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "lstResult" } }
```

`substrings`: `ALL` | a number cap on how many pieces to return.

### beforeAfter

Extract the text before and/or after marker string(s):

```json
{ "commandName": "beforeAfter", "packageName": "String",
  "attributes": [
    { "name": "sourceString",                 "value": { "type": "STRING", "expression": "$strFileName$" } },
    { "name": "getCharacters",                "value": { "type": "STRING", "string": "BEFOREAFTER" } },
    { "name": "beforeStringInBeforeAfter",    "value": { "type": "STRING", "string": "gg" } },
    { "name": "beforeOccurrenceInBeforeAfter","value": { "type": "NUMBER", "number": "1" } },
    { "name": "beforeAfterCondition",         "value": { "type": "STRING", "string": "AND" } },
    { "name": "afterStringInBeforeAfter",     "value": { "type": "STRING", "string": "ff" } },
    { "name": "afterOccurrenceInBeforeAfter", "value": { "type": "NUMBER", "number": "1" } },
    { "name": "ifNoMatchFound",               "value": { "type": "STRING", "string": "SOURCE" } },
    { "name": "noOfCharsToGet",               "value": { "type": "STRING", "string": "ALL" } },
    { "name": "isCaseSensitive",              "value": { "type": "STRING", "string": "true" } },
    { "name": "trimSpaces",                   "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "removeEnter",                  "value": { "type": "BOOLEAN", "boolean": true } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strExtracted" } }
```

`getCharacters`: `BEFORE` | `AFTER` | `BEFOREAFTER`.
`ifNoMatchFound`: `SOURCE` (return the whole input) | `BLANK`.

### compare / uppercase / lowercase / toNumber

```json
{ "commandName": "compare", "packageName": "String",
  "attributes": [
    { "name": "sourceString",    "value": { "type": "STRING", "expression": "$strFileName$" } },
    { "name": "stringToCompare", "value": { "type": "STRING", "expression": "$strExtension$" } },
    { "name": "matchCase",       "value": { "type": "STRING", "string": "false" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "blnEqual" } }

{ "commandName": "uppercase", "packageName": "String",
  "attributes": [ { "name": "sourceString", "value": { "type": "STRING", "expression": "$strUser$" } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "strUser" } }

{ "commandName": "toNumber", "packageName": "String",
  "attributes": [ { "name": "sourceString", "value": { "type": "STRING", "expression": "$strDay$" } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrDay" } }
```

`lowercase` and `reverse` share the single-`sourceString` shape of `uppercase`.
`toBoolean` is identical to `toNumber` but returns a Boolean.

### toLocaleNumber

Parse a numeric string using a specific locale's grouping/decimal rules:

```json
{ "commandName": "toLocaleNumber", "packageName": "String",
  "attributes": [
    { "name": "sourceString", "value": { "type": "STRING", "expression": "$strAmount$" } },
    { "name": "localeFormat", "value": { "type": "STRING", "string": "SPECIFIC" } },
    { "name": "locale",       "value": { "type": "STRING", "string": "en-US" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrAmount" } }
```

`localeFormat`: `SPECIFIC` (use `locale`) | `SYSTEM` (runner's locale).

---

## 2. Number — arithmetic & formatting

`packageName: "Number"`.

| Command          | Purpose                                       |
|------------------|-----------------------------------------------|
| `assignToNumber` | Assign a numeric literal / expression         |
| `increment`      | `x = x + by`                                  |
| `decrement`      | `x = x - by`                                  |
| `randomNumber`   | Random integer/decimal in a range             |
| `toString`       | Format a number as a string (digits control)  |

### assignToNumber

```json
{ "commandName": "assignToNumber", "packageName": "Number",
  "attributes": [
    { "name": "input", "value": { "type": "NUMBER", "number": "3" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrRetryThreshold" } }
```

### decrement (increment is symmetric)

```json
{ "commandName": "decrement", "packageName": "Number",
  "attributes": [
    { "name": "source", "value": { "type": "NUMBER", "expression": "$nUserNameCharacterLength$" } },
    { "name": "by",     "value": { "type": "NUMBER", "number": "1" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nUserNameCharacterLength" } }
```

### randomNumber

```json
{ "commandName": "randomNumber", "packageName": "Number",
  "attributes": [
    { "name": "fromVal", "value": { "type": "NUMBER", "number": "100" } },
    { "name": "toVal",   "value": { "type": "NUMBER", "number": "900" } },
    { "name": "isRequiredPrecision", "value": { "type": "BOOLEAN", "boolean": false } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nRandom" } }
```

### toString

```json
{ "commandName": "toString", "packageName": "Number",
  "attributes": [
    { "name": "input",           "value": { "type": "NUMBER", "expression": "$nRandom$" } },
    { "name": "numFormatDigits", "value": { "type": "NUMBER", "number": "0" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "vRandom" } }
```

Inline expression alternative (no node needed):
`$nRandom.Number:toString$` – see SKILL.md §4.1.

---

## 3. Boolean

`packageName: "Boolean"`.

### assign

```json
{ "commandName": "assign", "packageName": "Boolean",
  "attributes": [
    { "name": "source",      "value": { "type": "STRING", "string": "constant" } },
    { "name": "userDefined", "value": { "type": "STRING", "string": "false" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "blnSuccess" } }
```

Notes:
* `source = "constant"` + `userDefined = "true"|"false"` is the literal form.
* `source = "variable"` binds another Boolean variable's value.
* Both `source` and `userDefined` are strings, not booleans — legacy design.

Other commands: `compareTo` / `equalTo` (compare two booleans), `invert`
(logical NOT), `toNumber`, `toString`.

### invert / compareTo

```json
{ "commandName": "invert", "packageName": "Boolean",
  "attributes": [ { "name": "source", "value": { "type": "BOOLEAN", "expression": "$blnSuccess$" } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "blnSuccess" } }

{ "commandName": "compareTo", "packageName": "Boolean",
  "attributes": [
    { "name": "source",      "value": { "type": "VARIABLE", "variableName": "blnSuccess" } },
    { "name": "checkSource", "value": { "type": "VARIABLE", "variableName": "blnIsTen" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nBooleanCompare" } }
```

`compareTo` returns a Number (`0` when equal); `equalTo` (same attributes)
returns a Boolean.

---

## 4. Datetime

`packageName: "Datetime"`.

| Command                  | Purpose                                                    |
|--------------------------|------------------------------------------------------------|
| `assign`                 | Build a datetime from a string constant or `System:Date`, using a preset or custom format |
| `toString`               | Format a datetime as a string (preset or custom pattern)   |
| `add` / `subtract`       | Add/subtract a number of time units                        |
| `get`                    | Extract a component (day-of-year, month, hour, …)          |
| `differenceBetweenDates` | Difference between two datetimes in a chosen unit          |
| `isAfter` / `isBefore`   | Compare two datetimes → Boolean                            |
| `isLeapYear`             | Whether the source year is a leap year → Boolean           |

### assign (from constant + pre-built format)

```json
{ "commandName": "assign", "packageName": "Datetime",
  "attributes": [
    { "name": "option",         "value": { "type": "STRING", "string": "constant" } },
    { "name": "source",         "value": { "type": "STRING", "string": "2022-02-03" } },
    { "name": "formatType",     "value": { "type": "STRING", "string": "preBuilt" } },
    { "name": "preBuiltFormat", "value": { "type": "STRING", "string": "ISO_LOCAL_DATE" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "vDatTime" } }
```

`option`: `"constant"` | `"variable"`
`formatType`: `"preBuilt"` | `"custom"`
Common `preBuiltFormat`: `ISO_LOCAL_DATE`, `ISO_LOCAL_DATE_TIME`,
`ISO_ZONED_DATE_TIME`, `ISO_WEEK_DATE`, `BASIC_ISO_DATE`, `RFC_1123_DATE_TIME`.

### toString

Two variants seen in the wild — **custom pattern** (from `COMMON_logger`):

```json
{ "commandName": "toString", "packageName": "Datetime",
  "attributes": [
    { "name": "source",        "value": { "type": "DATETIME", "expression": "$System:Date$" } },
    { "name": "selectPattern", "value": { "type": "STRING", "string": "CUSTOM" } },
    { "name": "patternInput",  "value": { "type": "STRING", "string": "MM-dd-yyyy_HH-mm-ss" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strCurrentTime" } }
```

… and **pre-built pattern** (from `SKILL_examples`):

```json
{ "commandName": "toString", "packageName": "Datetime",
  "attributes": [
    { "name": "source",           "value": { "type": "DATETIME", "expression": "$vDatTime$" } },
    { "name": "selectPattern",    "value": { "type": "STRING", "string": "PREBUILT" } },
    { "name": "preBuiltPattern",  "value": { "type": "STRING", "string": "ISO_WEEK_DATE" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "vIsoWeekDate" } }
```

### add / subtract

```json
{ "commandName": "add", "packageName": "Datetime",
  "attributes": [
    { "name": "source", "value": { "type": "DATETIME", "expression": "$System:Date$" } },
    { "name": "val",    "value": { "type": "NUMBER", "number": "2" } },
    { "name": "unit",   "value": { "type": "STRING", "string": "DAYS" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "dtDayAfterTomorrow" } }
```

`unit`: `SECONDS` | `MINUTES` | `HOURS` | `DAYS` | `WEEKS` | `MONTHS` | `YEARS`.
`subtract` is identical with the sign reversed.

### get / differenceBetweenDates

```json
{ "commandName": "get", "packageName": "Datetime",
  "attributes": [
    { "name": "source",     "value": { "type": "DATETIME", "expression": "$dtDayAfterTomorrow$" } },
    { "name": "getOptions", "value": { "type": "STRING", "string": "DAYOFYEAR" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrDayOfY" } }

{ "commandName": "differenceBetweenDates", "packageName": "Datetime",
  "attributes": [
    { "name": "source", "value": { "type": "DATETIME", "expression": "$dtDayAfterTomorrow$" } },
    { "name": "target", "value": { "type": "DATETIME", "expression": "$dtOneDate$" } },
    { "name": "unit",   "value": { "type": "STRING", "string": "SECONDS" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrDiffDate" } }
```

`getOptions`: `DAYOFYEAR`, `DAYOFMONTH`, `DAYOFWEEK`, `MONTH`, `YEAR`, `HOUR`,
`MINUTE`, `SECOND`, … (returns a Number).

### isAfter / isBefore / isLeapYear

```json
{ "commandName": "isAfter", "packageName": "Datetime",
  "attributes": [
    { "name": "source", "value": { "type": "DATETIME", "expression": "$System:Date$" } },
    { "name": "other",  "value": { "type": "DATETIME", "expression": "$dtDayAfterTomorrow$" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "blnLater" } }

{ "commandName": "isLeapYear", "packageName": "Datetime",
  "attributes": [ { "name": "source", "value": { "type": "DATETIME", "expression": "$System:Date$" } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "blnLeap" } }
```

`isBefore` mirrors `isAfter`. All three return a Boolean.

---

## 5. System

`packageName: "System"`. Reads environment/machine info and runs OS actions.

| Command             | Purpose                                             |
|---------------------|-----------------------------------------------------|
| `systemInformation` | Read a system variable (`USERNAME`, `Machine`, …)   |
| `lock`              | Lock the workstation                                |
| `logoff`            | Log off current user                                |
| `restart`          | Restart the machine                                 |
| `shutdown`          | Shutdown the machine                                |

### systemInformation

```json
{ "commandName": "systemInformation", "packageName": "System",
  "attributes": [
    { "name": "variableOption",   "value": { "type": "STRING", "string": "BY_TEXT" } },
    { "name": "systemNameByText", "value": { "type": "STRING", "string": "USERNAME" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strUsername" } }
```

Common `systemNameByText`: `USERNAME`, `Machine`, `PROCESSOR`, `OSNAME`,
`WINDOWSDIR`, `TEMPDIR`, plus system dictionary members reachable via
`$System:Machine$`, `$System:Date$`, `$System:AATaskName$` (see SKILL.md §4.1).

### lock / logoff / restart / shutdown

All take **no attributes**:

```json
{ "commandName": "lock",    "packageName": "System" }
{ "commandName": "logoff",  "packageName": "System" }
{ "commandName": "restart", "packageName": "System" }
{ "commandName": "shutdown","packageName": "System" }
```

⚠ Guardrail: `logoff` / `restart` / `shutdown` affect the whole runner
machine. Wrap in an explicit `if` and never emit them unattended without
confirmation. `lock` is comparatively safe (locks the session only).

---

## 6. Folder

`packageName: "Folder"`.

### createFolder

```json
{ "commandName": "createFolder", "packageName": "Folder",
  "attributes": [
    { "name": "folderPath",  "value": { "type": "STRING", "string": "C:\\temp" } },
    { "name": "isOverwrite", "value": { "type": "BOOLEAN", "boolean": false } }
  ] }
```

Notes:
* Other Folder commands (`deleteFolder` / `copyFolder` / `renameFolder` /
  `openFolder`) follow the same shape with `folderPath` /
  `destinationFolderPath` / `newFolderName`, plus optional `isDate` / `isSize`
  filters.
* Existence checks are done via the `If → folderExists / folderDoesNotExists`
  conditional (see SKILL.md §2.5).

### zipFiles / unzipFiles

```json
{ "commandName": "zipFiles", "packageName": "Folder",
  "attributes": [
    { "name": "sourcePath",            "value": { "type": "STRING", "string": "C:\\temp" } },
    { "name": "filterType",            "value": { "type": "STRING", "string": "StringValue" } },
    { "name": "filterExtensions",      "value": { "type": "STRING", "string": "*.doc" } },
    { "name": "targetPath",            "value": { "type": "FILE", "string": "file:///C:/temp/kesz.zip" } },
    { "name": "isUpdateNewer",         "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "isDeleteOriginalFiles", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "compressionLevel",      "value": { "type": "STRING", "string": "Superfast" } }
  ] }

{ "commandName": "unzipFiles", "packageName": "Folder",
  "attributes": [
    { "name": "sourcePath",  "value": { "type": "FILE", "string": "file:///C:/temp/kesz.zip" } },
    { "name": "targetPath",  "value": { "type": "STRING", "string": "C:\\unzipped" } },
    { "name": "isOverwrite", "value": { "type": "BOOLEAN", "boolean": false } }
  ] }
```

`filterType`: `AllFiles` | `StringValue` (then `filterExtensions`, wildcards
allowed). `compressionLevel`: `Superfast` | `Fast` | `Normal` | `Maximum`.

---

## 7. TextFile

`packageName: "TextFile"`. Read/write text without opening Notepad.

### ReadFile

```json
{ "commandName": "ReadFile", "packageName": "TextFile",
  "attributes": [
    { "name": "filePath",         "value": { "type": "FILE", "string": "file:///C:/temp/file.txt" } },
    { "name": "encoding",         "value": { "type": "STRING", "string": "UTF-8-WITHOUT-BOM" } },
    { "name": "trimLeadingSpace", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "trimTrailingSpace","value": { "type": "BOOLEAN", "boolean": false } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "vReadText" } }
```

Common `encoding`: `ANSI`, `UTF-8`, `UTF-8-WITHOUT-BOM`, `UTF-16`.

---

## 8. LogToFile

`packageName: "LogToFile"`. Append/overwrite a text file — the workhorse of
the `COMMON_logger` bot.

### logToFile

```json
{ "commandName": "logToFile", "packageName": "LogToFile",
  "attributes": [
    { "name": "filePath",        "value": { "type": "FILE", "expression": "file://$strLogFilePath$" } },
    { "name": "logContent",      "value": { "type": "STRING", "expression": "$strBotID$ - $strLogMessage$" } },
    { "name": "appendTimestamp", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "logOption",       "value": { "type": "STRING", "string": "APPEND_FILE" } },
    { "name": "encodingValue",   "value": { "type": "STRING", "string": "ANSI" } }
  ] }
```

`logOption`: `APPEND_FILE` | `OVERWRITE_FILE`.

### logVariablesToFile

Dumps a set of named variables (and their values) to the file in one call —
handy for debug snapshots:

```json
{ "commandName": "logVariablesToFile", "packageName": "LogToFile",
  "attributes": [
    { "name": "filePath",        "value": { "type": "FILE", "string": "file:///C:/temp/log.txt" } },
    { "name": "logOption",       "value": { "type": "STRING", "string": "APPEND_FILE" } },
    { "name": "appendTimestamp", "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "variables",
      "value": { "type": "VARIABLEMAP",
        "variableMapNames": [ "strFileName", "nbrListSize", "strPersonName" ] } }
  ] }
```

The `variables` attribute is a special `VARIABLEMAP` value whose
`variableMapNames` array lists the (lowercased) variable names to log.

---

## 9. Screen

`packageName: "Screen"`. Screenshots.

### captureDesktop

```json
{ "commandName": "captureDesktop", "packageName": "Screen",
  "attributes": [
    { "name": "filePath",        "value": { "type": "FILE", "expression": "file://$strScreenshotFile$" } },
    { "name": "isOverwriteFile", "value": { "type": "BOOLEAN", "boolean": false } }
  ] }
```

Sibling: `captureWindow` (same shape + `window` attribute).

---

## 10. List

`packageName: "List"`.

### addItem

```json
{ "commandName": "addItem", "packageName": "List",
  "attributes": [
    { "name": "sourceList",   "value": { "type": "VARIABLE", "variableName": "lstAttachments" } },
    { "name": "listItem",     "value": { "type": "VARIABLE", "variableName": "fileScreenshot" } },
    { "name": "itemPosition", "value": { "type": "STRING", "string": "END" } }
  ] }
```

`itemPosition`: `END` | `START` | `BEFORE_INDEX` | `AFTER_INDEX` (with extra
`positionNumber` attribute).

| Command             | Purpose                                          |
|---------------------|--------------------------------------------------|
| `addItem`           | Append/insert an item                            |
| `get`               | Read item at a 1-based position                  |
| `listSet`           | Replace item at a position                       |
| `listRemove`        | Remove item at a position                        |
| `listSize`          | Item count → Number                              |
| `joinList`          | Concatenate to a string with a delimiter         |
| `assign`            | Copy another list                                |
| `assignToDataTable` | Push the list into a TABLE column                |
| `clear`             | Empty the list                                   |

### get / listSize / joinList

```json
{ "commandName": "get", "packageName": "List",
  "attributes": [
    { "name": "sourceList",         "value": { "type": "VARIABLE", "variableName": "lstResult" } },
    { "name": "itemPositionNumber", "value": { "type": "NUMBER", "number": "1" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strPersonName" } }

{ "commandName": "listSize", "packageName": "List",
  "attributes": [ { "name": "sourceList", "value": { "type": "VARIABLE", "variableName": "lstResult" } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrListSize" } }

{ "commandName": "joinList", "packageName": "List",
  "attributes": [
    { "name": "sourceList", "value": { "type": "VARIABLE", "variableName": "lstResult" } },
    { "name": "delimiter",  "value": { "type": "STRING", "string": "," } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strJoined" } }
```

### assignToDataTable

```json
{ "commandName": "assignToDataTable", "packageName": "List",
  "attributes": [
    { "name": "sourceList",       "value": { "type": "VARIABLE", "variableName": "lstResult" } },
    { "name": "toTable",          "value": { "type": "VARIABLE", "variableName": "tblNames" } },
    { "name": "positionSelected", "value": { "type": "STRING", "string": "firstPosition" } }
  ] }
```

Sibling operations (`listRemove`, `listSet`, `clear`, `assign`) follow the same
`sourceList` + position idiom.

---

## 11. CsvTxt — flat-file parsing

`packageName: "CsvTxt"`. Session-based (see §0.1).

| Command         | Purpose                                          |
|-----------------|--------------------------------------------------|
| `OpenCSVTXT`    | Open a CSV / TXT file for row-by-row access     |
| `ReadFromCsvTxt`| Read the whole file into a TABLE variable       |
| `CloseCsvTxt`   | Close the session                                |

### OpenCSVTXT

```json
{ "commandName": "OpenCSVTXT", "packageName": "CsvTxt",
  "attributes": [
    { "name": "session",          "value": { "type": "STRING", "string": "Default" } },
    { "name": "filePath",         "value": { "type": "FILE", "string": "file:///c:/temp/file.csv" } },
    { "name": "containsHeader",   "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "delimeter",        "value": { "type": "STRING", "string": "comma" } },
    { "name": "trimLeadingSpace", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "trimTrailingSpace","value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "encoding",         "value": { "type": "STRING", "string": "UTF-8" } }
  ] }
```

`delimeter` (sic, note spelling): `comma` | `tab` | `semicolon` | `pipe` | `custom`.

Iteration idiom — combine with `Loop` (see SKILL.md §2.6). The loop iterator
`loop.iterators.forEachRowInCSVTXT` yields a `RECORD` (row); field access is
`$rec{columnName}$` if a header was declared, otherwise `$rec[1]$` by index.

### ReadFromCsvTxt / CloseCsvTxt

```json
{ "commandName": "ReadFromCsvTxt", "packageName": "CsvTxt",
  "attributes": [ { "name": "session", "value": { "type": "STRING", "string": "Default" } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "TableFromCSV" } }

{ "commandName": "CloseCsvTxt", "packageName": "CsvTxt",
  "attributes": [ { "name": "session", "value": { "type": "STRING", "string": "Default" } } ] }
```

---

## 12. Excel_MS — Microsoft Excel

`packageName: "Excel_MS"`. Requires the desktop Excel application on the
runner. Session-based.

| Command                    | Purpose                                       |
|----------------------------|-----------------------------------------------|
| `OpenSpreadsheet`          | Open a workbook (returns SESSION)             |
| `SwitchToSheet`            | Change active sheet (by index / by name)      |
| `GoToCell`                 | Move active cell                              |
| `SetCell` / `GetSingleCell`| Write / read a single cell                    |
| `ReadExcelColumn` / `readExcelRow` | Read a column / row into a LIST       |
| `getWorksheetAsDataTable`  | Read the whole sheet into a TABLE             |
| `writeDataTableToWorksheet`| Write a TABLE into a sheet                    |
| `SetCellFormula` / `ReadCellFormula` | Put / read a cell formula           |
| `find` / `Replace`         | Search / search-and-replace                   |
| `GetCellColor`             | Read a cell's fill/font color                 |
| `SortTableV2` / `FilterTableV2` | Sort / filter a range or table           |
| `CreateWorksheet` / `renameWorksheet` / `DeleteSpreadsheet` | Sheet lifecycle |
| `HideWorksheet` / `UnhideWorksheet` / `ProtectWorksheet` / `ProtectWorkbook` | Visibility & protection |
| `ConvertToPDF`             | Export the workbook/sheet to PDF              |
| `SaveAs` / `SaveSpreadSheet`| Save under a new / same path                 |
| `removeBlankRows`          | Compact the sheet                             |
| `getNumberOfRows` / `RetrieveSheetsCount` / `getWorksheetNames` | Metadata |
| `CloseSpreadsheet`         | Save & close                                  |

There are ~50 commands in this package; the shapes below are representative.
All take a `session` attribute (§0.1). Boolean-ish flags are sometimes real
`BOOLEAN` and sometimes string `"true"`/`"false"` depending on the command —
copy the exact shape from a working bot.

### OpenSpreadsheet

```json
{ "commandName": "OpenSpreadsheet", "packageName": "Excel_MS",
  "attributes": [
    { "name": "excelSourceOption", "value": { "type": "STRING", "string": "desktopfilepath" } },
    { "name": "filePath",          "value": { "type": "FILE",   "string": "repository:///Automation%20Anywhere/…/ConfigFileFINACR001.xlsx" } },
    { "name": "containsHeader",    "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "isSpecificSheet",   "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "fileAccessMode",    "value": { "type": "STRING", "string": "READ_ONLY" } },
    { "name": "isSecure",          "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "loadAddIns",        "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "excludeHiddenSheets","value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "containsChart",     "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "setSensitivity",    "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "disableUpdateLinks","value": { "type": "BOOLEAN", "boolean": false } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "sessionVariable" } }
```

`excelSourceOption`: `desktopfilepath` | `controlRoomFile` | `existingSession`.
`fileAccessMode`: `READ_ONLY` | `READ_WRITE`.

### GoToCell

```json
{ "commandName": "GoToCell", "packageName": "Excel_MS",
  "attributes": [
    { "name": "cellOption", "value": { "type": "STRING", "string": "SpecificCell" } },
    { "name": "cell",       "value": { "type": "STRING", "string": "B2" } },
    { "name": "session",    "value": { "type": "SESSION", "expression": "$sessionVariable$" } }
  ] }
```

`cellOption`: `SpecificCell` | `ActiveCell` | `LastCellInColumn` |
`LastCellInRow` | `NextEmptyCellInColumn` | `NextEmptyCellInRow`.

### ReadExcelColumn

```json
{ "commandName": "ReadExcelColumn", "packageName": "Excel_MS",
  "attributes": [
    { "name": "activeCell",     "value": { "type": "STRING", "string": "true" } },
    { "name": "readFullColumn", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "readOption",     "value": { "type": "STRING", "string": "READ_CELL_TEXT" } },
    { "name": "session",        "value": { "type": "SESSION", "expression": "$sessionVariable$" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "ExcelColumnData" } }
```

`readOption`: `READ_CELL_TEXT` (rendered value) | `READ_CELL_FORMULA`.

### SetCellFormula

```json
{ "commandName": "SetCellFormula", "packageName": "Excel_MS",
  "attributes": [
    { "name": "activeCell",         "value": { "type": "STRING", "string": "false" } },
    { "name": "cellAddress",        "value": { "type": "STRING", "string": "A1" } },
    { "name": "cellFormulaToApply", "value": { "type": "STRING", "string": "=VLOOKUP(A2,B:B,1,0)" } },
    { "name": "session",            "value": { "type": "SESSION", "expression": "$sessionVariable$" } }
  ] }
```

### writeDataTableToWorksheet

```json
{ "commandName": "writeDataTableToWorksheet", "packageName": "Excel_MS",
  "attributes": [
    { "name": "tableObj",           "value": { "type": "VARIABLE", "variableName": "TableFromCSV" } },
    { "name": "sheetSelection",     "value": { "type": "STRING", "string": "ActiveWorksheet" } },
    { "name": "firstCellAddress",   "value": { "type": "STRING", "string": "A1" } },
    { "name": "isRetainCellFormat", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "session",            "value": { "type": "SESSION", "expression": "$sessionVariable$" } }
  ] }
```

### SwitchToSheet

```json
{ "commandName": "SwitchToSheet", "packageName": "Excel_MS",
  "attributes": [
    { "name": "sheetOption", "value": { "type": "STRING", "string": "BYINDEX" } },
    { "name": "sheetIndex",  "value": { "type": "NUMBER", "number": "2" } },
    { "name": "session",     "value": { "type": "SESSION", "expression": "$sessionVariable$" } }
  ] }
```

`sheetOption`: `BYINDEX` | `BYNAME` (then use `sheetName`).

### removeBlankRows / CloseSpreadsheet

```json
{ "commandName": "removeBlankRows", "packageName": "Excel_MS",
  "attributes": [
    { "name": "fromBeginningOfTheSheet","value": { "type": "STRING", "string": "BeginningOfSheet" } },
    { "name": "toEndOfTheFilledSheet",  "value": { "type": "STRING", "string": "EndOfSheet" } },
    { "name": "session", "value": { "type": "SESSION",
                                    "sessionName": { "type": "STRING", "string": "Default" } } }
  ] }

{ "commandName": "CloseSpreadsheet", "packageName": "Excel_MS",
  "attributes": [
    { "name": "session",               "value": { "type": "SESSION", "expression": "$sessionVariable$" } },
    { "name": "isSave",                "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "isDisplayErrorEnabled", "value": { "type": "BOOLEAN", "boolean": false } }
  ] }
```

### GetCellColor

```json
{ "commandName": "GetCellColor", "packageName": "Excel_MS",
  "attributes": [
    { "name": "cellColorOption", "value": { "type": "STRING", "string": "true" } },
    { "name": "cellOption",      "value": { "type": "STRING", "string": "false" } },
    { "name": "cellAddress",     "value": { "type": "STRING", "string": "A10" } },
    { "name": "session",         "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Default" } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "ExcelCellColor" } }
```

### SortTableV2

```json
{ "commandName": "SortTableV2", "packageName": "Excel_MS",
  "attributes": [
    { "name": "sortOption",            "value": { "type": "STRING", "string": "SortWorksheet" } },
    { "name": "worksheetName",         "value": { "type": "STRING", "string": "Servers" } },
    { "name": "columnOption",          "value": { "type": "STRING", "string": "ColumnName" } },
    { "name": "worksheetColumnName",   "value": { "type": "STRING", "string": "Name" } },
    { "name": "applySortOnColumnName", "value": { "type": "STRING", "string": "true" } },
    { "name": "hasHeader",             "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "sortBy",                "value": { "type": "STRING", "string": "SortByNumber" } },
    { "name": "numberSortOrder",       "value": { "type": "STRING", "string": "Smallest to largest" } },
    { "name": "session",               "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Default" } } }
  ] }
```

`sortOption`: `SortWorksheet` | `SortTable`. `sortBy`: `SortByText` |
`SortByNumber`. `numberSortOrder`: `Smallest to largest` | `Largest to smallest`.

### ConvertToPDF

```json
{ "commandName": "ConvertToPDF", "packageName": "Excel_MS",
  "attributes": [
    { "name": "convertSheetType",    "value": { "type": "STRING", "string": "ENTIRE_EXCEL" } },
    { "name": "fileStorageLocation", "value": { "type": "FILE", "string": "file:///C:/temp/out.pdf" } },
    { "name": "pdfFileName",         "value": { "type": "STRING", "string": "" } },
    { "name": "overwriteFile",       "value": { "type": "STRING", "string": "OVERWRITE" } },
    { "name": "session",             "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Default" } } }
  ] }
```

`convertSheetType`: `ENTIRE_EXCEL` | `ACTIVE_SHEET` | `SPECIFIC_SHEET`.

### ProtectWorksheet

Every `allow*` flag toggles one permission on the protected sheet; `password`
is the unlock secret (use a `CREDENTIAL` in real bots):

```json
{ "commandName": "ProtectWorksheet", "packageName": "Excel_MS",
  "attributes": [
    { "name": "password",               "value": { "type": "STRING", "string": "AAAA1" } },
    { "name": "allowFormattingCells",   "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "allowInsertingRows",     "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "allowDeletingRows",      "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "allowSorting",           "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "allowFiltering",         "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "session",                "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Default" } } }
  ] }
```

(Full set also includes `allowFormattingColumns`, `allowFormattingRows`,
`allowInsertingColumns`, `allowInsertingHyperlinks`, `allowDeletingColumns`,
`allowUsingPivotTables`, `drawingObjects`, `scenarios`.) Companion commands:
`ProtectWorkbook`, `UnprotectWorkbook`, `HideWorksheet`, `UnhideWorksheet`.

### getWorksheetAsDataTable

```json
{ "commandName": "getWorksheetAsDataTable", "packageName": "Excel_MS",
  "attributes": [
    { "name": "containsHeader", "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "readOption",     "value": { "type": "STRING", "string": "READ_CELL_TEXT" } },
    { "name": "sheetSelection", "value": { "type": "STRING", "string": "ActiveWorksheet" } },
    { "name": "session",        "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Default" } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "tblSheet" } }
```

---

## 13. Email — legacy SMTP / Outlook client

`packageName: "Email"`. Two modes: **sessionless sends** (`SendMailV2`,
`ForwardEmailV2`, `ReplyAllEmail` — each is self-contained) and a
**session-based read/manage flow** (`emailConnect` → work with the mailbox →
`closeEmail`). Prefer *Microsoft 365 Outlook* (§14) for Graph-API sending.

| Command              | Purpose                                        |
|----------------------|------------------------------------------------|
| `SendMailV2`         | Send a new message                             |
| `ForwardEmailV2`     | Forward the current message                    |
| `ReplyAllEmail`      | Reply-all to the current message               |
| `emailConnect`       | Open a POP3/IMAP/EWS mailbox session           |
| `saveAllAtatchments` | Save every attachment in a folder to disk*     |
| `saveAttachment`     | Save one attachment                            |
| `SaveEmailV2`        | Save a message to a file                       |
| `changeStatus`       | Mark current message read/unread               |
| `move`               | Move the current message to a folder           |
| `checkFolder`        | Test whether a mailbox folder exists           |
| `closeEmail`         | Close the mailbox session                      |

\* `saveAllAtatchments` — the misspelling is the real command name in the package.

### SendMailV2

```json
{ "commandName": "SendMailV2", "packageName": "Email",
  "attributes": [
    { "name": "toAddress",             "value": { "type": "STRING", "string": "support@support.hu" } },
    { "name": "cc",                    "value": { "type": "STRING", "string": "" } },
    { "name": "bcc",                   "value": { "type": "STRING", "string": "valaki@valalki.hu" } },
    { "name": "replyTO",               "value": { "type": "STRING", "string": "" } },
    { "name": "invalidAddress",        "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "importance",            "value": { "type": "STRING", "string": "Normal" } },
    { "name": "subject",               "value": { "type": "STRING", "string": "Hey, this is exists" } },
    { "name": "fileList",              "value": { "type": "LIST",
                                                  "list": [ { "type": "FILE", "string": "file:///C:/temp/file.csv" } ] } },
    { "name": "ensureAttachmentsExist","value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "bodyFormat",            "value": { "type": "STRING", "string": "PLAINTEXT" } },
    { "name": "message",               "value": { "type": "STRING", "string": "This is the message body" } },
    { "name": "goGreen",               "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "serverType",            "value": { "type": "STRING", "string": "OUTLOOK" } }
  ] }
```

`importance`: `Low` | `Normal` | `High`.
`bodyFormat`: `PLAINTEXT` | `HTMLCODE`.
`serverType`: `OUTLOOK` (uses local Outlook profile) | `EWS` | `SMTP`.

### ForwardEmailV2 / ReplyAllEmail

Same sessionless-send shape as `SendMailV2`, operating on the *current*
message. `ForwardEmailV2` takes `toAddress`; `ReplyAllEmail` replaces it with
`excludeSender` (BOOLEAN) and adds `subject`:

```json
{ "commandName": "ForwardEmailV2", "packageName": "Email",
  "attributes": [
    { "name": "toAddress",  "value": { "type": "STRING", "string": "info@own.hu" } },
    { "name": "cc",         "value": { "type": "STRING", "string": "" } },
    { "name": "bcc",        "value": { "type": "STRING", "string": "someone@example.com" } },
    { "name": "importance", "value": { "type": "STRING", "string": "High" } },
    { "name": "bodyFormat", "value": { "type": "STRING", "string": "PLAINTEXT" } },
    { "name": "message",    "value": { "type": "STRING", "string": "Here it is" } },
    { "name": "goGreen",    "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "serverType", "value": { "type": "STRING", "string": "OUTLOOK" } }
  ] }
```

### emailConnect

Opens a mailbox session for the read/manage commands. `session` is a **string
name** (not a returned SESSION variable) reused by the other commands via
`sessionName`.

```json
{ "commandName": "emailConnect", "packageName": "Email",
  "attributes": [
    { "name": "session",                     "value": { "type": "STRING", "string": "EmailSession" } },
    { "name": "serverType",                  "value": { "type": "STRING", "string": "EMAIL_SERVER" } },
    { "name": "useSecure",                   "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "serverHost",                  "value": { "type": "STRING", "string": "smtp://smtp.corning.com" } },
    { "name": "port",                        "value": { "type": "NUMBER", "number": "25" } },
    { "name": "protocol",                    "value": { "type": "STRING", "string": "POP3" } },
    { "name": "emailServerAuthType",         "value": { "type": "STRING", "string": "Basic" } },
    { "name": "username",                    "value": { "type": "STRING", "string": "admin" } },
    { "name": "securedPassword",             "value": { "type": "STRING", "string": "Aa1234" } },
    { "name": "emailServerConnectionTimeOut","value": { "type": "NUMBER", "number": "120" } }
  ] }
```

`protocol`: `POP3` | `IMAP` | `EWS`. ⚠ **Guardrail** — `securedPassword` is a
plaintext string in the raw capture; real bots MUST use a `CREDENTIAL` value
(SKILL.md §4.2).

### saveAllAtatchments / changeStatus / move / closeEmail

```json
{ "commandName": "saveAllAtatchments", "packageName": "Email",
  "attributes": [
    { "name": "sessionName",          "value": { "type": "STRING", "string": "EmailSession" } },
    { "name": "readStatus",           "value": { "type": "STRING", "string": "ALL" } },
    { "name": "enableStatusNoUpdate", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "folder",               "value": { "type": "STRING", "string": "Inbox" } },
    { "name": "folderPath",           "value": { "type": "STRING", "string": "C:\\temp" } },
    { "name": "checkOverrwrite",      "value": { "type": "BOOLEAN", "boolean": true } }
  ] }

{ "commandName": "changeStatus", "packageName": "Email",
  "attributes": [
    { "name": "sessionName",    "value": { "type": "STRING", "string": "EmailSession" } },
    { "name": "changeStatusTo", "value": { "type": "STRING", "string": "Read" } }
  ] }

{ "commandName": "move", "packageName": "Email",
  "attributes": [
    { "name": "sessionName", "value": { "type": "STRING", "string": "EmailSession" } },
    { "name": "folderPath",  "value": { "type": "STRING", "string": "Inbox" } }
  ] }

{ "commandName": "closeEmail", "packageName": "Email",
  "attributes": [ { "name": "session", "value": { "type": "STRING", "string": "EmailSession" } } ] }
```

`readStatus`: `ALL` | `READ` | `UNREAD`. `changeStatusTo`: `Read` | `Unread`.

---

## 14. Microsoft 365 Outlook — Graph-API mail

`packageName: "Microsoft 365 Outlook"`. Session-based. Auth is done through
the Credential Vault; the connection returns a `SESSION` variable.

| Command               | Purpose                                       |
|-----------------------|-----------------------------------------------|
| `Connect`             | Authenticate & open a session                 |
| `Send`                | Send a message                                |
| `ReplyAll`            | Reply-all to the current message              |
| `Forward`             | Forward the current message                   |
| `Move`                | Move the current message to a folder          |
| `MoveAll`             | Bulk-move messages matching a filter          |
| `DeleteAll`           | Bulk-delete messages matching a filter        |
| `SaveAllAttachments`  | Save attachments from matching messages       |
| `CheckIfFolderExists` | Test whether a mailbox folder exists → BOOLEAN|
| `Disconnect`          | Close the session                             |

The bulk commands (`MoveAll`, `DeleteAll`, `SaveAllAttachments`) filter by
`readStatus`/`emailStatus`, `subject`, `senders`, and (optionally) a
`receivedDateSince` DATETIME rather than acting on a single current message.

### Connect (client-credentials flow)

```json
{ "commandName": "Connect", "packageName": "Microsoft 365 Outlook",
  "attributes": [
    { "name": "azureCloud",         "value": { "type": "STRING", "string": "com" } },
    { "name": "authMode",           "value": { "type": "STRING", "string": "clientcred" } },
    { "name": "clientCredClientId", "value": { "type": "CREDENTIAL",
                                               "credential": { "name": "AZURE_CREDENTIALS_ATAWAY",
                                                               "lockerName": "Azure_Credentials_Ataway",
                                                               "attributeName": "CLIENT_ID" } } },
    { "name": "clientCredTenantId", "value": { "type": "CREDENTIAL",
                                               "credential": { "name": "AZURE_CREDENTIALS_ATAWAY",
                                                               "lockerName": "Azure_Credentials_Ataway",
                                                               "attributeName": "TENANT_ID" } } },
    { "name": "clientCredUsername", "value": { "type": "STRING", "expression": "$strFromEmail$" } },
    { "name": "clientCredSecret",   "value": { "type": "CREDENTIAL",
                                               "credential": { "name": "AZURE_CREDENTIALS_ATAWAY",
                                                               "lockerName": "Azure_Credentials_Ataway",
                                                               "attributeName": "CLIENT_SECRET" } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "ssnGraphAPI" } }
```

`authMode`: `clientcred` (app-only) | `userpassword` | `interactive`.

### Send

```json
{ "commandName": "Send", "packageName": "Microsoft 365 Outlook",
  "attributes": [
    { "name": "sessionName",           "value": { "type": "SESSION", "expression": "$ssnOutlook$" } },
    { "name": "from",                  "value": { "type": "STRING", "string": "" } },
    { "name": "toRecipients",          "value": { "type": "STRING", "expression": "$strSupportEmail$" } },
    { "name": "ccRecipients",          "value": { "type": "STRING", "string": "" } },
    { "name": "bccRecipients",         "value": { "type": "STRING", "string": "" } },
    { "name": "subject",               "value": { "type": "STRING", "expression": "$strBotID$ - ERROR - $strLogMessage$" } },
    { "name": "listOfAttachments",     "value": { "type": "LIST",   "expression": "$lstAttachments$" } },
    { "name": "ensureAttachmentsExist","value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "bodyFormat",            "value": { "type": "STRING", "string": "HTMLCODE" } },
    { "name": "htmlCodeMessage",       "value": { "type": "STRING", "expression": "<html>…$var$…</html>" } }
  ] }
```

Multiple recipients: comma- or semicolon-separated string; A360 accepts
both (the `COMMON_send_mail` bot normalizes `;`→`,` with `String.replace`
before sending).

### ReplyAll

`bodyFormat: "htmlEditor"` pairs with an `htmlEditorMessage` **dictionary**
(`{ "key": "html", "value": … }`) instead of a plain string; `fileList` is a
LIST of FILE values:

```json
{ "commandName": "ReplyAll", "packageName": "Microsoft 365 Outlook",
  "attributes": [
    { "name": "sessionName",       "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Microsoft365OutlookSession" } } },
    { "name": "from",              "value": { "type": "STRING", "string": "sender@sender.hu" } },
    { "name": "ccRecipients",      "value": { "type": "STRING", "string": "" } },
    { "name": "bccRecipients",     "value": { "type": "STRING", "expression": "$strUser$" } },
    { "name": "excludeSender",     "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "fileList",          "value": { "type": "LIST",
                                              "list": [ { "type": "FILE", "string": "file:///C:/temp/file1.xls" },
                                                        { "type": "FILE", "string": "file:///C:/temp/file2.xls" } ] } },
    { "name": "bodyFormat",        "value": { "type": "STRING", "string": "htmlEditor" } },
    { "name": "htmlEditorMessage", "value": { "type": "DICTIONARY",
                                              "dictionary": [ { "key": "html", "value": { "type": "STRING", "string": "<p>Hello!</p><p>See attached files.</p>" } } ] } }
  ] }
```

`bodyFormat`: `htmlEditor` (rich, uses `htmlEditorMessage` dict) | `HTMLCODE`
(raw, uses `htmlCodeMessage` string) | `plainText` (uses `message`).

### MoveAll / SaveAllAttachments

```json
{ "commandName": "MoveAll", "packageName": "Microsoft 365 Outlook",
  "attributes": [
    { "name": "sessionName",       "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Microsoft365OutlookSession" } } },
    { "name": "destinationFolder", "value": { "type": "STRING", "string": "Deleted Items" } },
    { "name": "readStatus",        "value": { "type": "STRING", "string": "UNREAD" } },
    { "name": "sourceFolder",      "value": { "type": "STRING", "string": "Inbox" } },
    { "name": "subject",           "value": { "type": "STRING", "string": "" } },
    { "name": "senders",           "value": { "type": "STRING", "string": "" } }
  ] }

{ "commandName": "SaveAllAttachments", "packageName": "Microsoft 365 Outlook",
  "attributes": [
    { "name": "sessionName",       "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Microsoft365OutlookSession" } } },
    { "name": "emailStatus",       "value": { "type": "STRING", "string": "ALL" } },
    { "name": "specificFolder",    "value": { "type": "STRING", "string": "Inbox" } },
    { "name": "subject",           "value": { "type": "STRING", "string": "" } },
    { "name": "senders",           "value": { "type": "STRING", "string": "" } },
    { "name": "receivedDateSince", "value": { "type": "VARIABLE", "variableName": "dtOneDate" } },
    { "name": "localFolderPath",   "value": { "type": "STRING", "string": "c:/temp" } },
    { "name": "overwrite",         "value": { "type": "BOOLEAN", "boolean": true } }
  ] }
```

`readStatus`/`emailStatus`: `ALL` | `READ` | `UNREAD`. Empty `subject`/`senders`
mean "no filter on that field".

### Disconnect

```json
{ "commandName": "Disconnect", "packageName": "Microsoft 365 Outlook",
  "attributes": [
    { "name": "sessionName", "value": { "type": "SESSION", "expression": "$ssnGraphAPI$" } }
  ] }
```

---

## 15. SharePoint

`packageName: "SharePoint"`. Session-based, OAuth-connected.

| Command                | Purpose                                          |
|------------------------|--------------------------------------------------|
| `Authentication`       | Open session (returns SESSION)                   |
| `UpdateListItem`       | Update a single list-item row                    |
| `DownloadFile`         | Download a library file                          |
| `CreateFolder`         | Create a folder in a library                     |
| `RevokeAuthentication` | Close session                                    |

Also common (same shape): `AddListItem`, `DeleteListItem`, `UploadFile`,
`ReadListItems`, `SearchListItem`.

### Authentication

```json
{ "commandName": "Authentication", "packageName": "SharePoint",
  "attributes": [
    { "name": "authType",   "value": { "type": "STRING", "string": "AuthenticateViaControlRoom" } },
    { "name": "connection", "value": { "type": "OAUTHCONNECTION",
                                       "oauthConnection": { "connectionName": "SharePointOnlineV2",
                                                            "isShared": true } } },
    { "name": "api",        "value": { "type": "STRING", "string": "sharePointAPI" } },
    { "name": "options",    "value": { "type": "STRING", "string": "cloud" } },
    { "name": "subdomain",  "value": { "type": "STRING", "string": "corningonline" } },
    { "name": "siteName",   "value": { "type": "STRING", "string": "SOX_audit" } },
    { "name": "isTeams",    "value": { "type": "BOOLEAN", "boolean": false } }
  ],
  "returnTo": { "type": "SESSION",
                "sessionName": { "type": "STRING", "string": "Default" },
                "sessionTarget": "LOCAL" } }
```

`authType`: `AuthenticateViaControlRoom` (recommended, uses CR OAuth pool) |
`ClientSecret` | `UserCredentials`.
`options`: `cloud` (SharePoint Online) | `onPremises` (legacy).

### UpdateListItem

```json
{ "commandName": "UpdateListItem", "packageName": "SharePoint",
  "attributes": [
    { "name": "site",       "value": { "type": "STRING", "string": "defaultSite" } },
    { "name": "listName",   "value": { "type": "STRING", "string": "ThisList" } },
    { "name": "listItemID", "value": { "type": "NUMBER", "number": "23" } },
    { "name": "tableFieldsEntryList",
      "value": { "type": "LIST",
        "list": [
          { "type": "DICTIONARY",
            "dictionary": [
              { "key": "COLUMN_NAME", "value": { "type": "STRING", "string": "name" } },
              { "key": "TYPE",        "value": { "type": "STRING", "string": "Text" } },
              { "key": "VALUE",       "value": { "type": "STRING", "string": "Rita Vandor" } } ] },
          { "type": "DICTIONARY",
            "dictionary": [
              { "key": "COLUMN_NAME", "value": { "type": "STRING", "string": "Born" } },
              { "key": "TYPE",        "value": { "type": "STRING", "string": "DateTime" } },
              { "key": "VALUE",       "value": { "type": "STRING", "string": "07/24/1987" } } ] } ] } },
    { "name": "session", "value": { "type": "SESSION",
                                    "sessionName": { "type": "STRING", "string": "Default" } } }
  ] }
```

Each field is a **dictionary of `COLUMN_NAME` / `TYPE` / `VALUE`**.
`TYPE` values: `Text`, `Number`, `DateTime`, `Boolean`, `Choice`, `URL`,
`User`, `Lookup`, `MultiChoice`.

### DownloadFile / CreateFolder

```json
{ "commandName": "DownloadFile", "packageName": "SharePoint",
  "attributes": [
    { "name": "siteType",          "value": { "type": "STRING", "string": "Default" } },
    { "name": "filePath",          "value": { "type": "STRING", "string": "library/folder/thisfile.xlsx" } },
    { "name": "destinationFolder", "value": { "type": "STRING", "string": "c:\\temp" } },
    { "name": "session",           "value": { "type": "SESSION",
                                              "sessionName": { "type": "STRING", "string": "Default" } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "fileName" } }

{ "commandName": "CreateFolder", "packageName": "SharePoint",
  "attributes": [
    { "name": "siteType",   "value": { "type": "STRING", "string": "Default" } },
    { "name": "parentPath", "value": { "type": "STRING", "string": "library/folder" } },
    { "name": "folderName", "value": { "type": "STRING", "string": "newfolder" } },
    { "name": "session",    "value": { "type": "SESSION",
                                       "sessionName": { "type": "STRING", "string": "Default" } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "newFolderPath" } }
```

### RevokeAuthentication

```json
{ "commandName": "RevokeAuthentication", "packageName": "SharePoint",
  "attributes": [
    { "name": "session", "value": { "type": "SESSION",
                                    "sessionName": { "type": "STRING", "string": "Default" } } }
  ] }
```

---

## 16. ActiveDirectory

`packageName: "ActiveDirectory"`. Session-based. `session` is a **string
name** ("Default") threaded through every command, not a returned SESSION
variable. The package is broad — users, groups, computers, and organizational
units each get create/delete/get-property/set-property commands plus a few
specials.

| Command                       | Purpose                                    |
|-------------------------------|--------------------------------------------|
| `connect`                     | Bind to an LDAP provider                   |
| `disconnect`                  | Close the session                          |
| `createUser` / `updateUser`   | Create / update a user                     |
| `deleteUser`                  | Delete a user                              |
| `enableUserAccount` / `disableUserAccount` | Toggle account status         |
| `renameUser`                  | Rename a user                              |
| `changeUserCredential`        | Reset a user's password                    |
| `updateAccountOptions`        | Set account flags (must-change-pwd, etc.)  |
| `getUserProperty` / `setUserProperty` | Read / write one user attribute    |
| `createGroup` / `deleteGroup` | Create / delete a group                    |
| `getGroupProperty` / `setGroupProperty` | Read / write a group attribute   |
| `addUsersToGroup` / `removeUsersFromGroup` | Group membership              |
| `getAllUsersOfGroup`          | List a group's members → LIST              |
| `createComputer` / `deleteComputer` / `moveComputer` | Computer objects    |
| `getComputerProperty` / `setComputerProperty` | Computer attributes       |
| `createOrganizationalUnit` / `deleteOrganizationalUnit` / `moveOrganizationalUnit` | OU objects |
| `getOrganizationalUnitProperty` / `setOrganizationalUnitProperty` | OU attributes |
| `runQuery`                    | Run an LDAP query → LIST                   |

The get/set/create/delete commands share consistent shapes: **user** commands
take `userNameOption` + `logonName`; **group/OU/computer** commands take the
object name directly. `get*Property` returns to a variable; `set*Property`
takes `propertyName` + `propertyValue`.

### connect

```json
{ "commandName": "connect", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "session",        "value": { "type": "STRING", "string": "Default" } },
    { "name": "providerPath",   "value": { "type": "STRING", "string": "LDAP://domain/CN=user" } },
    { "name": "userName",       "value": { "type": "STRING", "string": "user@corning.com" } },
    { "name": "userSecureText", "value": { "type": "STRING", "string": "Aa123445" } }
  ] }
```

⚠ **Guardrail** — the raw example uses a plaintext password. In real bots
`userSecureText` MUST use a `CREDENTIAL` value (SKILL.md §4.2).

### addUsersToGroup

```json
{ "commandName": "addUsersToGroup", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "users",
      "value": { "type": "LIST",
        "list": [
          { "type": "DICTIONARY",
            "dictionary": [
              { "key": "name",     "value": { "type": "STRING", "string": "user_abc" } },
              { "key": "ldapPath", "value": { "type": "STRING", "string": "CN=users"  } } ] } ] } },
    { "name": "groupName", "value": { "type": "STRING", "string": "xyz_group" } },
    { "name": "session",   "value": { "type": "STRING", "string": "Default" } }
  ] }
```

Each user is a dictionary of `name` + `ldapPath`.

### runQuery

```json
{ "commandName": "runQuery", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "session",           "value": { "type": "STRING", "string": "Default" } },
    { "name": "query",             "value": { "type": "STRING", "string": "(&(objectCategory=person)(objectClass=user)(name=A*))" } },
    { "name": "adReturnObjectType","value": { "type": "STRING", "string": "OBJECT_NAME" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "queryOutput" } }
```

`adReturnObjectType`: `OBJECT_NAME` | `DISTINGUISHED_NAME` | `SAM_ACCOUNT_NAME` | `EMAIL`.

### createUser

```json
{ "commandName": "createUser", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "userName",          "value": { "type": "STRING", "string": "Attila" } },
    { "name": "logonName",         "value": { "type": "STRING", "string": "attilaa" } },
    { "name": "firstName",         "value": { "type": "STRING", "string": "Attila" } },
    { "name": "lastName",          "value": { "type": "STRING", "string": "Alabas" } },
    { "name": "displayName",       "value": { "type": "STRING", "string": "" } },
    { "name": "initials",          "value": { "type": "STRING", "string": "" } },
    { "name": "email",             "value": { "type": "STRING", "string": "attilaa@corning.com" } },
    { "name": "description",       "value": { "type": "STRING", "string": "" } },
    { "name": "department",        "value": { "type": "STRING", "string": "RTP" } },
    { "name": "title",             "value": { "type": "STRING", "string": "Manager" } },
    { "name": "isActive",          "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "setAccountOptions", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "session",           "value": { "type": "STRING", "string": "Default" } }
  ] }
```

`updateUser` takes the same field set but keys the target with
`userNameOption` + `logonName` (like the property commands below) instead of
creating a new one.

### User lifecycle — deleteUser / enable / disable / rename

All key the target the same way: `userNameOption` (`BY_LOGON_NAME` |
`BY_DISTINGUISHED_NAME` | `BY_USER_NAME`) + `logonName`:

```json
{ "commandName": "deleteUser", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "session",        "value": { "type": "STRING", "string": "Default" } },
    { "name": "userNameOption", "value": { "type": "STRING", "string": "BY_LOGON_NAME" } },
    { "name": "logonName",      "value": { "type": "STRING", "string": "attilaa" } }
  ] }
```

`enableUserAccount`, `disableUserAccount` are identical in shape. `renameUser`
adds `newName` + `renameUserOption`; `changeUserCredential` takes `userName` +
`secret` (use a `CREDENTIAL`).

### getUserProperty / setUserProperty

```json
{ "commandName": "getUserProperty", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "session",        "value": { "type": "STRING", "string": "Default" } },
    { "name": "userNameOption", "value": { "type": "STRING", "string": "BY_LOGON_NAME" } },
    { "name": "logonName",      "value": { "type": "STRING", "string": "koczurr" } },
    { "name": "propertyName",   "value": { "type": "STRING", "string": "email" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strUserEmail" } }

{ "commandName": "setUserProperty", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "session",        "value": { "type": "STRING", "string": "Default" } },
    { "name": "userNameOption", "value": { "type": "STRING", "string": "BY_LOGON_NAME" } },
    { "name": "logonName",      "value": { "type": "STRING", "string": "koczurr" } },
    { "name": "propertyName",   "value": { "type": "STRING", "string": "email" } },
    { "name": "propertyValue",  "value": { "type": "STRING", "string": "new.address@corning.com" } }
  ] }
```

`propertyName` uses the AD attribute name (`email`, `department`, `title`,
`telephoneNumber`, `manager`, …). The group / OU / computer `get*Property` /
`set*Property` commands are the same but key on `groupName` /
`organizationalUnitName` / `computerName` instead of the user options.

### createGroup / getAllUsersOfGroup

```json
{ "commandName": "createGroup", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "session",     "value": { "type": "STRING", "string": "Default" } },
    { "name": "groupName",   "value": { "type": "STRING", "string": "Buda_employees" } },
    { "name": "description", "value": { "type": "STRING", "string": "" } },
    { "name": "groupScope",  "value": { "type": "STRING", "string": "DOMAIN_LOCAL" } },
    { "name": "groupType",   "value": { "type": "STRING", "string": "DISTRIBUTION" } }
  ] }

{ "commandName": "getAllUsersOfGroup", "packageName": "ActiveDirectory",
  "attributes": [
    { "name": "session",            "value": { "type": "STRING", "string": "Default" } },
    { "name": "groupName",          "value": { "type": "STRING", "string": "Buda_employees" } },
    { "name": "adReturnObjectType", "value": { "type": "STRING", "string": "OBJECT_NAME" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "lstBudaEmployees" } }
```

`groupScope`: `DOMAIN_LOCAL` | `GLOBAL` | `UNIVERSAL`.
`groupType`: `DISTRIBUTION` | `SECURITY`.

### disconnect

```json
{ "commandName": "disconnect", "packageName": "ActiveDirectory",
  "attributes": [ { "name": "session", "value": { "type": "STRING", "string": "Default" } } ] }
```

---

## 17. Browser — Chrome / Edge / Firefox automation

`packageName: "Browser"`.

| Command           | Purpose                                        |
|-------------------|------------------------------------------------|
| `openbrowser`     | Launch the browser at a URL                    |
| `close`           | Close a tab / window                           |
| `downloadFile`    | Download a URL directly to disk                |
| `Extractsource`   | Read a page's HTML source for a UI element     |
| `RunJavaScript`   | Run an inline JS snippet in the page → result  |
| `CallJavaScript`  | Call a named page function with arguments      |
| `Goback`          | Navigate back N steps in history               |
| `findbrokenLinks` | Crawl a page/site for broken links → file      |

### openbrowser

```json
{ "commandName": "openbrowser", "packageName": "Browser",
  "attributes": [
    { "name": "openOption",   "value": { "type": "STRING", "string": "NEW_WIN" } },
    { "name": "browser",      "value": { "type": "STRING", "string": "CHROME" } },
    { "name": "url",          "value": { "type": "STRING", "string": "http://www.corning.com" } },
    { "name": "timeoutValue", "value": { "type": "NUMBER", "number": "240" } },
    { "name": "version",      "value": { "type": "NUMBER", "number": "3810" } }
  ] }
```

`openOption`: `NEW_WIN` | `EXISTING_WIN` | `NEW_TAB`.
`browser`: `CHROME` | `EDGE` | `FIREFOX` | `IE`.

### downloadFile

```json
{ "commandName": "downloadFile", "packageName": "Browser",
  "attributes": [
    { "name": "url",       "value": { "type": "STRING", "string": "http://something.com/file.xlsx" } },
    { "name": "filePath",  "value": { "type": "FILE", "string": "file:///c:/temp/file.xlsx" } },
    { "name": "overwrite", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "version",   "value": { "type": "NUMBER", "number": "3810" } }
  ] }
```

### Extractsource

```json
{ "commandName": "Extractsource", "packageName": "Browser",
  "attributes": [
    { "name": "windowValue",  "value": { "type": "WINDOW", "expression": "$Browser1$" } },
    { "name": "uiObject",     "value": { "type": "UIOBJECT", "uiObject": { "…": "…" } } },
    { "name": "timeoutValue", "value": { "type": "NUMBER", "number": "240" } },
    { "name": "version",      "value": { "type": "NUMBER", "number": "3810" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "SourceCode" } }
```

### RunJavaScript / CallJavaScript

`RunJavaScript` runs an inline snippet; `scriptOption` is `SCRIPT` (inline,
uses `script`) or `FILE` (uses a file path). `CallJavaScript` invokes a named
function already on the page, passing typed arguments. Both return to a
variable and carry a `uiObject` (often empty when targeting the whole page)
plus a `version` number:

```json
{ "commandName": "RunJavaScript", "packageName": "Browser",
  "attributes": [
    { "name": "windowValue",  "value": { "type": "WINDOW", "expression": "$Browser1$" } },
    { "name": "uiObject",     "value": { "type": "UIOBJECT", "uiObject": { "blob": "", "criteria": {} } } },
    { "name": "scriptOption", "value": { "type": "STRING", "string": "SCRIPT" } },
    { "name": "script",       "value": { "type": "STRING", "string": "var fff = 12" } },
    { "name": "timeoutValue", "value": { "type": "NUMBER", "number": "240" } },
    { "name": "version",      "value": { "type": "NUMBER", "number": "3810" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "JSOutput" } }

{ "commandName": "CallJavaScript", "packageName": "Browser",
  "attributes": [
    { "name": "windowValue",          "value": { "type": "WINDOW", "window": { "type": "WINDOW", "presetType": "CURRENTLY_ACTIVE" } } },
    { "name": "uiObject",             "value": { "type": "UIOBJECT", "uiObject": { "blob": "", "criteria": {} } } },
    { "name": "functionName",         "value": { "type": "STRING", "string": "isEqual" } },
    { "name": "functionArguments",    "value": { "type": "LIST",
        "list": [ { "type": "DICTIONARY", "dictionary": [
                    { "key": "argumentType", "value": { "type": "STRING", "string": "System.String" } },
                    { "key": "stringValue",  "value": { "type": "STRING", "string": "num" } } ] } ] } },
    { "name": "timeoutValue",         "value": { "type": "NUMBER", "number": "240" } },
    { "name": "returnJavaScriptType", "value": { "type": "STRING", "string": "LIST" } },
    { "name": "version",              "value": { "type": "NUMBER", "number": "3810" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "JSOutput" } }
```

Each `functionArguments` entry is a dict of `argumentType` (a .NET type name
like `System.String`, `System.Int32`, `System.Boolean`) + a matching value key
(`stringValue`, etc.). `returnJavaScriptType`: `STRING` | `NUMBER` | `BOOLEAN`
| `LIST` | `DICTIONARY`.

### Goback / close

```json
{ "commandName": "Goback", "packageName": "Browser",
  "attributes": [
    { "name": "windowValue",             "value": { "type": "WINDOW", "expression": "$Browser1$" } },
    { "name": "noOfSteps",               "value": { "type": "NUMBER", "number": "1" } },
    { "name": "errorThrownForExceedSteps","value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "timeoutValue",            "value": { "type": "NUMBER", "number": "240" } },
    { "name": "version",                 "value": { "type": "NUMBER", "number": "3810" } }
  ] }

{ "commandName": "close", "packageName": "Browser",
  "attributes": [
    { "name": "whatToClose",  "value": { "type": "STRING", "string": "CURRENT_TAB" } },
    { "name": "timeoutValue", "value": { "type": "NUMBER", "number": "240" } },
    { "name": "version",      "value": { "type": "NUMBER", "number": "3810" } }
  ] }
```

`whatToClose`: `CURRENT_TAB` | `CURRENT_WINDOW` | `ALL`.

---

## 18. Recorder — universal UI capture

`packageName: "Recorder"`. Single command `capture` — the *action* is
encoded inside its attributes.

### capture

```jsonc
{ "commandName": "capture", "packageName": "Recorder",
  "attributes": [
    { "name": "uiObject",         "value": { "type": "UIOBJECT", "uiObject": { "…": "…" } } },
    { "name": "buttonAction",     "value": { "type": "STRING", "string": "CLICK" } },     // control-specific
    { "name": "runInBackground",  "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "advancedWait",     "value": { "type": "STRING", "string": "BASIC" } },
    { "name": "wait",             "value": { "type": "NUMBER", "number": "15" } }
  ] }
```

Depending on the captured control type, one of the following action
attributes appears:

| controlType | Action attribute name  | Example values                                    |
|-------------|------------------------|---------------------------------------------------|
| BUTTON      | `buttonAction`         | `CLICK`, `LEFTCLICK`, `RIGHTCLICK`, `DOUBLECLICK` |
| TEXTBOX     | `textboxAction`        | `SETTEXT`, `APPENDTEXT`, `GETTEXT`, `CLEARTEXT`   |
| LINK / any  | `linkAction`           | `CLICK`, `GETPROPERTY`                            |
| CHECKBOX    | `checkboxAction`       | `CHECK`, `UNCHECK`                                |
| RADIOBUTTON | `radioAction`          | `SELECT`                                          |
| COMBOBOX    | `comboBoxAction`       | `SELECTBYTEXT`, `SELECTBYINDEX`, `GETSELECTED`    |
| TABLE       | `tableAction`          | `CLICKCELL`, `GETCELLTEXT`, `GETROWCOUNT`         |

For "set text" style actions, add `typeOfInput` + `value`. For
"get property" style actions, add `value` = property name (e.g. `"HTML Href"`)
and set node `returnTo`.

Example — set text into an input:

```jsonc
{ "commandName": "capture", "packageName": "Recorder",
  "attributes": [
    { "name": "uiObject",         "value": { "type": "UIOBJECT", "uiObject": { "…": "…" } } },
    { "name": "textboxAction",    "value": { "type": "STRING", "string": "SETTEXT" } },
    { "name": "typeOfInput",      "value": { "type": "STRING", "string": "VALUE" } },
    { "name": "value",            "value": { "type": "STRING", "string": "This is an email subject" } },
    { "name": "delay",            "value": { "type": "NUMBER", "number": "20" } },
    { "name": "advancedWait",     "value": { "type": "STRING", "string": "BASIC" } },
    { "name": "wait",             "value": { "type": "NUMBER", "number": "15" } }
  ] }
```

Never regenerate the `blob` by hand — always re-capture it in the editor.
The `criteria` map's `enabled: true` entries are the runtime selectors and
**are** safe to tune.

---

## 19. Keystrokes

`packageName: "Keystrokes"`. Send keyboard input to a window.

### Keystrokes

```json
{ "commandName": "Keystrokes", "packageName": "Keystrokes",
  "attributes": [
    { "name": "windowValue",             "value": { "type": "WINDOW",
                                                    "window": { "type": "WINDOW", "presetType": "CURRENTLY_ACTIVE" } } },
    { "name": "typeOfInputStringToType", "value": { "type": "STRING", "string": "VALUE" } },
    { "name": "stringToType",            "value": { "type": "STRING", "string": "[CTRL DOWN][SHIFT DOWN]a[SHIFT UP][CTRL UP]" } },
    { "name": "delay",                   "value": { "type": "NUMBER", "number": "10" } }
  ] }
```

Special-key tokens (samples): `[ENTER]`, `[TAB]`, `[ESC]`, `[F1]`–`[F12]`,
`[CTRL DOWN]…[CTRL UP]`, `[SHIFT DOWN]…[SHIFT UP]`, `[ALT DOWN]…[ALT UP]`.
Use `typeOfInputStringToType: "SECURE"` for password-style typing (paired
with a `secureString` attribute referencing a credential).

---

## 20. Mouse

`packageName: "Mouse"`.

### mouseMove

```jsonc
{ "commandName": "mouseMove", "packageName": "Mouse",
  "attributes": [
    { "name": "coordinateFrom", "value": { "type": "COORDINATE",
        "coordinate": { "x": {"type":"NUMBER","number":"1175"}, "y": {"type":"NUMBER","number":"257"}, "capture": { "…": "…" } } } },
    { "name": "coordinateTo",   "value": { "type": "COORDINATE",
        "coordinate": { "x": {"type":"NUMBER","number":"1318"}, "y": {"type":"NUMBER","number":"791"}, "capture": { "…": "…" } } } },
    { "name": "delay",          "value": { "type": "NUMBER", "number": "0" } }
  ] }
```

Siblings: `mouseClick`, `mouseDrag`, `mouseScroll`. Coordinate-based
automation is brittle; prefer `Recorder.capture` when possible.

---

## 21. Window

`packageName: "Window"`. Window management.

| Command            | Purpose                             |
|--------------------|-------------------------------------|
| `maximizeWindow`   | Maximize a window                   |
| `minimizeWindow`   | Minimize                            |
| `restoreWindow`    | Restore from minimized/maximized    |
| `closeWindow`      | Close a specific window             |
| `closeAllWindows`  | Close every window except a whitelist |
| `activateWindow`   | Bring to foreground                 |
| `resizeWindow`     | Move + resize (left/top/width/height) |
| `SetTitle`         | Rename a window's title bar         |
| `assign`           | Capture a window handle → variable  |
| `activeWindowTitle`| Get the foreground window's title   |

The single-window commands (`maximizeWindow`, `minimizeWindow`,
`restoreWindow`, `closeWindow`, `activateWindow`) all share the one-attribute
`window` shape shown below. `activeWindowTitle` takes no attributes and returns
to a variable.

### maximizeWindow / closeWindow (identical shape)

```json
{ "commandName": "maximizeWindow", "packageName": "Window",
  "attributes": [ { "name": "window", "value": { "type": "WINDOW", "expression": "$Window1$" } } ] }
```

### closeAllWindows

```json
{ "commandName": "closeAllWindows", "packageName": "Window",
  "attributes": [
    { "name": "openWindowList",
      "value": { "type": "LIST",
        "list": [
          { "type": "DICTIONARY", "dictionary": [ { "key": "winTitle", "value": { "type": "STRING", "string": "Outlook" } } ] },
          { "type": "DICTIONARY", "dictionary": [ { "key": "winTitle", "value": { "type": "STRING", "string": "Excel"   } } ] }
        ] } }
  ] }
```

Semantics: closes every window whose title does **not** match any of the
listed `winTitle` patterns (wildcards allowed).

### resizeWindow

```json
{ "commandName": "resizeWindow", "packageName": "Window",
  "attributes": [
    { "name": "window", "value": { "type": "WINDOW", "expression": "$Window3$" } },
    { "name": "left",   "value": { "type": "NUMBER", "number": "350" } },
    { "name": "top",    "value": { "type": "NUMBER", "number": "111" } },
    { "name": "width",  "value": { "type": "NUMBER", "number": "500" } },
    { "name": "height", "value": { "type": "NUMBER", "number": "600" } }
  ] }
```

### SetTitle

```json
{ "commandName": "SetTitle", "packageName": "Window",
  "attributes": [
    { "name": "sourceWindow", "value": { "type": "WINDOW", "expression": "$Window4$" } },
    { "name": "filterType",   "value": { "type": "STRING", "string": "StringValue" } },
    { "name": "newTitle",     "value": { "type": "STRING", "string": "New Title" } }
  ] }
```

`filterType`: `StringValue` (literal) | `WildCard` | `Regularexpression` —
how the current title is matched before it is replaced with `newTitle`.

### assign

Captures a window handle into a WINDOW variable for later reuse:

```json
{ "commandName": "assign", "packageName": "Window",
  "attributes": [
    { "name": "sourceWindow", "value": { "type": "WINDOW", "expression": "$Window1$" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "winSaved" } }
```

---

## 22. Wait

`packageName: "Wait"`. Pause bot execution until a condition holds.

### waitForWindow

```json
{ "commandName": "waitForWindow", "packageName": "Wait",
  "attributes": [
    { "name": "waitType",        "value": { "type": "STRING", "string": "OPEN" } },
    { "name": "window",          "value": { "type": "WINDOW", "expression": "$Window3$" } },
    { "name": "waitTimeout",     "value": { "type": "NUMBER", "number": "5" } },
    { "name": "isThrowException","value": { "type": "BOOLEAN", "boolean": false } }
  ] }
```

`waitType`: `OPEN` | `CLOSE`.

### waitForCondition

```jsonc
{ "commandName": "waitForCondition", "packageName": "Wait",
  "attributes": [
    { "attributes": [
        { "name": "uiObject", "value": { "type": "UIOBJECT", "uiObject": { "…": "…" } } }
      ],
      "name": "conditionPredicate",
      "value": { "type": "CONDITIONAL", "conditionalName": "capture", "packageName": "Recorder" } }
  ] }
```

The `conditionPredicate` attribute nests **another attribute list**
inside itself — the same nested-conditional pattern used by `If`
(SKILL.md §2.5). Common predicates:

| conditionalName             | packageName  | Meaning                             |
|-----------------------------|--------------|-------------------------------------|
| `capture`                   | `Recorder`   | UI element exists                   |
| `windowExists`              | `Window`     | Window with title/handle is open    |
| `fileExists`                | `File`       | Path exists on disk                 |
| `folderExists`              | `Folder`     | Folder exists                       |
| `stringVariable`, `numberVariable`, `booleanVariable` | (various) | Value comparison |

### waitForScreenChange_V1

Waits until a screen **region** stops changing (or a timeout). The `windowArea`
is a `REGION` value carrying pixel coordinates plus a `capture` block with the
recorded screenshot/thumbnail metadata (regenerate in the editor — never by
hand):

```jsonc
{ "commandName": "waitForScreenChange_V1", "packageName": "Wait",
  "attributes": [
    { "name": "relativeTo",           "value": { "type": "STRING", "string": "SCREEN" } },
    { "name": "window",               "value": { "type": "WINDOW", "expression": "$Window1$" } },
    { "name": "windowArea",           "value": { "type": "REGION",
        "region": { "x": {"type":"NUMBER","number":"384"}, "y": {"type":"NUMBER","number":"302"},
                    "width": {"type":"NUMBER","number":"1089"}, "height": {"type":"NUMBER","number":"534"},
                    "capture": { "…": "…" } } } },
    { "name": "waitTimeBeforeCompare","value": { "type": "NUMBER", "number": "5" } },
    { "name": "waitTimeout",          "value": { "type": "NUMBER", "number": "5" } },
    { "name": "isThrowException",     "value": { "type": "BOOLEAN", "boolean": true } }
  ] }
```

`relativeTo`: `SCREEN` | `WINDOW`. `waitTimeBeforeCompare` is how long to let
the region settle before sampling; `waitTimeout` is the overall cap.

---

## 23. Clipboard

`packageName: "Clipboard"`.

### assignToClipboard / clearClipboard / getFromClipboard

```json
{ "commandName": "assignToClipboard", "packageName": "Clipboard",
  "attributes": [ { "name": "value", "value": { "type": "STRING", "string": "this goes to clipboard" } } ] }

{ "commandName": "clearClipboard", "packageName": "Clipboard" }

// getFromClipboard: no attributes, uses returnTo:
{ "commandName": "getFromClipboard", "packageName": "Clipboard",
  "returnTo": { "type": "VARIABLE", "variableName": "vClipContents" } }
```

---

## 24. MessageBox

`packageName: "MessageBox"`. Attended-only — pops up a dialog. Avoid in
unattended bots or set `closeMsgBox: true` with a small `timeOut`.

### messageBox

```json
{ "commandName": "messageBox", "packageName": "MessageBox",
  "attributes": [
    { "name": "title",       "value": { "type": "STRING", "string": "Last line" } },
    { "name": "content",     "value": { "type": "STRING", "expression": "User: $vUserName$, Company: $vCompany$" } },
    { "name": "scrollLines", "value": { "type": "NUMBER", "number": "30" } },
    { "name": "closeMsgBox", "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "timeOut",     "value": { "type": "NUMBER", "number": "2" } }
  ] }
```

---

## 25. Python — inline scripting

`packageName: "Python"`. Session-based.

| Command                          | Purpose                                    |
|----------------------------------|--------------------------------------------|
| `python.commands.openScript`     | Load a script (returns SESSION)            |
| `python.commands.executeFunction`| Call a function inside the loaded script   |
| `python.commands.closeScript`    | End the session                            |

### openScript

```json
{ "commandName": "python.commands.openScript", "packageName": "Python",
  "attributes": [
    { "name": "scriptOption",           "value": { "type": "STRING", "string": "SCRIPT" } },
    { "name": "script",                 "value": { "type": "STRING", "string": "def power(a):\n\treturn a^2" } },
    { "name": "version",                "value": { "type": "STRING", "string": "3" } },
    { "name": "pythonInterpreterPath",  "value": { "type": "STRING", "string": "" } }
  ],
  "returnTo": { "type": "SESSION",
                "sessionName": { "type": "STRING", "string": "Default" },
                "sessionTarget": "LOCAL" } }
```

`scriptOption`: `SCRIPT` (inline) | `FILE` (add `filePath` attribute instead).

### executeFunction

```json
{ "commandName": "python.commands.executeFunction", "packageName": "Python",
  "attributes": [
    { "name": "session",      "value": { "type": "SESSION",
                                         "sessionName": { "type": "STRING", "string": "Default" } } },
    { "name": "functionName", "value": { "type": "STRING", "string": "power" } },
    { "name": "argument",     "value": { "type": "VARIABLE", "variableName": "nRandom" } },
    { "name": "exactMessage", "value": { "type": "BOOLEAN", "boolean": false } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nPowerOfRandom" } }
```

The Python function accepts **exactly one argument** (limitation of the
Automation Anywhere Python package).

### closeScript

```json
{ "commandName": "python.commands.closeScript", "packageName": "Python",
  "attributes": [
    { "name": "session", "value": { "type": "SESSION",
                                    "sessionName": { "type": "STRING", "string": "Default" } } }
  ] }
```

---

## 26. File

`packageName: "File"`. File-level operations & the `File` value type.

| Command       | Purpose                                          |
|---------------|--------------------------------------------------|
| `assign`      | Build a FILE value from a path expression        |
| `copyFiles`   | Copy file(s), optional size/date filters         |
| `deleteFiles` | Delete file(s), optional size/date filters       |
| `renameFiles` | Rename a file                                    |
| `createFile`  | Create an empty file                             |
| `getName` / `getPath` | Extract the name / directory of a FILE   |
| `openFile` / `downloadTo` / `createShortcut` | misc file ops     |

### assign (turn a path string into a FILE variable)

```json
{ "commandName": "assign", "packageName": "File",
  "attributes": [
    { "name": "sourceFile", "value": { "type": "FILE", "expression": "file://$strScreenshotFile$" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "fileScreenshot" } }
```

Existence check → via `If` with `conditionalName: "fileExists"` /
`"fileNotExists"` (SKILL.md §2.5).

### copyFiles / deleteFiles / renameFiles

```json
{ "commandName": "copyFiles", "packageName": "File",
  "attributes": [
    { "name": "sourceFilePath", "value": { "type": "FILE", "string": "file:///C:/tools/lib.dll" } },
    { "name": "destinationPath","value": { "type": "STRING", "string": "C:\\temp" } },
    { "name": "isOverwrite",    "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "isParallel",     "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "isSize",         "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "sizeValue",      "value": { "type": "STRING", "string": "Atleast" } },
    { "name": "size",           "value": { "type": "NUMBER", "number": "500" } },
    { "name": "isDate",         "value": { "type": "BOOLEAN", "boolean": false } }
  ] }

{ "commandName": "deleteFiles", "packageName": "File",
  "attributes": [
    { "name": "filePath",        "value": { "type": "FILE", "expression": "file://$FilesInFolder{name}$.$FilesInFolder{extension}$" } },
    { "name": "isParallelDelete","value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "isSize",          "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "isDate",          "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "dateValue",       "value": { "type": "STRING", "string": "Created" } },
    { "name": "dateRangeValue",  "value": { "type": "STRING", "string": "Days" } },
    { "name": "days",            "value": { "type": "NUMBER", "number": "10" } }
  ] }

{ "commandName": "renameFiles", "packageName": "File",
  "attributes": [
    { "name": "filePath",    "value": { "type": "FILE", "string": "file:///C:/temp/old.txt" } },
    { "name": "newFileName", "value": { "type": "STRING", "string": "new.json" } },
    { "name": "isSize",      "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "isDate",      "value": { "type": "BOOLEAN", "boolean": false } }
  ] }
```

Optional `isSize` / `isDate` filters let one call act on many files: `sizeValue`
is `Atleast` | `Atmost`; `dateValue` is `Created` | `Modified`; `dateRangeValue`
is `Days` | `Hours` | `Minutes` | a date range.

### getName / getPath

```json
{ "commandName": "getName", "packageName": "File",
  "attributes": [ { "name": "sourceFile", "value": { "type": "FILE", "expression": "$FileInput$" } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "strFileName" } }
```

`getPath` returns the containing directory instead of the file name.

---

## 27. Ping (declared but rarely used)

`packageName: "Ping"`. Simple ICMP-style reachability check.

Typical shape:

```jsonc
{ "commandName": "ping", "packageName": "Ping",
  "attributes": [
    { "name": "host",         "value": { "type": "STRING", "string": "server.corp.local" } },
    { "name": "timeoutMillis","value": { "type": "NUMBER", "number": "2000" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "blnReachable" } }
```

Also used as an `If` predicate — `conditionalName: "canBePinged"`, package
`Ping`. Prefer the `If` conditional over a plain command when the result is
only used for branching.

---

## 28. DataTable — in-memory tables

`packageName: "DataTable"`. Operates on `TABLE` variables. A `TABLE` is also
consumed by other packages (e.g. `Excel_MS.writeDataTableToWorksheet` takes one
in `tableObj`; `Database.exportToDataTable` produces one).

| Command               | Purpose                                          |
|-----------------------|--------------------------------------------------|
| `assign`              | Create a table from a literal or copy one        |
| `insertRow`           | Append/insert a row (from a RECORD)              |
| `deleteRow`           | Remove a row                                     |
| `insertColumn` / `deleteColumn` | Add / drop a column                    |
| `setCellValue`        | Write one cell by row + column                   |
| `getNumberOfRows` / `getNumberOfColumns` | Dimensions → Number           |
| `getColumnName`       | Column header at an index                        |
| `sort`                | Sort by a column                                 |
| `join` / `merge`      | Combine two tables                               |
| `removeDuplicateRows` | Deduplicate                                      |
| `clearContent`        | Empty the table (keep schema)                    |
| `writeToFile`         | Export to CSV/delimited file                     |

`TABLE` literal value shape (used by `assign` and in variable defaults):

```jsonc
{ "type": "TABLE",
  "table": {
    "schema": [ { "name": "Name", "type": "STRING" }, { "name": "Email", "type": "STRING" } ],
    "rows":   [ { "values": [ {"type":"STRING","string":"Jack"},
                              {"type":"STRING","string":"jack@gmail.com"} ] } ] } }
```

### assign (from a literal table)

```json
{ "commandName": "assign", "packageName": "DataTable",
  "attributes": [
    { "name": "option",      "value": { "type": "STRING", "string": "table" } },
    { "name": "sourceTable", "value": { "type": "TABLE", "table": { "schema": [ … ], "rows": [ … ] } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "tblNames" } }
```

`option`: `table` (literal/`sourceTable`) | `variable` (copy another TABLE).

### setCellValue / insertRow / getNumberOfRows

```json
{ "commandName": "setCellValue", "packageName": "DataTable",
  "attributes": [
    { "name": "table",       "value": { "type": "VARIABLE", "variableName": "tblNames" } },
    { "name": "rowPosition", "value": { "type": "NUMBER", "number": "1" } },
    { "name": "columnType",  "value": { "type": "STRING", "string": "colIndex" } },
    { "name": "columnIndex", "value": { "type": "NUMBER", "number": "2" } },
    { "name": "value",       "value": { "type": "STRING", "string": "3333" } }
  ] }

{ "commandName": "insertRow", "packageName": "DataTable",
  "attributes": [
    { "name": "table",             "value": { "type": "VARIABLE", "variableName": "tblNames" } },
    { "name": "positionSelection", "value": { "type": "STRING", "string": "lastPosition" } },
    { "name": "rowRecord",         "value": { "type": "VARIABLE", "variableName": "CsvTxtRow" } }
  ] }

{ "commandName": "getNumberOfRows", "packageName": "DataTable",
  "attributes": [
    { "name": "table",             "value": { "type": "VARIABLE", "variableName": "tblNames" } },
    { "name": "rowCountSelection", "value": { "type": "STRING", "string": "nonEmptyRowSelection" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrOfRows" } }
```

`columnType`: `colIndex` (use `columnIndex`) | `colName` (use `columnName`).
`positionSelection`: `firstPosition` | `lastPosition` | `specificPosition`.

### sort / join / removeDuplicateRows / writeToFile

```json
{ "commandName": "sort", "packageName": "DataTable",
  "attributes": [
    { "name": "table",       "value": { "type": "VARIABLE", "variableName": "tblNames" } },
    { "name": "sortOptions", "value": { "type": "STRING", "string": "NAME" } },
    { "name": "columnName",  "value": { "type": "STRING", "string": "email" } },
    { "name": "sortType",    "value": { "type": "STRING", "string": "ASCENDING" } }
  ] }

{ "commandName": "join", "packageName": "DataTable",
  "attributes": [
    { "name": "firstTable",       "value": { "type": "VARIABLE", "variableName": "tblNames" } },
    { "name": "firstColumnName",  "value": { "type": "STRING", "string": "name" } },
    { "name": "secondTable",      "value": { "type": "VARIABLE", "variableName": "TableFromCSV" } },
    { "name": "secondColumnName", "value": { "type": "STRING", "string": "username" } },
    { "name": "joinType",         "value": { "type": "STRING", "string": "INNER_JOIN" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "tblJoined" } }

{ "commandName": "removeDuplicateRows", "packageName": "DataTable",
  "attributes": [ { "name": "table", "value": { "type": "VARIABLE", "variableName": "tblNames" } } ] }

{ "commandName": "writeToFile", "packageName": "DataTable",
  "attributes": [
    { "name": "sourceTable",         "value": { "type": "VARIABLE", "variableName": "tblNames" } },
    { "name": "filePath",            "value": { "type": "FILE", "string": "file:///C:/temp/out.csv" } },
    { "name": "createDirectories",   "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "appendToExistingFile","value": { "type": "STRING", "string": "append" } },
    { "name": "rowDelimiter",        "value": { "type": "STRING", "string": "NEW_LINE" } },
    { "name": "columnDelimiter",     "value": { "type": "STRING", "string": "SEMI_COLON" } },
    { "name": "encoding",            "value": { "type": "STRING", "string": "UTF-8-WITHOUT-BOM" } }
  ] }
```

`sortOptions`: `NAME` (by column name) | `INDEX`. `sortType`: `ASCENDING` |
`DESCENDING`. `joinType`: `INNER_JOIN` | `LEFT_JOIN` | `RIGHT_JOIN` |
`FULL_JOIN`. `columnDelimiter`: `COMMA` | `SEMI_COLON` | `TAB` | `PIPE`.

---

## 29. Dictionary — key/value maps

`packageName: "Dictionary"`. A `DICTIONARY` variable holds typed key→value
pairs. Field access inside an expression is `$dic{keyName}$`.

| Command  | Purpose                                            |
|----------|----------------------------------------------------|
| `assign` | Create/replace a dictionary from a literal map     |
| `get`    | Read one key's value → `returnTo`                  |
| `put`    | Insert/update one key                              |
| `remove` | Delete one key                                     |
| `size`   | Number of entries → Number                         |

### assign (literal map)

```json
{ "commandName": "assign", "packageName": "Dictionary",
  "attributes": [
    { "name": "sourceDictionary",
      "value": { "type": "DICTIONARY",
        "dictionary": [
          { "key": "name", "value": { "type": "STRING", "string": "Richard" } },
          { "key": "age",  "value": { "type": "NUMBER", "number": "55" } } ] } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "dicPerson" } }
```

### get / put / remove / size

```json
{ "commandName": "get", "packageName": "Dictionary",
  "attributes": [
    { "name": "sourceMap", "value": { "type": "VARIABLE", "variableName": "dicPerson" } },
    { "name": "key",       "value": { "type": "STRING", "string": "name" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strPersonName" } }

{ "commandName": "put", "packageName": "Dictionary",
  "attributes": [
    { "name": "sourceMap",   "value": { "type": "VARIABLE", "variableName": "dicPerson" } },
    { "name": "key",         "value": { "type": "STRING", "string": "email" } },
    { "name": "varOrManual", "value": { "type": "STRING", "string": "Variable" } },
    { "name": "newValue",    "value": { "type": "VARIABLE", "variableName": "strUserEmail" } }
  ] }

{ "commandName": "remove", "packageName": "Dictionary",
  "attributes": [
    { "name": "sourceMap", "value": { "type": "VARIABLE", "variableName": "dicPerson" } },
    { "name": "key",       "value": { "type": "STRING", "string": "age" } }
  ] }

{ "commandName": "size", "packageName": "Dictionary",
  "attributes": [ { "name": "sourceMap", "value": { "type": "VARIABLE", "variableName": "dicPerson" } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrDicSize" } }
```

`varOrManual` on `put`: `"Variable"` (bind `newValue` from a variable) |
`"Manual"` (type a literal into `newValue`).

---

## 30. Math — expression evaluation

`packageName: "Math"`. Single command `mathevaluate` — evaluates an
arithmetic expression string and returns a Number.

### mathevaluate

```json
{ "commandName": "mathevaluate", "packageName": "Math",
  "attributes": [
    { "name": "expression", "value": { "type": "STRING", "string": "x=15-3*(444/66)^2" } },
    { "name": "precision",  "value": { "type": "NUMBER", "number": "2" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrResult" } }
```

* Supports `+ - * / ^`, parentheses, and an assignment form `x=…`.
* `precision` = decimal places to round the result to.
* Embed bot variables with `$var$` inside the `expression` string.

---

## 31. Delay — pause execution

`packageName: "Delay"`. Simple fixed or random wait. (For waiting on a
*condition* use the `Wait` package, §22.)

### delay

```json
{ "commandName": "delay", "packageName": "Delay",
  "attributes": [
    { "name": "delayType", "value": { "type": "STRING", "string": "REGULAR" } },
    { "name": "delayTime", "value": { "type": "NUMBER", "number": "50" } },
    { "name": "timeUnit",  "value": { "type": "STRING", "string": "MILLISECONDS" } }
  ] }
```

`delayType`: `REGULAR` (fixed) | `RANDOM` (then supply `from` / `to` instead
of `delayTime`). `timeUnit`: `MILLISECONDS` | `SECONDS` | `MINUTES`.

---

## 32. Application — launch an executable

`packageName: "Application"`. `runApp` starts a program with arguments.

### runApp

```json
{ "commandName": "runApp", "packageName": "Application",
  "attributes": [
    { "name": "filePath",    "value": { "type": "FILE", "string": "file:///C:/Windows/System32/taskkill.exe" } },
    { "name": "startInPath", "value": { "type": "STRING", "string": "C:\\temp" } },
    { "name": "parameters",  "value": { "type": "STRING", "string": "/f /im" } },
    { "name": "timeout",     "value": { "type": "NUMBER", "number": "11" } }
  ] }
```

* `filePath` is a `FILE` value (`file:///…`).
* `parameters` are the command-line arguments as a single string.
* `timeout` = seconds to wait for the process before continuing (0 = don't wait).

---

## 33. Credential Manager — read a vault credential

`packageName: "Credential Manager"`. One command, `Read Credential`, resolves
a Credential-Vault attribute into a variable at runtime — the recommended way
to pull a username/secret when a package can't take a `CREDENTIAL` value
directly.

### Read Credential

```json
{ "commandName": "Read Credential", "packageName": "Credential Manager",
  "attributes": [
    { "name": "CMInput",
      "value": { "type": "CREDENTIAL",
        "credential": { "name":          "CDTRTP002_OA_Credentials",
                        "lockerName":    "CDT_ISG",
                        "attributeName": "sBot_NT_ID" } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strUser" } }
```

The `credential` shape matches SKILL.md §4.2. Prefer passing a `CREDENTIAL`
value straight into the consuming command; use this only when the target
attribute is plain STRING and cannot accept a vault reference.

---

## 34. Database — SQL / ODBC / OLEDB

`packageName: "Database"`. Session-based (§0.1): `connect` → work → `disconnect`.
Optional explicit transactions with `begin` / `commit`.

| Command              | Purpose                                                |
|----------------------|--------------------------------------------------------|
| `connect`            | Open a connection (returns SESSION)                    |
| `sqlQuery`           | Run a SELECT; optionally export the result to CSV      |
| `exportToDataTable`  | Run a SELECT into a `TABLE` variable                   |
| `store`              | Run a named/stored query, keep the result in session   |
| `insertUpdateDelete` | Run a non-SELECT statement                             |
| `batchInsert`        | Bulk-load a CSV into a table via column mappings       |
| `begin` / `commit`   | Start / commit an explicit transaction                 |
| `disconnect`         | Close (optionally saving data)                         |

### connect

```json
{ "commandName": "connect", "packageName": "Database",
  "attributes": [
    { "name": "connectionMode",     "value": { "type": "STRING", "string": "USER" } },
    { "name": "databaseProvider",   "value": { "type": "STRING", "string": "SQLOLEDB.1" } },
    { "name": "server",             "value": { "type": "STRING", "string": "192.11.213.5" } },
    { "name": "database",           "value": { "type": "STRING", "string": "PRD" } },
    { "name": "user",               "value": { "type": "CREDENTIAL", "expression": "$cUser$" } },
    { "name": "auth",               "value": { "type": "CREDENTIAL", "expression": "$cPass$" } },
    { "name": "instance",           "value": { "type": "STRING", "string": "" } },
    { "name": "timeout",            "value": { "type": "NUMBER", "number": "10" } },
    { "name": "isUserDefinedDriver","value": { "type": "BOOLEAN", "boolean": false } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "ssnDBSession" } }
```

`connectionMode`: `USER` (server+db+user/auth) | `CONNECTION_STRING`.
Common `databaseProvider`: `SQLOLEDB.1` (SQL Server), `Microsoft.ACE.OLEDB.12.0`
(Access/Excel), plus ODBC DSNs. `user` / `auth` should be `CREDENTIAL` values.

### sqlQuery (SELECT, optional CSV export)

```json
{ "commandName": "sqlQuery", "packageName": "Database",
  "attributes": [
    { "name": "query",        "value": { "type": "STRING", "string": "SELECT * FROM botlist WHERE owner = 'koczur'" } },
    { "name": "fetchSize",    "value": { "type": "NUMBER", "number": "10" } },
    { "name": "doExport",     "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "filePath",     "value": { "type": "FILE", "string": "file:///c:/temp/query.csv" } },
    { "name": "encodingType", "value": { "type": "STRING", "string": "ANSI" } },
    { "name": "withHeader",   "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "noBlankCSV",   "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "appendTo",     "value": { "type": "STRING", "string": "false" } },
    { "name": "session",      "value": { "type": "SESSION", "expression": "$ssnDBSession$" } }
  ] }
```

When `doExport` is `false`, the `filePath` / `withHeader` / `noBlankCSV` group
is ignored. To get a `TABLE` variable instead of a CSV, use `exportToDataTable`.

### exportToDataTable / insertUpdateDelete

```json
{ "commandName": "exportToDataTable", "packageName": "Database",
  "attributes": [
    { "name": "query",   "value": { "type": "STRING", "string": "SELECT * FROM botlist ORDER BY name" } },
    { "name": "session", "value": { "type": "SESSION", "expression": "$ssnDBSession$" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "tblNames" } }

{ "commandName": "insertUpdateDelete", "packageName": "Database",
  "attributes": [
    { "name": "query",   "value": { "type": "STRING", "string": "INSERT INTO botlist (name) VALUES ('AAAA')" } },
    { "name": "session", "value": { "type": "SESSION", "expression": "$ssnDBSession$" } }
  ] }
```

### batchInsert (bulk CSV → table)

```json
{ "commandName": "batchInsert", "packageName": "Database",
  "attributes": [
    { "name": "session",           "value": { "type": "SESSION", "expression": "$ssnDBSession$" } },
    { "name": "csvFilePath",       "value": { "type": "FILE", "string": "file:///C:/temp/AuditLog.csv" } },
    { "name": "tableName",         "value": { "type": "STRING", "string": "botlist" } },
    { "name": "delimiter",         "value": { "type": "STRING", "string": "comma" } },
    { "name": "csvStartRowNumber", "value": { "type": "NUMBER", "number": "2" } },
    { "name": "columnMappings",
      "value": { "type": "LIST",
        "list": [
          { "type": "DICTIONARY", "dictionary": [
              { "key": "CSVColumnName",   "value": { "type": "STRING", "string": "name" } },
              { "key": "TableColumnName", "value": { "type": "STRING", "string": "name" } } ] },
          { "type": "DICTIONARY", "dictionary": [
              { "key": "CSVColumnName",   "value": { "type": "STRING", "string": "owner" } },
              { "key": "TableColumnName", "value": { "type": "STRING", "string": "server_owner" } } ] } ] } },
    { "name": "batchSize",        "value": { "type": "NUMBER", "number": "1000" } },
    { "name": "timeoutInSeconds", "value": { "type": "NUMBER", "number": "1800" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "nbrRecordsInserted" } }
```

Each mapping is a dictionary of `CSVColumnName` → `TableColumnName`.

### begin / commit / disconnect

```json
{ "commandName": "begin",  "packageName": "Database",
  "attributes": [ { "name": "session", "value": { "type": "SESSION", "expression": "$ssnDBSession$" } } ] }

{ "commandName": "commit", "packageName": "Database",
  "attributes": [ { "name": "session", "value": { "type": "SESSION", "expression": "$ssnDBSession$" } } ] }

{ "commandName": "disconnect", "packageName": "Database",
  "attributes": [
    { "name": "dosaveData", "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "session",    "value": { "type": "SESSION", "expression": "$ssnDBSession$" } }
  ] }
```

---

## 35. Json — parse / query / edit JSON

`packageName: "Json"`. Session-based: `StartSession` loads a JSON document,
then node queries run against that handle until `EndSession`.

| Command            | Purpose                                              |
|--------------------|------------------------------------------------------|
| `StartSession`     | Load JSON (text or file) into a session              |
| `GetNodeValue`     | Read a scalar at a node path → variable              |
| `GetNodeList`      | Read an array node → LIST                            |
| `UpdateNodeValue`  | Set a node's value                                   |
| `JSONToDictionary` | Convert the whole document to a DICTIONARY           |
| `EndSession`       | Close the session                                    |

Node paths use dotted names and `[index]` array access, e.g. `dev[2].idnumber`.

### StartSession / GetNodeValue

```json
{ "commandName": "StartSession", "packageName": "Json",
  "attributes": [
    { "name": "inputType", "value": { "type": "STRING", "string": "text" } },
    { "name": "data",      "value": { "type": "STRING", "expression": "$SensLabel$" } }
  ],
  "returnTo": { "type": "SESSION",
                "sessionName": { "type": "STRING", "string": "jsonssession" },
                "sessionTarget": "LOCAL" } }

{ "commandName": "GetNodeValue", "packageName": "Json",
  "attributes": [
    { "name": "session",  "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "jsonssession" } } },
    { "name": "nodePath", "value": { "type": "STRING", "string": "dev[2].idnumber" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "idnumber" } }
```

`inputType`: `text` (inline `data` string) | `file` (a `filePath` attribute).

### GetNodeList / UpdateNodeValue / JSONToDictionary / EndSession

```json
{ "commandName": "GetNodeList", "packageName": "Json",
  "attributes": [
    { "name": "session",  "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "jsonssession" } } },
    { "name": "nodePath", "value": { "type": "STRING", "string": "dev" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "lstResult" } }

{ "commandName": "UpdateNodeValue", "packageName": "Json",
  "attributes": [
    { "name": "session",           "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "jsonssession" } } },
    { "name": "nodePath",          "value": { "type": "STRING", "string": "dev[2].idnumber" } },
    { "name": "valueType",         "value": { "type": "STRING", "string": "String" } },
    { "name": "stringVal",         "value": { "type": "STRING", "string": "2345" } },
    { "name": "replaceArrayValue", "value": { "type": "BOOLEAN", "boolean": false } }
  ] }

{ "commandName": "JSONToDictionary", "packageName": "Json",
  "attributes": [ { "name": "session", "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "jsonssession" } } } ],
  "returnTo": { "type": "VARIABLE", "variableName": "jsonOutput" } }

{ "commandName": "EndSession", "packageName": "Json",
  "attributes": [ { "name": "session", "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "jsonssession" } } } ] }
```

`valueType` on `UpdateNodeValue`: `String` | `Number` | `Boolean` (the payload
attribute name changes accordingly — `stringVal` for strings).

---

## 36. JavaScript — inline / file scripting

`packageName: "JavaScript"`. Same three-step session model as Python (§25):
`openScript` → `executeFunction` → `closeScript`.

### openScript / executeFunction / closeScript

```json
{ "commandName": "javascript.commands.openScript", "packageName": "JavaScript",
  "attributes": [
    { "name": "session",      "value": { "type": "STRING", "string": "jssession" } },
    { "name": "scriptOption", "value": { "type": "STRING", "string": "FILE" } },
    { "name": "file",         "value": { "type": "FILE", "string": "file:///C:/somejavascriptfile.js" } }
  ] }

{ "commandName": "javascript.commands.executeFunction", "packageName": "JavaScript",
  "attributes": [
    { "name": "session",      "value": { "type": "STRING", "string": "jssession" } },
    { "name": "functionName", "value": { "type": "STRING", "string": "FunctionName" } },
    { "name": "argument",     "value": { "type": "VARIABLE", "variableName": "strDay" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "strResult" } }

{ "commandName": "javascript.commands.closeScript", "packageName": "JavaScript",
  "attributes": [ { "name": "session", "value": { "type": "STRING", "string": "jssession" } } ] }
```

`scriptOption`: `FILE` (load `file`) | `SCRIPT` (inline `script` string).
The session here is a plain STRING handle, not a SESSION object.

---

## 37. SAP — SAP GUI scripting

`packageName: "SAP"`. Session-based; SAP GUI scripting must be enabled on the
runner. Elements are addressed by their SAP GUI **field path**
(`wnd[0]/usr/txtRSYST-BNAME`-style), passed as `fieldPath`.

| Command                          | Purpose                                    |
|----------------------------------|--------------------------------------------|
| `connect` / `disconnect`         | Attach to / detach from an SAP session     |
| `setText`                        | Type into a field                          |
| `click` / `doubleClick` / `leftClick` / `rightClick` | Activate a control |
| `sendVirtualkey`                 | Send a function/virtual key                |
| `getCell` / `getRow` / `getColumn` | Read grid/table data                     |
| `getTableCellTextByIndexAction`  | Read one grid cell by row/column index     |
| `exportTable`                    | Export a grid to CSV/file                  |
| `selectItem` / `expand`          | Tree / dropdown interaction                |

### connect

```json
{ "commandName": "connect", "packageName": "SAP",
  "attributes": [
    { "name": "sessionName",      "value": { "type": "STRING", "string": "Default" } },
    { "name": "connectionType",   "value": { "type": "STRING", "string": "SAP GUI" } },
    { "name": "sapServerName",    "value": { "type": "STRING", "string": "SQ3" } },
    { "name": "clientID",         "value": { "type": "STRING", "string": "500" } },
    { "name": "secureUser",       "value": { "type": "STRING", "string": "gbauser21" } },
    { "name": "secureCredential", "value": { "type": "STRING", "string": "Aa123456" } },
    { "name": "language",         "value": { "type": "STRING", "string": "EN" } }
  ] }
```

⚠ **Guardrail** — the raw example has a plaintext `secureCredential`. In real
bots `secureUser` / `secureCredential` MUST use a `CREDENTIAL` value (SKILL.md
§4.2).

### setText / click / sendVirtualkey

```json
{ "commandName": "setText", "packageName": "SAP",
  "attributes": [
    { "name": "sessionName",         "value": { "type": "STRING", "string": "Default" } },
    { "name": "fieldPath",           "value": { "type": "STRING", "string": "wnd[0]/fld[1]" } },
    { "name": "fieldValue",          "value": { "type": "STRING", "string": "kovacs" } },
    { "name": "isAppendTextEnabled", "value": { "type": "BOOLEAN", "boolean": true } }
  ] }

{ "commandName": "click", "packageName": "SAP",
  "attributes": [
    { "name": "sessionName", "value": { "type": "STRING", "string": "Default" } },
    { "name": "fieldPath",   "value": { "type": "STRING", "string": "wnd[0]/btn[1]" } }
  ] }

{ "commandName": "sendVirtualkey", "packageName": "SAP",
  "attributes": [
    { "name": "sessionName",      "value": { "type": "STRING", "string": "Default" } },
    { "name": "virtualKeyToSend", "value": { "type": "STRING", "string": "9" } }
  ] }
```

`virtualKeyToSend` maps to an SAP function key (e.g. `0`=Enter, `8`=F8/Execute,
`9`… — the SAP OK-code number).

### getTableCellTextByIndexAction / exportTable

```json
{ "commandName": "getTableCellTextByIndexAction", "packageName": "SAP",
  "attributes": [
    { "name": "sessionName", "value": { "type": "STRING", "string": "Default" } },
    { "name": "fieldPath",   "value": { "type": "STRING", "string": "wnd[0]/tbl[1]" } },
    { "name": "row",         "value": { "type": "NUMBER", "number": "1" } },
    { "name": "column",      "value": { "type": "NUMBER", "number": "1" } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "idnumber" } }

{ "commandName": "exportTable", "packageName": "SAP",
  "attributes": [
    { "name": "sessionName",     "value": { "type": "STRING", "string": "Default" } },
    { "name": "fieldPath",       "value": { "type": "STRING", "string": "wnd[0]/tbl[1]" } },
    { "name": "exportAs",        "value": { "type": "STRING", "string": "CSV" } },
    { "name": "filePath",        "value": { "type": "FILE", "string": "file:///c:/temp/result.csv" } },
    { "name": "encodingType",    "value": { "type": "STRING", "string": "UNICODE" } },
    { "name": "withHeader",      "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "overwriteOption", "value": { "type": "STRING", "string": "true" } }
  ] }
```

### disconnect

```json
{ "commandName": "disconnect", "packageName": "SAP",
  "attributes": [ { "name": "sessionName", "value": { "type": "STRING", "string": "Default" } } ] }
```

---

## 38. Excel (classic / basic)

`packageName: "Excel"`. The **older** basic Excel package (distinct from
`Excel_MS`, §12). Prefer `Excel_MS` for new work; document `Excel` only when a
legacy bot uses it. Session-based.

| Command            | Purpose                                    |
|--------------------|--------------------------------------------|
| `OpenSpreadsheet`  | Open a workbook (returns SESSION)          |
| `GetSingleCell`    | Read the active/selected cell              |
| `SetCell`          | Write a value to a cell                    |
| `GoToCell`         | Move the active cell                       |
| `find` / `Replace` | Search / search-and-replace                |
| `ActivateSheet`    | Switch active worksheet                    |
| `CloseSpreadsheet` | Save & close                               |

### OpenSpreadsheet

```json
{ "commandName": "OpenSpreadsheet", "packageName": "Excel",
  "attributes": [
    { "name": "filePath",        "value": { "type": "FILE", "string": "file:///C:/temp/Audit.xlsx" } },
    { "name": "containsHeader",  "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "isSpecificSheet", "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "fileAccessMode",  "value": { "type": "STRING", "string": "EDIT" } },
    { "name": "isSecure",        "value": { "type": "BOOLEAN", "boolean": false } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "ssnSession" } }
```

`fileAccessMode` here is `EDIT` | `READ_ONLY` (note: `Excel_MS` uses
`READ_WRITE`/`READ_ONLY` instead — the enums differ between the two packages).

### GetSingleCell / SetCell

```json
{ "commandName": "GetSingleCell", "packageName": "Excel",
  "attributes": [
    { "name": "activeCell", "value": { "type": "STRING", "string": "true" } },
    { "name": "session",    "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Default" } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "ExcelCellValue" } }

{ "commandName": "SetCell", "packageName": "Excel",
  "attributes": [
    { "name": "setCellType", "value": { "type": "STRING", "string": "ACTIVE_CELL" } },
    { "name": "value",       "value": { "type": "STRING", "string": "Ezvan" } },
    { "name": "session",     "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Default" } } }
  ] }
```

`setCellType`: `ACTIVE_CELL` | `SPECIFIC_CELL` (then add a `cellAddress`).

### find / CloseSpreadsheet

```json
{ "commandName": "find", "packageName": "Excel",
  "attributes": [
    { "name": "from",            "value": { "type": "STRING", "string": "BEGINNING" } },
    { "name": "till",            "value": { "type": "STRING", "string": "END" } },
    { "name": "findText",        "value": { "type": "STRING", "string": "EztKeresem" } },
    { "name": "searchOptions",   "value": { "type": "STRING", "string": "BYROWS" } },
    { "name": "matchCase",       "value": { "type": "BOOLEAN", "boolean": false } },
    { "name": "matchEntireCell", "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "session",         "value": { "type": "SESSION", "sessionName": { "type": "STRING", "string": "Default" } } }
  ],
  "returnTo": { "type": "VARIABLE", "variableName": "lstResult" } }

{ "commandName": "CloseSpreadsheet", "packageName": "Excel",
  "attributes": [
    { "name": "isSave",  "value": { "type": "BOOLEAN", "boolean": true } },
    { "name": "session", "value": { "type": "SESSION", "expression": "$ssnSession$" } }
  ] }
```

`searchOptions`: `BYROWS` | `BYCOLUMNS`.

---

## Appendix A — Package-to-line quick lookup

Grepping the JSON quickly:

```bash
python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
def walk(n, out):
    if isinstance(n, dict):
        if 'commandName' in n: out.append((n['packageName'], n['commandName']))
        for v in n.values(): walk(v, out)
    elif isinstance(n, list):
        [walk(x, out) for x in n]
lst=[]; walk(d['nodes'], lst)
from collections import Counter
for (p,c),n in sorted(Counter(lst).items()):
    print(f'{n:4d}  {p:25s} {c}')
" path/to/bot.json
```

## Appendix B — Adding a new package to this reference

Minimum required to document a command:

1. Its exact `packageName` and `commandName` (from the JSON, not the UI label).
2. Attribute list: name, value type, allowed enum values.
3. Whether it returns a value (`returnTo`) and of what type.
4. Session dependency (open → work → close, if any).
5. One real JSON snippet, minified, from a working bot.
6. Any gotchas: string-booleans, hidden defaults, credential requirements.

If you cannot verify (2)–(4) against a real bot, prefix the section with
`> ⚠ Unverified — verify against a live A360 Control Room before use.`
