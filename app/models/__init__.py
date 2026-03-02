# モデルをここで全部インポートしておくと
# alembic env.py や main.py での import 漏れを防げる
from app.models.user import User, RoleEnum, StatusEnum                    # noqa: F401
from app.models.permission import Permission, PermEnum, ALL_ADMIN_PERMS   # noqa: F401
from app.models.attendance import AttendanceLog, CheckMethodEnum           # noqa: F401
from app.models.qr_token import QRToken   # noqa: F401
from app.models.audit import ScanEvent, AlertLog   # noqa: F401
# ── 宿題・成績管理モデル（新規追加）
from app.models.homework import Homework, HomeworkStatusEnum              # noqa: F401
from app.models.homework_submission import HomeworkSubmission             # noqa: F401
from app.models.exam import Exam                                          # noqa: F401
from app.models.exam_score import ExamScore                               # noqa: F401