# Control-Plane Publication Attempts

Updated: 2026-08-30

MediaPoster exposes one authenticated, idempotent provider boundary for
Airtime-approved content work items. It does not infer approvals, select an
account, schedule content, or fall back to ACTP.

## Routes

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/v1/control-plane/publication-preflights` | Validate exact approval, QC, schedule, account, asset, and provider readiness without writing |
| POST | `/v1/control-plane/publication-attempts` | Journal one destination attempt and submit it to the provider |
| GET | `/v1/control-plane/publication-attempts/{attempt_id}` | Read one durable attempt receipt |
| POST | `/v1/control-plane/publication-attempts/{attempt_id}/reconcile` | Poll an already-submitted provider ID |

All routes require `Authorization: Bearer $MEDIAPOSTER_CONTROL_TOKEN`.
Creating an attempt also requires `Idempotency-Key`.
Provider preflight and submission remain disabled unless
`MEDIAPOSTER_CONTROL_PUBLISH_ENABLED=true`. This is the independent workspace
kill switch; turning it off blocks new provider writes before asset download.

The formal request and receipt schema is
`schema/control-plane-publication.schema.json`.

## Required proof

The attempt request must bind:

- content work item and immutable production plan hash
- exact Airtime destination and provider account IDs
- due scheduled time and optional freshness deadline
- Media Vault asset ID, byte count, download path, and SHA-256
- passing QC receipt for the same asset SHA-256
- generation approval ID, timestamp, `auto_publish_after_qc`, and explicit
  scheduled-publication approval
- `held: false`
- `confirm_provider_write: true`

MediaPoster downloads the authenticated Media Vault path and recomputes byte
count and SHA-256 before calling the provider.

## Attempt states

| State | Meaning |
| --- | --- |
| `prepared` | Journal exists and provider submission has not begun |
| `downloading` | Exact Media Vault bytes are being verified |
| `submitting` | Provider call may have begun |
| `submitted` | Provider submission ID is durable; public URL is pending |
| `processing` | Provider still reports in progress |
| `published` | Public URL and terminal receipt are durable |
| `failed` | Provider outcome is known failed; a higher attempt number may retry |
| `unknown` | Provider call may have happened but no safe outcome is known |

An `unknown` attempt must reconcile or receive operator investigation. It must
never be retried blindly with a new attempt number.

## Restart guarantees

- A restart during `downloading` returns the attempt to `prepared` because no
  provider call began.
- A restart during `submitting` changes the attempt to `unknown`.
- Replaying the same idempotency key and request returns the original receipt.
- Completed receipts replay even if the schedule or freshness window has since
  passed; current-time preflight is not allowed to erase historical truth.
- One destination attempt is independent of every other destination.

## Secret and response handling

Provider credentials remain in environment variables. Provider results are
recursively bounded and redact authorization, cookie, password, secret,
credential, API-key, and token fields before persistence. Public URLs must be
HTTP(S), cannot contain URL credentials, and are stored without query strings
or fragments.

Configure outside the repository:

```text
MEDIAPOSTER_CONTROL_TOKEN
MEDIAPOSTER_CONTROL_PLANE_DB
MEDIAPOSTER_CONTROL_PUBLISH_ENABLED=true
MEDIA_VAULT_CONTROL_URL
MEDIA_VAULT_CONTROL_TOKEN
BLOTATO_API_KEY
```

## Validation

```bash
python3 -m pytest tests/test_control_plane_publications.py -q
python3 -m json.tool ../schema/control-plane-publication.schema.json >/dev/null
python3 ../scripts/generate_agent_service_contracts.py --check
```

The tests use an in-memory request application, temporary SQLite, local
deterministic asset/provider receipts, and no live provider call.
