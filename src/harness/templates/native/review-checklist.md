# Pre-Landing Review Checklist

## Instructions

Review the `git diff origin/main` output for the issues listed below. Be specific — cite `file:line` and suggest fixes. Skip anything that's fine. Only flag real problems.

**Two-pass review:**
- **Pass 1 (CRITICAL):** Run SQL & Data Safety, Race Conditions, LLM Output Trust Boundary, Shell Injection, and Enum Completeness first. Highest severity.
- **Pass 2 (INFORMATIONAL):** Run remaining categories below. Lower severity but still actioned.
- **Specialist categories (handled by parallel subagents, NOT this checklist):** Test Gaps, Dead Code, Magic Numbers, Performance & Bundle Impact. See `specialists/` for these.

All findings get action via Fix-First Review: obvious mechanical fixes are applied automatically,
genuinely ambiguous issues are batched into a single user question.

**Output format:**

```
Pre-Landing Review: N issues (X critical, Y informational)

**AUTO-FIXED:**
- [file:line] Problem → fix applied

**NEEDS INPUT:**
- [file:line] Problem description
  Recommended fix: suggested fix
```

If no issues found: `Pre-Landing Review: No issues found.`

Be terse. For each issue: one line describing the problem, one line with the fix. No preamble, no summaries, no "looks good overall."

---

## Confidence Calibration

Every finding MUST include a confidence score (1-10):

| Score | Meaning | Display rule |
|-------|---------|-------------|
| 9-10 | Verified by reading specific code. Concrete bug or exploit demonstrated. | Show normally |
| 7-8 | High confidence pattern match. Very likely correct. | Show normally |
| 5-6 | Moderate. Could be a false positive. | Show with caveat: "Medium confidence — verify this is actually an issue" |
| 3-4 | Low confidence. Pattern is suspicious but may be fine. | Suppress from main report. Include in appendix only. |
| 1-2 | Speculation. | Only report if severity would be CRITICAL. |

**Finding format:**

`[SEVERITY] (confidence: N/10) file:line — description`

Example:
`[CRITICAL] (confidence: 9/10) app/models/user.py:42 — SQL injection via string interpolation in where clause`
`[INFORMATIONAL] (confidence: 5/10) app/services/gen.py:88 — Possible N+1 query, verify with production logs`

---

## Review Categories

### Pass 1 — CRITICAL

#### SQL & Data Safety
- String interpolation in SQL (even if values are cast — use parameterized queries)
- TOCTOU races: check-then-set patterns that should be atomic `WHERE` + `UPDATE`
- Bypassing ORM validations for direct DB writes
- N+1 queries: Missing eager loading for associations used in loops/views

#### Race Conditions & Concurrency
- Read-check-write without uniqueness constraint or duplicate key error handling
- find-or-create without unique DB index — concurrent calls can create duplicates
- Status transitions that don't use atomic `WHERE old_status = ? UPDATE SET new_status`
- Unsafe HTML rendering on user-controlled data (XSS)

#### LLM Output Trust Boundary
- LLM-generated values written to DB or passed to mailers without format validation
- Structured tool output accepted without type/shape checks before database writes
- LLM-generated URLs fetched without allowlist — SSRF risk
- LLM output stored in knowledge bases without sanitization — stored prompt injection

#### Shell Injection
- `subprocess.run()` / `subprocess.call()` / `subprocess.Popen()` with `shell=True` AND f-string interpolation — use argument arrays instead
- `os.system()` with variable interpolation — replace with `subprocess.run()` using argument arrays
- `eval()` / `exec()` on LLM-generated code without sandboxing

#### Enum & Value Completeness
When the diff introduces a new enum value, status string, tier name, or type constant:
- **Trace it through every consumer.** Read each file that switches on, filters by, or displays that value. If any consumer doesn't handle the new value, flag it.
- **Check allowlists/filter arrays.** Search for arrays containing sibling values and verify the new value is included where needed.
- **Check `match`/`if-elif` chains.** If existing code branches on the enum, does the new value fall through to a wrong default?

### Pass 2 — INFORMATIONAL

#### Async/Sync Mixing
- Synchronous `subprocess.run()`, `open()`, `requests.get()` inside `async def` endpoints — blocks the event loop
- `time.sleep()` inside async functions — use `asyncio.sleep()`
- Sync DB calls in async context without `run_in_executor()` wrapping

#### Column/Field Name Safety
- Verify column names in ORM queries against actual DB schema — wrong names silently return empty results
- Check `.get()` calls on query results use the column name that was actually selected

#### Dead Code & Consistency
- Version mismatch between PR title and VERSION/CHANGELOG files
- CHANGELOG entries that describe changes inaccurately

#### LLM Prompt Issues
- 0-indexed lists in prompts (LLMs reliably return 1-indexed)
- Prompt text listing available tools that don't match what's actually wired up
- Word/token limits stated in multiple places that could drift

#### Completeness Gaps
- Shortcut implementations where the complete version would cost <30 minutes
- Test coverage gaps where adding the missing tests is straightforward
- Features implemented at 80-90% when 100% is achievable with modest additional code

#### Time Window Safety
- Date-key lookups that assume "today" covers 24h
- Mismatched time windows between related features

#### Type Coercion at Boundaries
- Values crossing language/serialization boundaries where type could change
- Hash/digest inputs that don't normalize types before serialization

#### View/Frontend
- Inline `<style>` blocks in templates (re-parsed every render)
- O(n*m) lookups in views (linear search in a loop instead of dict/set)

#### Distribution & CI/CD Pipeline
- CI/CD workflow changes: verify build tool versions, artifact paths, secrets handling
- New artifact types: verify a publish/release workflow exists
- Version tag format consistency across VERSION file, git tags, and publish scripts

---

## Severity Classification

```
CRITICAL (highest severity):      INFORMATIONAL (main agent):
├─ SQL & Data Safety              ├─ Async/Sync Mixing
├─ Race Conditions & Concurrency  ├─ Column/Field Name Safety
├─ LLM Output Trust Boundary      ├─ Dead Code (version only)
├─ Shell Injection                ├─ LLM Prompt Issues
└─ Enum & Value Completeness      ├─ Completeness Gaps
                                   ├─ Time Window Safety
                                   ├─ Type Coercion at Boundaries
                                   ├─ View/Frontend
                                   └─ Distribution & CI/CD Pipeline
```

---

## Fix-First Heuristic

```
AUTO-FIX (agent fixes without asking):     ASK (needs human judgment):
├─ Dead code / unused variables            ├─ Security (auth, XSS, injection)
├─ N+1 queries (missing eager loading)      ├─ Race conditions
├─ Stale comments contradicting code       ├─ Design decisions
├─ Missing LLM output validation           ├─ Large fixes (>20 lines)
├─ Version/path mismatches                 ├─ Enum completeness
├─ Variables assigned but never read       ├─ Removing functionality
└─ Inline styles, O(n*m) view lookups     └─ Anything changing user-visible behavior
```

**Rule of thumb:** If the fix is mechanical and a senior engineer would apply it
without discussion, it's AUTO-FIX. If reasonable engineers could disagree about
the fix, it's ASK.

---

## Suppressions — DO NOT flag these

- "X is redundant with Y" when the redundancy is harmless and aids readability
- "Add a comment explaining why this threshold was chosen" — thresholds change, comments rot
- "This assertion could be tighter" when the assertion already covers the behavior
- Suggesting consistency-only changes with no functional benefit
- "Regex doesn't handle edge case X" when the input is constrained and X never occurs
- Eval threshold changes — these are tuned empirically
- Harmless no-ops
- ANYTHING already addressed in the diff you're reviewing — read the FULL diff before commenting
