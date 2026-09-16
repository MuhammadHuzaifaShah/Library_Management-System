from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
from app.config import settings
from app.database import Base
from app import models  # noqa: F401 -- register metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online():
    engine = create_engine(settings.sqlalchemy_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=connection.dialect.name == 'sqlite', compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError('These data-preserving migrations require an online database connection.')
else:
    run_migrations_online()
