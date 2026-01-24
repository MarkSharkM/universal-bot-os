"""add_token_hash_to_bots

Revision ID: 005_token_hash
Revises: 004_perf_indexes
Create Date: 2026-01-24 14:00:00

Add token_hash column to bots table for O(1) bot lookup by token.

Security and Performance improvements:
- token_hash: SHA-256 hash of bot token for fast lookup
- Indexed for O(1) queries instead of O(N) decryption loop
- Reduces attack surface by minimizing decryption operations
- Standard practice for credential lookup (like password hashing)

Usage:
- Webhook receives bot token from Telegram
- Compute SHA-256 hash of incoming token
- Fast database lookup by hash (indexed)
- Decrypt only the matched bot's token for verification
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_token_hash'
down_revision = '004_perf_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add token_hash column and index to bots table.
    
    Security architecture:
    1. token (encrypted) - for storage security (AES-256)
    2. token_hash (hashed) - for lookup speed (SHA-256, indexed)
    
    This combines best of both worlds:
    - Encryption protects from database breach
    - Hashing enables fast lookup without decryption
    """
    # Add token_hash column (nullable initially for existing bots)
    op.add_column(
        'bots',
        sa.Column('token_hash', sa.String(64), nullable=True)
    )
    
    # Create unique index for fast O(1) lookup
    # Unique constraint ensures no token collisions
    op.create_index(
        'idx_bots_token_hash',
        'bots',
        ['token_hash'],
        unique=True
    )
    
    # Note: Existing bots need token_hash populated via migration script
    # See scripts/migrate_bot_token_hashes.py


def downgrade():
    """
    Remove token_hash column and index.
    Falls back to O(N) decryption loop for bot lookup.
    """
    op.drop_index('idx_bots_token_hash', table_name='bots')
    op.drop_column('bots', 'token_hash')
