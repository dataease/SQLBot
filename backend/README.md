# FastAPI Project - Backend

## Table sample data in SQL generation

`TABLE_SAMPLE_DATA_ENABLED` controls whether SQLBot fetches table sample rows
and includes them in SQL-generation prompts. It defaults to `true` to preserve
existing behavior, including the current three-row sample limit.

To disable automatic sampling, set the following environment variable (or add it
to the project-root `.env` used when running the backend from `backend/`):

```dotenv
TABLE_SAMPLE_DATA_ENABLED=false
```

For Docker Compose, pass it explicitly to the SQLBot service:

```yaml
environment:
  TABLE_SAMPLE_DATA_ENABLED: "false"
```

A Compose `.env` file alone does not automatically pass all its variables into a
container. For `docker run`, use `-e TABLE_SAMPLE_DATA_ENABLED=false`.
Settings are loaded at process startup: restart a source deployment, or recreate
the container with the new environment configuration.

When disabled, the automatic sample-data helper returns before reading table
metadata or sample rows. The SQL prompt template also ignores pre-existing
`sample_data` values. Schema context, explicit SQL queries, manual data previews
and their existing permission checks remain unchanged. Less sample context may
affect SQL-generation quality.

This is not a global data-loss-prevention switch. User messages, field comments,
SQL examples, query results and analysis prompts can still contain business
data. Existing logs are not deleted or retroactively redacted.

### Focused regression tests

From the repository root, with the backend development dependencies available:

```bash
python -m pytest -q tests/test_table_sample_data.py
```

The tests execute actual source function definitions with dependency doubles to
avoid initializing database drivers, embedding models or X-Pack. They cover
configuration parsing, sampling, prompt rendering and unaffected query/preview
behavior; they are not full application or model-provider integration tests.
