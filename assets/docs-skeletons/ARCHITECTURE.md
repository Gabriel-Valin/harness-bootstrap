# Architecture

Map for agents and new developers. Keep it under ~150 lines and update it in the same PR as the
code it describes. Mark anything unconfirmed as `TODO(confirm): ...`.

## Overview

Two or three sentences: what the system does and its main runtime pieces.

## Layers and modules

| Module / path | Responsibility | May depend on | Must not depend on |
|---|---|---|---|
| `src/...` | | | |

Boundaries in the last column are enforced by `harness/architecture-rules.json`.

## Main flows

Describe the two or three flows that matter most, step by step, naming the files involved.

```
1. Entry point (file) receives ...
2. ...
```

## Data and state

Where data lives (databases, files, caches, queues), who owns each store, and how schema changes
are made.

## External dependencies

Services, APIs and SDKs the system calls, and where the integration code lives.

## Conventions

Patterns to copy when adding code (where new endpoints, components or jobs go; how errors are
represented; how config is read). Point to one good example file for each.

## Decisions

Links to the relevant records in `docs/decisions/`.
