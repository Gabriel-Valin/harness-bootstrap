# Reliability and observability

How to know what the system is doing, and how to get it back to a known state. An agent that
cannot see runtime behavior can only guess at fixes.

## Running locally

- Prerequisites (runtime versions, services, env vars; `.env.sample` or equivalent):
- Start: 
- Health check / proof that it is up:
- Services it needs (database, queue) and how to start them:

## Verification layers

Defined in `harness/config.sh` and run by `scripts/harness/verify.sh`:

| Layer | Command | What it proves | Typical duration |
|---|---|---|---|
| static | | | |
| tests | | | |
| smoke | | | |
| e2e | | | |

Faster per-package variants for local loops:

## Logs

- Where logs go locally and in each environment:
- Format (structured? fields?):
- How to raise the log level:
- The log lines that prove each main flow worked:

## Resetting to a clean state

How to wipe local data, reset the database, clear caches, so tests and debugging start from a
known state. Make the commands idempotent.

## Known failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
