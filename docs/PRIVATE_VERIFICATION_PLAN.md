# Cogan private verification: migration plan

This public repository is GPL-2.0 licensed. Existing public Git history,
kernel sources, and any third-party license obligations remain accessible.
A public workflow's repository-ID check is not a copy-protection mechanism:
a fork owner can remove it. Treat the new guard as an official-build identity
check, not as exclusive intellectual-property protection.

## Private backend prerequisites (not deployed yet)

1. Create a **private** verification service and private report store under
   Cogan's control. The existing connected account currently exposes no such
   repository/service.
2. Authenticate via GitHub Actions OIDC (short-lived identity token). The
   service must validate the GitHub OIDC issuer and JWKS signatures, audience,
   token expiry, repository ID `1397614374`, repository owner ID `79615344`,
   ref/workflow restrictions, and reject fork identities. Never trust request
   parameters alone and never place long-lived secrets in a public repo.
3. Execute proprietary **new** compatibility-report logic only server-side.
   Recompute or verify source commits, kernel image, module ZIP checksum, and
   expected combinations server-side; do not trust client-supplied `passed`.
   Signed authorization receipts must be bound to repo ID, workflow run ID,
   commit SHA, manifest digest and expiry.
4. Keep detailed Indonesian failure diagnostics and English reports in private
   storage, not GitHub Actions job logs, job Summary, or public artifacts.
   The public Summary should show only a generic status and a private-access
   reference, without commits/diagnostics.
5. Gate both the artifact-upload stage and Manual Release From Run against
   valid signed receipts. Missing/expired/invalid checks must fail closed.
   Roll out first on a private testing workflow, then after device-specific
   testing migrate the official pipeline; avoid making public build depend on
   a non-existent service.

## Constraints

- GitHub public repositories cannot directly use private reusable workflows
  as a way to hide implementation; use OIDC-authenticated services or a
  genuinely private build runner/workflow as the execution boundary.
- Build/test logs in a public repository can disclose sensitive details. Do
  not attempt to hide data by merely omitting it from Summary.
- The GPL-2.0 source and redistributed kernel/derivative licensing duties
  remain in force; consult maintainers/legal review before moving any
  integrated kernel code into a private component.
- Existing public synchronization code remains copyable from Git history.
- No static pairing test guarantees the absence of bootloops/brick.

## Status

This branch provides a basic original-repository workflow guard only.
The private service, OIDC verifier, private reports, signed receipts, and
release-time receipt checks have **not** been provisioned or activated.
