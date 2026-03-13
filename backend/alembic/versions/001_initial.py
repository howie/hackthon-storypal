"""Initial migration — all StoryPal tables.

Revision ID: 001
Revises:
Create Date: 2026-03-13

"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create PostgreSQL ENUM types
    interaction_mode_enum = postgresql.ENUM(
        "realtime", "cascade", name="interaction_mode", create_type=False
    )
    session_status_enum = postgresql.ENUM(
        "active", "completed", "failed", "disconnected", name="session_status", create_type=False
    )

    interaction_mode_enum.create(op.get_bind(), checkfirst=True)
    session_status_enum.create(op.get_bind(), checkfirst=True)

    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("google_id", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("picture_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Interaction Sessions
    op.create_table(
        "interaction_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", interaction_mode_enum, nullable=False),
        sa.Column("provider_config", postgresql.JSONB, nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("user_role", sa.String(100), nullable=False, server_default="使用者"),
        sa.Column("ai_role", sa.String(100), nullable=False, server_default="AI 助理"),
        sa.Column("scenario_context", sa.Text, nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", session_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_session_user_id", "interaction_sessions", ["user_id"])
    op.create_index("idx_session_status", "interaction_sessions", ["status"])

    # Conversation Turns
    op.create_table(
        "conversation_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interaction_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_number", sa.Integer, nullable=False),
        sa.Column("user_audio_path", sa.String(500), nullable=True),
        sa.Column("user_transcript", sa.Text, nullable=True),
        sa.Column("ai_response_text", sa.Text, nullable=True),
        sa.Column("ai_audio_path", sa.String(500), nullable=True),
        sa.Column("interrupted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "turn_number", name="uq_turn_session_number"),
    )
    op.create_index("idx_turn_session_id", "conversation_turns", ["session_id"])
    op.create_index("idx_turn_session_number", "conversation_turns", ["session_id", "turn_number"])

    # Latency Metrics
    op.create_table(
        "latency_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "turn_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversation_turns.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("total_latency_ms", sa.Integer, nullable=False),
        sa.Column("stt_latency_ms", sa.Integer, nullable=True),
        sa.Column("llm_ttft_ms", sa.Integer, nullable=True),
        sa.Column("tts_ttfb_ms", sa.Integer, nullable=True),
        sa.Column("realtime_latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_latency_turn_id", "latency_metrics", ["turn_id"])

    # Story Templates
    op.create_table(
        "story_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("target_age_min", sa.Integer, nullable=False, server_default="3"),
        sa.Column("target_age_max", sa.Integer, nullable=False, server_default="8"),
        sa.Column("language", sa.String(10), nullable=False, server_default="zh-TW"),
        sa.Column("characters", postgresql.JSONB, nullable=False),
        sa.Column("scenes", postgresql.JSONB, nullable=False),
        sa.Column("opening_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("system_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_story_template_category", "story_templates", ["category"])
    op.create_index("idx_story_template_language", "story_templates", ["language"])

    # Story Sessions
    op.create_table(
        "story_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("story_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="zh-TW"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("story_state", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("characters_config", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("child_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "interaction_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interaction_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generation_status", sa.String(20), nullable=True),
        sa.Column("generation_error", sa.Text, nullable=True),
        sa.Column("synthesis_status", sa.String(20), nullable=True),
        sa.Column("synthesis_error", sa.Text, nullable=True),
        sa.Column("image_generation_status", sa.String(20), nullable=True),
        sa.Column("image_generation_error", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_story_session_user", "story_sessions", ["user_id"])
    op.create_index("idx_story_session_status", "story_sessions", ["status"])

    # Story Turns
    op.create_table(
        "story_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("story_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_number", sa.Integer, nullable=False),
        sa.Column("turn_type", sa.String(20), nullable=False),
        sa.Column("character_name", sa.String(100), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("audio_path", sa.String(500), nullable=True),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("scene_description", sa.Text, nullable=True),
        sa.Column("choice_options", postgresql.JSONB, nullable=True),
        sa.Column("child_choice", sa.Text, nullable=True),
        sa.Column("bgm_scene", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "turn_number", name="uq_story_turn_number"),
    )
    op.create_index("idx_story_turn_session", "story_turns", ["session_id"])
    op.create_index("idx_story_turn_number", "story_turns", ["session_id", "turn_number"])

    # Story Generated Content
    op.create_table(
        "story_generated_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("story_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("content_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_story_content_session", "story_generated_content", ["session_id"])
    op.create_index(
        "idx_story_content_type",
        "story_generated_content",
        ["session_id", "content_type"],
    )

    # Story Cost Events
    op.create_table(
        "story_cost_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("story_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False, server_default=""),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("characters_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_estimate", sa.DECIMAL(10, 6), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_story_cost_session", "story_cost_events", ["session_id"])
    op.create_index("idx_story_cost_created", "story_cost_events", ["created_at"])

    # Seed default story templates
    story_templates = sa.table(
        "story_templates",
        sa.column("id", postgresql.UUID),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("target_age_min", sa.Integer),
        sa.column("target_age_max", sa.Integer),
        sa.column("language", sa.String),
        sa.column("characters", postgresql.JSONB),
        sa.column("scenes", postgresql.JSONB),
        sa.column("opening_prompt", sa.Text),
        sa.column("system_prompt", sa.Text),
        sa.column("is_default", sa.Boolean),
    )

    op.bulk_insert(
        story_templates,
        [
            {
                "id": "a1b2c3d4-1111-4000-8000-000000000001",
                "name": "勇敢小兔的森林冒險",
                "description": "小兔子棉花糖在神秘森林中展開一場勇敢的冒險",
                "category": "fairy_tale",
                "target_age_min": 4,
                "target_age_max": 8,
                "language": "zh-TW",
                "characters": [
                    {
                        "name": "棉花糖",
                        "description": "一隻勇敢又善良的小白兔",
                        "voice_provider": "gemini",
                        "voice_id": "Puck",
                        "voice_settings": {},
                        "emotion": "happy",
                    },
                    {
                        "name": "松果爺爺",
                        "description": "一隻年老的松鼠",
                        "voice_provider": "gemini",
                        "voice_id": "Charon",
                        "voice_settings": {},
                        "emotion": "neutral",
                    },
                ],
                "scenes": [
                    {"scene_number": 1, "title": "出發", "description": "棉花糖決定出發冒險"},
                    {"scene_number": 2, "title": "森林深處", "description": "進入神秘的森林"},
                    {"scene_number": 3, "title": "結局", "description": "冒險的結局"},
                ],
                "opening_prompt": "在一個陽光明媚的早晨，小兔子棉花糖決定出發去探險...",
                "system_prompt": "",
                "is_default": True,
            },
            {
                "id": "a1b2c3d4-2222-4000-8000-000000000002",
                "name": "星際探險家",
                "description": "小太空人阿星駕駛太空船探索未知星球",
                "category": "adventure",
                "target_age_min": 5,
                "target_age_max": 10,
                "language": "zh-TW",
                "characters": [
                    {
                        "name": "阿星",
                        "description": "勇敢的小太空人",
                        "voice_provider": "gemini",
                        "voice_id": "Puck",
                        "voice_settings": {},
                        "emotion": "excited",
                    },
                    {
                        "name": "AI小助手",
                        "description": "太空船的智慧助手",
                        "voice_provider": "gemini",
                        "voice_id": "Kore",
                        "voice_settings": {},
                        "emotion": "neutral",
                    },
                ],
                "scenes": [
                    {"scene_number": 1, "title": "發射", "description": "太空船發射升空"},
                    {"scene_number": 2, "title": "外太空", "description": "抵達未知星球"},
                    {"scene_number": 3, "title": "返航", "description": "安全返回地球"},
                ],
                "opening_prompt": "三、二、一...發射！小太空人阿星的太空船衝上了天空...",
                "system_prompt": "",
                "is_default": True,
            },
            {
                "id": "a1b2c3d4-3333-4000-8000-000000000003",
                "name": "魔法廚房大冒險",
                "description": "小廚師咪咪在魔法廚房學習製作神奇料理",
                "category": "daily_life",
                "target_age_min": 3,
                "target_age_max": 7,
                "language": "zh-TW",
                "characters": [
                    {
                        "name": "咪咪",
                        "description": "愛做菜的小貓咪",
                        "voice_provider": "gemini",
                        "voice_id": "Aoede",
                        "voice_settings": {},
                        "emotion": "happy",
                    },
                    {
                        "name": "鍋鍋師傅",
                        "description": "會說話的魔法鍋",
                        "voice_provider": "gemini",
                        "voice_id": "Fenrir",
                        "voice_settings": {},
                        "emotion": "neutral",
                    },
                ],
                "scenes": [
                    {
                        "scene_number": 1,
                        "title": "發現魔法廚房",
                        "description": "咪咪發現一間神奇的廚房",
                    },
                    {"scene_number": 2, "title": "料理挑戰", "description": "開始製作魔法料理"},
                    {"scene_number": 3, "title": "完成", "description": "成功做出美味料理"},
                ],
                "opening_prompt": "小貓咪咪打開了一扇從未見過的門，裡面是一間閃閃發光的廚房...",
                "system_prompt": "",
                "is_default": True,
            },
            {
                "id": "a1b2c3d4-4444-4000-8000-000000000004",
                "name": "海洋探險記",
                "description": "小海龜阿海和朋友們在海底世界探險",
                "category": "science",
                "target_age_min": 4,
                "target_age_max": 9,
                "language": "zh-TW",
                "characters": [
                    {
                        "name": "阿海",
                        "description": "好奇心旺盛的小海龜",
                        "voice_provider": "gemini",
                        "voice_id": "Puck",
                        "voice_settings": {},
                        "emotion": "happy",
                    },
                    {
                        "name": "珊珊",
                        "description": "美麗的珊瑚精靈",
                        "voice_provider": "gemini",
                        "voice_id": "Aoede",
                        "voice_settings": {},
                        "emotion": "neutral",
                    },
                ],
                "scenes": [
                    {"scene_number": 1, "title": "出發探險", "description": "阿海決定探索海底"},
                    {"scene_number": 2, "title": "海底世界", "description": "發現美麗的珊瑚礁"},
                    {"scene_number": 3, "title": "回家", "description": "帶著新知識回家"},
                ],
                "opening_prompt": "在溫暖的海水中，小海龜阿海伸了個懶腰...",
                "system_prompt": "",
                "is_default": True,
            },
            {
                "id": "a1b2c3d4-5555-4000-8000-000000000005",
                "name": "時光機大冒險",
                "description": "小發明家阿諾搭乘時光機穿越到不同時代",
                "category": "adventure",
                "target_age_min": 6,
                "target_age_max": 10,
                "language": "zh-TW",
                "characters": [
                    {
                        "name": "阿諾",
                        "description": "愛發明的小男孩",
                        "voice_provider": "gemini",
                        "voice_id": "Puck",
                        "voice_settings": {},
                        "emotion": "excited",
                    },
                    {
                        "name": "時鐘精靈",
                        "description": "守護時間的精靈",
                        "voice_provider": "gemini",
                        "voice_id": "Charon",
                        "voice_settings": {},
                        "emotion": "neutral",
                    },
                ],
                "scenes": [
                    {"scene_number": 1, "title": "發明時光機", "description": "阿諾完成了時光機"},
                    {"scene_number": 2, "title": "穿越時空", "description": "來到不同的時代"},
                    {"scene_number": 3, "title": "回到現在", "description": "安全回到現代"},
                ],
                "opening_prompt": "阿諾的小工作室裡，一台奇怪的機器開始發出嗡嗡聲...",
                "system_prompt": "",
                "is_default": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("story_cost_events")
    op.drop_table("story_generated_content")
    op.drop_table("story_turns")
    op.drop_table("story_sessions")
    op.drop_table("story_templates")
    op.drop_table("latency_metrics")
    op.drop_table("conversation_turns")
    op.drop_table("interaction_sessions")
    op.drop_table("users")

    # Drop ENUM types
    sa.Enum(name="session_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="interaction_mode").drop(op.get_bind(), checkfirst=True)
