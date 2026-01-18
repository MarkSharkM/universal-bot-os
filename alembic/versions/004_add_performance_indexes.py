"""add_performance_indexes

Revision ID: 004_perf_indexes
Revises: add_soft_delete_to_business_data
Create Date: 2026-01-18 01:04:00

Add database indexes for performance optimization:
- messages(bot_id, role, timestamp) for admin panel queries
- users(bot_id, external_id, platform) for user lookups
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_perf_indexes'
down_revision = 'add_soft_delete_to_business_data'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add performance indexes for 100K users/month scale.
    
    These indexes optimize:
    1. Admin panel message queries (filter by bot + role + time)
    2. User lookup queries (by external_id + platform)
    """
    # Index for messages table - optimizes admin panel queries
    # Usage: filtering messages by bot_id, role, and timestamp
    op.create_index(
        'idx_messages_bot_role_timestamp',
        'messages',
        ['bot_id', 'role', 'timestamp'],
        unique=False
    )
    
    # Index for messages table - optimizes user message history
    # Usage: fetching all messages for specific user
    op.create_index(
        'idx_messages_bot_user_role_timestamp',
        'messages',
        ['bot_id', 'user_id', 'role', 'timestamp'],
        unique=False
    )
    
    # Index for users table - optimizes user lookups
    # Usage: get_user(external_id, platform) queries
    op.create_index(
        'idx_users_bot_external_platform',
        'users',
        ['bot_id', 'external_id', 'platform'],
        unique=False
    )
    
    # Index for business_data - optimizes partner/log queries
    # Usage: filtering by bot_id, data_type, and deleted_at
    op.create_index(
        'idx_business_data_bot_type_deleted',
        'business_data',
        ['bot_id', 'data_type', 'deleted_at'],
        unique=False
    )


def downgrade():
    """
    Remove performance indexes.
    """
    op.drop_index('idx_business_data_bot_type_deleted', table_name='business_data')
    op.drop_index('idx_users_bot_external_platform', table_name='users')
    op.drop_index('idx_messages_bot_user_role_timestamp', table_name='messages')
    op.drop_index('idx_messages_bot_role_timestamp', table_name='messages')
