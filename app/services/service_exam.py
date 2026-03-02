"""
試験・成績管理サービス

責務:
  - 試験の作成・更新・削除
  - 点数の登録/更新（upsert: 既存なら更新、なければ新規作成）
  - 点数の一括登録
  - 生徒ごとの成績推移データ取得（グラフ用）
  - 試験ごとの点数一覧取得

設計方針:
  - upsert を使うことで「登録」「修正」を同じAPIで処理する
  - 成績推移は exam_date 昇順で返し、フロントがそのままグラフに使える形にする
"""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.exam_score import ExamScore
from app.models.user import User, RoleEnum, StatusEnum


# ════════════════════════════════════════════════════════════
#  試験 CRUD
# ════════════════════════════════════════════════════════════

def create_exam(
    db: Session,
    *,
    title: str,
    subject: Optional[str],
    exam_date,
    max_score: int,
    description: Optional[str],
    created_by: int,
) -> Exam:
    """試験を作成する"""
    exam = Exam(
        title=title,
        subject=subject,
        exam_date=exam_date,
        max_score=max_score,
        description=description,
        created_by=created_by,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def get_exam_or_404(db: Session, exam_id: int) -> Exam:
    """試験を取得する。存在しない場合は404エラー"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"試験 id={exam_id} が見つかりません",
        )
    return exam


def list_exams(db: Session) -> list[Exam]:
    """試験一覧を取得する（試験日の新しい順）"""
    return db.query(Exam).order_by(Exam.exam_date.desc()).all()


def update_exam(
    db: Session,
    exam_id: int,
    *,
    title: Optional[str] = None,
    subject: Optional[str] = None,
    exam_date=None,
    max_score: Optional[int] = None,
    description: Optional[str] = None,
) -> Exam:
    """試験情報を更新する。指定されたフィールドのみ更新する。"""
    exam = get_exam_or_404(db, exam_id)

    if title       is not None: exam.title       = title
    if subject     is not None: exam.subject     = subject
    if exam_date   is not None: exam.exam_date   = exam_date
    if max_score   is not None: exam.max_score   = max_score
    if description is not None: exam.description = description

    db.commit()
    db.refresh(exam)
    return exam


def delete_exam(db: Session, exam_id: int) -> None:
    """
    試験を削除する。
    CASCADE 設定により関連する点数レコードも自動削除される。
    """
    exam = get_exam_or_404(db, exam_id)
    db.delete(exam)
    db.commit()


# ════════════════════════════════════════════════════════════
#  点数の登録/更新（upsert）
# ════════════════════════════════════════════════════════════

def upsert_score(
    db: Session,
    exam_id: int,
    student_id: int,
    *,
    score: Optional[int],
    comment: Optional[str] = None,
) -> ExamScore:
    """
    点数を登録/更新する（upsert）。

    既に点数レコードがあれば更新、なければ新規作成する。
    これにより「登録」と「修正」を同じAPIで処理できる。
    """
    # 試験の存在確認
    exam = get_exam_or_404(db, exam_id)

    # 満点を超えていないか確認
    if score is not None and score > exam.max_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"点数（{score}）が満点（{exam.max_score}）を超えています",
        )

    # 既存レコードを検索
    existing = (
        db.query(ExamScore)
        .filter(
            ExamScore.exam_id    == exam_id,
            ExamScore.student_id == student_id,
        )
        .first()
    )

    if existing:
        # 既存レコードを更新
        existing.score   = score
        if comment is not None:
            existing.comment = comment
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 新規レコードを作成
        new_score = ExamScore(
            exam_id=exam_id,
            student_id=student_id,
            score=score,
            comment=comment,
        )
        db.add(new_score)
        db.commit()
        db.refresh(new_score)
        return new_score


def bulk_upsert_scores(
    db: Session,
    exam_id: int,
    scores: list[dict],
) -> list[ExamScore]:
    """
    点数を一括登録/更新する。

    scores: [{"student_id": 1, "score": 85, "comment": "..."}, ...]

    クラス全員の点数を一括入力する際に使用する。
    各生徒に対して upsert_score を呼ぶ。
    """
    results = []
    for item in scores:
        result = upsert_score(
            db,
            exam_id,
            item["student_id"],
            score=item.get("score"),
            comment=item.get("comment"),
        )
        results.append(result)
    return results


# ════════════════════════════════════════════════════════════
#  点数一覧
# ════════════════════════════════════════════════════════════

def get_exam_scores(db: Session, exam_id: int) -> list[ExamScore]:
    """
    試験の点数一覧を取得する（教師用）。
    生徒名でソートして返す。
    """
    get_exam_or_404(db, exam_id)

    return (
        db.query(ExamScore)
        .join(User, ExamScore.student_id == User.id)
        .filter(ExamScore.exam_id == exam_id)
        .order_by(User.name)
        .all()
    )


# ════════════════════════════════════════════════════════════
#  生徒の成績推移（グラフ用）
# ════════════════════════════════════════════════════════════

def get_student_score_history(db: Session, student_id: int) -> dict:
    """
    生徒の成績推移データを取得する。
    試験日の古い順で返すため、フロントはそのまま折れ線グラフに使える。

    Returns:
        {
          "student_id": 1,
          "student_name": "田中 太郎",
          "exams": [
            {
              "exam_id": 1,
              "title": "5月中間テスト",
              "subject": "数学",
              "exam_date": "2025-05-20",
              "score": 82,
              "max_score": 100,
              "score_pct": 82.0
            },
            ...
          ]
        }
    """
    # 生徒の存在確認
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"生徒 id={student_id} が見つかりません",
        )

    # 点数を試験日の古い順で取得（試験情報もJOIN）
    scores = (
        db.query(ExamScore)
        .join(Exam, ExamScore.exam_id == Exam.id)
        .filter(ExamScore.student_id == student_id)
        .order_by(Exam.exam_date.asc())
        .all()
    )

    # グラフ用データに整形
    exams_data = []
    for s in scores:
        score_pct = None
        if s.score is not None:
            score_pct = round(s.score / s.exam.max_score * 100, 1)

        exams_data.append({
            "exam_id":   s.exam.id,
            "title":     s.exam.title,
            "subject":   s.exam.subject,
            "exam_date": s.exam.exam_date.isoformat(),
            "score":     s.score,
            "max_score": s.exam.max_score,
            "score_pct": score_pct,
        })

    return {
        "student_id":   student.id,
        "student_name": student.name,
        "exams":        exams_data,
    }
