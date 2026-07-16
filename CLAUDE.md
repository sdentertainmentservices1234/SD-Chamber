# SD Chamber — Claude Code handover

Chamber-management PWA for a Supreme Court senior advocate's chamber. Save this
file as `CLAUDE.md` in the repository root — Claude Code reads it automatically.

## What this app is

A work-allocation and cause-list tool **between the clerk and the juniors**.
The senior advocate is deliberately NOT a user (role removed by owner decision).

## Review-pass changes (Jul 2026, most recent)

- **Board nav label is dynamic** (`paintChrome()`): colleagues land on the
  personal `renderMyWork()` home, so their sidebar/mobile board item reads **"My
  work"**; Staff/admin keep **"Work board"**. Label matches the page.
- **New-brief assignment mode** (`briefForm()`): a `.seg` toggle — **Choose
  colleague** (the existing checklist, now with each person's active count) vs
  **Auto-assign** (roster engine, with a live `#autoPickName` preview of who it
  lands on). Save-time auto path reuses `pickNext()` + `advancePointer()` and
  records `assignHistory` mode `auto`/`forced`, identical to the standalone
  `autoAssign()`. `asgnMode` var drives it; `directed` is manual-only.
- **Roster fairness view** (`renderRoster()`): a colleague sees a
  `.roster-standing-banner` ("You're #N in the rotation · next up in K turns ·
  carrying … active … lifetime") and a **You** tag + `.is-me` accent on their
  own row. Banner is colleagues-only (Staff/admin aren't in the rotation).
- **Demo seed** (`make-test.py`): dropped the fake "Sample holiday/Sample
  vacation" clutter; seeds the real SC summer-vacation range via
  `config/vacation` so the preview shows true calm shading.

## Branding & onboarding copy (Jul 2026)

- **SD logo**: gold Fraunces "SD" with a hairline underline (echoes the app
  icon). `.sb-logo` in the sidebar masthead (gold on navy); `.brand-mark` =
  navy rounded tile w/ gold SD on the light auth + pending cards. Colour scheme
  unchanged (navy #101418 / gold #cbb682 institutional).
- **Onboarding relabelled** away from "invite / pre-approve" to just **"Add
  member"** (owner's call — Adith enters real members, no approval step in his
  head). The MECHANISM is unchanged: still `approvals/{emailLower}` claimed on
  first sign-in (the only credential-free way — Firestore users are uid-keyed).
  Button "Add member", panel "Members — awaiting first sign-in", form fields
  name/email/role/phone/joinedOn. Junior signs in with that email + "Set your
  password". Keep the approvals-doc plumbing; only the words changed.
- **Roster shows added-but-not-logged-in members** (`rosterDisplay()` merges
  role=junior approvals into the seniority list, tagged "awaiting first login",
  no loads). effectiveRoster()/assignment still use logged-in `users` only —
  a member with no uid can't be assigned/ack until they activate. The People
  directory (Chamber tab) stays alphabetical-by-role; the Roster is seniority.

## Terminology (Jul 2026 — display only)

The owner renamed the user-facing labels: **Clerk → "Staff"**, **Junior →
"Chamber Colleague"** (plural "Chamber Colleagues", shortened to "Colleagues"
where space is tight). The internal role KEYS are unchanged (`clerk`,
`junior`) — data, comparisons (`me.role==="junior"`), `juniors()`,
`juniorUid(s)`, `heldForClerk`, and the security rules all still use the old
keys. Only `ROLES` labels and rendered copy changed. Keep it that way; a key
rename would touch Firestore data + rules for no benefit.

## Roles & onboarding (Jul 2026 — load-bearing)

Three personas, split by a hard rule: **all TECHNICAL feeding is Adith's; the
clerk only does day-to-day operational input.**
- **admin** (Adith Deshmukh, `adithdeshmukh@gmail.com`): members, their contact
  details + joining dates, email pre-approval, matter weights, holiday calendar.
  Recognised BY EMAIL (`CHAMBER.adminEmail`) as well as by `role:"admin"`, so
  his first-ever login is admin with no chicken-and-egg — **never remove the
  email check**. `isAdmin()` / `canAdmin()` gate every technical surface.
- **clerk/pa**: matters (briefs), conferences, senior availability, day sheet,
  assignment. `canManage()` = admin+clerk+pa. Clerk is NOT technically adept —
  no member management, no weights, no holidays surface at all.
- **junior**: self-onboards. Adith pre-approves their email
  (`approvals/{emailLower}` with role+details) → junior visits the app, uses
  **"Set your password"** (`auth.signUp` = createUserWithEmailAndPassword) →
  `onAuthStateChanged` claims the approval, creates their `users/{uid}` at the
  approved role, deletes the approval. No manual approval step. An un-invited
  sign-in lands as `pending` (the "Not approved yet" screen). Demo has no real
  auth, so the Chamber tab exposes a **"Simulate sign-in"** button on each
  invite to exercise the claim end-to-end.
- **Restore credit for a re-added colleague (Jul 2026):** because members are
  id-keyed, deleting a colleague (e.g. wrong email) and adding them back mints a
  NEW id — their old matters still name the OLD id, so their credit disappears.
  Nothing is destroyed: `orphanAssignees()` finds assignee ids referenced in
  briefs / day sheets / leaves that are neither a current member nor a live invite
  (`currentIdSet()`), and an **admin-only "Restore credit" panel** on the Team →
  Workload snapshot view lets Adith map each orphan onto the right colleague.
  `remapAssignee(oldId,newUid)` rewrites assignedTo / everAssigned / ackBy /
  assignHistory(.uid+.by) / declinedBy / creditClaim across briefs, juniorUids on
  day sheets, and leaves.uid — deduping so a shared matter isn't double-counted.
  Works for a deleted invite (`pending:wrongEmail`) or a removed uid. jsc-verified
  (detect + remap + dedup, no false positives) + live UI test (add invite → assign
  → delete invite → restore onto a colleague). `remapAssignee` updates the local
  `briefs`/`dsAll`/`leaves` optimistically before the Firestore echo, so the panel
  clears at once instead of lingering a round-trip (owner: "still flashing").

## Display board — Regular list is numbered 101+ (board.html)

Regular-list matters are numbered from **101** up (Miscellaneous holds 1–100), and
the court finishes its whole Misc list (main + supp) before starting Regular. In
`classify()` for a `listType=Regular` matter: while the court is still on Misc,
`gap = miscLeft + (regRank − 1)` where `regRank = itemNo − 100` (item 101 = the 1st
Regular matter, so it's `miscLeft` away, NOT `miscLeft + 101`). `miscLeft` comes
from the causelist Misc total (`miscTotalFor`, main+supp) or the live sequence
position. `onRegularList()` treats **any current board item ≥ 101** as "Regular has
started" (`REG_BASE=101`) and then falls through to normal within-Regular proximity
(both items are 101+, so they compare directly). Shows "Reg N · Misc: K to go".
jsc-verified (Reg#101 behind 11 Misc → 11 not 112; reached-Regular → within-list).
Priorities, in the owner's words:

1. **Primary:** work allocation and distribution among ~10 juniors
2. **Secondary:** clerk's ease in preparing the daily chamber cause list
3. **Third:** linking those two functions
4. **Ancillary:** linking assigned matters to their records (Drive links) accessible to all

Human context that shapes every decision: **Adith (the owner) runs the
infrastructure; the clerk is technologically challenged** — he can prepare a
cause list and send files on WhatsApp/email, nothing more. Every clerk-facing
flow must stay at that level: type court+item, click share. Everything is
shared within the chamber — no information walls between members (owner's
explicit instruction; the old senior-notes restriction was removed from both
UI and rules).

## Deployment state (as of handover)

- **Live app:** https://sdentertainmentservices1234.github.io/SD-Chamber/
- **Repo:** `SD-Chamber` under GitHub user `sdentertainmentservices1234`
- **Firebase project:** `sd-chamber-1aa78` (Auth email/password ON, Firestore
  in `asia-south1`, rules published — current version below)
- **firebaseConfig is baked into index.html** (public by design; security is
  in the rules): apiKey AIzaSyAagQ_-1LLvKtmsfJwSPJvURHWB-FkO-NQ, project
  sd-chamber-1aa78, appId 1:287957629475:web:9c7804acf3060c73abcf96,
  storageBucket sd-chamber-1aa78.firebasestorage.app
- **IMPORTANT divergence risk:** the owner edited `seniorName` directly on
  GitHub with the pencil editor. Any regenerated index.html from this codebase
  has `PASTE_SENIOR_NAME_HERE`. Before pushing a new index.html, read the live
  repo's current seniorName and carry it over, or you will clobber his edit.
- First clerk bootstrap (Firebase Auth user + Firestore role flip to `clerk`)
  was in progress at handover — verify a `users` doc with role `clerk` exists
  before assuming multi-user flows work.

## Files

| File | Purpose |
|---|---|
| `index.html` | Production app. `const DEMO = false;` + real firebaseConfig. |
| `demo.html` / `app.html` | Same code with `DEMO = true` — in-memory mock, seeded sample chamber, amber "View as" role switcher. No login. |
| `sw.js` | Service worker (Jul 2026): the app **HTML is NETWORK-FIRST** so a deployed change is live on the next open (cache is only the offline fallback); the heavy immutable libs — **Firebase SDK + fonts + Tabler icons are CACHE-FIRST** so mobile stays fast. NEVER caches Firestore/Auth/`court-updates.json` (live data). Registered from index.html head. `CACHE` now `chamber-shell-v9`. `board-sw.js` = same pattern for the war room (`sdboard-v3`). NOTE: the previous stale-while-revalidate version made HTML one-open-behind (owner: "change is not live") — hence network-first HTML. |
| `manifest.json` | PWA manifest (navy #101418, maskable icons). Linked from index.html head. |
| `icon-192.png` / `icon-512.png` / `apple-touch-icon.png` | App icon: gold "SD" monogram in Fraunces on the sidebar-navy. Regenerate with `python3 make-icon.py` (Pillow + Fraunces TTF, self-downloading); never hand-transcribe base64. |
| `firestore.rules` | Security rules — **git-ignored by owner's decision (Jul 2026), kept only locally / in the Firebase console**, NOT hosted on GitHub. Recover the last committed copy with `git show f2073ff:firestore.rules`. Still the source of truth for what the console rules must be. |
| `test.html` | Real-chamber test build (owner's juniors + the 13.07.2026 paper list), regenerated by `make-test.py`. Never deploy it. |
| `make-test.py` | Rebuilds test.html from index.html after edits: `python3 make-test.py`. |
| `fetch_causelist.py` + `.github/workflows/causelist.yml` | Scheduled Action: fetch SC lists → per-court benches → commits `court-updates.json` (repo root). See the SC cause-list section + CAUSELIST-SETUP.md. Test the parser OFFLINE against saved PDFs; don't hammer the live site in dev. |

Single-file architecture is deliberate (owner deploys by uploading one file,
edits via GitHub pencil). Do not split into modules without his say-so.

## Architecture

One `<script type="module">`. Two-branch data layer selected by `DEMO`:

```js
db.watchCollection(path, cb, [orderField, dir]) -> unsub   // cb gets [{id,...}]
db.watchDoc(path, cb) -> unsub                              // cb gets {id,...}|null
db.set(path, data, merge) / db.add(path, data) / db.update(path, data) / db.remove(path)
db.now()            // serverTimestamp in prod; {_t: Date.now()} in demo
auth.onChange / signIn / signOut / setUser(demo only)
```

Demo branch: in-memory Map store + synchronous listeners + `seedDemo()`
(50 matters, deliberately skewed distribution, SC index for today, demo
eventualities). Prod branch: Firebase v10.12.2 ESM from gstatic CDN,
top-level await imports.

**Subscription lifecycle (fixed bug — do not regress):** `auth.onChange`
tears down ALL watchers (`unsub[]`, `dsUnsub`, `scUnsub`, `userDocUnsub`) and
re-boots per user via a `booted` flag inside the users/{uid} watchDoc callback.
The old code only booted once, so data went stale after user switches.

Timestamps are dual-format everywhere: demo `{_t: ms}`, prod Firestore
Timestamp. Read with `x?._t ?? x?.toDate?.()` patterns; keep both paths alive.

## Data model (Firestore)

- `users/{uid}`: name, email, phone (for WhatsApp nudges), role
  (`admin|clerk|pa|junior|pending`), active, joinedOn (ISO date — sets chamber
  seniority; juniors sort by it everywhere, roster order derives from it)
- `approvals/{emailLower}`: {email, name, role, phone, joinedOn, by, at} —
  Adith's email pre-approvals. Keyed by the LOWERCASED email so rules can
  recompute the key from `request.auth.token.email.lower()` and verify the
  claimed role. Consumed + deleted on that person's first sign-in.
- `briefs/{id}`: caseTitle, diaryNo ("12345/2026"), caseNo, matterType,
  appearingFor, aor, status (`received|assigned|prep|ready|conf|listed|disposed`),
  priority, directed, detailsAwaited (auto: no diaryNo AND no caseNo),
  nextDate/conferenceAt (ISO), assignedTo[], everAssigned[], ackBy[],
  assignedAt (ms), declinedBy[{uid,ground,note,at}], heldForClerk,
  assignHistory[{uid,at,by?,mode}], createdBy/At, updatedAt
  - subcollections `comments/{id}` + `files/{id}` EXIST in the rules but their
    UI (Files & Discussion in the brief detail) was **removed Jul 2026** (owner:
    file/note upload is a later phase). Rules left in place (harmless); re-add
    the brief-detail sections when that phase resumes. Current app scope: brief
    details, causelist, work distribution + roster only.
- `daysheets/{YYYY-MM-DD}`: {date, entries[], conferences[], updatedAt, updatedBy} —
  entries: {briefId?, caseTitle, courtNo, itemNo (free text — "MM" = mentioning),
  listType (one of CAUSELIST_TYPES: Miscellaneous/Regular/Chamber/Single Judge/
  Registrar/Curative & Review — keys the SC bench lookup), time (default
  "10.30"), bench (auto-filled from the SC causelist by court+type+date), counsel
  (briefing counsel, autofilled from brief.aor), juniorUids[], juniorUid (legacy
  = juniorUids[0]; keep writing both, read via `jrsOf(e)`), remarks, done}. conferences: {time, name, briefId?} —
  the paper's evening "Conferences and meetings" list; clerk board auto-suggests
  briefs whose conferenceAt falls on that date. One doc per day, last-write-wins
  (acceptable: one clerk + one PA). Modelled 1:1 on the clerk's real paper cause
  list (letterhead → matters with bench + "briefing counsel — chamber juniors" →
  conferences by time).
- `scindex/{YYYY-MM-DD}`: {date, entries[], loadedBy, at} — parsed SC list:
  {court, item, diaryNo, caseNo, title, raw}
- `availability/{uid_date}`: {uid, date, status:`available|incourt|half|leave`, note}
- `config/roster`: {pointer:int} — order is no longer stored (owner's Jul 2026
  decision): the roster IS seniority order from users.joinedOn, senior-most
  first; manual reordering was removed. Old docs' `order` field is ignored.
- `config/weights`: {matterType: int 1–9} — live matter weights, editable from
  the Roster tab (clerk/pa). Merged over DEFAULT_WEIGHT in code; absent doc =
  defaults. Covered by existing config/* rules — no rules change needed.
- `config/holidays`: {dateISO: name|null} — SC holidays/vacations, entered by
  the clerk from the Calendar (per-day via day detail, or the "Mark holidays /
  vacation" range tool; null = cleared, checked via `!= null`). Deliberately
  under config/* so existing rules cover it.
- `config/senioravail`: {dateISO: note|null} — days the SENIOR is not
  available (he is not a user; the clerk inputs this). Same null semantics,
  same config/* rules rationale.

## Calendar (home screen — owner's request, Jul 2026)

The default tab for everyone (`curTab="cal"`; sixth mobile tab). Month grid,
Monday-first, Fraunces day numerals. Weekends auto-shaded "Non-sitting";
holidays tinted warn-bg with the name; senior-away days flagged with a
user-off icon; today ringed in accent. Per-day chips: total active matters
with that nextDate (everyone), "N mine" (juniors only — their assignedTo),
"N conf" (from that date's daysheet doc — the whole `daysheets` collection is
watched as `dsAll` for this). Clicking a day opens a detail sheet: the holiday-name input is ADMIN-ONLY
(technical feeding), the senior-availability input is clerk/pa/admin; plus the
day's matters (clickable), conferences, and an "Open day sheet" jump that sets
dsDate and switches tabs. The "Mark holidays / vacation" range tool is admin.
SC holiday data is ENTERED BY THE CLERK (range tool for vacations) — do not
fabricate/hardcode holiday dates; a future autofetch from sci.gov.in could
populate config/holidays the way the cause-list Action populates scindex.

## Assignment engine (the heart — owner's primary purpose)

- `weightOf(brief)` = `Math.max(1, Number(b.weight)||1)`. Weight is an OPTIONAL
  per-brief field the STAFF sets on the brief form (owner's call Jul 2026 —
  the old matter-type weight table + config/weights + Roster-tab editor were
  removed). Blank = 1 (every matter counts equally). `hasWeight(b)` gates the
  "N×" chips so unweighted matters show nothing.
- `isImminent(b)`: nextDate within 0–4 days → that brief counts **double**
  in `activeLoad(uid)`. This is how "junior busy with a matter coming up"
  auto-repels new work.
- `lifetimeCount(uid)`: LIFETIME count — every brief ever assigned
  (everAssigned), disposed included, counted **1 each — NO weightage** (owner's
  decision Jul 2026: weightage is only for immediate distribution, not the
  career clock). `totalLoad` (the old weighted-lifetime fn) was removed.
- `pickNext(brief, exclude)`: eligible = effectiveRoster() (= seniority order)
  minus declinedBy minus on-leave-today. **Fair-distribution cap (Jul 2026,
  owner's rule):** anyone who has taken **≥ CATCHUP_MAX (2)** fresh matters in
  the last **CATCHUP_WINDOW_MIN (90 min)** is held out of the pool (unless that
  empties it), so a batch spreads instead of piling on the lightest person —
  `recentAssigns(uid)` counts non-disposed assigned briefs with `assignedAt`
  inside the window. The remaining pool is ranked by (activeLoad asc [lightest
  first — skips the busy], then recentAssigns asc, then lifetimeCount asc, then
  turn-distance from `roster.pointer` asc) — "active → recent → lifetime → turn".
  **Leave-clash skip (Jul 2026, owner's rule):** the matter's hearing date
  (`brief.nextDate`, or the day-sheet listing date passed in) blocks any colleague
  on leave that day OR the day before — prep happens the day before, so leave on
  the 12th bars matters listed on the 12th AND 13th. `leaveClash(uid,hearingDate)`
  = `onLeaveOn(hearingDate) || onLeaveOn(dayBefore(hearingDate))`; with no date on
  the brief it falls back to `isSkippable` (on leave today). Every pickNext call
  site now passes the date (autoAssign/objection via `brief.nextDate`; day sheet
  via the listing date; brief form via `b_next`). jsc-verified + live (Vikram on
  leave 19th → skipped for a 20th matter, still fine for the 18th). **The SAME
  `leaveClash` window governs CREDIT (Jul 2026):** `presentSharers` /
  `shareForDate` now zero a colleague's share when he's on leave on the matter's
  date OR the day before (prep day) — so a co-assignee on leave the day before a
  listing earns no credit even if back on the listing day, and his share
  redistributes to whoever actually carries it. This flows through `shareFor` →
  `activeLoad` / `lifetimeCount` / `loadInWindow` (load and credit stay coupled, as
  before). 12-case jsc suite: leave-prev-day → 0, leave-2-days-before → kept,
  deleted leave ignored, both-out → nobody credited.
- **Workload snapshot is a CALENDAR period (Jul 2026 fix), not a rolling ±window.**
  The Chamber-tab week/month/year tally (`loadInWindow`/`casesInWindow` via
  `periodRange`) attributes a matter to the calendar week (Mon–Sun) / month / year
  of its **listing date**, NOT by `assignedAt`. Old bug: a ±30-day "month" window
  from mid-July spanned into August AND counted by assign date, so a matter listed
  4 Aug showed in July's tally. Now: listed 4 Aug → counts only in August's
  week/month (and the current year); a matter with a July listing + an August next
  hearing counts once in each month (per appearance); an undated active matter
  counts in the current period. jsc-verified (10 cases) + live (week ≤ month ≤ year
  monotonic, drill-down works, no errors).
  So standing load decides WHO is next; the cap only limits the RATE of catch-up
  (a returning-light colleague gets ~2 then the rotation moves on, and keeps
  catching up in the next window). Proven with a jsc sim vs the real functions:
  burst 0-vs-5 → gets 2 not 6; 0-vs-20 → still capped at 2; equal loads → clean
  round-robin. If none eligible → **forced** assign to lightest-loaded non-leave
  member, `{forced:true}` (flagged toast). Auto-pick previews now show the pick's
  load ("Name · N active — lightest") for transparency.
- `autoAssign` sets assignedTo=[pick], status=assigned, resets `ackBy=[]`,
  stamps `assignedAt`, appends assignHistory, then `advancePointer()`.
- **Objections:** normal brief → auto-advance to next eligible (objector
  excluded per-brief via declinedBy), pointer advances. **Directed brief**
  (`directed:true`, "on Senior's direction") → NO auto-advance; sets
  `heldForClerk:true`; clerk's board shows a held notice with "Keep as
  assigned" (clears hold) or manual reassign. Directed assignment does NOT
  consume a roster turn but DOES count toward load.
- **Acknowledgment:** every (re)assignment starts unacked. Junior sees banner
  + "Acknowledge assignment" button; clerk sees "unseen · Nd" ageing on the
  board and per-assignee clock icons in the detail; WhatsApp "Nudge" buttons
  (see below).
- Manual assignment via briefForm keeps acks only for still-assigned juniors;
  new assignees need fresh ack; clears heldForClerk if team changed.
- Roster tab: fixed seniority order (joinedOn; no reordering), "Next up"
  marker, per-junior joined date + active load / total load / live / lifetime
  / objection counts, pointer reset, and the matter-weights editor (clerk/pa).

## Cause list (owner's "nothing would beat this" feature)

Flow: SC list gets indexed once per day → clerk types **Court + Item** →
entry autofills (title/caseNo/diaryNo), matches the register (diaryNo exact
match first, then caseNo substring), pre-tags assignedTo[0] as junior; no
register match → added with remarks "Not in register". Duplicate court+item
refused. Entries auto-sort by court then item.

Index sources, in priority order:
1. `data/scindex-<date>.json` in the repo (committed by the GitHub Action) —
   fetched same-origin on Pages, flagged `fromRepo:true`, wins over Firestore
2. `scindex/{date}` Firestore doc, written by the in-app "Load SC list" paste
   modal (paste PDF text → `parseSCList()` → saves index AND offers
   checkbox-add of chamber matches)

`parseSCList(text)`: tracks `COURT NO.` headers; `^(\d{1,3})[.)]\s` starts an
item; block scanned for diary (`\d{3,6}[/-]\d{4}`), caseNo (prefix regex:
SLP|W.?P|C.?A|CRL.?A|T.?P|R.?P|M.?A|CONMT|CONT|ARB|CUR|DIARY), and
"X Versus Y" title. Best-effort; hardening against real PDFs is pending.

**Share** button (day-sheet toolbar, visible to all members once the sheet has
content) opens an editable plain-text preview in the clerk's own paper format —
`SENIOR NAME / SUPREME COURT (DAY) DD.MM.YYYY`, then per matter
`n) Ct-<court>#<item> — <time>` / title / `Bench: …` / `counsel — junior / junior`
/ `(remarks)`, then `Conferences and meetings:` with `time — name` lines — with
Copy / WhatsApp (`wa.me/?text=` on mobile, `web.whatsapp.com/send?text=` on
desktop, UA-sniffed) / mailto buttons acting on the edited text. This IS the
clerk's delivery mechanism; composer lives in `shareText()`/`shareDaySheet()`.
**Print** button (beside Share) — `printCauseList()` opens a print window in the
clerk's PAPER format: centred `SENIOR NAME` (big caps) + italic "Senior
Advocate", underlined `SUPREME COURT (DAY) DD.MM.YYYY`, then the six-column
table (Court/Item · Time · Case Name · Judges · Advocates Name · Total matter;
Advocates cell = briefing counsel over "/"-joined colleagues), then Conferences.
EB Garamond (Google Fonts) 14px, serif fallback. Print is triggered from the
PARENT after `w.document.fonts.ready` — no inline script in the written HTML.
Admin is a `canManage()` superset, so Adith can add matters + print like Staff.

## SC cause-list auto-fetch (Jul 2026 — owner's "enrich entered listings" model)

Ported+reworked from the ASD app's proven pipeline. Files: `fetch_causelist.py`,
`.github/workflows/causelist.yml` (hourly 08:00–23:00 IST Mon–Sat), output
`court-updates.json` at repo root, `CAUSELIST-SETUP.md`. The fetcher is
change-detecting: `probe_size()` does a 1KB ranged GET per list URL and reuses
the previous parse (stored `sources:{date:{suffix:size}}` in the output) unless
a size changed; identical results leave the file unwritten so the workflow
commits nothing (`generated_at` = time of last CHANGE). App side: a long-open
tab re-fetches court-updates.json on visibilitychange / Day-Calendar tab switch
when older than 10 min (`courtUpdatesAt`/`courtUpdatesStale`). **Model:** the scheduled Action can't read
Firestore, so it does NOT search for the chamber's matters (owner rejected the
ASD watchlist/name-discovery approach). It downloads the 6 SC list PDFs for a
rolling 8-weekday window and extracts, per (date → list-type → court), the
**bench (coram)** + total/fresh. Staff enter court/item/**listType**/date on the
day sheet; the app (`loadCourtUpdates` → `coramFor(date,type,court)` →
`cleanCoram`) auto-fills the authoritative bench and prints it. No watchlist.json.
Jul 2026 UPGRADE: the fetcher also stores `items:{itemNo: case-line}` per court
(case number + parties, ~96KB/day for ~1150 items). The Add-matter form now
takes just **court + item** as the primary inputs; `lookupCauselistItem(date,
court,item)` searches ALL list types (item-number ranges differ so court+item is
unique) and fills case title (`titleFromCauseLine`), list type, and bench.
Everything else on the form is optional.
- Item capture (Jul 2026): parse_courts grabs the petitioner line + the line
  after "Versus" (`caseLine` = "PET .. VERSUS RESP .."). **total/main/supp count
  only SERIAL matters** via `n_matters()` = keys without a "." — connected matters
  are stored as sub-items ("4.1", "102.2") for lookup but the court lists them
  UNDER their main item, so counting them (old `len(items)`) over-reported every
  court (Court 5's 30 read 32). PARSER_VERSION bumped so the Action re-parses all
  cached dates. App `titleFromCauseLine` strips the case-no prefix, splits on
  VERSUS, trims each side at "& Ors./and Anr." (drops the trailing AoR),
  title-cases → "Petitioner vs Respondent". Bug fixed: the entry form tracks
  what IT auto-filled (`auto{title,bench,type}`) so typing item "3"→"30" lands
  on the FINAL item's case, and a value the clerk edits is never overwritten.
- Briefing counsel is an `<input list="lawfirms">` datalist of top Indian firms
  (`LAW_FIRMS`) — pick or type any AoR. Each entry has an optional `confTime`
  (add now or edit later). `conferenceList(date)` builds the Conferences section
  (day sheet + print + share) from entries' confTime: "time — counsel", and
  when a counsel has >1 conference that day, "(FirstWordOfCauseTitle)". Manual
  daysheet.conferences[] merge in.
- `resolveEntry(e,date)` returns title/bench/listType/total from the entry
  falling back to the fetched causelist — used by rail, table, share AND print
  so a court+item-only entry completes once its list is fetched.
- Print heading = "SUPREME COURT (DAY) DATE"; `<title>` (= saved PDF file name)
  = "SD Causelist DATE". Columns: Court/Item (one line) | Time | Case Name |
  Judges | Advocates | Total & Seq. (court total + item seq). EB Garamond 14.
- **Ordering (Jul 2026, owner's rule):** `byCourt(arr, date)` groups by LIST TYPE
  first — every court finishes its Miscellaneous list before its Regular list, so
  ALL Misc matters (court-wise) print before ANY Regular matter, then the rest, in
  `CAUSELIST_TYPES` order (`_typeRank`). Within a type: court, then item. An entry
  carrying a `listType` is used directly; a court+item-only entry resolves its type
  via `resolveEntry(e,date)`. Single sort → day sheet display, print AND share all
  follow it. **Print fits one page for a busy day** (owner's 12-matter 15th + two
  conference days): top margin cut (`@page margin:6mm 11mm 8mm`, `body margin:0`
  — header sits at the top edge). Font sizing balances "one page" against the
  clerk's **"too small / too faint"** feedback: **weight 500 throughout** (EB
  Garamond 400 printed faint; headers 700, and the font link now loads the 500
  weight), case name 13px, judges/advocates 11px (cols widened to 114/120 so names
  don't wrap), court/item 13.5px, line-heights ~1.2. Conferences use a
  DETERMINISTIC two-column flex (`.cfsplit`/`.cfcol`), NOT CSS multicol (which
  balanced unpredictably and fragmented onto page 2): one conference day → its
  rows split left/right; two+ days → each day fills a column (e.g. 8 on the
  14th-evening left, 2 on the 15th-morning right). Measured faithfully against an
  A4 box (REAL print CSS, heavy 12-matter rows): ~1028px vs ~1070px printable →
  ~42px headroom. **Don't enlarge the font without re-measuring the worst-case fit.**
- Jul 2026 (2nd pass): Add-matter form order = **Causelist type FIRST**, then
  court+item (lookup is scoped to the chosen type — `lookupCauselistItem(...,
  preferType)`). Fetcher captures **sub-items** (ITEM_LINE_RE = `N` or `N.M`,
  e.g. 37.1 "Connected .."). Party cleaning: `cleanCauseSide` strips the
  case-TYPE prefix ("SLP(C) No.") even when the number sits on the next PDF
  line, strips a leading "Connected", trims trailing AoR at "& Ors./and Anr.".
  `partiesFromCauseLine`→{pet,resp}; `renderTitle(title,appearingFor,mode)`
  bolds the side we appear for (`<b>` in html, `*..*` in WhatsApp text) — entry
  has `appearingFor`. Time + conference time are `<input list="courttimes">`
  (COURT_TIMES datalist).
- List-type → PDF suffix (verified against real 13-07-2026 PDFs, via an
  authorised one-time probe): Miscellaneous `M_J`, Regular `F_J`, Chamber `M_C`,
  Single Judge `M_S`, Registrar `M_R`, Curative & Review `M_CC`; `_1` main,
  `_2` supplementary. Server returns 200-HTML for missing files, so `fetch_pdf`
  checks Content-Type is application/pdf.
- `parse_courts()` (in the fetcher) collects the coram only on a court's FIRST
  header (page headers repeat → would duplicate). `cleanCoram()` (in the app)
  turns "HON'BLE MR. JUSTICE …" into the clerk's short form; the honorific regex
  needs `\b` (else "MRS" matches "MR" and leaves a stray "S.").
- Validated OFFLINE against real downloaded PDFs (never hammer the live site in
  dev). court-updates.json fetched with `?_=Date.now()` + no-store (Pages CDN).
  A 13-07-2026 seed is committed; the Action overwrites it on first run. Owner
  must enable workflow write permission + run once (see CAUSELIST-SETUP.md).

## SC annual calendar import (Jul 2026)

The SC publishes an annual calendar (image PDF, no text layer — can't auto-parse)
each Nov/Dec. `SC_CALENDAR` encodes it per year: `holidays:[[from,to|null,name]]`
+ `vacation:[[from,to,label]]` (summer partial-court period). Calendar tab →
**Import SC calendar** (admin): one-click `applySCYear(year)` expands the ranges
into `config/holidays` (merge) and writes `config/vacation`; a paste box takes
future years line-by-line ("YYYY-MM-DD Name" / "YYYY-MM-DD to YYYY-MM-DD Name").
`config/vacation` = {ranges:[[from,to,label]]}, watched into `vacation`;
`isPartial(iso)` shades vacation weekdays "Partial court" (holiday > weekend >
partial priority). To add a year: extend `SC_CALENDAR` from the published PDF.

## Lookup note

`lookupCauselistItem(date,court,item,preferType)`: a chosen `preferType` is
AUTHORITATIVE — NO cross-type fallback (picking Miscellaneous can't return a
Registrar matter). Only an empty type searches all lists. The form message
distinguishes "no list fetched for this date" from "not in the <type> list".

## Calendar & brand visuals (Jul 2026 — calmed down)

- Calendar cells are NEUTRAL. The only strong colour is a small workload DOT in
  a pill beside the count: `.ld.lg`<5 green, `.ld.ly`5–10 amber, `.ld.lr`>10 red
  (load = max(register next-dates, day-sheet entries)). Non-working days get one
  faint mute + a thin left accent: `.day-hol` purple, `.day-vac` amber,
  `.day-off` weekend (no accent) + a muted `.cal-tag`. One-line dot legend.
  (Owner found the earlier full-cell tints overwhelming — keep it restrained.)
- **Refresh button** (topbar, `#btnRefresh`/`hardRefresh`): clears caches +
  updates SW + reloads with cache-buster — for installed PWAs holding an old
  shell. sw.js CACHE bumped when the shell changes (currently v3).
- Brand: circular seal emblem `.brand-mark` (navy field, double gold rule, gold
  Fraunces SD) on the login + pending cards; `.sb-logo` is the ring-emblem
  variant in the sidebar. Login = radial navy gradient, gold "CHAMBERS OF",
  Fraunces name + short gold rule. Stay within navy #101418 / gold #cbb682.

## Colleague "My work" home (Jul 2026)

Juniors are phone-first users, so the Work-board tab renders `renderMyWork()`
for `me.role==="junior"` (Staff/admin keep the distribution board). It's a
personal home: 4 metrics (to-acknowledge / my active / coming-up ≤4d / roster
position), a one-tap availability set (Available/In court/Half day/On leave →
`availability/{uid}_{today}`), an "acknowledge / object" card per unacked
assignment, their matters sorted by next date (imminent flame), and roster
standing ("#N · next up in M turns · X active · Y lifetime"). App is responsive
throughout: fixed sidebar ≥860px, dark bottom-nav <860px.

## Out-of-app notification

`waLink(uid, brief)` → WhatsApp deep link with prefilled nudge message;
mobile→wa.me, desktop→web.whatsapp.com (clerk uses WhatsApp Web on his PC,
QR-paired once). Copy-message fallback button beside every nudge. Phone
stored per user (10 digits → auto-prefix 91). True push (FCM + Functions)
is explicitly v2.

## Design system (do not drift)

Modern institutional, spacious. Tokens in `:root`: bg #f5f5f3, ink #141719,
sidebar #101418, single accent #3a5a8c, gold #cbb682 only in sidebar-active/
demo bar. Fonts: Fraunces (serif — masthead, page titles, case titles, metric
numerals ONLY), Inter (UI), IBM Plex Mono (diary/item/court numbers).
Desaturated status chips. Desktop: fixed left sidebar; mobile ≤860px: sidebar
hidden, dark bottom tab bar (5 tabs). **Board defaults are OPEN** (owner's
Jul 2026 reversal of the earlier collapse-by-default): balance panel starts
open, junior cards start expanded (`uiExp.cardsClosed` tracks user collapses).
Day sheet renders as the clerk's paper TABLE on desktop (>860px: Ct/Item ·
Time · Case & Bench · Counsel — Juniors · Remarks) and as the card rail on
mobile — both markups render, CSS switches. Still collapsed: day-sheet clerk
tools behind "⋯" (rail only), detail Files/Discussion, roster explainer.
Unassigned queue is ALWAYS open (it's the action list).
Icons: Tabler webfont via jsdelivr CDN.

## Security rules (`firestore.rules` now IN the repo — reconstructed)

`firestore.rules` was MERGED (Jul 2026) from the owner's actual live console
rules + the new features: admin role (by email AND role, get()-safe against a
missing users doc), `approvals` (read: any signed-in; write: admin; self-delete
of own invite), `config/holidays` (admin), `config/senioravail` (canManage),
constrained self-create of `users/{uid}` (role must be `pending`, or the admin
email, or match a pre-approval keyed by lowercased email). config is enumerated
so the catch-all (admin-only) never widens holidays. Still must be PUBLISHED in
the console by the owner. If `CHAMBER.adminEmail` changes, change it here too.

## Security rules (legacy notes; keep in lockstep with app writes)

Junior may update ONLY these brief fields (rules enforce):
`status, updatedAt, ackBy, declinedBy, heldForClerk, assignedTo, everAssigned,
assignHistory, assignedAt` — i.e. status moves, acknowledge, and the
objection's onward reassignment. Any new junior-writable field MUST be added
to that hasOnly list or production silently permission-fails where demo works.
`config/*`: clerk/pa full; any approved member may change `pointer` only
(objection advances rotation). Files/comments: any approved member reads all,
creates own; clerk/pa delete. daysheets rule still mentions role `senior` —
vestigial, harmless, cleanup candidate. If rules change, the owner must
re-paste in Firebase console (walk him through it; he edits nothing locally).

## Testing conventions (all proven in this project)

- Syntax gate after every edit: extract the module script → `node --check`.
  **The owner's Mac has no Node.** Use JavaScriptCore instead:
  `/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc`
  with a tiny script calling `checkModuleSyntax(readFile("_mod.mjs"))`.
  Behaviour checks: `python3 -m http.server` + the harness's preview tools
  (demo copy = `sed 's/const DEMO = false;/const DEMO = true;/' index.html >
  app.html` — the repo does not actually contain demo.html/app.html).
- Behaviour: Playwright headless Chromium against `file://.../app.html`
  (demo mode), viewport 1320×1000 desktop / 390×844 mobile, collect
  `pageerror`. Role-switch via `#demoRole` select (all seeded users listed)
  or `window.__demoSetUser(uid)`.
- Known harness quirks: clipboard writeText is permission-denied headless
  (not a bug); after modal submits, clear `#modalRoot` between steps;
  select_option fails if the option isn't in #demoRole.
- Engine logic: replicate pickNext in a standalone node script for unit
  tests (lightest-load, leave-skip, objector-exclusion, forced fallback,
  20-round fairness spread ≤3).

## Known wrinkles / cleanup candidates

- Dead code in `seedDemo`: an empty `Object.entries({b23:...}).forEach` block
  (harmless leftover; remove when touching the seed).
- PWA is now fully wired (Jul 2026): manifest linked, apple-touch-icon, iOS
  meta tags, SW registered, "SD" monogram icons. An already-installed shortcut
  keeps its OLD icon until removed and re-added to the device.
- Demo seed titles/numbers are synthetic; `scindex` demo entries mirror seed
  formulas (diary = 27000+i*37, case = 7000+i*13) — keep in sync if reseeding.
- File delivery to the owner via chat downloads is unreliable; he now hosts
  `demo.html` in the repo. Prefer giving him GitHub-pencil-edit instructions
  or small paste-able diffs over new file downloads.

## Pending (rough priority)

1. **Autofetch first SCHEDULED run** — the parser is validated offline against
   real PDFs, but the Action's live scheduled run is its first end-to-end;
   watch the first `causelist-bot` commit. Owner must enable workflow
   write-permission + run once. Possible optimisation: it re-downloads the huge
   M_J list 6×/day per window-day; could skip dates already parsed.
2. FCM push notifications via Firebase Functions (shared backend decision
   with the owner's ASD app — build once, serve both).
4. Native file uploads (needs Blaze; schema already URL-based so it's
   additive).
5. Rules cleanup (drop vestigial `senior`), icons, seed cleanup.

## Working with the owner

Adith is an Advocate on Record — sophisticated, direct, allergic to
over-agreement. Flag weak reasoning proactively; he has corrected fabricated
claims before and expects "tested" to mean actually tested (show the check).
He makes design decisions fast when given crisp options with trade-offs.
Legal-domain terminology must be exact (diary no. vs case no., AoR,
mentioning, pass-over). The clerk-simplicity constraint is load-bearing:
every new clerk-facing feature must survive the question "can a man who only
knows WhatsApp and email use this without training?"
