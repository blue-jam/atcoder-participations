# atcoder-participations

指定したユーザーが、指定した種類の AtCoder コンテストに直近1週間で参加したかを確認します。
参加がなければ IFTTT の事前警告 webhook を送り、1分後に罰を実行する webhook を送ります。
API サーバーやデータベースは使用せず、GitHub Actions が毎週月曜日23:00（JST）に単発実行します。

## GitHub の設定

リポジトリの Settings → Secrets and variables → Actions で次を設定してください。

Secrets:

- `WARNING_WEBHOOK_URL`: 事前警告用 IFTTT Webhooks URL
- `PENALTY_WEBHOOK_URL`: 罰実行用 IFTTT Webhooks URL

Variables:

- `ATCODER_USERNAME`: 確認するAtCoderユーザー名。省略時は `blue_jam`
- `TARGET_CONTEST_CLASSES`: 対象クラスをカンマ区切りで指定（例: `abc,arc`）。省略時は `abc`
- `ATCODER_USER_AGENT`: 管理者の連絡先を含む User-Agent（設定を推奨）
- `WEBHOOK_VALUE1`: IFTTTの `value1`。省略時はAtCoderユーザー名
- `WEBHOOK_VALUE2`: IFTTTの `value2`。省略時は対象クラス
- `WEBHOOK_VALUE3`: IFTTTの `value3`。省略時は判定時刻（UTC）

対象クラスには `abc`、`arc`、`agc`、`ahc`、`other` を指定できます。判定期間は実行時刻の
直前7日間です。`WEBHOOK_VALUE1`〜`WEBHOOK_VALUE3` が未設定の場合、IFTTT には
ユーザー名・対象クラス・判定時刻（UTC）を JSON で送ります。

Actions の `Weekly participation check` は手動実行もできます。スケジュールの cron は UTC の
月曜14:00で、JST の月曜23:00に相当します。

## ローカル開発

Python 3.12以上を使用します。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
cp .env.example .env
atcoder-participations
```

本番利用前に `.env` の `ATCODER_USER_AGENT` を管理者の連絡先へ変更してください。

## 品質チェック

```bash
ruff check .
mypy app
pytest
```
