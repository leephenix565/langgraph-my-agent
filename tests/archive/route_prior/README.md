# Archived Route-Prior / RARP Tests

This directory holds offline route-prior, RARP, manual-gold, teacher-proxy, and
router-advisory experiment tests that are no longer part of the default
`pytest tests/unit_tests` mainline acceptance gate.

They are retained for historical lineage and reproducibility only. The active
runtime gate in `tests/unit_tests` protects the current no-route-prior graph
contract. As of AC-1B-2A, `react_agent.graph` no longer imports or executes the
old route-prior shadow seam; the helper tests here only cover archived/offline
behavior.
