# 09 - Agent orchestration

MAYA is designed to run mostly autonomously: a pool of coding agents drains each wave in
parallel, self-validates through both MAYA phases, and only escalates to a human on the
rare unresolved parity issue. See [core/orchestration.py](../core/orchestration.py) and
[templates/agent_prompt.md](../templates/agent_prompt.md).

## Pooled work-queue within a wave
Within a wave, pipelines are independent, so a pool of 15-20 agents draws from a common
queue. Pod size is a dynamic split of the pool that responds to wave width.

```mermaid
flowchart TD
  q["Wave queue (all pipelines in wave N)"] --> a1["agent 1"]
  q --> a2["agent 2"]
  q --> a3["agent ..."]
  q --> aN["agent 20"]
  a1 --> barrier{"all in wave certified?"}
  a2 --> barrier
  a3 --> barrier
  aN --> barrier
  barrier -->|"yes"| next["Wave N+1"]
  barrier -->|"no"| q
```

## Strict wave barrier
The next wave depends on this wave's data, so a wave advances only when **every**
pipeline in it is at least **provisionally** MAYA-certified (dev AND SIT). No early
starts. The sustained soak (below) then runs in parallel and does not hold the barrier.

## The agent lifecycle (per pipeline)
1. Read the contract (context pack). Fail fast if G0 is not green.
2. Author bronze/silver/gold (SQL-first) - translate real source logic, never invent.
3. **MAYA-Dev**: run on the sampled tables; drift-loop until the dev profile is green.
4. **MAYA-SIT**: run at scale on prod-copied data; drift-loop until all 10 are green
   (dev + SIT green = provisional certification; the agent is freed to the next pipeline).
5. **MAYA-Soak**: on schedule, re-prove parity at T+7 and T+14 while the source still
   runs in parallel (cumulative + incremental delta); zero drift = final certification.
   Any drift (INCREMENTAL-LOGIC / LATE-DATA) reopens the drift loop and restarts the soak.
6. Emit `authored/<pipeline>.json`; record gates + parity to the control tables.

## Resumability + status
A pipeline is "done" iff a VALID `authored/<pipeline>.json` exists, so batches resume
naturally. `orchestration.status()` reports done/pending by wave and kind;
`pending()` yields the next work items; `validate()` checks authored specs against the
required schema per kind.

## What stays human
Setup (Phase 0) and watching the dashboard. Manual review is triggered only when a
pipeline cannot reach parity after the drift loop exhausts - expected to be rare.
