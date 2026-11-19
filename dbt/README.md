# dbt/

The dbt project and the daily build service (Cloud Run): staging, core and mart models, their tests, the reconciliation counts (R-nn) and seeds such as `actor_suppressions`.

Spec: `docs/data_contract.md` §4–§5. dbt unit tests live in `models/**/_unit_tests.yml` files, never inside a model's `schema.yml` (ways of working §3.1). Built in roadmap M4.
