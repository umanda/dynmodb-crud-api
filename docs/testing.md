# Testing Tutorial

This project uses `pytest` for unit and endpoint tests.

## What Is Covered

The test suite covers all public API endpoint groups:

1. Meta endpoints (`/health`, `/tables`)
2. Auth endpoint (`/auth/token`)
3. Channel endpoints (`/channels`, `/channels/{channel_code}`)
4. Activity log endpoints (`/activity-logs`, `/activity-logs/search`)

Tests use mocks/stubs for external systems, so they run without real AWS DynamoDB or Auth0 calls.

## Prerequisites

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest
```

## Run All Tests

From repository root:

```bash
pytest -q
```

## Run by Area

```bash
# Auth tests
pytest -q tests/auth

# Channel tests
pytest -q tests/channels

# Activity log tests
pytest -q tests/activity_logs

# Meta endpoint tests
pytest -q tests/test_meta_endpoints.py
```

## Run a Single Test

```bash
pytest -q tests/channels/test_channel_endpoints.py::test_create_channel
```

## Useful Options

```bash
# Stop on first failure
pytest -q -x

# Show print/log output during test run
pytest -q -s

# Verbose names
pytest -v
```

## Notes

1. Protected endpoints require a Bearer token in runtime, but tests provide mocked auth to keep tests deterministic.
2. CI runs these tests automatically via `.github/workflows/ci.yml`.
3. If you add a new endpoint, add at least one success and one failure/validation test case.
