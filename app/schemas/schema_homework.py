"""
宿題関連 Pydantic スキーマ

APIの入出力形式を定義する。
FastAPI はこのスキーマを使ってリクエストのバリデーションと
レスポンスのシリアライズを自動で行う。

スキーマ一覧:
  HomeworkCreate       … POST /api/homework/ のリクエストボディ
  HomeworkUpdate       … PATCH /api/homework/{id} のリクエストボディ
  HomeworkOut          … 宿題の基本情報レスポンス
  HomeworkWithStats    … 提出状況の統計付きレスポンス（教師用一覧）
  SubmissionOut        … 提出状況1件のレスポンス
  SubmissionCheck      … 提出チェック/取り消しのリクエストボディ
  UnsubmittedListOut   … 未提出者一覧レスポンス
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════
#  宿題 入力スキーマ
# ════════════════════════════════════════════════════════════

class HomeworkCreate(BaseModel):
    """
    宿題作成リクエスト。
    教師が POST /api/homework/ で送るボディ。
    """
    title:       str            = Field(..., min_length=1, max_length=200, description="宿題タイトル")
    description: Optional[str] = Field(None, description="説明・補足")
    due_date:    date           = Field(..., description="提出期限（YYYY-MM-DD）")
    subject:     Optional[str] = Field(None, max_length=100, description="科目")


class HomeworkUpdate(BaseModel):
    """
    宿題更新リクエスト。
    全フィールド任意（変更したい項目だけ送ればよい）。
    """
    title:       Optional[str]  = Field(None, max_length=200)
    description: Optional[str] = None
    due_date:    Optional[date] = None
    subject:     Optional[str] = Field(None, max_length=100)
    status:      Optional[str] = None  # "active" | "closed" | "archived"


# ════════════════════════════════════════════════════════════
#  宿題 出力スキーマ
# ════════════════════════════════════════════════════════════

class HomeworkOut(BaseModel):
    """宿題の基本情報レスポンス"""
    id:          int
    title:       str
    description: Optional[str]
    due_date:    date
    subject:     Optional[str]
    status:      str
    created_by:  Optional[int]
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


class HomeworkWithStats(HomeworkOut):
    """
    提出統計付き宿題レスポンス（教師用一覧）。
    HomeworkOut を継承し、集計フィールドを追加。
    """
    total_students:     int  # 対象生徒総数
    submitted_count:    int  # 提出済み人数
    unsubmitted_count:  int  # 未提出人数

    @property
    def submission_rate(self) -> float:
        """提出率（%）を計算"""
        if self.total_students == 0:
            return 0.0
        return round(self.submitted_count / self.total_students * 100, 1)


# ════════════════════════════════════════════════════════════
#  提出状況 スキーマ
# ════════════════════════════════════════════════════════════

class SubmissionOut(BaseModel):
    """提出状況1件のレスポンス"""
    id:           int
    homework_id:  int
    student_id:   int
    student_name: str        # 生徒名（JOIN して取得）
    submitted:    bool
    submitted_at: Optional[datetime]
    comment:      Optional[str]

    model_config = {"from_attributes": True}


class SubmissionCheck(BaseModel):
    """
    提出チェック/取り消しリクエスト。
    POST /api/homework/{id}/check で使用。
    """
    student_id: int              = Field(..., description="チェックする生徒のID")
    submitted:  bool             = Field(..., description="True=提出済み / False=未提出に戻す")
    comment:    Optional[str]    = Field(None, description="教師コメント（任意）")


class UnsubmittedListOut(BaseModel):
    """未提出者一覧レスポンス"""
    homework_id:    int
    homework_title: str
    due_date:       date
    unsubmitted:    list[SubmissionOut]  # 未提出の生徒一覧
