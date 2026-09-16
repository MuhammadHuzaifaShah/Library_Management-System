"""Convert legacy availability to boolean and add stock counts.

Revision ID: f5ad6bab5c44
Revises: 0001_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = 'f5ad6bab5c44'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('books') as batch:
        batch.add_column(sa.Column('available_quantity', sa.Integer(), nullable=True))
        batch.alter_column('available', existing_type=sa.Integer(), type_=sa.Boolean(),
                           postgresql_using='available::boolean', existing_nullable=True)
    op.execute(sa.text('UPDATE books SET available_quantity = quantity'))


def downgrade():
    with op.batch_alter_table('books') as batch:
        batch.alter_column('available', existing_type=sa.Boolean(), type_=sa.Integer(),
                           postgresql_using='available::integer', existing_nullable=True)
        batch.drop_column('available_quantity')
