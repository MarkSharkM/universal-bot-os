"""add soft delete to business_data

Revision ID: add_soft_delete_001
Revises: 
Create Date: 2025-01-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_soft_delete_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add deleted_at column to business_data table
    op.add_column('business_data', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add index for efficient soft delete queries
    op.create_index('idx_business_data_deleted_at', 'business_data', ['deleted_at'])


def downgrade():
    # Remove index
    op.drop_index('idx_business_data_deleted_at', 'business_data')
    
    # Remove column
    op.drop_column('business_data', 'deleted_at')

