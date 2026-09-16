"""Create the original schema before the existing availability migration."""
from alembic import op
import sqlalchemy as sa

revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('password', sa.String(), nullable=False),
        sa.Column('isadmin', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table('books',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('isbn', sa.String(), nullable=False, unique=True),
        sa.Column('author', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('available', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table('borrowings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id'), nullable=False),
        sa.Column('issue_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('return_date', sa.DateTime(timezone=True)),
        sa.Column('returned', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_table('borrowings')
    op.drop_table('books')
    op.drop_table('users')
