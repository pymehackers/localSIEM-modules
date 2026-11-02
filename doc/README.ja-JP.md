# localSIEM-modules

この README は次の言語でもご覧いただけます：\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), ja-JP, [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## 概要

[localSIEM](https://github.com/PYMEHackers/localSIEM) のモジュールです。localSIEM は、保護対象と同じサーバー上で動作する軽量な SIEM です。各モジュールはサーバーのサービスを 1 つずつ扱います：ログの場所、その読み方、適用するルールです。現在、モジュールは 2 つあります：

- **apache2**（Apache + ModSecurity）：各リクエストのアクセスログ、エラーログ、ModSecurity の監査ログを結び付けます。ブルートフォース、列挙、機密ファイル、Web シェル、データベースエラーのルールがあります。
- **privesc**（権限昇格）：サーバー上で実行されるもの（auditd、sudo、su、pkexec、doas、snoopy）を監視し、root への昇格の各段階を警告します。

モジュールはサーバーに何もインストールしません。サーバーにすでにあるもので動作します。

## スクリーンショット

![localSIEM の apache2 モジュール](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## インストール

モジュールは localSIEM の Web 画面からインストールします。まず localSIEM を `root` としてインストールしてください：

**Debian 13**：

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**：

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`：Web 画面（`https://<server>:10443`）を開くことを許可する IP。

次に Web 画面で **モジュール › インストール可能** を開き、**リポジトリを確認** を押し、**要件** を確認してから、モジュールの **インストール** を押してください。

## ドキュメントを読む

詳しくは次をご覧ください：

- [doc/MANUAL.ja-JP.md](MANUAL.ja-JP.md)：各モジュールのインストール、設定、使い方を説明します。
- [doc/CODE.ja-JP.md](CODE.ja-JP.md)：モジュールの仕組みと新しいモジュールの書き方を説明します（開発者と AI モデル向け）。
