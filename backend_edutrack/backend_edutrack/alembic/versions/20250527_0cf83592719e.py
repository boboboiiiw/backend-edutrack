"""Add role and prodi columns to User model

Revision ID: 0cf83592719e
Revises: 
Create Date: 2025-05-27 13:14:45.213575

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0cf83592719e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('urls',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_urls'))
    )
    op.create_table('post_recommendations',
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], name=op.f('fk_post_recommendations_post_id_posts')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_post_recommendations_user_id_users')),
    sa.PrimaryKeyConstraint('post_id', 'user_id', name=op.f('pk_post_recommendations'))
    )
    op.create_table('post_references',
    sa.Column('post_id', sa.Integer(), nullable=True),
    sa.Column('url_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], name=op.f('fk_post_references_post_id_posts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['url_id'], ['urls.id'], name=op.f('fk_post_references_url_id_urls'), ondelete='CASCADE')
    )
    op.drop_column('posts', 'references')
    op.drop_column('posts', 'recommended_by')
    op.alter_column('users', 'role',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    op.alter_column('users', 'prodi',
               existing_type=sa.VARCHAR(length=100),
               type_=sa.String(length=255),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'prodi',
               existing_type=sa.String(length=255),
               type_=sa.VARCHAR(length=100),
               existing_nullable=True)
    op.alter_column('users', 'role',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.add_column('posts', sa.Column('recommended_by', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('posts', sa.Column('references', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_table('post_references')
    op.drop_table('post_recommendations')
    op.drop_table('urls')
    # ### end Alembic commands ###
