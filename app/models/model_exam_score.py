"""
試験点数テーブルモデル

1試験 × 1生徒 = 1レコードで点数を管理する。
点数は後から修正可能（updated_at で最終更新日時を追跡）。

成績推移グラフ用のデータ取得フロー:
  GET /api/exam/student/{id}
    → student_id でフィルタして exam_date 順に取得
    → フロント側でグラフ描画
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Text, DateTime,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class ExamScore(Base):
    """
    試験点数テーブル。

    試験（Exam）と生徒（User）の中間テーブル。
    1試験につき1生徒1レコード（ユニーク制約あり）。
    score は NULL 可（未採点状態を表現する）。
    """
    __tablename__ = "exam_scores"
    __table_args__ = (
        # 同一試験・同一生徒のレコードは1件のみ
        UniqueConstraint("exam_id", "student_id", name="uq_score_exam_student"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # ── 紐付け ───────────────────────────────────────────────────────────────
    exam_id = Column(
        Integer,
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── 点数 ─────────────────────────────────────────────────────────────────
    # NULL = 未採点。0点と未採点を区別するため nullable=True にする
    score = Column(Integer, nullable=True)

    # ── 教師メモ ─────────────────────────────────────────────────────────────
    # 点数に対するコメント（例: 「計算ミスが多い」）
    comment = Column(Text, nullable=True)

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
    exam    = relationship("Exam", back_populates="scores")
    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return (
            f"<ExamScore exam={self.exam_id} "
            f"student={self.student_id} score={self.score}>"
        )
