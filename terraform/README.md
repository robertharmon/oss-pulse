# terraform/

Every GCP resource the access matrix and architecture list as Terraform-managed (`docs/architecture.md` §2, "Infra"). Tests in `terraform/tests/` use mock providers.

Grants must match `docs/access_matrix.md` §4 exactly; CI diffs them. CODEOWNERS-protected. Built in roadmap M5.
