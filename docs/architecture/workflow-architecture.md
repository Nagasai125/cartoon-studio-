# Workflow Architecture

## Purpose

This document defines durable execution, state transitions, retries, budgets,
events, human approval, and recovery.

## Core Decision

Use a coded event-driven state machine. PostgreSQL is authoritative and Cloud
Tasks delivers work. No process remains suspended while waiting for a provider
or human.

## Episode State Machine

```text
  [QUEUED]
      |
      v
  [PLANNING] -> [RESEARCHING] -> [SCRIPTING]
                                      |
                                      v
                              [SCRIPT_VALIDATION]
                                 |          |
                              pass        repair
                                 |          |
                                 v          +----> [SCRIPTING]
                           [STORYBOARDING]
                                 |
                                 v
                          [ASSET_PREPARATION]
                                 |
                                 v
                          [SCENE_PRODUCTION]
                                 |
                                 v
                          [SCENE_VALIDATION]
                             |          |
                          pass        repair
                             |          |
                             v          +----> [SCENE_PRODUCTION]
                       [AUDIO_PRODUCTION]
                             |
                             v
                         [RENDERING]
                             |
                             v
                      [FINAL_VALIDATION]
                             |
                             v
                       [NEEDS_APPROVAL]
                         |           |
                      approve      reject
                         |           |
                         v           +----> selected repair stage
                     [APPROVED]
                         |
                         v
                    [PUBLISHING]
                         |
                         v
                     [PUBLISHED]

  Any active state can enter [FAILED], [PAUSED], or [CANCELLED]
  when its explicit transition rules permit it.
```

## Job Lifecycle

```text
  PENDING -> DISPATCHED -> RUNNING -> SUCCEEDED
     |           |           |
     |           |           +----> RETRY_WAIT -> PENDING
     |           |
     |           +----------------> DELIVERY_FAILED -> PENDING
     |
     +----------------------------> CANCELLED

  RUNNING -> FAILED_PERMANENT
  RUNNING -> BLOCKED_BUDGET
  RUNNING -> BLOCKED_POLICY
```

## Transactional Outbox

A state transition and its next job are committed in one database transaction.

```text
  API or worker
       |
       v
  BEGIN TRANSACTION
       |
       +--> validate current state and version
       +--> write new state
       +--> append pipeline event
       +--> create job
       +--> insert outbox record
       |
  COMMIT
       |
       v
  Outbox dispatcher
       |
       +--> create Cloud Task using stable task ID
       +--> mark outbox record delivered
       |
       v
  Worker receives task and loads authoritative job
```

If dispatch fails, the outbox record remains and is retried. If delivery is
duplicated, the stable task and job idempotency keys prevent duplicate work.

## Activity Contract

Every workflow activity defines:

| Field | Purpose |
| --- | --- |
| `activity_type` | Stable activity identifier |
| `input_version` | Schema version |
| `idempotency_key` | Duplicate prevention |
| `attempt_limit` | Maximum worker attempts |
| `deadline_at` | Absolute completion deadline |
| `cost_limit_micros` | Maximum spend for activity |
| `provider_policy` | Allowed and fallback providers |
| `artifact_inputs` | Immutable input references |
| `policy_version_id` | Rules applied to output |

Activities return normalized result or typed failure. They do not directly
choose the next episode state.

## Retry Policy

Retry only failures classified as transient.

| Failure | Behavior |
| --- | --- |
| Network timeout | Exponential retry with jitter |
| Provider rate limit | Retry using provider hint or fallback policy |
| Provider unavailable | Retry, then optional configured fallback |
| Invalid provider response | One repair attempt, then permanent failure |
| Safety violation | Do not repeat unchanged prompt; route to repair |
| Budget exceeded | Block immediately |
| License missing | Block immediately |
| Authentication failure | Alert; do not repeatedly retry |
| Owner cancellation | Stop new work and safely end active work |

Recommended initial defaults:

- Delivery attempts: 5
- Generation candidates per scene: 2
- Automated repair rounds per scene: 2
- Full-render repair rounds: 1
- Backoff: exponential with randomized jitter
- Episode cost ceiling: configured before production starts

## Budget Control

```text
  Proposed paid operation
           |
           v
  Estimate maximum cost
           |
           v
  Lock episode budget row
           |
       +---+---+
       |       |
    available insufficient
       |       |
       v       v
    reserve   block job
       |
       v
  execute provider call
       |
       v
  reconcile actual cost
```

Budget reservations prevent parallel scenes from collectively exceeding an
episode limit. Every cost is stored as integer micro-units with currency and
provider usage details.

## Parallel Scene Production

Scenes without dependencies may run concurrently. The episode advances only
when required scenes have reached an accepted state.

```text
                     +--> Scene 01 job --> validate --+
                     +--> Scene 02 job --> validate --+
  storyboard --------+--> Scene 03 job --> validate --+--> completion barrier
                     +--> Scene 04 job --> validate --+
                     +--> Scene 05 job --> validate --+

  Failed validation schedules only the affected scene version.
```

Concurrency is limited by:

- Episode budget
- Provider rate limits
- Per-provider queue limits
- Worker capacity
- Scene dependency graph

## Provider Callbacks

Long-running providers return a job ID. The workflow records it and ends the
worker request.

```text
  Worker -> Provider submit -> provider job ID -> database

  Provider -> Signed callback endpoint
           -> verify signature/timestamp/nonce
           -> match provider job ID
           -> fetch and validate result
           -> complete internal job
           -> emit next outbox record
```

Polling is a fallback when callbacks are not available. Polling uses a scheduled
task and never blocks an API or worker process.

## Pause and Cancellation

Pause prevents new jobs from dispatching. Already running external jobs may
finish, but their results do not advance the workflow until resumed.

Cancellation:

- Marks the workflow cancelled.
- Cancels queued tasks where supported.
- Attempts provider cancellation where supported.
- Preserves completed artifacts and audit history.
- Prevents all future transitions except archival.

## Final Approval

An approval records:

- Owner user ID
- Episode version ID
- Final render asset version ID
- Final render SHA-256
- Final QA report version ID
- Approval timestamp
- Optional owner note

Publishing recomputes and compares the hash. It also checks that the QA report
is current and no approval revocation exists.

## Rejection

The owner can reject:

- The complete episode
- Specific scenes
- Audio only
- Captions only
- Metadata only

Rejection creates a new episode or scene version. It never mutates the rejected
artifact. Structured rejection categories support future automated repair.

## Recovery

Periodic reconciliation detects:

- Jobs stuck beyond heartbeat or deadline
- Outbox records not dispatched
- Provider jobs without callbacks
- Completed artifacts without database completion
- Episode states without active or completed required jobs
- Publishing records with unknown YouTube status

Recovery emits an audit event before changing state.

## Workflow Versioning

Each episode records its workflow definition version. New workflow code must
either support existing active versions or include an explicit migration path.
Do not silently reinterpret an active workflow under new transition rules.
