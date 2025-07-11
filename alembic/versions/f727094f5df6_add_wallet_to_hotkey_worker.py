"""add wallet to hotkey_worker

Revision ID: f727094f5df6
Revises: 01bca204c995
Create Date: 2025-07-11 14:06:00.019148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String

# revision identifiers, used by Alembic.
revision: str = 'f727094f5df6'
down_revision: Union[str, None] = '01bca204c995'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Import the default wallet value from config
from src.config import ValidatorSettings
DEFAULT_WALLET = ValidatorSettings().kaspa_pool_owner_wallet

def upgrade() -> None:
    # Add the new column with a default for existing rows
    with op.batch_alter_table('hotkey_worker') as batch_op:
        batch_op.add_column(sa.Column('wallet', sa.String(), nullable=False, server_default=DEFAULT_WALLET))
    # Remove the server_default so new inserts must specify wallet
    with op.batch_alter_table('hotkey_worker') as batch_op:
        batch_op.alter_column('wallet', server_default=None)

def downgrade() -> None:
    with op.batch_alter_table('hotkey_worker') as batch_op:
        batch_op.drop_column('wallet')
