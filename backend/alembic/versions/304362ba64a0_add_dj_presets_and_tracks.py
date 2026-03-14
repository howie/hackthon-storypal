"""add_dj_presets_and_tracks

Revision ID: 304362ba64a0
Revises: 001
Create Date: 2026-03-14 08:05:53.680997

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "304362ba64a0"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dj_presets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_dj_presets_user_name"),
    )
    op.create_index("idx_dj_presets_user_id", "dj_presets", ["user_id"], unique=False)
    op.create_table(
        "dj_tracks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("preset_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("hotkey", sa.String(length=10), nullable=True),
        sa.Column("loop", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("tts_provider", sa.String(length=50), nullable=True),
        sa.Column("tts_voice_id", sa.String(length=100), nullable=True),
        sa.Column("tts_speed", sa.DECIMAL(precision=3, scale=2), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("audio_storage_path", sa.String(length=500), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("volume", sa.DECIMAL(precision=3, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["preset_id"], ["dj_presets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dj_tracks_preset_id", "dj_tracks", ["preset_id"], unique=False)
    op.create_index(
        "idx_dj_tracks_sort_order", "dj_tracks", ["preset_id", "sort_order"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_dj_tracks_sort_order", table_name="dj_tracks")
    op.drop_index("idx_dj_tracks_preset_id", table_name="dj_tracks")
    op.drop_table("dj_tracks")
    op.drop_index("idx_dj_presets_user_id", table_name="dj_presets")
    op.drop_table("dj_presets")
