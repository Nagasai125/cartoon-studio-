# Knowledge and Asset Library

## Purpose

The Library is the live inventory of what Cartoon Studio knows, what it can
reuse, where each item came from, and whether it is safe and permitted for
production.

## Library Model

```text
  +--------------------------- LIBRARY ----------------------------+
  |                                                                |
  |  KNOWLEDGE                         PRODUCTION ASSETS             |
  |  +--------------------+            +-------------------------+  |
  |  | Curriculum         |            | Characters and rigs     |  |
  |  | Source snapshots   |            | Environments and props  |  |
  |  | Claims and chunks  |            | Voices, music, and SFX  |  |
  |  | Policies           |            | Templates and scenes    |  |
  |  +---------+----------+            +------------+------------+  |
  |            |                                    |               |
  |            +----------------+-------------------+               |
  |                             v                                   |
  |                    +-------------------+                         |
  |                    | Usage and rights  |                         |
  |                    | episode links     |                         |
  |                    +-------------------+                         |
  +----------------------------------------------------------------+
```

## Source Trust Tiers

| Tier | Description | Default eligibility |
| --- | --- | --- |
| A | Government, standards body, primary authoritative source | Eligible |
| B | Recognized educational or professional organization | Eligible after rule checks |
| C | Verified licensed or public-domain creative material | Eligible within rights |
| D | Discovery source, blog, search result, or unknown authority | Quarantine only |

Trust affects retrieval ranking but does not replace topic-specific validation.
A government source can still be outdated or irrelevant.

## Source Ingestion

```text
  Approved URL/domain
          |
          v
  Validate scheme, DNS, IP, redirect, and content limits
          |
          v
  Fetch original content
          |
          v
  Virus/type scan and content hash
          |
          v
  Store immutable original snapshot
          |
          v
  Parse and normalize text
          |
          v
  Determine trust, rights, freshness, and topic
          |
      +---+---+
      |       |
    pass    quarantine
      |
      v
  Chunk, index, and embed
      |
      v
  Active in retrieval and visible in dashboard
```

## Source Security

The fetcher must:

- Permit only HTTP and HTTPS.
- Resolve DNS and block private, loopback, link-local, and metadata IP ranges.
- Recheck every redirect.
- Apply response size, duration, and redirect limits.
- Verify detected file type rather than trusting extension.
- Sanitize HTML and discard scripts.
- Store source text as untrusted content.
- Never execute instructions found inside a document.
- Preserve exact original snapshot for later citation.

## Source Freshness

Each source has a refresh policy based on volatility:

| Content | Suggested review behavior |
| --- | --- |
| Stable curriculum framework | Periodic metadata check |
| Health or safety guidance | Frequent effective-date check |
| Platform policy | Frequent change detection |
| Public-domain text | Infrequent rights verification |
| Internal character bible | Versioned only on owner-authorized change |

If a source changes, create a new snapshot. Existing episode citations continue
to reference the original snapshot.

## Curriculum Graph

Curriculum records include:

- Domain and subdomain
- Learning objective
- Age band
- Prerequisites
- Related objectives
- Difficulty
- Recommended episode formats
- Required interaction patterns
- Coverage history
- Source support
- Safety considerations

Topic selection considers under-covered objectives, prerequisites, recent
episodes, character diversity, format diversity, and seasonality without
blindly following engagement metrics.

## Asset Classes

| Class | Examples |
| --- | --- |
| Character | Model sheet, rig, proportions, palette, personality |
| Expression | Happy, curious, worried, surprised, thinking |
| Pose | Standing, pointing, walking, brushing, clapping |
| Mouth shape | Phoneme and singing shapes |
| Environment | Classroom, bedroom, bathroom, park, street |
| Prop | Toothbrush, ball, book, bus, fruit |
| Graphic | Letter, number, shape, pattern, caption style |
| Audio | Voice, pronunciation, music stem, SFX |
| Template | Episode structure, transition, interaction, recap |
| Generated media | Candidate image, scene clip, final render |

## Character Package

A reusable character is production-ready only when it includes:

- Approved model sheet
- Layered rig
- Color tokens
- Scale and proportion rules
- Front, profile, and three-quarter references
- Core expressions
- Core pose library
- Mouth shapes
- Voice profile
- Personality and language constraints
- Disallowed depictions
- Rights record
- Version identifier

## Asset Provenance

Generated assets record:

- Creating episode or library request
- Provider and model revision
- Prompt-template version
- Normalized prompt hash
- Seed when supported
- Input asset versions
- Source dependencies
- Generation timestamp
- Generation cost
- Validator results
- Owner or automated reuse status

Imported assets record the rights holder, evidence, attribution, permitted uses,
and effective dates.

## Reuse Rules

Only assets in `APPROVED_FOR_REUSE` may be selected automatically for future
episodes. Episode-specific generated candidates are not silently promoted to
the reusable library.

Automatic reuse selection considers:

- Character and series compatibility
- Visual style version
- License eligibility
- Required resolution
- Previous overuse
- Scene context
- Validator history

## Library Dashboard

```text
  +------------------------------------------------------------------+
  | Library search: [ brushing teeth                         ]        |
  +------------------------------------------------------------------+
  | Sources 128 | Assets 642 | Stale 3 | Rights missing 0             |
  +------------------------------------------------------------------+
  | Filters: Type | Topic | Status | Trust | License | Character      |
  +------------------------------------------------------------------+
  | Name                 Type        Status       Used     Updated     |
  | Oral health guide    Source A    Active       4 eps    2d ago      |
  | Blue toothbrush      Prop        Reusable     3 eps    8d ago      |
  | Bathroom morning     Environment Reusable     2 eps    12d ago     |
  +------------------------------------------------------------------+
```

An item detail page shows preview, versions, source or generation history,
rights, validation, dependencies, and every episode usage.

## Retrieval Rules

- Apply eligibility filters before semantic ranking.
- Prefer exact curriculum and source metadata matches.
- Retrieve source snapshot IDs, not mutable web pages.
- Require citation coverage for factual script claims.
- Limit context by relevance and trust.
- Keep retrieved text separated from system instructions.
- Store the retrieval result set with the episode version.

## Quality and Rights Blocks

An item is unavailable to autonomous production when:

- Rights are unknown or expired.
- Source trust is insufficient for the requested topic.
- A policy marks the topic or depiction unsafe.
- The asset failed visual or technical validation.
- The asset belongs to an incompatible style version.
- The source is stale for a time-sensitive claim.
- The asset was blocked after a previous production incident.
