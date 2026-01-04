"""Add analytics_events table

Revision ID: add_analytics_events
Revises: add_soft_delete_to_business_data
Create Date: 2026-01-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_analytics_events'
down_revision = 'add_soft_delete_to_business_data'
branch_labels = None
depends_on = None


def upgrade():
    # Create analytics_events table
    op.create_table(
        'analytics_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_external_id', sa.String(200), nullable=True),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('event_data', postgresql.JSON, nullable=False, server_default='{}'),
        sa.Column('platform', sa.String(50), nullable=False, server_default='telegram'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    
    # Create indexes
    op.create_index('ix_analytics_events_bot_id', 'analytics_events', ['bot_id'])
    op.create_index('ix_analytics_events_user_id', 'analytics_events', ['user_id'])
    op.create_index('ix_analytics_events_user_external_id', 'analytics_events', ['user_external_id'])
    op.create_index('ix_analytics_events_event_name', 'analytics_events', ['event_name'])
    op.create_index('ix_analytics_events_created_at', 'analytics_events', ['created_at'])
    op.create_index('idx_analytics_bot_event', 'analytics_events', ['bot_id', 'event_name'])
    op.create_index('idx_analytics_bot_date', 'analytics_events', ['bot_id', 'created_at'])
    op.create_index('idx_analytics_user_event', 'analytics_events', ['user_id', 'event_name'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_analytics_user_event', table_name='analytics_events')
    op.drop_index('idx_analytics_bot_date', table_name='analytics_events')
    op.drop_index('idx_analytics_bot_event', table_name='analytics_events')
    op.drop_index('ix_analytics_events_created_at', table_name='analytics_events')
    op.drop_index('ix_analytics_events_event_name', table_name='analytics_events')
    op.drop_index('ix_analytics_events_user_external_id', table_name='analytics_events')
    op.drop_index('ix_analytics_events_user_id', table_name='analytics_events')
    op.drop_index('ix_analytics_events_bot_id', table_name='analytics_events')
    
    # Drop table
    op.drop_table('analytics_events')
