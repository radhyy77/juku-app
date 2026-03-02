"""
試験・成績管理ルーター

エンドポイント一覧:
  POST  /api/exam/                    … 試験作成（教師）
  GET   /api/exam/                    … 試験一覧
  GET   /api/exam/{id}                … 試験詳細
  PATCH /api/exam/{id}                … 試験更新（教師）
  DELETE /api/exam/{id}               … 試験削除（教師）
  POST  /api/exam/{id}/score          … 点数登録/更新（教師・1件）
  POST  /api/exam/{id}/score/bulk     … 点数一括登録（教師・複数件）
  GET   /api/exam/{id}/scores         … 点数一覧（教師）
  GET   /api/exam/student/{student_id} … 生徒の成績推移（グラフ用）

権限:
  試験作成・更新・削除・点数記録 → 教師ロール必須
  成績推移閲覧 → 教師は全生徒、生徒は自分のみ
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_teacher, require_login
from app.db.session import get_db
from app.models.user import User, RoleEnum
from app.schemas.exam import (
    ExamCreate, ExamUpdate, ExamOut,
    ScoreUpsert, ScoreBulkUpsert, ScoreOut,
    StudentScoreHistory,
)
from app.services import exam_service

router = APIRouter(prefix="/api/exam", tags=["exam"])


# ════════════════════════════════════════════════════════════
#  試験 CRUD
# ════════════════════════════════════════════════════════════

@router.post("/", response_model=ExamOut, summary="試験作成（教師）")
def create_exam(
    body: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """試験を作成する"""
    return exam_service.create_exam(
        db,
        title=body.title,
        subject=body.subject,
        exam_date=body.exam_date,
        max_score=body.max_score,
        description=body.description,
        created_by=current_user.id,
    )


@router.get("/", response_model=list[ExamOut], summary="試験一覧")
def list_exams(
    db: Session = Depends(get_db),
    _: User = Depends(require_login),
):
    """試験一覧を返す（試験日の新しい順）"""
    return exam_service.list_exams(db)


@router.get("/student/{student_id}", response_model=dict, summary="生徒の成績推移（グラフ用）")
def student_score_history(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """
    生徒の成績推移データを返す（折れ線グラフ用）。

    権限:
      - 教師 → 任意の生徒のデータを閲覧可能
      - 生徒 → 自分のデータのみ閲覧可能
    """
    # 生徒は自分のデータのみ閲覧可能
    if current_user.role == RoleEnum.student and current_user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="他の生徒の成績は閲覧できません",
        )

    return exam_service.get_student_score_history(db, student_id)


@router.get("/{exam_id}", response_model=ExamOut, summary="試験詳細")
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_login),
):
    """試験の詳細情報を返す"""
    return exam_service.get_exam_or_404(db, exam_id)


@router.patch("/{exam_id}", response_model=ExamOut, summary="試験更新（教師）")
def update_exam(
    exam_id: int,
    body: ExamUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """試験情報を更新する。送ったフィールドだけ更新される。"""
    return exam_service.update_exam(
        db, exam_id,
        title=body.title,
        subject=body.subject,
        exam_date=body.exam_date,
        max_score=body.max_score,
        description=body.description,
    )


@router.delete("/{exam_id}", status_code=204, summary="試験削除（教師）")
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """試験を削除する。関連する点数レコードも削除される。"""
    exam_service.delete_exam(db, exam_id)


# ════════════════════════════════════════════════════════════
#  点数登録
# ════════════════════════════════════════════════════════════

@router.post("/{exam_id}/score", response_model=dict, summary="点数登録/更新（教師・1件）")
def upsert_score(
    exam_id: int,
    body: ScoreUpsert,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """
    生徒の点数を登録/更新する。
    既に点数が登録されている場合は上書き更新する（upsert）。
    """
    score = exam_service.upsert_score(
        db, exam_id, body.student_id,
        score=body.score,
        comment=body.comment,
    )
    return {
        "id":         score.id,
        "exam_id":    score.exam_id,
        "student_id": score.student_id,
        "score":      score.score,
        "comment":    score.comment,
        "updated_at": score.updated_at.isoformat(),
    }


@router.post("/{exam_id}/score/bulk", response_model=dict, summary="点数一括登録（教師）")
def bulk_upsert_scores(
    exam_id: int,
    body: ScoreBulkUpsert,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """
    クラス全員の点数を一括で登録/更新する。
    1リクエストで複数生徒の点数を送ることができる。
    """
    scores = exam_service.bulk_upsert_scores(
        db, exam_id,
        [s.model_dump() for s in body.scores],
    )
    return {
        "updated_count": len(scores),
        "message": f"{len(scores)}件の点数を登録しました",
    }


@router.get("/{exam_id}/scores", response_model=list[dict], summary="点数一覧（教師）")
def list_scores(
    exam_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """試験の全生徒の点数一覧を返す（生徒名でソート）"""
    scores = exam_service.get_exam_scores(db, exam_id)
    exam = exam_service.get_exam_or_404(db, exam_id)

    return [
        {
            "id":           s.id,
            "student_id":   s.student_id,
            "student_name": s.student.name,
            "score":        s.score,
            "max_score":    exam.max_score,
            "score_pct":    round(s.score / exam.max_score * 100, 1) if s.score is not None else None,
            "comment":      s.comment,
            "updated_at":   s.updated_at.isoformat(),
        }
        for s in scores
    ]
