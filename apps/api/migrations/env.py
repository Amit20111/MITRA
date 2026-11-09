from alembic import context

from memory.store import metadata

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError(
        "Use python -m apps.api.migrate so the configured database is selected."
    )
context.configure(connection=connection, target_metadata=metadata)
with context.begin_transaction():
    context.run_migrations()
