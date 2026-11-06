# AGENTS.md

## リポジトリの目的

このリポジトリは、指定した AtCoder ユーザーが対象クラスのコンテストに直近 7 日間で参加したかを確認する Python CLI です。該当する参加がなければ、IFTTT の警告用 Webhook を送信し、一定時間後に罰実行用 Webhook を送信します。

API サーバーやデータベースは持ちません。通常は GitHub Actions から毎週月曜日 23:00（JST）に単発実行されます。

## 技術構成

- Python 3.12 以上
- パッケージ管理・ビルド設定: `pyproject.toml`、固定依存: `requirements.lock`
- HTTP クライアント: `httpx`
- HTML 解析: `beautifulsoup4`
- 環境変数の読み込みと検証: `pydantic-settings`
- テスト: `pytest`、`pytest-asyncio`
- 静的解析: `ruff`、`mypy`（strict モード）

## 主要ファイル

- `app/cli.py`: CLI のエントリーポイント。設定を読み込み、非同期の参加判定を実行する。
- `app/config.py`: 環境変数と `.env` を読み込む `Settings`。必須の Webhook URL や HTTP 設定を検証する。
- `app/domain.py`: コンテストクラス・種別の列挙型と、コンテスト名からクラスを判定するロジック。
- `app/scraper.py`: AtCoder のコンテスト履歴 HTML を取得・解析する。リクエスト間隔、リトライ、404、解析失敗もここで扱う。
- `app/checker.py`: 対象クラスの解析、直近 7 日間の絞り込み、Webhook の送信順序を担う。
- `tests/`: 上記の判定、HTML 解析、Webhook 制御に対応するテスト。
- `.github/workflows/weekly-check.yml`: 定期実行と手動実行の GitHub Actions ワークフロー。
- `.env.example`: ローカル実行用の設定例。

## 処理の流れ

1. `Settings` が環境変数または `.env` から設定を読み込む。
2. `AtCoderClient` が algorithm と heuristic の両方のユーザー履歴を取得する。
3. コンテスト名を `abc`、`arc`、`agc`、`ahc`、`other` のいずれかに分類する。
4. 判定時刻を UTC に変換し、`判定時刻 - 7日 <= 開始時刻 < 判定時刻` を満たす対象クラスの参加を探す。
5. 参加があれば Webhook を送信せず正常終了する。
6. 参加がなければ警告用 Webhook を送り、`WEBHOOK_DELAY_SECONDS` 待機してから罰実行用 Webhook を送る。

## 開発環境

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
cp .env.example .env
```

ローカル実行:

```bash
atcoder-participations
```

実際の AtCoder へアクセスする場合は、`.env` の `ATCODER_USER_AGENT` を管理者の連絡先を含む値に変更してください。Webhook URL やキーなどの秘密情報はコミットしないでください。

## 品質チェック

変更後は、影響範囲に応じて次を実行してください。原則として完了前に 3 つすべてを通します。

```bash
ruff check .
mypy app
pytest
```

Ruff の行長は 100、対象 Python バージョンは 3.12 です。型チェックは strict モードなので、公開・内部を問わず型を明示し、安易に `Any` を導入しないでください。

## 実装時の注意

- 時刻は内部で UTC にそろえ、タイムゾーンなしの `datetime` を新たに持ち込まないでください。
- AtCoder の HTML 構造は外部仕様です。パーサーを変更する場合は、正常系だけでなく欠損値、未レート、負のレート変動、404、想定外の HTML も考慮してください。
- AtCoder へのアクセス間隔と指数バックオフを維持してください。並列化によってリクエスト間隔の制御を迂回しないでください。
- コンテスト名は NFKC 正規化してから分類します。スポンサー名付き、全角括弧、ARC の `++`・`--` など既存の表記揺れを壊さないでください。
- `ScrapedContest` と `ScrapedParticipation` は不変データとして扱います。
- Webhook は必ず警告、待機、罰実行の順です。参加が見つかった場合はどちらも送信しません。
- Webhook の既定ペイロードは `value1` がユーザー名、`value2` が対象クラス、`value3` が UTC の判定時刻です。明示設定された値を優先します。
- テストで実際の AtCoder や IFTTT へ通信しないでください。HTTP や Webhook はモックし、HTML パーサーは最小限の入力例で検証してください。
- 挙動、環境変数、実行手順を変更した場合は、コードだけでなく `README.md`、`.env.example`、GitHub Actions の整合性も確認してください。

## 主な環境変数

- 必須: `WARNING_WEBHOOK_URL`、`PENALTY_WEBHOOK_URL`
- 判定対象: `ATCODER_USERNAME`、`TARGET_CONTEST_CLASSES`
- AtCoder 通信: `ATCODER_BASE_URL`、`ATCODER_USER_AGENT`、`HTTP_TIMEOUT_SECONDS`、`HTTP_MAX_RETRIES`、`HTTP_REQUEST_INTERVAL_SECONDS`
- Webhook: `WEBHOOK_VALUE1`、`WEBHOOK_VALUE2`、`WEBHOOK_VALUE3`、`WEBHOOK_DELAY_SECONDS`

`TARGET_CONTEST_CLASSES` は `abc,arc` のようにカンマ区切りで指定します。利用可能な値は `abc`、`arc`、`agc`、`ahc`、`other` です。
