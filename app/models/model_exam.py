"""
試験テーブルモデル

試験の基本情報を管理するテーブル。
教師が試験を作成し、試験名・日付・満点・科目を設定する。

テーブル設計:
  - exams テーブル … 試験の基本情報（1試験 = 1行）
  - 点数は exam_scores テーブルで管理（生徒ごとに1行）

フロー:
  教師が POST /api/exam/ で試験を作成
    → exams テーブルに1行追加
  教師が POST /api/exam/{id}/score で点数を記録
    → exam_scores テーブルに生徒ごとの点数を追加
"""
from datetime import datetime, timezone
import enum

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime,
    ForeignKey, Enum,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Exam(Base):
    """
    試験テーブル。

    教師が作成する試験の基本情報を保持する。
    max_score（満点）は点数の割合計算に使用する。
    """
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)

    # ── 基本情報 ────────────────────────────────────────────────────────────
    title     = Column(String(200), nullable=False)   # 試験名（例: 5月中間テスト）
    subject   = Column(String(100), nullable=True)    # 科目（例: 数学・英語）
    exam_date = Column(Date, nullable=False)           # 試験実施日
    max_score = Column(Integer, nullable=False, default=100)  # 満点（デフォルト100）
    description = Column(Text, nullable=True)         # 補足説明（任意）

    # ── 作成者（教師） ───────────────────────────────────────────────────────
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
    # 点数一覧（ExamScore テーブルへの1対多）
    scores = relationship(
        "ExamScore",
        back_populates="exam",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Exam id={self.id} title={self.title} date={self.exam_date}>"
