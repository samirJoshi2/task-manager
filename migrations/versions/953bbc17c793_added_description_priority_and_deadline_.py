"""Added description, priority, and deadline columns to task table

Revision ID: 953bbc17c793
Revises: 
Create Date: 2025-02-27 16:14:26.206389

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '953bbc17c793'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('priority', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('deadline', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('progress', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('progress')
        batch_op.drop_column('deadline')
        batch_op.drop_column('priority')
        batch_op.drop_column('description')

    # ### end Alembic commands ###
