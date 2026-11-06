# atcoder-participations

AtCoderのコンテストアーカイブとユーザー参加履歴をSQLiteに同期し、参加・未参加コンテストを返すFastAPIアプリです。

## ローカル開発

Python 3.12以上を使用します。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

本番利用前に `.env` の `ATCODER_USER_AGENT` を管理者の連絡先へ変更してください。

## ユーザー管理

```bash
atcoder-participations users add blue_jam
atcoder-participations users list
atcoder-participations users sync blue_jam
atcoder-participations users sync-all
atcoder-participations users delete blue_jam
atcoder-participations contests sync
atcoder-participations contests reclassify
```

ユーザー追加時にアーカイブとAlgorithm・Heuristicの全参加履歴を同期します。登録後は6時間ごとの枠内でユーザーごとにランダムな時刻に更新されます。

## API

```bash
curl 'http://localhost:8000/api/v1/users/blue_jam/contests?contest_class=abc&contest_class=arc&include_unparticipated=true&limit=50&offset=0'
```

`contest_class` は `abc`、`arc`、`agc`、`ahc`、`other` を複数指定できます。省略時は全クラス、`include_unparticipated` の既定値は `false` です。OpenAPI UIは `/docs` で確認できます。

## Docker Compose

```bash
export ATCODER_USER_AGENT='atcoder-participations/0.1 (contact: you@example.com)'
docker compose up --build -d
docker compose exec api atcoder-participations users add blue_jam
```

SQLiteは名前付きボリューム `atcoder_data` に保存されます。スケジューラ重複を避けるため、APIコンテナは1レプリカで運用してください。

## 品質チェック

```bash
ruff check .
mypy app
pytest
docker compose config
```
