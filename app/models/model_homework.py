"""
宿題テーブルモデル

宿題の基本情報を管理するテーブル。
教師が宿題を作成し、タイトル・説明・期限・科目を設定する。

テーブル設計:
  - homeworks テーブル … 宿題の基本情報（1宿題 = 1行）
  - 提出状況は homework_submissions テーブルで管理（別ファイル）

フロー:
  教師が POST /api/homework/ で宿題を作成
    → homeworks テーブルに1行追加
    → アクティブな全生徒分の HomeworkSubmission レコードを自動生成
"""
from datetime import datetime, timezone
import enum

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime,
    ForeignKey, Enum,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class HomeworkStatusEnum(str, enum.Enum):
    active   = "active"    # 受付中（期限前）
    closed   = "closed"    # 締め切り済み
    archived = "archived"  # アーカイブ（非表示）


class Homework(Base):
    """
    宿題テーブル。

    教師が作成する宿題の基本情報を保持する。
    提出数などはクエリ時に集計するため、このテーブルには持たない。
    """
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)

    # ── 基本情報 ────────────────────────────────────────────────────────────
    title       = Column(String(200), nullable=False)   # 宿題タイトル
    description = Column(Text, nullable=True)           # 説明・補足（任意）
    due_date    = Column(Date, nullable=False)           # 提出期限
    subject     = Column(String(100), nullable=True)    # 科目（例: 数学・英語）

    # ── 状態 ────────────────────────────────────────────────────────────────
    status = Column(
        Enum(HomeworkStatusEnum),
        nullable=False,
        default=HomeworkStatusEnum.active,
    )

    # ── 作成者（教師） ───────────────────────────────────────────────────────
    # ユーザー削除後も宿題レコードは残すため SET NULL
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── タイムスタンプ ──────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── リレーション ────────────────────────────────────────────────────────
    # 提出状況一覧（HomeworkSubmission テーブルへの1対多）
    submissions = relationship(
        "HomeworkSubmission",
        back_populates="homework",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Homework id={self.id} title={self.title} due={self.due_date}>"
