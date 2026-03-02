"""
試験・成績関連 Pydantic スキーマ

APIの入出力形式を定義する。

スキーマ一覧:
  ExamCreate        … POST /api/exam/ のリクエストボディ
  ExamUpdate        … PATCH /api/exam/{id} のリクエストボディ
  ExamOut           … 試験の基本情報レスポンス
  ScoreUpsert       … 点数登録/更新のリクエストボディ（1件）
  ScoreBulkUpsert   … 点数一括登録のリクエストボディ（複数件）
  ScoreOut          … 点数1件のレスポンス
  StudentScoreHistory … 生徒の成績推移レスポンス（グラフ用）
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════
#  試験 入力スキーマ
# ════════════════════════════════════════════════════════════

class ExamCreate(BaseModel):
    """
    試験作成リクエスト。
    教師が POST /api/exam/ で送るボディ。
    """
    title:       str            = Field(..., min_length=1, max_length=200, description="試験名")
    subject:     Optional[str] = Field(None, max_length=100, description="科目")
    exam_date:   date           = Field(..., description="試験実施日（YYYY-MM-DD）")
    max_score:   int            = Field(100, ge=1, description="満点（デフォルト100）")
    description: Optional[str] = Field(None, description="補足説明")


class ExamUpdate(BaseModel):
    """
    試験更新リクエスト。
    全フィールド任意。
    """
    title:       Optional[str]  = Field(None, max_length=200)
    subject:     Optional[str] = Field(None, max_length=100)
    exam_date:   Optional[date] = None
    max_score:   Optional[int]  = Field(None, ge=1)
    description: Optional[str] = None


# ════════════════════════════════════════════════════════════
#  試験 出力スキーマ
# ════════════════════════════════════════════════════════════

class ExamOut(BaseModel):
    """試験の基本情報レスポンス"""
    id:          int
    title:       str
    subject:     Optional[str]
    exam_date:   date
    max_score:   int
    description: Optional[str]
    created_by:  Optional[int]
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════
#  点数 スキーマ
# ════════════════════════════════════════════════════════════

class ScoreUpsert(BaseModel):
    """
    点数登録/更新リクエスト（1件）。
    既にレコードがあれば更新、なければ新規作成（upsert）。
    """
    student_id: int           = Field(..., description="生徒のユーザーID")
    score:      Optional[int] = Field(None, ge=0, description="点数（None=未採点）")
    comment:    Optional[str] = Field(None, description="教師コメント")


class ScoreBulkUpsert(BaseModel):
    """
    点数一括登録リクエスト。
    1回のAPIコールで複数生徒の点数を登録できる。
    例: クラス全員の点数を一括入力する場面で使用。
    """
    scores: list[ScoreUpsert] = Field(..., description="点数リスト")


class ScoreOut(BaseModel):
    """点数1件のレスポンス"""
    id:           int
    exam_id:      int
    student_id:   int
    student_name: str          # 生徒名（JOIN して取得）
    score:        Optional[int]
    max_score:    int          # 試験の満点（割合計算用）
    comment:      Optional[str]
    updated_at:   datetime

    model_config = {"from_attributes": True}

    @property
    def score_pct(self) -> Optional[float]:
        """得点率（%）を計算。未採点の場合は None"""
        if self.score is None:
            return None
        return round(self.score / self.max_score * 100, 1)


class StudentScoreHistory(BaseModel):
    """
    生徒の成績推移レスポンス（グラフ描画用）。
    GET /api/exam/student/{id} で返す。

    exams リストは exam_date 昇順で返すため、
    フロントはそのまま折れ線グラフの X 軸に使える。
    """
    student_id:   int
    student_name: str
    exams: list[dict]  # [{exam_id, title, exam_date, score, max_score, score_pct}]
