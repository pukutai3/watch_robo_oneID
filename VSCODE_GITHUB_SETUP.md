# VS Code と GitHub の連携メモ

このワークスペースでは、VS Code 側のおすすめ拡張と Git / GitHub 向け設定を入れてあります。

## 追加した内容

- `.vscode/extensions.json`
  - GitHub Pull Requests
  - GitHub Actions
  - GitLens
  - Python / Pylance
- `.vscode/settings.json`
  - Git の自動 fetch
  - Smart Commit
  - Actions ワークフローのピン留め
- `.vscode/tasks.json`
  - `Run watcher`
  - `Probe Robot ID`

## 最初にやること

1. Git for Windows をインストールする
2. VS Code でこのフォルダを開く
3. 拡張機能の推奨をまとめてインストールする
4. VS Code 右上のアカウントメニューから GitHub にサインインする
5. `Ctrl+Shift+P` で `Git: Clone` または `Git: Initialize Repository` を使う

## このプロジェクトで便利な使い方

- ソース管理タブから commit / push
- GitHub Pull Requests 拡張から PR の確認とレビュー
- GitHub Actions 拡張から `Watch ROBO-ONE garage` の実行結果確認
- `Terminal > Run Task` から watcher 実行

## 補足

- この環境ではまだ `git` と `python` コマンドが入っていなかったので、ローカル実行にはその導入が必要です
- GitHub Actions 側は Python を自動セットアップするので、リポジトリに push すればクラウド実行はできます
