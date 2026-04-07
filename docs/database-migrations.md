# Database Migrations

AI News Open uses SQLite and applies schema migrations automatically on startup.

## Current Schema Version

The current schema version is `3`.

The repository stores schema metadata in the `meta` table:

- `schema_version`

## Migration Model

Migration behavior is implemented in [src/ainews/repository.py](../src/ainews/repository.py).

Rules:

- The application creates missing tables automatically.
- The application adds missing columns automatically.
- Startup upgrades older SQLite files in place.
- The application records the latest schema version in `meta.schema_version`.

## Operator Workflow

Before upgrading the application:

```bash
cp data/ainews.db data/ainews.db.bak
```

After upgrading, start the app once:

```bash
python -m ainews stats
```

Or query the admin API:

```bash
curl -H "X-Admin-Token: your-secret-token" http://127.0.0.1:8000/admin/stats
```

Look for:

- `schema_version`
- `total_articles`
- `total_digests`
- `total_publications`

## Rollback

If an upgrade behaves incorrectly:

1. Stop the process.
2. Restore the backup database.
3. Roll back the application version.
4. Start the old version again.

Because SQLite migrations are applied in place, the backup copy is the rollback anchor.

## Compatibility Notes

- `v1.x` treats automatic forward migration as part of the supported upgrade path.
- A future major version may require explicit manual steps if SQLite schema semantics change substantially.
- Breaking migration behavior must be called out in [CHANGELOG.md](../CHANGELOG.md).
