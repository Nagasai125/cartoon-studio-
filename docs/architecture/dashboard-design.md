# Dashboard Design

## Purpose

This document defines the owner-facing information architecture, interaction
standards, live behavior, and accessibility baseline.

## Design Intent

The dashboard is a calm production control room. It is not styled like the
children's cartoons and it is not organized around AI prompts.

The owner should understand these facts within ten seconds:

- What is running?
- What needs attention?
- What needs approval?
- What did production cost?
- What knowledge and assets are available?

## Information Architecture

```text
  Cartoon Studio
  |
  |-- Overview
  |-- Productions
  |   |-- Queue
  |   |-- Active
  |   |-- Needs attention
  |   `-- Published
  |-- Review
  |-- Library
  |   |-- Knowledge
  |   |-- Curriculum
  |   |-- Characters
  |   |-- Environments
  |   |-- Props
  |   |-- Audio
  |   |-- Templates
  |   `-- Licenses
  `-- Settings
      |-- Schedule
      |-- Budgets
      |-- Providers
      |-- Policies
      `-- Publishing
```

## Desktop Layout

```text
  +-----------------------------------------------------------------------+
  | Cartoon Studio                         Search        Owner menu         |
  +------------------+----------------------------------------------------+
  | Overview         | Production this week                               |
  | Productions      |                                                    |
  | Review        1  | +------------+ +------------+ +------------+       |
  | Library          | | Planned  3 | | Active   1 | | Review   1 |       |
  | Settings         | +------------+ +------------+ +------------+       |
  |                  |                                                    |
  |                  | Active pipeline                                    |
  |                  | Letter B Adventure                                 |
  |                  | Scene production  [########------] 8 / 12          |
  |                  |                                                    |
  |                  | Alerts                 Cost                         |
  |                  | Scene 7 retrying       $42.18 / $200 monthly       |
  +------------------+----------------------------------------------------+
```

## Mobile Layout

Mobile prioritizes status and approval. Complex timeline and library tables use
focused detail screens rather than compressed desktop tables.

```text
  +------------------------------+
  | Cartoon Studio        Owner  |
  +------------------------------+
  | Needs approval: 1            |
  | Active: 1                    |
  | Failed: 0                    |
  +------------------------------+
  | Letter B Adventure           |
  | Scene production 8 / 12      |
  | [############--------]       |
  +------------------------------+
  | Overview | Work | Review |   |
  +------------------------------+
```

## Primary Screens

### Overview

- Weekly production calendar
- Active episode progress
- Review queue
- Failures and policy blocks
- Monthly budget and provider spend
- Knowledge freshness warnings
- Missing rights metadata
- Recent owner and system activity

### Productions

- Cursor-paginated episode list
- Filters by state, week, objective, format, and character
- Current stage and progress
- Cost, attempts, and next scheduled action
- Pause, resume, cancel, and inspect controls

### Episode Detail

```text
  +------------------------------------------------------------------+
  | Letter B Adventure                       NEEDS APPROVAL            |
  | Learn the B sound and identify ball, bird, and banana             |
  +------------------------------------------------------------------+
  | Preview             | Quality                                    |
  | +-----------------+ | 24 passed                                  |
  | |                 | |  1 warning: music slightly loud            |
  | | final video     | | Sources: 4 verified                        |
  | |                 | | Rights: complete                           |
  | +-----------------+ | Cost: $8.42                                |
  +------------------------------------------------------------------+
  | Scenes | Script | Sources | Assets | Timeline | Advanced          |
  +------------------------------------------------------------------+
  | [Reject selected scenes]                       [Approve episode]  |
  +------------------------------------------------------------------+
```

### Review

The review screen must keep the final video and decision context together.

Required information:

- Final rendered video
- Learning objective
- Script and captions
- Source citations
- Automated QA report
- Rights and provenance summary
- Cost and retry summary
- Final file hash
- Approve and reject controls

Approval requires an explicit confirmation containing the episode title and
final hash suffix. It must never be an optimistic UI operation.

### Library

Provides combined search with type-specific views. See
`knowledge-asset-library.md` for lifecycle details.

### Settings

Settings are versioned. Editing a policy creates a draft policy version and does
not alter active episodes.

## Live Activity

The API provides Server-Sent Events. The client:

- Reconnects automatically.
- Supplies the last received event ID.
- Deduplicates by event ID.
- Falls back to periodic polling.
- Shows connection state without interrupting normal use.
- Never assumes an operation succeeded until confirmed by the API.

## Status Semantics

| Status | Meaning |
| --- | --- |
| Queued | Waiting for its scheduled start or available capacity |
| Running | A production stage is actively progressing |
| Waiting | Waiting for a provider callback or dependency |
| Needs attention | Automated progress stopped and owner inspection is useful |
| Needs approval | All automated gates passed |
| Approved | Exact final render approved but not yet published |
| Scheduled | YouTube upload exists with future publication time |
| Published | Publication confirmed |
| Failed | Terminal failure after configured recovery |
| Cancelled | Owner ended the run |

Colors supplement labels and icons; they never carry status alone.

## Visual Standards

- Neutral operator palette with restrained semantic colors.
- One primary accent reserved for owner actions.
- Monospace only for IDs, hashes, logs, and timestamps.
- Tabular numerals for cost and durations.
- Eight-pixel spacing scale.
- Consistent card and table density.
- Minimal animation limited to state changes and progress.
- No decorative gradients, cartoon decoration, or gamification.

## Accessibility

- WCAG 2.2 AA target.
- Complete keyboard operation.
- Visible focus ring.
- Semantic headings and landmarks.
- Form errors associated with inputs.
- Captions available for every video preview.
- Audio controls never autoplay.
- Minimum 44 by 44 pixel touch target.
- Reduced-motion preference honored.
- Contrast tested in CI where tooling permits.

## Error Design

Errors answer:

1. What failed?
2. What was affected?
3. Will it retry automatically?
4. What can the owner do?

Do not expose provider stack traces in primary error messages. Link to Advanced
diagnostics using the job and request IDs.

## Performance Budget

- Initial JavaScript should remain under a documented compressed budget.
- Route-level code splitting for Library and Advanced diagnostics.
- Thumbnails instead of loading original media in lists.
- Signed media URLs requested only when needed.
- Virtualize only after list measurements justify it.
- Use skeletons that preserve layout dimensions.

## Frontend Security

- No secrets in `VITE_*` variables.
- No provider SDK requiring privileged credentials.
- No unapproved third-party scripts.
- Sanitize rendered source excerpts.
- Do not render arbitrary provider HTML.
- Clear sensitive in-memory data on logout.
- Backend remains authoritative for all permissions.
