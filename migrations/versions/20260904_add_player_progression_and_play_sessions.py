"""Add player progression and Neon Runner session tables.

Revision ID: 20260904_phase2
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260904_phase2"
down_revision = None
branch_labels = None
depends_on = None


def _user_table(bind):
    tables = inspect(bind).get_table_names()
    if "user" in tables:
        return "user"
    if "users" in tables:
        return "users"
    raise RuntimeError("The existing user table was not found; migration stopped safely.")


def upgrade():
    bind = op.get_bind()
    user_table = _user_table(bind)
    user_columns = {column["name"] for column in inspect(bind).get_columns(user_table)}

    new_user_columns = [
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("total_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_login_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_date", sa.Date(), nullable=True),
        sa.Column("last_reward_claimed_date", sa.Date(), nullable=True),
    ]
    for column in new_user_columns:
        if column.name not in user_columns:
            op.add_column(user_table, column)

    tables = set(inspect(bind).get_table_names())
    if "user_activities" not in tables:
        op.create_table(
            "user_activities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("action_type", sa.String(length=60), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=False),
            sa.Column("xp_earned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("idempotency_key", sa.String(length=160), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], [f"{user_table}.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("idempotency_key", name="uq_user_activity_idempotency_key"),
        )
        op.create_index("ix_user_activities_user_id", "user_activities", ["user_id"])
        op.create_index("ix_user_activities_action_type", "user_activities", ["action_type"])
        op.create_index("ix_user_activities_created_at", "user_activities", ["created_at"])

    if "play_sessions" not in tables:
        op.create_table(
            "play_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("game_slug", sa.String(length=80), nullable=False),
            sa.Column("session_token_hash", sa.String(length=64), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["user_id"], [f"{user_table}.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("session_token_hash", name="uq_play_session_token_hash"),
        )
        op.create_index("ix_play_sessions_user_id", "play_sessions", ["user_id"])
        op.create_index("ix_play_sessions_game_slug", "play_sessions", ["game_slug"])


def downgrade():
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "play_sessions" in tables:
        op.drop_index("ix_play_sessions_game_slug", table_name="play_sessions")
        op.drop_index("ix_play_sessions_user_id", table_name="play_sessions")
        op.drop_table("play_sessions")
    if "user_activities" in tables:
        op.drop_index("ix_user_activities_created_at", table_name="user_activities")
        op.drop_index("ix_user_activities_action_type", table_name="user_activities")
        op.drop_index("ix_user_activities_user_id", table_name="user_activities")
        op.drop_table("user_activities")

    user_table = _user_table(bind)
    user_columns = {column["name"] for column in inspect(bind).get_columns(user_table)}
    for column_name in (
        "last_reward_claimed_date",
        "last_activity_date",
        "current_login_streak",
        "level",
        "total_xp",
        "avatar_url",
    ):
        if column_name in user_columns:
            op.drop_column(user_table, column_name)
