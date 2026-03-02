"""
宿題管理ルーター

エンドポイント一覧:
  POST   /api/homework/              … 宿題作成（教師）
  GET    /api/homework/              … 宿題一覧（教師）
  GET    /api/homework/{id}          … 宿題詳細
  PATCH  /api/homework/{id}          … 宿題更新（教師）
  DELETE /api/homework/{id}          … 宿題削除（教師）
  POST   /api/homework/{id}/check    … 提出チェック/取り消し（教師）
  GET    /api/homework/{id}/submissions … 提出状況一覧（教師）
  GET    /api/homework/{id}/unsubmitted … 未提出者一覧（教師）

権限:
  全エンドポイント教師ロール必須（require_teacher）
  生徒は自分の宿題一覧のみ閲覧可能（GET /api/homework/my）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_teacher, require_login
from app.db.session import get_db
from app.models.user import User, RoleEnum
from app.schemas.homework import (
    HomeworkCreate, HomeworkUpdate, HomeworkOut,
    HomeworkWithStats, SubmissionOut, SubmissionCheck,
)
from app.services import homework_service

router = APIRouter(prefix="/api/homework", tags=["homework"])


# ════════════════════════════════════════════════════════════
#  宿題 CRUD
# ════════════════════════════════════════════════════════════

@router.post("/", response_model=HomeworkOut, summary="宿題作成（教師）")
def create_homework(
    body: HomeworkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """
    宿題を作成する。
    作成と同時に、アクティブな全生徒分の提出レコードを自動生成する。
    """
    hw = homework_service.create_homework(
        db,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        subject=body.subject,
        created_by=current_user.id,
    )
    return hw


@router.get("/", response_model=list[HomeworkOut], summary="宿題一覧")
def list_homeworks(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """
    宿題一覧を返す。
    教師は全宿題、生徒は自分に関係する宿題を返す。
    include_archived=True でアーカイブ済みも含む。
    """
    return homework_service.list_homeworks(db, include_archived=include_archived)


@router.get("/my", response_model=list[dict], summary="自分の宿題一覧（生徒用）")
def my_homeworks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """
    生徒自身の宿題提出状況一覧を返す。
    提出済み/未提出がひと目でわかる形で返す。
    """
    from app.models.homework_submission import HomeworkSubmission
    from app.models.homework import Homework

    subs = (
        db.query(HomeworkSubmission)
        .join(Homework, HomeworkSubmission.homework_id == Homework.id)
        .filter(HomeworkSubmission.student_id == current_user.id)
        .order_by(Homework.due_date.asc())
        .all()
    )

    return [
        {
            "homework_id":    s.homework_id,
            "title":          s.homework.title,
            "subject":        s.homework.subject,
            "due_date":       s.homework.due_date.isoformat(),
            "status":         s.homework.status,
            "submitted":      s.submitted,
            "submitted_at":   s.submitted_at.isoformat() if s.submitted_at else None,
        }
        for s in subs
    ]


@router.get("/{homework_id}", response_model=HomeworkOut, summary="宿題詳細")
def get_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_login),
):
    """宿題の詳細情報を返す"""
    return homework_service.get_homework_or_404(db, homework_id)


@router.patch("/{homework_id}", response_model=HomeworkOut, summary="宿題更新（教師）")
def update_homework(
    homework_id: int,
    body: HomeworkUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """宿題情報を更新する。送ったフィールドだけ更新される。"""
    return homework_service.update_homework(
        db, homework_id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        subject=body.subject,
        status=body.status,
    )


@router.delete("/{homework_id}", status_code=204, summary="宿題削除（教師）")
def delete_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """宿題を削除する。関連する提出レコードも削除される。"""
    homework_service.delete_homework(db, homework_id)


# ════════════════════════════════════════════════════════════
#  提出チェック
# ════════════════════════════════════════════════════════════

@router.post("/{homework_id}/check", response_model=SubmissionOut, summary="提出チェック（教師）")
def check_submission(
    homework_id: int,
    body: SubmissionCheck,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """
    生徒の提出状況を更新する。
    submitted=True で提出済み、False で未提出に戻す。
    """
    sub = homework_service.check_submission(
        db, homework_id, body.student_id,
        submitted=body.submitted,
        comment=body.comment,
    )
    # レスポンス用に生徒名を付加
    return SubmissionOut(
        id=sub.id,
        homework_id=sub.homework_id,
        student_id=sub.student_id,
        student_name=sub.student.name,
        submitted=sub.submitted,
        submitted_at=sub.submitted_at,
        comment=sub.comment,
    )


# ════════════════════════════════════════════════════════════
#  提出状況一覧・未提出者一覧
# ════════════════════════════════════════════════════════════

@router.get("/{homework_id}/submissions", response_model=list[SubmissionOut], summary="提出状況一覧（教師）")
def list_submissions(
    homework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """指定した宿題の全生徒の提出状況一覧を返す"""
    from app.models.homework_submission import HomeworkSubmission
    from app.models.user import User as UserModel

    subs = (
        db.query(HomeworkSubmission)
        .join(UserModel, HomeworkSubmission.student_id == UserModel.id)
        .filter(HomeworkSubmission.homework_id == homework_id)
        .order_by(UserModel.name)
        .all()
    )
    return [
        SubmissionOut(
            id=s.id,
            homework_id=s.homework_id,
            student_id=s.student_id,
            student_name=s.student.name,
            submitted=s.submitted,
            submitted_at=s.submitted_at,
            comment=s.comment,
        )
        for s in subs
    ]


@router.get("/{homework_id}/unsubmitted", response_model=list[SubmissionOut], summary="未提出者一覧（教師）")
def list_unsubmitted(
    homework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """指定した宿題の未提出者一覧を返す"""
    subs = homework_service.get_unsubmitted(db, homework_id)
    return [
        SubmissionOut(
            id=s.id,
            homework_id=s.homework_id,
            student_id=s.student_id,
            student_name=s.student.name,
            submitted=s.submitted,
            submitted_at=s.submitted_at,
            comment=s.comment,
        )
        for s in subs
    ]


@router.get("/{homework_id}/stats", response_model=dict, summary="宿題提出統計（教師）")
def homework_stats(
    homework_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """宿題の提出率などの統計情報を返す"""
    return homework_service.get_homework_stats(db, homework_id)
