# localSIEM-modules ユーザーマニュアル

この MANUAL は次の言語でもご覧いただけます：\
[de-DE](MANUAL.de-DE.md), [en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md), [fr-FR](MANUAL.fr-FR.md), [he-IL](MANUAL.he-IL.md), [hi-IN](MANUAL.hi-IN.md), [it-IT](MANUAL.it-IT.md), ja-JP, [ko-KR](MANUAL.ko-KR.md), [pt-BR](MANUAL.pt-BR.md), [pt-PT](MANUAL.pt-PT.md), [ru-RU](MANUAL.ru-RU.md), [zh-CN](MANUAL.zh-CN.md)

[インストール](README.ja-JP.md) · [コードリファレンス](CODE.ja-JP.md) · [localSIEM のマニュアル](../../localSIEM/doc/MANUAL.ja-JP.md)

## 目次

1. [モジュールとは](#what)
2. [モジュールのインストールと更新](#installation)
3. [モジュールページ](#modules-page)
4. [Apache モジュールのページ](#apache-page)
5. [Apache モジュールの設定](#settings)
6. [Apache モジュールが SOC に送信するもの](#soc)
7. [Apache と ModSecurity の要件：診断](#doctor)
8. [クライアントのログには一切手を加えない](#client-logs)
9. [Apache モジュールのルール](#rules)
10. [Apache モジュールのヘルス警告](#health)
11. [権限昇格モジュール](#privesc)
12. [権限昇格モジュールの設定](#privesc-settings)
13. [権限昇格モジュールが SOC に送信するもの：ルール](#privesc-rules)
14. [権限昇格モジュールの要件：診断](#privesc-doctor)
15. [権限昇格モジュールのバージョン 1.0.0 から更新したサーバー](#privesc-legacy)
16. [権限昇格モジュールの攻撃対象領域とヘルス警告](#privesc-health)
17. [コマンドライン](#cli)

<a id="what"></a>
## 1. モジュールとは

localSIEM は、**コア**と**モジュール**で構成されています。コアは、イベントを保存して検索し、ルールを実行し、アラートをグループ化して SOC に送信し、自身のヘルスを監視します。各モジュールは、サーバーの1つのサービスを追加します。そのサービスのログを見つけて読み取り、イベントに変換し、何がすでに対処済みかを判断し、独自のルールを提供し、そのサービスの要件を確認します。

このプロジェクトのモジュールは `/opt/localsiem/modules/<name>/` にインストールされます。現在、モジュールは2つあります：**apache2**（«Apache + ModSecurity»、セクション 4〜10）と **privesc**（«権限昇格»、セクション 11〜16）です。localSIEM には独自のモジュールはなく、モジュールページには、このリポジトリからインストールされたモジュールだけが一覧表示されます。

<a id="installation"></a>
## 2. モジュールのインストールと更新

先に localSIEM をインストールしておく必要があります。localSIEM のインストーラーはコアだけをインストールし、モジュールは一切インストールしません。このプロジェクトのモジュールのインストールは、**localSIEM の Web 画面からのみ**行います。このプロジェクトには独自のインストーラーはありません。Web 画面は、リポジトリ `https://github.com/PYMEHackers/localSIEM-modules`（ブランチ `main`）からモジュールをダウンロードします。モジュールには localSIEM 2.2.0 以降が必要です。

**インストール。** 管理者として、モジュール › **インストール可能**（セクション 3）を開き、**リポジトリを確認**を押して、**要件**（モジュールがサーバー上で必要とするものと、それをインストールするコマンド。モジュールをインストールする前に実行します）を確認してから、モジュールの**インストール**を押します。すると localSIEM は、次の処理を行います：

1. リポジトリをダウンロードし、安全に展開します（フォルダーの外には何も置かず、サイズの制限もあります）。
2. モジュールのフォルダー（リポジトリ内の `mod-<name>/`）を、`tests/`（および Python のキャッシュ）を除いて `/opt/localsiem/modules/<name>/` にコピーします。再びインストールされたモジュールは、以前の設定を取り戻します。
3. コレクターを再起動します。コレクターは数秒以内にモジュールを読み込みます。
4. モジュールを一覧から外し、ダイアログ «<module> をインストールしました» を開きます。ダイアログには、サーバーで root として実行するコマンド（`manage.py setup-modules`）と**コピー**ボタンが表示されます。このコマンドは、モジュールの `module.json` の `read_paths` に記載されたフォルダー（apache2 モジュールでは `/var/log/apache2`、privesc モジュールでは `/var/log/audit`）の読み取り権限を、今後のローテーションで作られるファイルも含めて `localsiem` ユーザーに与え、localSIEM を再起動します。モジュールに必要なのはこの読み取り権限だけです。モジュールにはセットアップオプションがなく、サーバーを変更することもありません（セクション 8 と 11）。コマンドを実行するまで、モジュールは «エラー» を表示することがあります。まだログを読み取れないためです。ダイアログは «閉じる» または «インストール済みモジュールを表示» で閉じます。後者はインストール済みを開きます。

**更新。** モジュール › **インストール済み**を開くと、Web 画面がリポジトリを確認し、リポジトリに新しいバージョンがあるモジュールには、**更新**付きの通知が表示されます（セクション 3）。確認すると、localSIEM は新しいバージョンをダウンロードしてインストール済みのものと置き換え（手順 1〜3）、設定を保持し、モジュールの有効／無効の状態をそのままにします。root 用のコマンドが再び表示されるのは、新しいバージョンが別のログ（`read_paths`）を読み取る場合だけです。それ以外の場合、実行するものはありません。localSIEM を更新しても、インストール済みのモジュールとその読み取り権限は保持されます。

**再インストール。** Web 画面では、モジュールの再インストールも、古いバージョンのインストールもできません。モジュールを再インストールするには、**アンインストール**（セクション 3）を押してから、**インストール可能**から再びインストールします。設定は保持されます。

**モジュールをインストールしても、それが監視するソフトウェアがインストールされることはありません。** apache2 モジュールは Apache も ModSecurity もインストールせず、privesc モジュールは auditd も syslog デーモンも snoopy もインストールしません。初回のインストール時に、モジュールが必要とするもの（apache2 では Apache と ModSecurity、privesc では `localsiem` が読み取れるソース。セクション 14）がサーバーにない場合、モジュールは**無効**の状態でインストールされます。ダイアログにはコマンドの代わりに不足しているものが一覧表示され、**再構成**がそれらを検出するまで（セクション 4）、モジュールを有効にすることはできません。更新では、モジュールの有効／無効の状態はそのまま保持されます。

<a id="modules-page"></a>
## 3. モジュールページ

管理者は **管理 › モジュール** を開きます。ここには2つのセクションがあり、それぞれ独自のアドレスを持ちます。既定で開く**インストール済み**（`/admin/dashboard/modules/installed/`。`/admin/dashboard/modules/` からもここに移動します）と、**インストール可能**（`/admin/dashboard/modules/installable/`）です。アナリストは、自分のダッシュボードの**モジュール**（`/user/dashboard/modules/`）で、インストール済みモジュールの一覧だけを、読み取り専用で、セクションなしで確認できます。

**インストール済み**には、インストールされているモジュールごとに1行が全幅で表示されます。名前、ID、バージョン、状態を示すピル、概要、そしてその下に、その状態の理由が表示されます。一覧は10秒ごとに自動で更新されます。モジュールが1つもインストールされていない場合は、«インストール可能タブからモジュールをインストールしてください。» と表示されます（アナリストには «インストールされているモジュールはありません。モジュールは、管理者が モジュール › インストール可能 でインストールします。»）。

| 状態 | 意味 |
|---|---|
| **有効・動作中** | 有効で、コレクターに読み込まれ、ソースを読み取っています。診断の警告は注記として一覧表示されますが、状態は変わりません。 |
| **有効（警告あり）** | 有効ですが、読み取るログが見つからない、まだ存在しないソースがある、またはコレクターの起動後にモジュールがインストールされた（`localsiem` サービスを再起動してください）状態です。 |
| **エラー** | モジュールが読み込まれない（エラーが表示されます）、診断がエラーを報告している、または読み取れないソースがある（`localsiem` ユーザーの権限）状態です。 |
| **無効** | 無効にされているか、要件を満たさずにインストールされた（apache2 では Apache または ModSecurity がない、privesc では `localsiem` が auditd のログも syslog も読み取れない）状態です。理由に表示されるとおりです。 |
| **変更を適用中…** | 有効または無効にした直後で、コレクターが変更を適用しています。 |
| **不明** | コレクター（`localsiem` サービス）が稼働していないため、何も読み取られていません。 |

モジュールが無効でない場合、行には次の項目も表示されます：**読み取り中のソース**（読み取り中 / 検出数）、**行数（1時間）**、**最終データ**、**イベント（24時間）**、**ブロック（24時間）**、**診断**の件数（«OK n 件 · 警告 n 件 · エラー n 件»）。

管理者には、各行に次の項目も表示されます：

- 各モジュールの**スイッチ**。モジュールを無効にするときは確認が求められます。localSIEM は、再び有効にするまでそのログの読み取りとアラートの送信を停止します。すでに保存されているものは残ります。有効にすると、すぐに読み取りを開始します。モジュールの要件が不足している間は、スイッチはロックされています（«無効：要件が不足しています»）。**再構成**（セクション 4）が要件を検出すると、ロックが解除されます。
- **構成**：モジュールのページ `/admin/dashboard/modules/installed/<name>/` を開きます（セクション 4）。以前のアドレス `/admin/dashboard/modules/<name>/` からもここに移動します。
- **アンインストール**：読み込まれないモジュールにも表示されます（モジュールのページにもあります）。確認すると、localSIEM は `/opt/localsiem/modules/<name>/` を削除し、そのモジュールなしでコレクターを再起動します。モジュールのログの読み取りとアラートの送信は停止します。すでに保存されているイベントは引き続き検索でき、再びインストールする場合に備えて、設定も残ります。root が `localsiem` に与えたそのログへの読み取り権限は、取り消されません。
- **更新**：リポジトリにモジュールの新しいバージョンがある場合に表示されます。インストール済みを開くたびに、Web 画面がリポジトリを確認し（«リポジトリで新しいバージョンを確認しています…»。ブラウザーはその応答を10分間再利用します）、新しいバージョンがあるモジュールの行には、«リポジトリにバージョン X があります（インストール済みは Y）。» と**更新**ボタンが表示されます。確認すると、localSIEM は新しいバージョンをインストールし（セクション 2）、設定を保持し、モジュールの有効／無効の状態をそのままにして、コレクターを再起動します。root 用のコマンドがダイアログに表示されるのは、新しいバージョンが別のログを読み取る場合だけです。新しいバージョンがより新しい localSIEM を必要とする場合、通知には «リポジトリにバージョン X がありますが、localSIEM Z 以降が必要です。インストールするには、localSIEM を更新してください。» と表示され、ボタンはありません。

**インストール可能**（管理者のみ）には、カード «インストール可能なモジュール» があります。**リポジトリを確認**は、リポジトリをダウンロードし、このサーバーにまだインストールされていないモジュールを一覧表示します。各モジュールには、名前、ID、バージョン、概要と、ボタンまたは注記が表示されます：

| ボタンまたは注記 | 意味 |
|---|---|
| **要件** | モジュールがサーバー上で必要とするものと、それをインストールするコマンドを、root として実行する形と sudo を付けて実行する形で表示します（後述） |
| **インストール** | モジュールをインストールします（セクション 2） |
| «localSIEM X 以降が必要» | インストールできません。先に localSIEM を更新してください |
| «リポジトリのモジュールが無効です» | インストールできません |

すでにインストールされているモジュールは、ここには表示されません。それらはインストール済みから更新します。リポジトリのモジュールがすべてインストール済みの場合、カードには «リポジトリのモジュールはすべてインストール済みです。» と表示されます。インストール後、ダイアログ «<module> をインストールしました» には、`localsiem` がモジュールのログを読み取れるようにするために root として実行するコマンド（セクション 2）が、**コピー**ボタン付きで表示されます。コマンドを実行するまで、モジュールは «エラー» を表示することがあります。まだログを読み取れないためです。モジュールが必要とするものがサーバーにない場合は、代わりに不足しているものがダイアログに一覧表示され、それが揃ったら、インストール済みでモジュールを開き（**構成**）、**再構成**を押すよう案内されます。

**要件**を押すと «<module>：要件» が開きます。モジュールがサーバー上で必要とするものと、それをこのサーバーのシステム（«このサーバー：…»）にインストールするコマンドが、モジュールの宣言（その `module.json` の `install_requirements`）に基づいて、**root として**と**sudo を付けて**（同じコマンドの前に `sudo` を付けたもの）の2通りで、それぞれ**コピー**付きで表示されます。モジュールをインストールする前に、これらをサーバーで実行してください。モジュールをインストールしても、そのソフトウェアがインストールされることはなく、localSIEM がこれらのコマンドを実行することもありません。apache2 モジュールの場合、Debian では `apt-get -y update`、`apt-get -y install apache2 libapache2-mod-security2 modsecurity-crs`、`a2enmod security2 unique_id`、`cp --update=none /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf`（ModSecurity の設定がない場合にのみ、DetectionOnly の設定を作成します）、`systemctl restart apache2` です。Alpine では Apache のみです（`apk add apache2` の後、`rc-update` と `rc-service` で起動します）。Alpine には ModSecurity 2 のパッケージがないためで、ModSecurity をソースからビルドして読み込むまで、モジュールは無効のままです。privesc モジュールの場合、Debian では `apt-get -y install auditd rsyslog`、Alpine では `apk add audit` と、起動時に auditd を開始する設定です。読み取り可能なソースが1つあれば十分で、コンテナでは auditd は動作しません。

<a id="apache-page"></a>
## 4. Apache モジュールのページ

`/admin/dashboard/modules/installed/apache2/`（管理者のみ。以前のアドレス `/admin/dashboard/modules/apache2/` からもここに移動します）は、5つの部分で構成されています：

1. **ヘッダー**：名前、ID、バージョン、インストール先のパス（`/opt/localsiem/modules/apache2`）、スイッチ、状態とその理由、セクション 3 の数値。**インストール済みモジュールに戻る**でインストール済みに戻ります。**再検出して診断を実行**は、Apache の設定をすぐに読み直して診断を更新します。**再構成**は、Apache と ModSecurity を再び探します（後述）。**アンインストール**はモジュールをアンインストールし（セクション 3）、インストール済みに戻ります。
2. **設定**：セクション 5 のフォーム。**設定を保存**はすべての値を確認し、誤った値がある場合はどれかを示します（«無効な値：…»）。
3. **ソース**：読み取り中のすべてのログと、その**種類**（`access`、`error`、`audit`）、**パス**、**Vhost**、**行数（1時間）**、**未解析（1時間）**、**最終データ**（例：`2026/10/29@13:59:59.723`）、**状態**（読み取れない場合はエラー、まだ存在しない場合は警告）。その下には、見つかったものの読み取られていないログが、理由とともに表示されます：«パイプ出力のログ（非対応）»、«すべての vhost を書き込む GlobalLog に含まれています»、または «フォーマットにデータがありません。すべての行が同じテキストです（定義されていない LogFormat のニックネーム）»。
4. **診断**：セクション 7 のチェックと、その実行時刻。不足している各要件（ModSecurity、CRS、`SecRuleEngine`、`mod_unique_id`、`localsiem` の読み取り権限）には、それを解決する設定例またはコマンドと、**コピー**ボタンが示されます。ログに関するチェックは、ログと、localSIEM がそこから読み取れるものを説明するだけで、修正方法は示しません。クライアントのログが変更されることはありません（セクション 8）。
5. **ルール**：セクション 9 のルール。各ルールには**有効**、**ルール**（名前、ID、カテゴリ）、**重大度**、**しきい値**、**ウィンドウ（秒）** の項目があり、**ルールを保存**ボタンがあります。

**要件と再構成。** Apache または ModSecurity がない間は、モジュールは無効で、ヘッダーには不足しているものが、それをインストールするコマンドとともに一覧表示されます。**再構成**（モジュールが無効のときも使えます）は、保存された設定でそれらを再び探します。Apache が標準ではない場所にある場合は、先に **Apache の設定ファイル** を設定してください（セクション 5）。両方が見つかると、スイッチのロックを解除し（モジュールを有効にするかどうかは、あなたが決めます）、モジュールのインストール後に作成された Apache のログを `localsiem` が読み取れるようにするために root として実行するコマンドを表示します。有効になっているモジュールで Apache や ModSecurity がなくなっても、モジュールは有効のままです。診断とヘルス警告（セクション 10）がそれを報告します。

**すべての変更は、何も再起動せずに即座に適用されます**。Web 画面が変更を保存してコレクターに伝え、コレクターは設定を読み直し、ソースを再検出し、診断を実行します。コレクターが応答しない場合は、Web 画面がその旨を表示し、変更はコレクターの起動時に適用されます。

<a id="settings"></a>
## 5. Apache モジュールの設定

| 設定 | 既定値 | 内容 |
|---|---|---|
| **以下のソースのみ** | 無効 | Apache の設定からログを検出せず、手動で追加したソースのみを読み取ります。 |
| **手動で追加したソース** | なし | 検出されたログに加えて（上のオプションを使う場合はその代わりに）読み取るログ。最大50個。 |
| **Apache の設定ファイル** | 空 | 空の場合は自動で検出します（Debian では `/etc/apache2/apache2.conf`、Alpine では `/etc/apache2/httpd.conf`。`/etc/httpd/conf/httpd.conf` も認識されます）。絶対パスを指定すると、そのファイルが存在する場合は、代わりにそのファイルを使います。 |
| **検出間隔（秒）** | 3600 | 新しい vhost やログを見つけるために、Apache の設定を読み直す間隔（60〜86400）。 |
| **ModSecurity のブロックしきい値** | 0 | 0：CRS の設定（`crs-setup.conf` の `tx.inbound_anomaly_score_threshold`）から読み取り、見つからない場合は 5。ModSecurity のメッセージ自体にしきい値が示されていない場合に、ブロックしきい値を上回る一致と下回る一致を区別するために使います（0〜1000）。 |
| **新しい PHP ファイルの学習日数** | 3 | モジュールの初回起動後の最初の数日間は、初めて見る PHP ファイルを、ルール `apache-webshell` が新規として報告しません（0〜365）。DocumentRoot 内で過去1日以内に作成または変更されたファイルは、常に新規として扱われます。 |

**手動で追加したソース**には、それぞれ次のフィールドがあります（* は必須）：

| フィールド | 用途 |
|---|---|
| **種類** * | `access.log`、`error.log`、または `ModSecurity の監査ログ` |
| **パス** * | ファイルの絶対パス |
| **Vhost** | 行に vhost が記載されていないログについて、その行の vhost |
| **LogFormat** | アクセスログの場合：ニックネーム（`localsiem_combined`、`combined`、`vhost_combined`、`common`、`combinedio`、または Apache の設定で定義されたもの）、またはフォーマットそのもの。空の場合は、一般的なフォーマットを試します。 |
| **監査ログの種類** | `シリアル（単一ファイル）` または `コンカレント（リクエストごとに1ファイル）` |
| **監査ログの保存フォルダー** | コンカレントの種類の場合：`SecAuditLogStorageDir` のフォルダー |

ファイルは、検出され、かつ手動でも追加されている場合でも、一度だけ読み取られます。localSIEM の稼働中に現れたソースは、5 MB 以下であれば先頭から、それより大きければ末尾から読み取られます。

localSIEM の **管理 › 設定** にある2つの設定も、このモジュールに作用します：**相関ウィンドウ**（5秒：リクエストの3つの記録を待つ時間）と、**ブロックしきい値未満の重大度**（`low`）です。ModSecurity がフラグを立てたリクエストは、ModSecurity がリクエストの終了時に書き込む監査記録も、最大2分間待ちます。これにより、時間のかかるリクエストが2つのイベントに分かれることはありません。

<a id="soc"></a>
## 6. Apache モジュールが SOC に送信するもの

モジュールは、リクエストごとに、同じ `UNIQUE_ID` を持つアクセスログの行、エラーログの行、監査記録を結合します。Apache が既定で書き込むアクセスログ（`combined`、`vhost_combined`、`common`）には `UNIQUE_ID` がありません。その場合、各アクセスログの行は、同じリクエストが同じ秒に繰り返された場合でも、クライアント IP、メソッド、URI、ステータス、時刻（±2秒）によって、それ自身のリクエストの監査記録とエラーログの行に結合され、イベントには «弱い相関» の印が付きます。vhost は `%v` から取得し、フォーマットにそれがない場合は、監査記録の Host ヘッダーとポートから、Apache と同じ方法で選びます。時刻には監査記録のマイクロ秒が使われます。次に、すでに何らかの対処がされたかどうか（«実行されたアクション»）を、まず監査ログ（`Action: Intercepted (phase N)`）、次に error.log（`Access denied with code NNN (phase N)`）を読んで判断します。ModSecurity の痕跡がない 403 はブロックとはみなされず、疑わしいものとして印が付けられます。

| 状況 | SOC に送信されるか |
|---|---|
| フェーズ 1-2 で ModSecurity にブロックされた（アプリケーションは受け取っていない） | **いいえ。** localSIEM に保存されて検索でき（`action:blocked`）、その IP の次のアラートのコンテキストでカウントされます。 |
| フェーズ 3-4 でブロックされた（アプリケーションはすでに実行していた） | はい |
| エンジンが `DetectionOnly` の状態でのルールの一致 | はい |
| ブロックしきい値未満のルールの一致 | はい |
| セクション 9 のルールのシグナル | はい |

ModSecurity の一致によって発生するアラートの重大度（モジュールのファイル `severity.yaml`）：

| 状況 | 重大度 |
|---|---|
| ブロックされなかった一致、応答 3xx、4xx、5xx | 中 |
| ブロックされなかった一致、応答 2xx | 高 |
| フェーズ 3-4 でブロック | 高 |
| 成功の兆候：送信方向のルール（950-955）に一致し、何もブロックされなかった、またはリクエストの後にデータベースエラーが発生した | 重大 |
| ブロックしきい値未満（多くはアプリケーション自体の誤検知） | 低（管理 › 設定 のブロックしきい値未満の重大度） |

各アラートには、固定の名前（例：«Apache/ModSecurity: SQL injection not blocked (CRS 942)»）、localSIEM の検索に貼り付けるクエリで終わる説明（例：`ip:203.0.113.7 category:sqli`）、そして詳細があります：vhost、クライアント IP、メソッド、URI（マスク済み）、応答、ユーザーエージェント、ModSecurity のデータ（エンジン、アクション、フェーズ、異常スコア、しきい値、ルール、一致したデータ）。送信時、アラートには IP のコンテキストも含まれます：過去1時間のリクエスト数とブロックされたリクエスト数、その IP をブロックしたルール、その IP が最初に確認された時刻。

パスワード、Cookie、`Authorization` ヘッダー、トークンは、リクエスト本文の中にあるものも含め、保存される前にマスクされます。リクエスト本文が SOC に送られることはありません。監査ログのレスポンス本文（パート E）と、実行されたルールの全文（パート K）は保持されません。

<a id="doctor"></a>
## 7. Apache と ModSecurity の要件：診断

apache2 モジュールの診断は、Apache の設定を（変更せずに）読み取り、各要件を確認します。診断が実行されるのは、コレクターの起動時、設定を変更するたび、検出のたび、**再検出して診断を実行**を押したとき、そして `manage.py doctor`（セクション 17）を実行したときで、モジュールが有効な間だけです。Apache または ModSecurity がないためにモジュールが無効になっている間は、代わりにモジュールのページにそれらの要件が表示されます（セクション 4）。状態：OK、警告（制限付きで動作する）、エラー（修正が必要）、情報（一部の状況でのみ重要）。

| チェック | 問題ない場合 | 問題がある場合 |
|---|---|---|
| Apache の設定 | `apache2.conf` または `httpd.conf`（または設定したファイル）が見つかり、読み取れる | エラー：ソースを手動で追加してください（セクション 5）。読み取れない部分は警告として一覧表示されます。 |
| ModSecurity | `mod_security2`（ModSecurity 2）が読み込まれている | エラー。Debian：`apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`。Alpine にはパッケージがありません：mod_security2 2.9 をソースからビルドしてください。ModSecurity 3（libmodsecurity）には対応していません。 |
| OWASP CRS | CRS のファイルがインクルードされている（診断にはその数と異常しきい値が表示されます） | エラー：`apt-get install modsecurity-crs`、または ModSecurity の後に `crs-setup.conf` と `rules/*.conf` をインクルードしてください |
| SecRuleEngine | `On`（しきい値を超えるリクエストはフェーズ 2 でブロックされ、localSIEM に保存されます）または `DetectionOnly`（何もブロックされず、すべての一致が SOC に送られます） | `Off` の場合はエラー。一部の vhost を除いて `Off` の場合、設定がない場合（その場合 ModSecurity の既定値は `Off`）、または一部の vhost で `Off` に設定されている場合は警告 |
| mod_unique_id | 読み込まれている：ModSecurity が動作し、リクエストの3つのソースが `UNIQUE_ID` で結合される | ModSecurity が読み込まれている場合はエラー：ModSecurity 2 はこれがないと何も検査しません（Alpine では読み込まれません）。それ以外の場合は警告（弱い相関）。Debian：`a2enmod unique_id`、Alpine：`LoadModule unique_id_module modules/mod_unique_id.so` |
| アクセスログのフォーマット | Apache が既定で書き込むフォーマットと同様に、アクセスログにクライアント IP、時刻、リクエスト行、ステータスがある（OK、«Access logs in the format Apache writes»）：各行は、クライアント IP、メソッド、URI、ステータス、時刻によって、そのリクエストの ModSecurity の記録と結合されます。フォーマットにミリ秒、vhost、`UNIQUE_ID` がある場合（例：すでにそれを書き込んでいるサーバーでの `localsiem_combined`）は、`UNIQUE_ID` で結合されます（OK、«Access log with milliseconds, vhost, duration and UNIQUE_ID»） | アクセスログに4つのうちいずれかがない場合は情報（修正方法なし）：localSIEM はそのまま読み取りますが、その行を ModSecurity の記録と結合できません（それらのリクエストは監査ログで確認できます）。アクセスログが1つも読み取られていない場合も情報（リクエストはエラーログと監査ログで確認できます）。ログのフォーマットはクライアントのものです（セクション 8） |
| mod_remoteip | `RemoteIPHeader` 付きで読み込まれている | 情報（修正方法なし）：Web サイトがプロキシやロードバランサーの背後にある場合、ログにはプロキシの IP が記録され、アラートや IP ごとのルールも同様になります |
| 監査ログ | `SecAuditLog` があり、`SecAuditEngine RelevantOnly`（または `On`）になっている | 無効の場合は警告：localSIEM は error.log だけで判断し、リクエストのカードにはヘッダーもルールの一覧もありません。有効な場合、注記は監査ログを説明するだけです：コンカレントの種類（トランザクションごとに1ファイル。ModSecurity は通常モード 600 でファイルを作成し、`localsiem` が読み取れれば localSIEM はそれらを読み取ります）、ネイティブフォーマット（そのまま読み取ります）、パート E が記録されている（SOC に送られることはありません）、パート H がない（監査ログから実行されたアクションを読み取れません。チェックを警告にする唯一の注記です）。修正方法はありません：監査ログはクライアントが設定するものです（セクション 8） |
| ソースでのマスク | `sanitise` アクションがある | 情報（修正方法なし。«The audit log on disk is not masked»）：ModSecurity が書き込むファイルにはパスワードや Cookie が含まれる可能性があります。localSIEM はそれらを保存前にマスクし、SOC に送られることはありません |
| 権限 | `localsiem` がすべてのソースを読み取れる | エラー。Debian：`usermod -aG adm localsiem`、Alpine：表示される `setfacl` コマンド。まだ存在しないソースは情報のみです。 |
| パイプ出力のログ | — | 警告：`\|/usr/bin/rotatelogs ...` と syslog は読み取れません。ログをファイルにも書き込むか、ソースを手動で追加してください |
| データのないアクセスログ | — | 警告：`CustomLog` が、どの `LogFormat` でも定義されていないフォーマット（または `%` ディレクティブを1つも含まない `LogFormat`）を使っているため、Apache はすべての行に同じテキストを書き込み、クライアント IP も時刻もリクエストも記録されません。localSIEM はそのログを読み取らず、その vhost のリクエストはエラーログと ModSecurity の監査ログで確認します。サーバーのログのフォーマットが変更されることはありません。 |
| エンジンが Off として確認された | — | エラー：監査記録が、エンジンが無効であると報告しています |
| ModSecurity のバージョン | — | 情報：監査ログから読み取ったバージョン |

設定に、フォーマットに `%v` を含む `GlobalLog`（すべての vhost を書き込みます）がある場合、他のアクセスログは読み取られません。その行を繰り返すだけだからです。診断が、ログのフォーマットや監査ログの設定の変更を提案することはありません（セクション 8）。

<a id="client-logs"></a>
## 8. クライアントのログには一切手を加えない

apache2 モジュールは、Apache と ModSecurity のログを**読み取る**だけです。それらに書き込むことも、ローテーション、切り詰め、移動、削除をすることもなく、そのフォーマットや、それらを書き込む Apache や ModSecurity の設定を変更することもありません。サーバーが独自のフォーマットでログを書き込んでいる場合（例：独自の `LogFormat`、または `mod_remoteip` が与えるクライアント IP）、モジュールはそれに合わせます。各アクセスログは、その `CustomLog` が使うフォーマットで読み取ります。診断（セクション 7）は、ログと、localSIEM がそこから読み取れるものと読み取れないものを説明するだけで、変更を提案することはありません。修正方法を示すのは、ログ以外のもの、つまり ModSecurity、CRS、`SecRuleEngine`、`mod_unique_id`、`localsiem` ユーザーの読み取り権限についてだけです。このモジュールのために root として行うことは、その読み取り権限の付与（`manage.py setup-modules`、セクション 2）だけです。

モジュールのバージョン 1.2.0 以前には、セットアップオプション `--configure-apache` がありましたが、バージョン 1.3.0 で削除されました。これを適用したサーバーには、それが書き込んだファイル `/etc/apache2/conf-available/localsiem.conf`（Debian）または `/etc/apache2/conf.d/localsiem.conf`（Alpine）が残っています。このファイルには、`localsiem_combined` フォーマットとその `GlobalLog`（`localsiem_access.log`）、監査ログの設定、機密性の高い値をマスクする `SecAction` が含まれています。このファイルがある間、モジュールはそれらのログを他のログと同じように読み取ります。元に戻すには、そのファイルを削除し（Debian：`a2disconf localsiem`）、Apache をリロードします。Alpine では、このファイルは `mod_unique_id` と `mod_logio` も読み込んでいました。ModSecurity 2 はこれがないと何も検査しないため（セクション 7）、ファイルを削除する前に、Apache の設定の別の場所で `mod_unique_id` を読み込んでください。localSIEM のインストーラーは、`--uninstall` または `--reinstall` でこのファイルを削除し（Alpine では、先に別の場所で `mod_unique_id` を読み込んでください）、ログ（`localsiem_access.log`、`modsec_audit.log`）はそのまま残します。

<a id="rules"></a>
## 9. Apache モジュールのルール

ルールはすべてのイベントに対して評価されます。ルールのシグナルは常に SOC に送られます。モジュールのページでは、各ルールを無効にしたり、重大度、しきい値（1〜100000）、ウィンドウ（1〜86400秒）を変更したりできます。しきい値とウィンドウは、しきい値ルールとシーケンスルールにのみ適用されます。そのイベントは `rule:localsiem:<id>` で検索できます。

| ルール | 種類 | 重大度 | 条件 | しきい値 / ウィンドウ |
|---|---|---|---|---|
| `apache-bruteforce` «ログインページに対するブルートフォース» | しきい値 | 中 | 1つの IP から、1つの vhost のログインページ（`/wp-login.php`、`/xmlrpc.php`、`/administrator/index.php`、`/user/login`、`/login`、`/admin/login`、`/login.php`、`/admin.php`、`/signin`、`/auth/login`、`/phpmyadmin/index.php`）への、ブロックされなかった POST リクエスト | 300秒間に20回 |
| `apache-login-after-bruteforce` «ブルートフォース後のログイン成功» | シーケンス | 高 | ログインページへの少なくとも10回のログイン失敗（200、401、403 で応答された POST）の後に、302 または 303 で応答されたもの（WordPress は、ログイン失敗には 200、成功には 302 で応答します） | 10回、1800秒以内 |
| `apache-enumeration` «列挙（404 応答の集中）» | しきい値 | 中 | 1つの vhost から1つの IP への、ブロックされなかった 404 応答 | 60秒間に30回 |
| `apache-sensitive-file` «機密ファイルの配信» | 一致 | 高 | 公開されるべきでないファイルへの 2xx 応答：`.env`、`.git/`、`.svn/`、`.hg/`、`.htaccess`、`.htpasswd`、ダンプとバックアップ（`.sql`、`.sql.gz`、`.bak`、`.old`、`.orig`、`.swp`、`.save`、`.backup`、`.dump`、`~` で終わる名前）、`phpinfo`、`info.php`、`server-status`、`server-info`、`wp-config.php` と `config.php`/`config.inc` のコピー、`.DS_Store`、SSH の秘密鍵、`composer.json`/`composer.lock`、`.aws/`、`backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «Web シェルの可能性（新しい PHP ファイルへの POST）» | 一致 | 重大 | DocumentRoot 内で過去1日以内に作成または変更された PHP ファイル、または（学習日数の経過後に）過去1時間以内に初めて確認された PHP ファイルへの、2xx で応答された POST | — |
| `apache-db-error-after-attack` «不審なリクエスト後のデータベースエラー» | シーケンス | 重大 | CRS のルールに一致したリクエストと、それに続く、同じ IP からの error.log 内のデータベースエラー（SQL または PDO） | 1回、30秒以内 |

<a id="health"></a>
## 10. Apache モジュールのヘルス警告

localSIEM 自体のヘルス警告に加えて、モジュールは最大で5分に1回、次のことを確認して SOC に送信します：

| 警告 | 重大度 | 対処 |
|---|---|---|
| ModSecurity が読み込まれなくなった | 高 | 以前は読み込まれていましたが、現在は読み込まれていません。リクエストは検査されていません。誰も意図的に行っていないのであれば、何者かが保護を無効にした可能性があります。 |
| ModSecurity エンジンが Off にされた | 高 | `SecRuleEngine` が `Off` に変更されたか、監査ログがエンジンを無効と報告しています。Apache の設定とその最近の変更を確認してください。 |
| 実際のクライアント IP がない（mod_remoteip） | 中 | 過去1時間に、100件以上のリクエストのうち少なくとも 90% が、1つのプライベートアドレスまたはローカルアドレスから来ています。Web サイトはおそらくプロキシの背後にあり、Apache はプロキシの IP を記録しているため、これらのリクエストには IP ごとのルールが機能しません。送信は最大で1日1回です。 |

すでに報告されたものは再起動後も記憶されるため、更新によって再送信されることはありません。これらの警告があるため、有効になっているモジュールは、Apache や ModSecurity がなくなっても、自ら無効になることはありません。

<a id="privesc"></a>
## 11. 権限昇格モジュール

**privesc** モジュール（«権限昇格»）は、サーバー上で人やサービスが実行するものを監視し、root への権限昇格の各段階を報告します：偵察、setuid プログラムの探索、linpeas などの列挙ツール、既知のエクスプロイト、リバースシェル、sudo や su を使わずに取得された root、残されたバックドア、監視を妨害しようとする試み。また、サーバーの攻撃対象領域、つまり setuid プログラム、ケーパビリティ、他者が書き込み可能な機密ファイルも確認します（セクション 16）。

読み取るのは、サーバーにすでにあるものだけです。何かをインストールすることも、監査ルールを読み込むことも、auditd、snoopy、シェルの設定を変更することもありません。最大2つのソースを読み取ります：

| ソース | 把握できるもの | 動作する場所 |
|---|---|---|
| **auditd**（`/var/log/audit/audit.log`） | sudo、su、pkexec、SSH ログイン（PAM）と、サーバーの監査ルールが記録するもの（後述） | 物理サーバーと仮想マシンで、auditd が稼働している間。**コンテナ内では動作しません**（LXC、podman、systemd-nspawn、Docker）：カーネルの監査は名前空間で分離されていないため、auditd はホストでしか動作しません。 |
| **syslog**（`/var/log/auth.log`、`/var/log/secure`、`/var/log/messages`） | sudo、su、pkexec、doas、SSH ログイン、そして **snoopy** がインストールされていれば、実行されたすべてのプログラム | コンテナを含むあらゆる環境。auditd が稼働していない場合、そのログを読み取れない場合、または snoopy がインストールされている場合に読み取られます（設定 **syslog を読み取る**）。ファイルに書き込む syslog デーモンが必要です。systemd のジャーナルだけでは読み取られません。 |

auditd が示す内容は、サーバーが読み込む監査ルールによって異なり、それを決めるのはサーバーの管理者です。モジュールはそれらのルールを、キーにかかわらずそのまま使い、各記録をその種類、システムコール、ファイルによって分類します：

| モジュールが把握するもの | サーバーの監査ルールが記録している場合 |
|---|---|
| 実行されたすべてのプログラム（スクリプト、Web シェル、エクスプロイトからのものも含む）、setuid プログラム、そこから引き継がれた root、取得されたケーパビリティ | `execve` |
| アカウント、sudoers、PAM、preload、SSH、cron、サービス、`/etc/audit` の変更 | それらのファイルの監視（`-w ... -p wa`）、またはそれらを変更するシステムコール |
| 設定された setuid または setgid ビット | `chmod`、`fchmod`、`fchmodat` |
| 読み込まれた、または削除されたカーネルモジュール | `init_module`、`finit_module`、`delete_module` |
| ptrace でアタッチされたプロセス | `ptrace` |
| 人に対して拒否されたファイル | `EACCES` または `EPERM` で失敗した `open`、`openat`、`execve`... |
| 削除された監査ルール、無効にされた監査、停止された auditd、クラッシュしたプログラム | 常に（カーネルと auditd が報告します） |

物理サーバーや仮想マシンでは、auditd はユーザーが回避できないソースです。診断は、サーバーの監査ルールがこれまでに記録したものを示します（セクション 14）。コンテナでは、実行されたすべてのプログラムを把握する唯一の方法は snoopy です。

シェルの組み込みコマンド（`pwd`、`cd`、`unset HISTFILE`、`history -c`）はプログラムを実行しないため、`bash -c '...'` のようなコマンドラインの中で使われた場合を除き、どのソースからも把握できません。`whoami` を1回実行しただけでアラートになることはありません。モジュールは、各セッションの**異なる**偵察コマンドをウィンドウ内で数え、それらが集中して実行された場合にのみアラートになります（セクション 13）。

モジュールの各イベントの内容と、その検索方法：

| 列 | 内容 | 検索の例 |
|---|---|---|
| `vhost` | 人：ログインユーザー（sudo や su を経由しても変わりません） | `module:privesc vhost:alice` |
| `method` | イベントの種類：`exec`（実行されたプログラム。auditd または snoopy）、`sudo`、`su`、`pkexec`、`doas`、`login`、`pam`、`file`（変更された機密ファイル）、`chmod`（setuid ビット）、`kmod`、`ptrace`、`denied`（拒否されたファイル）、`audit_config`、`auditd`、`crash`、`syscall`（サーバーの監査ルールが記録したその他のシステムコール） | `module:privesc method:sudo` |
| `uri` | コマンドライン（パスワードはマスク済み） | `module:privesc uri:*linpeas*` |
| `path` | 実行されたプログラム、または変更されたファイル | `module:privesc path:/tmp/*` |
| `ip` | セッションの SSH アドレス（判明している場合） | `module:privesc ip:203.0.113.7` |
| `score` | ウィンドウ内での、そのセッションの異なる偵察コマンドの数 | `module:privesc score:>=8` |
| `action` | システム自体が阻止した場合は `blocked`：実行できなかったプログラム、拒否された sudo や su、拒否されたファイル | `module:privesc action:blocked` |
| `source` | `audit` または `syslog` | `module:privesc source:syslog` |

試行に関するルール（sudo の失敗の繰り返し、多数のファイルの拒否）は、ブロックされたイベントも数えます。それ以外のルールは、実際に実行されたものだけを対象にします。

モジュールのページ `/admin/dashboard/modules/installed/privesc/` は、Apache モジュールのページ（セクション 4）と同じ部分で構成されています：ヘッダー（**再検出して診断を実行**、**再構成**、**アンインストール**付き）、設定（セクション 12）、ソース（`audit`、`syslog`。読み取られていないものも、理由とともに表示されます）、診断（セクション 14）、ルール（セクション 13）。

<a id="privesc-settings"></a>
## 12. 権限昇格モジュールの設定

| 設定 | 既定値 | 内容 |
|---|---|---|
| **監査ログ** | 空 | 空の場合：`/etc/audit/auditd.conf` の `log_file`、または `/var/log/audit/audit.log`。 |
| **syslog を読み取る** | 自動 | 自動：auditd が稼働していない場合、そのログを読み取れない場合、または snoopy がインストールされている場合のみ。ほかの選択肢は «常に» と «しない» です。 |
| **syslog ファイル** | 空 | 空の場合：`/var/log/auth.log`、`/var/log/secure`、`/var/log/messages` のうち、最初に存在するもの。 |
| **無視するユーザー** | 空 | カンマ区切り。これらのユーザーのコマンドは保存され、検索もできますが、アラートは発生しません：自動化アカウント（ansible、バックアップ）。ユーザー `localsiem` は常に無視されます。 |
| **管理者グループ** | `sudo,wheel,admin` | カンマ区切り。メンバー（と root）には高い方の偵察しきい値が適用され、アラートなしで自分の sudo 権限を一覧表示できます。 |
| **偵察ウィンドウ（秒）** | 120 | セッションの異なる偵察コマンドを数えるウィンドウ（10〜3600）。 |
| **偵察しきい値** | 8 | ユーザーとサービスアカウントについて、集中実行とみなす、ウィンドウ内の異なる偵察コマンドの数（2〜500）。 |
| **管理者の偵察しきい値** | 20 | root と管理者に適用される同様のしきい値。これらのユーザーは、業務の一環としてこれらのコマンドを実行します（2〜500）。 |
| **自動列挙のしきい値** | 40 | スクリプトでしか実行されないとみなす、ウィンドウ内の異なる偵察コマンドの数（linpeas 型）。全員に適用されます（5〜1000）。 |
| **サービスアカウントの学習日数** | 3 | モジュールの初回起動後の最初の数日間は、各サービスアカウントが実行するプログラム（`sh -c sendmail` を実行する `www-data`）を、アラートを出さずに学習します（0〜365）。 |
| **setuid プログラムのスキャン間隔（時間）** | 24 | setuid と setgid のプログラム、およびファイルケーパビリティを探索する間隔（セクション 16）。0：実行しない（0〜168）。 |
| **スキャンするフォルダー** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | カンマ区切り。各フォルダーは、そのファイルシステムから出ずに走査されます。コンテナのフォルダーと、`/proc`、`/sys` は常にスキップされます。 |
| **検出間隔（秒）** | 300 | 監査ログ、syslog、auditd の状態を探す間隔（60〜86400）。有効なモジュールの中で最も短い間隔が、すべてのモジュールに適用されます。 |

偵察とみなされるもの：`whoami`、`id`、`groups`、`uname`、`hostname`、`w`、`who`、`last`、`ps`、`ss`、`netstat`、`ip`、`ifconfig`、`env`、`pwd`、`history`、`getcap`、`lsmod`、`dmesg`、`mount` とその類似コマンド。`sudo -l`、`crontab -l`、`systemctl list-*`、パッケージの一覧。`which`、`locate`、`command -v`。`docker ps` とその類似コマンド。異なるすべての `find`。`/etc/passwd`、`/etc/shadow`、`/etc/sudoers`、`/etc/*-release`、`/proc/version`、`/root/...`、履歴、SSH 鍵、`.env` ファイルの読み取り。`/root`、`/home`、`/opt`、`/tmp`、cron のフォルダーなどの一覧表示。`grep -r password`。そして `<program> --version`。セッション内の異なるコマンドは、ウィンドウ内でそれぞれ1回として数えられます。

<a id="privesc-rules"></a>
## 13. 権限昇格モジュールが SOC に送信するもの：ルール

モジュールのアラートはすべて、セクション 16 のものを除き、そのルールのいずれかから発生します（ルールは、どのソースがコマンドを確認したかにかかわらず同じように動作します）。Apache と同様に、モジュールのページで各ルールを無効にしたり、重大度、しきい値、ウィンドウを変更したりできます。そのイベントは `rule:localsiem:<id>` で検索できます。**無視するユーザー**に対しては、どのルールも発動しません。«auditd» と記されたルールには、セクション 11 の監査記録が必要です。

| ルール | 種類 | 重大度 | 条件 | しきい値 / ウィンドウ |
|---|---|---|---|---|
| `privesc-recon-burst` «偵察コマンドの集中実行» | 一致 | 中 | セッションが偵察しきい値（セクション 12）に達した | — |
| `privesc-enumeration` «自動列挙（linpeas 型）» | 一致 | 高 | スクリプトの名前が変えられていても、セッションが自動列挙のしきい値に達した | — |
| `privesc-suid-hunt` «setuid プログラムまたはケーパビリティの探索» | 一致 | 高 | `find ... -perm -4000`（または `-u=s`、`/6000`、`-2000`...）、`getcap -r`、`find -writable` | — |
| `privesc-sudo-list` «管理者以外による sudo 権限の一覧表示» | 一致 | 中 | 管理者ではないユーザーまたはサービスアカウントによる `sudo -l` | — |
| `privesc-known-tool` «既知の列挙ツール» | 一致 | 高 | linpeas、LinEnum、lse.sh、linux-exploit-suggester、les.sh、pspy、unix-privesc-check、linuxprivchecker、traitor、BeRoot、GTFONow、PEASS、deepce、CDK、sudo_killer、suid3num、mimipenguin、LaZagne、pwncat、searchsploit | — |
| `privesc-exploit` «既知のエクスプロイト» | 一致 | 重大 | PwnKit、DirtyPipe、Dirty COW、Baron Samedit（`sudoedit -s '\'`）、Looney Tunables（`GLIBC_TUNABLES`）、GameOver(lay)、nf_tables（CVE-2024-1086）、CVE-2023-22809（`EDITOR=... -- /...`）、polkit CVE-2021-3560（`dbus-send ... CreateUser`）、sudo と組み合わせた `LD_PRELOAD`、CVE の名前が付いたスクリプト、`exploit`、`getroot`、`rootme` という名前のプログラム | — |
| `privesc-pwnkit` «PwnKit（引数なしで実行された pkexec）» | 一致 | 重大 | 引数なしで実行された `pkexec`（auditd） | — |
| `privesc-pwnkit-log` «pkexec が PwnKit の試みを報告» | 一致 | 重大 | pkexec が `GCONV_PATH`、«suspicious content»、または «was not found the /etc/shells» を記録する（syslog） | — |
| `privesc-suid-escape` «setuid プログラムから引き継がれた root» | 一致 | 重大 | setuid ではないプログラムが、root の実効 UID とユーザーの実 UID で実行されている：setuid プログラムが悪用された（GTFOBins）。マウントヘルパー、D-Bus、polkit、X は除外されます。 | — |
| `privesc-root-without-door` «sudo、su、pkexec を使わずに取得された root» | 一致 | 重大 | 開始が確認された人のセッションが、sudo、su、pkexec、doas を経由せずに root としてプログラムを実行している（カーネルエクスプロイト）（auditd） | — |
| `privesc-root-shell-interpreter` «インタープリターが起動した root シェル» | 一致 | 高 | 一般ユーザーが実行していた python、perl、ruby、awk、gdb... によって起動されたシェル（その子プロセス、または同じプロセス）が、root として実行されている（auditd） | — |
| `privesc-file-capabilities` «ファイルから root のケーパビリティを得たプログラム» | 一致 | 高 | ユーザーが、ファイルによって `cap_setuid`、`cap_dac_override`、`cap_sys_admin`... が与えられるプログラムを実行した（auditd） | — |
| `privesc-tmp-exec` «誰でも書き込めるフォルダーから実行されたプログラム» | 一致 | 高 | `/tmp`、`/var/tmp`、`/dev/shm`、`/run/user/<uid>` 内のプログラム | — |
| `privesc-compile-tmp` «一時フォルダーでコンパイルされたプログラム» | 一致 | 高 | 一時フォルダー内での、またはそのファイルに対する `gcc`、`cc`、`clang`、`make`... | — |
| `privesc-download-shell` «ダウンロードしたスクリプトをシェルで実行» | 一致 | 高 | `curl ... \| sh`、`bash -c "$(curl ...)"`、`bash <(wget ...)`、または同じパイプライン内でダウンローダーの後にシェルが続くもの | — |
| `privesc-reverse-shell` «リバースシェル» | 一致 | 高 | `/dev/tcp/`、`nc -e`、`ncat --exec`、`socat exec:`、`mkfifo ... \| nc`、python/perl/php/ruby/lua/node のソケット、`openssl s_client ... \| sh`、`awk /inet/tcp` | — |
| `privesc-tty-upgrade` «完全な端末にアップグレードされたシェル» | 一致 | 高 | `pty.spawn`、`script ... /dev/null`、`stty raw -echo`、`socat ... pty`、`expect ... spawn sh` | — |
| `privesc-service-recon` «サービスアカウントによる偵察コマンドの実行» | 一致 | 高 | `www-data`、`mysql` などのサービスアカウントが `whoami`、`id`、`uname`... を実行している（Web シェル） | — |
| `privesc-service-new-program` «サービスアカウントが初めて実行したプログラム» | 一致 | 高 | 学習日数の経過後、サービスアカウントが、これまで実行したことのないシェル、インタープリター、ツールを実行した（`sh -c sendmail` だけを実行していたところでの `sh -c id`） | — |
| `privesc-container-escape` «root としてホストに到達するために使われたコンテナ» | 一致 | 高 | root ではない人が `docker run -v /:/...`、`--privileged`、`--pid=host`、`nsenter -t 1`、`lxc config set ... security.privileged true`、`lxc config device add ... source=/`、`debugfs /dev/...` を実行した | — |
| `privesc-auth-failures` «sudo または su の失敗の繰り返し» | しきい値 | 中 | 1人のユーザーによる sudo、su、pkexec、doas の失敗 | 600秒間に3回 |
| `privesc-sensitive-file` «アカウント、sudo、PAM、preload のファイルの変更» | 一致 | 高 | パッケージツールやアカウントツールではないプログラムによる、`/etc/passwd`、`shadow`、`group`、`gshadow`、`sudoers`、`sudoers.d`、`doas.conf`、`doas.d`、`ld.so.preload`、`ld.so.conf`、`ld.so.conf.d`、`pam.d`、`security` の変更（auditd） | — |
| `privesc-persistence-file` «SSH、cron、サービスのファイルの変更» | 一致 | 中 | `/root/.ssh`、`sshd_config`、`sshd_config.d`、cron のファイル、`/etc/systemd/system`、`/etc/init.d`、`rc.local`、`/etc/local.d` の変更（auditd） | — |
| `privesc-monitoring-changed` «auditd の設定の変更» | 一致 | 中 | パッケージツールではないプログラムによる `/etc/audit` の変更（auditd） | — |
| `privesc-suid-set` «ファイルへの setuid または setgid ビットの設定» | 一致 | 高 | パッケージマネージャー以外による、ファイル（フォルダーではない）に対する `chmod u+s`/`g+s`（auditd） | — |
| `privesc-setcap` «ファイルケーパビリティの設定» | 一致 | 高 | `setcap ... cap_...` | — |
| `privesc-kernel-module` «セッションから読み込まれたカーネルモジュール» | 一致 | 高 | 人のセッションから読み込まれた、または削除されたモジュール（auditd） | — |
| `privesc-ptrace` «ptrace でアタッチされたプロセス» | 一致 | 中 | `PTRACE_ATTACH` または `PTRACE_SEIZE`（auditd） | — |
| `privesc-denied-burst` «多数のファイルの拒否（列挙）» | しきい値 | 中 | 1人のユーザーに対するファイルの拒否（`EACCES`、`EPERM`）（auditd） | 60秒間に30回 |
| `privesc-sensitive-denied` «パスワードハッシュまたは root のファイルを読み取る試み» | 一致 | 中 | ユーザーに対して拒否された `/etc/shadow`、`/etc/gshadow`、`/etc/sudoers`、`/etc/sudoers.d/`、`/root`（auditd） | — |
| `privesc-history-tampering` «シェル履歴の消去または無効化» | 一致 | 中 | `ln -s /dev/null ~/.bash_history`、`rm .bash_history`...。`unset HISTFILE`、`HISTFILE=/dev/null`、`HISTSIZE=0`、`history -c`、`set +o history` は、組み込みコマンドはプログラムを実行しないため、コマンドライン（`bash -c`）の中で使われた場合のみ | — |
| `privesc-audit-stop-command` «auditd を無効にするコマンド» | 一致 | 重大 | `auditctl -e 0`、`auditctl -D`、`auditctl -a never`、`systemctl stop/disable/mask auditd`、`service auditd stop`、`pkill auditd`、`/var/log/audit` または `/etc/audit` の消去 | — |
| `privesc-audit-disabled` «監査の無効化» | 一致 | 重大 | カーネルが `audit_enabled=0` を報告する（auditd） | — |
| `privesc-auditd-stopped` «プロセスによる auditd の停止» | 一致 | 高 | init 以外のプロセスの要求によって auditd が停止した（サーバーのシャットダウンは報告されません） | — |
| `privesc-crash` «setuid プログラムまたは一時フォルダーのプログラムのクラッシュ» | 一致 | 中 | setuid プログラム、または一時フォルダー内のプログラムがクラッシュした（auditd `ANOM_ABEND`）：多くの場合、失敗したエクスプロイトです | — |

各アラートには、固定の名前、localSIEM の検索に貼り付けるクエリで終わる説明、そして詳細があります：ユーザー、アカウントの種類（`root`、`admin`、`user`、`service`）、実ユーザーと実効ユーザー、コマンド、プログラム、フォルダー、端末、セッション、ソース（`auditd`、`snoopy`、`syslog`）、クライアント IP、そして該当する場合は、親プログラム、インタープリター、変更されたファイルとそのグループ、数えられた偵察コマンド、ケーパビリティ、設定されたモード、ptrace の要求、拒否されたファイルのエラー。送信時、アラートにはセッションのコンテキストも含まれます：開始が確認されたかどうか、sudo や su を経由したかどうか、SSH アドレス、そして**直近20個のコマンド**です。これにより、アナリストは検索しなくても、アラートに至った経緯を読み取れます。

同じコマンドが複数のソース（auditd と snoopy）で確認されることがあります。アラートはモジュール、ユーザー、IP、カテゴリ、重大度ごとにグループ化されるため、それでも1件のアラートになります。コマンドライン内のパスワード（`mysql -p...`、`sshpass -p`、`curl -u user:pass`、`PASSWORD=...`、パスワード付きの URL）は、監査記録の16進数表記の中にあるものも含め、保存される前にマスクされます。

<a id="privesc-doctor"></a>
## 14. 権限昇格モジュールの要件：診断

**要件。** モジュールには、`localsiem` ユーザーが読み取れるソース（ファイルが存在し、`localsiem` がそれを開ける）が1つ必要です：**auditd** のログ（auditd が稼働していること。コンテナの外）、または sudo、su、pkexec、doas を記録する **syslog** のファイル（`/var/log/auth.log`、`/var/log/secure`、`/var/log/messages`、または設定 **syslog ファイル**。ただし **syslog を読み取る** が «しない» の場合を除く）です。**snoopy** がインストールされていれば、このファイルには実行されたすべてのプログラムも書き込まれます。いずれか1つあれば十分です。ソースは存在するものの `localsiem` が読み取れない場合は、要件にその旨が、読み取り権限を与えるコマンド（監査ログの場合はモジュールページのコマンド `manage.py setup-modules`、syslog の場合は `setfacl -m g:localsiem:r <file>`）とともに示されます。どれもない場合は、何をインストールすべきかが示されます：auditd（Debian：`apt-get install auditd`、Alpine：`apk add audit && rc-update add auditd && rc-service auditd start`）、syslog デーモン（Debian：`apt-get install rsyslog`、Alpine：`apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`）、または snoopy です。それまでモジュールは無効のままで、**再構成**で再確認します。モジュールが自ら何かをインストールすることはありません。初回のインストールでは、通常ログは root のものです：Web 画面に表示されるコマンドを実行してから、**再構成**を押してください。

診断は、Apache の診断（セクション 7）と同じように実行されます。サーバーにあるものでモジュールが把握できることと把握できないことを説明するだけで、修正方法として示すのは、インストールするパッケージと `localsiem` の読み取り権限だけです。監査ルール、`auditd.conf`（後述の `log_group` を除く）、`snoopy.ini`、シェル、その他の設定の変更を提案することはありません：

| チェック | 問題ない場合 | 問題がある場合 |
|---|---|---|
| auditd | auditd が稼働している | インストールされていない場合は警告（Debian：`apt-get install auditd`、Alpine：`apk add audit && rc-update add auditd && rc-service auditd start`）。インストールされているが停止している場合は警告（修正方法なし。稼働させるかどうかは管理者が決めます）。コンテナ内では情報：auditd はコンテナ内では動作しません。 |
| 監査ログ | `localsiem` が読み取れる | エラー（モジュールページのコマンド付き）。auditd が稼働しているが、そのログがモジュールの探す場所にない場合は警告（設定 **監査ログ**） |
| 監査ログのグループ | 監査ログがグループ `root` に属していない | 属している場合は警告（`auditd.conf` の `log_group = root`）：auditd がローテーション時に作成するログはすべてモード 600 になり、root しか読み取れず、localSIEM は読み取りを停止します。修正方法は、`/etc/audit/auditd.conf` に `log_group = adm` の行を追加することです（その後 auditd を再起動します）。新しいログはモード 640 で作成されます。 |
| 監査ルールの記録 | 実行されたプログラム（`EXECVE`）が読み取られている | auditd が記録を書き込んでいるのに、実行されたプログラムの記録が1つもない場合は警告：サーバーの監査ルールが `execve` を記録していないため、スクリプト、Web シェル、エクスプロイトのコマンドは auditd では把握できません。ルールがこれまでに記録したほかのもの（機密ファイルの変更、setuid ビット、カーネルモジュール、ptrace、拒否されたファイル）と、まだ記録していないものは情報として示されます |
| syslog | syslog ファイルが読み取られている | 読み取れない場合はエラー（`setfacl -m g:localsiem:r <file>`）。使用可能な監査ログも syslog ファイルもない場合は警告（Debian：`apt-get install rsyslog`、Alpine：`apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`） |
| snoopy | インストールされており、その行が読み取られている | auditd がない場合は警告：スクリプトや Web シェルのコマンドは把握できません（Debian：`apt-get install snoopy`。Alpine にはパッケージがなく、ソースからビルドします）。インストールされているが syslog が読み取られていない場合は警告。行に実効 UID がない場合（`snoopy.ini` の `message_format`）は情報：setuid プログラムから引き継がれた root は、snoopy では把握できません |
| モジュールが把握できるもの | — | 情報：auditd（とそのルールが記録するもの）、snoopy（実行されたすべてのプログラム）、または警告として、sudo、su、pkexec、doas のみ（snoopy なしの syslog：ほとんどのルールが発動できません）。何も読み取れない場合はエラー。シェルの組み込みコマンドは決して把握できないことも示します |
| バージョン 1.0.0 のファイル | — | `--configure-privesc` が残したファイルが見つかった場合は情報（修正方法なし。セクション 15） |
| setuid プログラムとケーパビリティ | — | 情報：最後のスキャン（セクション 16）。root シェルを与える setuid プログラム（GTFOBins）と、ケーパビリティが事実上 root となるプログラムがある場合は、それらを示す警告（修正方法なし） |
| 機密ファイル | root 以外が書き込めるものがない | 該当するファイルごとにエラー（修正方法なし）（`/etc/passwd`、`sudoers`、cron、`/etc/profile.d`、root の `PATH` のフォルダー、`docker.sock`...） |
| 特権グループ | — | `docker`、`lxd`、`incus-admin`、`disk`、`libvirt` のメンバーを示す警告（修正方法なし）：これらのメンバーは事実上 root です |

<a id="privesc-legacy"></a>
## 15. 権限昇格モジュールのバージョン 1.0.0 から更新したサーバー

モジュールのバージョン 1.0.0 には、セットアップオプション `--configure-privesc` と bash フックがありました。モジュールが `/opt/localsiem` の外で何かをインストールしたり変更したりすることはないため、バージョン 1.1.0 で両方とも削除されました。これを適用したサーバーには、それが書き込んだものが残っていますが、localSIEM はそれを使うことも削除することもありません：

- `/etc/audit/rules.d/90-localsiem-privesc.rules`：その監査ルール（キー `lsiem_*`）。これらが読み込まれている間、モジュールはその記録を、サーバーのほかのルールの記録と同じように読み取ります。
- `/etc/localsiem-privesc/`（フック）、`/etc/profile.d/localsiem-privesc.sh`、および `/etc/bash.bashrc`（Debian）または `/etc/bash/bashrc`（Alpine）内の «localSIEM privesc: command hook» の次の行：これらがある間、すべての対話型 bash は、誰も読まない `/var/log/localsiem-privesc/` にコマンドを書き込み続けます。
- `/var/log/localsiem-privesc/`：各ユーザーのコマンドファイル。
- `/etc/audit/auditd.conf` の `log_group = adm`、`/root/.ssh`（空で作成されたもの）、`/etc/snoopy.ini` の `message_format`：これらは残しておいて構いません。`log_group = adm` により、ローテーションされた監査ログは読み取り可能なまま保たれ（セクション 14）、モジュールは snoopy のそのフォーマットも、既定のフォーマットと同様に読み取ります。

診断は、確認できるものを一覧表示します（チェック «Files of version 1.0.0 of the module»）。これらを削除するには、root として次のことを行います：ルールファイルを削除してルールを読み込み直し（`augenrules --load`）、`/etc/profile.d/localsiem-privesc.sh`、`/etc/localsiem-privesc/`、bashrc の該当行を削除し、そこに保存されているコマンドを残しておく必要がなければ、`/var/log/localsiem-privesc/` を削除します。

<a id="privesc-health"></a>
## 16. 権限昇格モジュールの攻撃対象領域とヘルス警告

ルールに加えて、モジュールはサーバー自体を確認し、次のものを SOC に送信します：

| 警告 | 重大度 | 条件 |
|---|---|---|
| 新しい setuid または setgid プログラム | 高 | 前回のスキャンになかった setuid または setgid プログラムがスキャンで見つかった（最初のスキャンは基準にすぎません）。root になった攻撃者は、setuid シェルを残していくことがよくあります。パッケージの更新で追加されることもあります。 |
| 書き込み可能なフォルダー内の新しい setuid プログラム | 重大 | 同上。`/tmp`、`/var/tmp`、`/dev/shm`、`/home`、`/srv`、`/var/www` 内のもの |
| GTFOBins の新しい setuid プログラム | 重大 | 同上。setuid のときに root シェルを与えるプログラム（`bash`、`find`、`python`、`vim`、`less`、`cp`...）の場合 |
| 新しいケーパビリティ | 高 | プログラムが、事実上 root となるケーパビリティ（`cap_setuid`、`cap_dac_override`、`cap_sys_admin`...）を得た |
| root 以外が書き込める機密ファイル | 重大 | 1時間ごとに確認：`/etc/passwd`、`/etc/shadow`（誰でも読み取れる場合も）、`sudoers`、cron、`/etc/profile.d`、PAM、サービス、`ld.so.preload`、root の `PATH` のフォルダー、`docker.sock`...。ファイルと問題ごとに1回報告されます。 |
| auditd の停止（localSIEM のヘルス） | 高 | auditd が稼働していたが、稼働しなくなった（コンテナの外） |

スキャンはバックグラウンドで、最大で **setuid プログラムのスキャン間隔（時間）** ごとに1回（最初のスキャンはコレクターの起動から5分後）、**スキャンするフォルダー** を対象に、`localsiem` ユーザーとして実行され（読み取れないものはスキップされます）、300万ファイルまたは15分で停止します。その結果は、見つかった GTFOBins とケーパビリティとともに、診断に表示されます。これらの警告の重大度は、モジュールの `severity.yaml` にあります。すでに報告されたものは、再起動後も記憶されます。

<a id="cli"></a>
## 17. コマンドライン

root として、`/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <command>`：

| コマンド | 用途 |
|---|---|
| `modules` | インストール済みのモジュール：ID、バージョン、有効・無効・未読み込みの別、フォルダー、そして不足している要件があればその要件。読み込めなかったモジュールとそのエラー |
| `doctor` | 有効なモジュールごとに：各チェック（`✓`、`!`、`✗`、`·`）とそれを解決する設定例、そして見つかったソース。要件が不足しているため無効になっているモジュールについては、その要件。`--json` は同じ内容を JSON で出力します。 |
| `read-paths` | モジュールが読み取るフォルダー。localSIEM が root として、これらへの読み取り権限を与えます |
| `setup-modules [--no-restart]` | root として：Web 画面に表示されるコマンド。モジュールのフォルダー（`read_paths`）への読み取り権限の付与と、localSIEM の再起動（`--no-restart`：再起動なし）。モジュールにはセットアップオプションはありません |

実際の権限を確認するには、`localsiem` ユーザーとして診断を実行します：

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
