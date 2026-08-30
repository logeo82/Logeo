# Logeo aggregation providers

Providers are independent and fail-safe. The pipeline merges the richest available fields.

Current providers:
- JSON-LD structured data
- HTML/OpenGraph metadata

Next providers can implement `fetch(url) -> Listing` without changing the API or merge logic.
