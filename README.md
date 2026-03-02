# Juku Attendance App

FastAPI + SQLAlchemy + Alembic で作られた塾向けの出席管理アプリ。

## 構成

- `app/` … アプリ本体
  - `routers/` … API ルータ
  - `services/` … ビジネスロジック
  - `models/` … DB モデル
  - `schemas/` … Pydantic スキーマ
  - `db/` … DB セッション/初期化
  - `web/pages/` … 画面（HTML）を集約（`/`, `/dashboard.html`, `/checkin.html`, `/qr_display.html` で配信）
- `alembic/` … マイグレーション
- `static/` … 将来の CSS/JS 追加用

## 起動

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

必要に応じて `.env` を用意してください（DB 接続、初期管理者など）。
