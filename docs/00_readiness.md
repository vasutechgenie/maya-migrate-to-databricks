# 00 - Stage 0: readiness (the non-data estate)

Stage 1 proves the **data** estate is 100% traversable. A real migration also has to
carry over everything that is *not* a pipeline - who can touch what, which secrets back
which connections, and which columns are sensitive. Stage 0 is the "collect + score" for
that non-data estate, and it gates the rest of the flow exactly like Stage 1 does.

## What it collects
Via the adapter's Stage-0 hooks (safe defaults; the reference Synapse adapter reads
`examples/northwind/artifacts/security/*`):

- **Identity** - `export_principals()` -> users, groups, roles, service principals.
- **Access** - `export_grants()` -> the grant matrix `{principal, object, privilege}`.
- **Secrets** - `export_secrets()` -> the credential inventory backing every connection
  (names/scopes only, never values).
- **Classification** - `classify_data()` -> per-column sensitivity (PII/PHI/PCI) + mask.
- **Security posture** - `export_security_facts()` -> encryption, network, audit,
  compliance.

Everything is persisted under `out/readiness/`.

## The gate
Stage 0 PASSes only when the collected estate is internally consistent:

- at least one principal is collected;
- every grant references a **known principal** and an object that **resolves** to a home
  schema or a known table/view;
- every secret references a **known connection**, and every *active* connection
  (used by >= 1 pipeline) is **backed by a secret**;
- at least one column is classified, and every sensitive column has a **mask**.

```bash
python3 cli.py readiness --config examples/northwind/northwind.yaml
# or: make stage0
```

Emits `out/stage0_gate.json`. A missing owner, an unmapped grant, an unsecured
connection, or an unmasked PII column fails the gate - the same "no guessing" discipline
Stage 1 applies to data.

## How it relates to Phase 0
[02_phase0_prereqs.md](02_phase0_prereqs.md) is the *platform* setup (workspaces,
catalogs, connections proven). Stage 0 is the *estate* setup: it inventories the identity,
access, and classification that Stage 7 will translate into Unity Catalog. Do Phase 0
first; run Stage 0 to prove the non-data estate is complete before building.
