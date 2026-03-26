# ROBO-ONE robot garage watcher

`https://www.robo-one.com/rankings/view/{Robot ID}` を定期確認して、新しいロボットガレージが作られたら通知する最小構成です。

## 仕組み

- `state.json` に最後に見つけた `last_seen_id` を保存します
- 実行時に `last_seen_id + 1` から順番にページを確認します
- `Robot ID` と `Robot name` に実値が入っているページだけを「存在する」と判定します
- 新規ページがあれば通知し、最後に見つけた ID を `state.json` に保存します

この実装は「Robot ID は作成順に連番で増える」という前提です。もし将来ギャップが入るなら、`scan_for_new_pages` の停止条件を変えてください。

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

必要に応じて使う Secrets:

- `DISCORD_WEBHOOK_URL`
- `NOTIFY_WEBHOOK_URL`

必要に応じてワークフロー内で変更する環境変数:

- `ROBO_ONE_LOOKAHEAD`

`watch.yml` は 30 分おきに実行し、`state.json` に更新があれば自動で commit / push します。
