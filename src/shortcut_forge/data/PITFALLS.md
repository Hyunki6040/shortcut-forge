# Shortcuts field notes: what breaks on a real iPhone

Every rule below cost at least one round-trip of "import → run → error screenshot".
They were collected while building a two-person supplement tracker on iOS 27 (Oct 2026).
The builder applies each fix automatically; the linter flags each pattern in any shortcut.

| ID | Pattern | What you see on the phone | Fix (applied by the builder) |
|----|---------|---------------------------|------------------------------|
| SF001 | `Set Stored Content` given a variable *attachment* | Imports fine, runs fine, **stores nothing**. Reads come back empty. | Always pass a text token string (`tok(ref)`). |
| SF002 | `Delete Stored Content` on a key that does not exist | Error 16, the run stops | Read first; delete only inside `If <stored> has any value`. |
| — | Reading a corrupt stored value (left by an older build) | "Could not communicate with a helper application" | `storage_wipe`: overwrite with "-" then delete, never read. Bump a `schema` key to wipe once on upgrade. |
| SF003 | Health sample with unit `mcg` | Health shows 77,400,000 mcg instead of 77.4 (the unit string is read as grams) | Divide by 1000 and log as `mg`. |
| SF004 | Health sample magnitude as a token string | "Choose a value for each parameter of this action" | Magnitude must be the raw variable dictionary. |
| SF008 | Health sample *type* from a variable | Parameter rejected | Types are literals; unroll one action per type and skip empty values. |
| SF005 | `If <dictionary value> is "x"` (text compare) | The comparison field shows empty → "choose a value" error | Pass the left side through a Text action first. |
| SF006 | Dictionary key path `a.b` | "Cannot evaluate key path" whenever `a` is missing | One `Get Dictionary Value` per level. |
| SF007 | `Set Reminder: Is Completed` on the *list* returned by Find Reminders | A "choose item" picker pops up mid-run | `Repeat with Each`, set per item, and skip when Count = 0. |
| SF009 | Output reference to an action without a UUID / deleted action | "Choose a value for each parameter" | Every action whose output is used gets a UUID. |
| SF010 | Variable read before any Set Variable exists in the file | Silent empty value | Declare every variable, including on else-branches. |
| SF011 | Menu items list differs from case branches | Items that do nothing | Builder adds empty branches for undeclared cases. |
| SF014 | `Get Contents of URL` on every run | Offline or a 5xx aborts the whole shortcut (there is no try/catch) | Fetch once a day, cache in Stored Content, fall back to the cache (`remote_config`). |
| — | Hard-coded data (doses, lists, prices) inside the shortcut | Every change means re-signing and every user re-downloading | Keep data in a JSON URL read by `remote_config`; ship code changes with `update_check`. |
| — | Empty input to Add to List / setters | "Choose a value…" | Guard with `If … has any value`. |
| — | History split on new lines without trimming | Counts off by one (leading blank line) | `Trim Whitespace` before `Split Text`. |
| — | Reminder created on every run | Duplicates pile up | Search by a fixed phrase (`<user> <slot> <word> <M/d>`); create only when Count < 1. |
| — | `shortcuts run` on the Mac for QA | Hangs forever on hidden prompts; Health actions do not exist on macOS | Do behavioural QA on the iPhone. Use the Mac only to **sign**. |
| — | Unsigned file AirDropped to iPhone | "This shortcut cannot be opened" | `shortcuts sign -m anyone -i in -o out`; signed files start with bytes `AEA1`. |
| — | Same storage keys for QA and real data | QA runs pollute real history | Prefix every key in QA builds (`storage_prefix="qa_"`), skip Health writes, and use a different reminder word. |

## Debugging loop that works

1. Build a tiny diagnostic shortcut per suspicion (one feature each, e.g. "store → read → compare").
2. Each step posts a numbered notification (`QA 03 ✓ stored=…`). The last notification you receive tells you where it died.
3. Only then rebuild the real shortcut. Ten 15-action probes are faster than one 900-action guess.

## Things that did work first time

- `Use Model` (Apple Intelligence) with a prompt that embeds JSON + history text, returning Text.
- Find Reminders with a `Title contains` + `Is Completed is false` filter.
- `Add New Reminder` with `WFAlertCustomTime` given as text `yyyy-MM-dd HH:mm`.
- Big JSON in a Text action → `Get Dictionary from Input` (more robust than a nested Dictionary action).
