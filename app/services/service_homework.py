"""
宿題管理サービス

責務:
  - 宿題の作成・更新・削除
  - 宿題作成時の全生徒分提出レコード自動生成
  - 提出チェック / 取り消し
  - 未提出者一覧の取得

設計方針:
  - ルーターからビジネスロジックを分離し、テストしやすくする
  - DB の commit はこのサービス内で行う
  - 例外は HTTPException でラップしてルーターに伝える
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.homework import Homework, HomeworkStatusEnum
from app.models.homework_submission import HomeworkSubmission
from app.models.user import User, RoleEnum, StatusEnum


# ════════════════════════════════════════════════════════════
#  宿題 CRUD
# ════════════════════════════════════════════════════════════

def create_homework(
    db: Session,
    *,
    title: str,
    description: Optional[str],
    due_date,
    subject: Optional[str],
    created_by: int,
) -> Homework:
    """
    宿題を作成し、アクティブな全生徒分の提出レコードを自動生成する。

    生徒が後から追加された場合のレコードは別途作成が必要（現バージョンでは未対応）。
    """
    # ① 宿題レコード作成
    hw = Homework(
        title=title,
        description=description,
        due_date=due_date,
        subject=subject,
        created_by=created_by,
        status=HomeworkStatusEnum.active,
    )
    db.add(hw)
    db.flush()  # hw.id を確定させる（commit前）

    # ② アクティブな全生徒分の提出レコードを自動生成
    students = (
        db.query(User)
        .filter(
            User.role == RoleEnum.student,
            User.status == StatusEnum.active,
        )
        .all()
    )
    for student in students:
        submission = HomeworkSubmission(
            homework_id=hw.id,
            student_id=student.id,
            submitted=False,
        )
        db.add(submission)

    db.commit()
    db.refresh(hw)
    return hw


def get_homework_or_404(db: Session, homework_id: int) -> Homework:
    """宿題を取得する。存在しない場合は404エラー"""
    hw = db.query(Homework).filter(Homework.id == homework_id).first()
    if not hw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"宿題 id={homework_id} が見つかりません",
        )
    return hw


def list_homeworks(
    db: Session,
    *,
    include_archived: bool = False,
) -> list[Homework]:
    """
    宿題一覧を取得する。
    デフォルトではアーカイブ済みを除外する。
    作成日の新しい順で返す。
    """
    q = db.query(Homework)
    if not include_archived:
        q = q.filter(Homework.status != HomeworkStatusEnum.archived)
    return q.order_by(Homework.created_at.desc()).all()


def update_homework(
    db: Session,
    homework_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date=None,
    subject: Optional[str] = None,
    status: Optional[str] = None,
) -> Homework:
    """宿題情報を更新する。指定されたフィールドのみ更新する。"""
    hw = get_homework_or_404(db, homework_id)

    if title       is not None: hw.title       = title
    if description is not None: hw.description = description
    if due_date    is not None: hw.due_date    = due_date
    if subject     is not None: hw.subject     = subject
    if status      is not None: hw.status      = HomeworkStatusEnum(status)

    db.commit()
    db.refresh(hw)
    return hw


def delete_homework(db: Session, homework_id: int) -> None:
    """
    宿題を削除する。
    CASCADE 設定により関連する提出レコードも自動削除される。
    """
    hw = get_homework_or_404(db, homework_id)
    db.delete(hw)
    db.commit()


# ════════════════════════════════════════════════════════════
#  提出チェック
# ════════════════════════════════════════════════════════════

def check_submission(
    db: Session,
    homework_id: int,
    student_id: int,
    *,
    submitted: bool,
    comment: Optional[str] = None,
) -> HomeworkSubmission:
    """
    生徒の提出状況を更新する（提出済みにする / 未提出に戻す）。

    提出レコードが存在しない場合（宿題作成後に追加された生徒など）は
    新規作成する。
    """
    # 宿題の存在確認
    get_homework_or_404(db, homework_id)

    # 提出レコードを取得（なければ新規作成）
    sub = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id  == student_id,
        )
        .first()
    )

    if sub is None:
        # 宿題作成後に追加された生徒のケース
        sub = HomeworkSubmission(
            homework_id=homework_id,
            student_id=student_id,
            submitted=False,
        )
        db.add(sub)

    # 提出状況を更新
    sub.submitted    = submitted
    sub.submitted_at = datetime.now(timezone.utc) if submitted else None
    if comment is not None:
        sub.comment = comment

    db.commit()
    db.refresh(sub)
    return sub


# ════════════════════════════════════════════════════════════
#  未提出者一覧
# ════════════════════════════════════════════════════════════

def get_unsubmitted(
    db: Session,
    homework_id: int,
) -> list[HomeworkSubmission]:
    """
    指定した宿題の未提出者一覧を返す。
    生徒名でソートして返す（フロントでの表示順を統一）。
    """
    get_homework_or_404(db, homework_id)

    # 未提出の提出レコードを取得し、生徒情報をJOIN
    subs = (
        db.query(HomeworkSubmission)
        .join(User, HomeworkSubmission.student_id == User.id)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.submitted   == False,
        )
        .order_by(User.name)
        .all()
    )
    return subs


# ════════════════════════════════════════════════════════════
#  統計情報
# ════════════════════════════════════════════════════════════

def get_homework_stats(db: Session, homework_id: int) -> dict:
    """
    宿題の提出統計を返す。

    Returns:
        {
          "total_students": 30,
          "submitted_count": 22,
          "unsubmitted_count": 8,
          "submission_rate": 73.3
        }
    """
    get_homework_or_404(db, homework_id)

    total = (
        db.query(HomeworkSubmission)
        .filter(HomeworkSubmission.homework_id == homework_id)
        .count()
    )
    submitted = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.submitted   == True,
        )
        .count()
    )

    return {
        "total_students":    total,
        "submitted_count":   submitted,
        "unsubmitted_count": total - submitted,
        "submission_rate":   round(submitted / total * 100, 1) if total > 0 else 0.0,
    }
