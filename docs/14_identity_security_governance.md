# 14 - Stage 7: identity, security & governance

Certified data is not the same as a *secure, governed* platform. Stage 7 takes the estate
collected in Stage 0 and deterministically authors the Unity Catalog security model that
must exist before go-live - then proves it matches the source (access parity).

## What it produces
`python3 cli.py identity --config <project>.yaml` (or `make stage7`) emits
`out/stage7_identity.sql` and `out/stage7_gate.json`:

- **Identity** - account groups + service principals (managed via SCIM; emitted for
  completeness).
- **Access (RBAC)** - the source grant matrix translated **1:1** into Unity Catalog
  `GRANT` statements, scoped to schema / table / view against the target catalog
  (`security.target_catalog`, defaults to the SIT catalog).
- **Column masking (CLS)** - a mask function per distinct mask, and
  `ALTER ... SET MASK` for every classified PII/PHI column. Stewards see raw values;
  everyone else sees the mask.
- **Row-level security (RLS)** - a row-filter function + `SET ROW FILTER` for every
  policy declared in `security.row_filters`.
- **Secrets** - a Databricks secret scope (`security.secret_scope`) with one key per
  migrated credential (values are never stored by MAYA).
- **Governance** - schema owners, medallion tags, and a business glossary from the
  `governance:` config block.

## The access-parity gate
Stage 7 PASSes only when:

- every source grant is mapped 1:1 (no missing, no extra) - `grants_mapped == grants_total`;
- every sensitive column has a mask (`unmasked_pii == []`);
- every active credential has a secret scope key (`unsecured_connections == []`).

## Compliance
The security posture facts (`export_security_facts()`) capture encryption at rest / in
transit, network posture, audit logging, and the compliance regimes in scope
(e.g. GDPR, HIPAA, SOX, PCI-DSS). Classification + masking + access parity together give
the evidence an auditor asks for: *who can see what, and is sensitive data protected?*

## Offline vs. live
Offline (the demo) this is pure SQL/DDL generation - zero Databricks calls - so the plan
is fully reviewable. With `agents.driver: cursor`, the same plan can be **applied** by the
agent swarm (create groups, run the grants, attach masks/filters, create the secret
scope), the same model Stages 4-5 use for building and BI.

See also: [00_readiness.md](00_readiness.md) (what Stage 0 collects) and
[13_bi_layer_migration.md](13_bi_layer_migration.md) (BI access).
