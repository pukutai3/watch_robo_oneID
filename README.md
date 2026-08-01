# ROBO-ONE robot garage watcher

`https://www.robo-one.com/rankings/view/{Robot ID}` を定期確認して、新しいロボットガレージが作られたら通知する最小構成です。

## 仕組み

- `state.json` に最後に見つけた `last_seen_id` を保存します
- 検索一覧の最終ページから現在の最大 Robot ID を取得します
- `last_seen_id + 1` から最大 ID までを確認し、ID の欠番を飛ばします
- `Robot ID` とロボット情報に実値が入っているページだけを「存在する」と判定します
- 新規ページは1件ずつ通知し、通知成功ごとに ID を `state.json` に保存します

この実装は「検索一覧が Robot ID の昇順でページ分割される」という現在のサイト構造を前提にしています。構造を解析できなくなった場合は、未通知のまま成功扱いにせずエラー終了します。

## ローカル実行

```bash
python watch_robo_one.py
```

特定 ID の判定を試すとき:

```bash
python watch_robo_one.py --probe 1930
```

`--probe` は存在するページなら終了コード `0`、未作成ページなら `1` を返します。

## 通知方法

優先順位は次の通りです。

1. `DISCORD_WEBHOOK_URL`
2. `NOTIFY_WEBHOOK_URL`
3. 未設定なら標準出力

GitHub Actions では `REQUIRE_NOTIFICATION=true` を設定しているため、両方の Webhook が未設定ならエラー終了します。ローカル実行では `.env.local` で明示的に有効化できます。

Discord 以外の Webhook を使う場合、`NOTIFY_WEBHOOK_URL` には次の JSON を POST します。

```json
{
  "robot_id": 1930,
  "name": "sample",
  "team_name": "sample team",
  "country": "日本",
  "comment": "sample comment",
  "url": "https://www.robo-one.com/rankings/view/1930"
}
```

## GitHub Actions で使う手順

1. このフォルダを GitHub の公開リポジトリに push する
2. リポジトリの `Settings > Secrets and variables > Actions` で必要なシークレットを設定する
3. `Actions` を有効化する
4. `Watch ROBO-ONE garage` ワークフローを実行する

どちらか一方が必要な Secrets:

- `DISCORD_WEBHOOK_URL`
- `NOTIFY_WEBHOOK_URL`

`watch.yml` は10分おきに実行する設定で、`state.json` に更新があれば自動で commit / push します。通知途中で失敗した場合も、通知成功分の状態は保存します。

GitHub Actions の `schedule` は遅延・欠落する可能性があるため、10分間隔の厳密な実行保証はありません。即時性が必要な運用では、常駐プロセスまたは実行保証のある外部スケジューラを使用してください。
