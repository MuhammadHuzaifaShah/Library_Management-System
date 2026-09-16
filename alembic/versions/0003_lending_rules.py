"""Add due dates and fines, reconcile inventory, and enforce lending invariants."""
from datetime import timedelta
from alembic import op
import sqlalchemy as sa

revision = '0003_lending_rules'
down_revision = 'f5ad6bab5c44'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # Validate legacy data before applying DDL. Do not silently discard duplicate loans.
    duplicate = connection.execute(sa.text('''
        SELECT user_id, book_id FROM borrowings WHERE returned = false OR returned IS NULL
        GROUP BY user_id, book_id HAVING COUNT(*) > 1
    ''')).first()
    if duplicate:
        raise RuntimeError('Duplicate active loans exist. Resolve them before upgrading.')
    duplicate_email = connection.execute(sa.text('''
        SELECT lower(email) FROM users GROUP BY lower(email) HAVING COUNT(*) > 1
    ''')).first()
    if duplicate_email:
        raise RuntimeError('Case-insensitive duplicate emails exist. Resolve them before upgrading.')
    op.add_column('borrowings', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('borrowings', sa.Column('fine_amount', sa.Numeric(12, 2), nullable=False, server_default='0'))
    loans = sa.table('borrowings', sa.column('id', sa.Integer()), sa.column('issue_date', sa.DateTime(timezone=True)),
                     sa.column('due_date', sa.DateTime(timezone=True)))
    for row in connection.execute(sa.select(loans.c.id, loans.c.issue_date)).all():
        # Fixed policy for historical loans; new loans use configured LOAN_DAYS.
        connection.execute(loans.update().where(loans.c.id == row.id).values(due_date=row.issue_date + timedelta(days=14)))
    op.execute(sa.text('UPDATE users SET isadmin = false WHERE isadmin IS NULL'))
    op.execute(sa.text('UPDATE users SET email = lower(email)'))
    op.execute(sa.text('UPDATE borrowings SET returned = false WHERE returned IS NULL'))
    books = sa.table('books', sa.column('id', sa.Integer()), sa.column('quantity', sa.Integer()),
                     sa.column('available_quantity', sa.Integer()), sa.column('available', sa.Boolean()))
    for book in connection.execute(sa.select(books.c.id, books.c.quantity)).all():
        active = connection.execute(sa.text('SELECT count(*) FROM borrowings WHERE book_id = :id AND returned = false'), {'id': book.id}).scalar_one()
        quantity = max(book.quantity or 0, active, 0)
        stock = quantity - active
        connection.execute(books.update().where(books.c.id == book.id).values(quantity=quantity, available_quantity=stock, available=stock > 0))
    with op.batch_alter_table('users') as batch:
        batch.alter_column('isadmin', existing_type=sa.Boolean(), nullable=False, server_default=sa.false())
    with op.batch_alter_table('books') as batch:
        batch.alter_column('quantity', existing_type=sa.Integer(), nullable=False)
        batch.alter_column('available_quantity', existing_type=sa.Integer(), nullable=False)
        batch.alter_column('available', existing_type=sa.Boolean(), nullable=False)
        batch.create_check_constraint('books_quantity_nonnegative', 'quantity >= 0')
        batch.create_check_constraint('books_stock_bounds', 'available_quantity >= 0 AND available_quantity <= quantity')
        batch.create_check_constraint('books_available_matches_stock', 'available = (available_quantity > 0)')
    with op.batch_alter_table('borrowings') as batch:
        batch.alter_column('due_date', existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.alter_column('returned', existing_type=sa.Boolean(), nullable=False, server_default=sa.false())
        batch.create_check_constraint('borrowings_fine_nonnegative', 'fine_amount >= 0')
    op.create_index('ix_borrowings_user_id', 'borrowings', ['user_id'])
    op.create_index('ix_borrowings_book_id', 'borrowings', ['book_id'])
    op.create_index('uq_active_user_book', 'borrowings', ['user_id', 'book_id'], unique=True,
                    postgresql_where=sa.text('returned = false'), sqlite_where=sa.text('returned = 0'))


def downgrade():
    op.drop_index('uq_active_user_book', table_name='borrowings')
    op.drop_index('ix_borrowings_book_id', table_name='borrowings')
    op.drop_index('ix_borrowings_user_id', table_name='borrowings')
    with op.batch_alter_table('borrowings') as batch:
        batch.drop_constraint('borrowings_fine_nonnegative', type_='check')
        batch.drop_column('due_date')
        batch.drop_column('fine_amount')
        batch.alter_column('returned', existing_type=sa.Boolean(), nullable=True, server_default=None)
    with op.batch_alter_table('books') as batch:
        for name in ('books_quantity_nonnegative', 'books_stock_bounds', 'books_available_matches_stock'):
            batch.drop_constraint(name, type_='check')
        batch.alter_column('quantity', existing_type=sa.Integer(), nullable=True)
        batch.alter_column('available_quantity', existing_type=sa.Integer(), nullable=True)
        batch.alter_column('available', existing_type=sa.Boolean(), nullable=True)
    with op.batch_alter_table('users') as batch:
        batch.alter_column('isadmin', existing_type=sa.Boolean(), nullable=True, server_default=None)
