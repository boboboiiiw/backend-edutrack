"""Add PostInteraction model for likes/dislikes

Revision ID: 86aa1283baff
Revises: 0cf83592719e
Create Date: 2025-05-27 13:55:05.668999

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '86aa1283baff'
down_revision = '0cf83592719e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('post_interactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('interaction_type', sa.String(length=10), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], name=op.f('fk_post_interactions_post_id_posts')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_post_interactions_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_post_interactions')),
    sa.UniqueConstraint('user_id', 'post_id', name='_user_post_uc')
    )
    op.alter_column('comments', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('urls', 'url',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.String(length=500),
               existing_nullable=False)
    op.create_unique_constraint(op.f('uq_urls_url'), 'urls', ['url'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('uq_urls_url'), 'urls', type_='unique')
    op.alter_column('urls', 'url',
               existing_type=sa.String(length=500),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)
    op.alter_column('comments', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.drop_table('post_interactions')
    # ### end Alembic commands ###
