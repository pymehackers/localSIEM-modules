# localSIEM-modules コードリファレンス

この CODE は次の言語でもご覧いただけます：\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), ja-JP, [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## 目次

1. [アーキテクチャと設計上の判断](#architecture)
2. [モジュールマップ](#modules)
3. [主要なシンボル](#symbols)
4. [主な呼び出し経路](#flows)
5. [エントリーポイント](#routes)
6. [影響分析](#impact)
7. [拡張ポイント](#extensions)

[インストール](README.ja-JP.md) · [ユーザーマニュアル](MANUAL.ja-JP.md) · [localSIEM のコードリファレンス](../../localSIEM/doc/CODE.ja-JP.md)

<a id="architecture"></a>
## 1. アーキテクチャと設計上の判断

このプロジェクトには、localSIEM（兄弟プロジェクト `../localSIEM`）のインストール可能なモジュールが収められています。独自のサービスもインストーラーもありません。モジュールは localSIEM の Web 画面の モジュール › インストール可能 からのみインストールされ（更新とアンインストールは モジュール › インストール済み で行います）、Web 画面はこのリポジトリ（ブランチ `main`）をダウンロードして、各モジュールのフォルダー `mod-<name>/` を `/opt/localsiem/modules/<name>/` にコピーします。localSIEM のインストーラーはコアだけをインストールし、モジュールは一切インストールしません。また、localSIEM には独自のモジュールはありません。localSIEM のプロセス（コレクター、Web、`manage.py`）がモジュールを読み込みます。`mod-` という接頭辞は、このリポジトリ内のフォルダー名だけのものです。モジュール自体（その `module.json` の `id`、オプション、設定、インストール先のフォルダー）は、接頭辞のない名前を保ちます。現在、モジュールは2つあります：`apache2`（フォルダー `mod-apache2/`）と `privesc`（フォルダー `mod-privesc/`）。

### モジュールがコアの外にある理由

localSIEM のコア（[backend/core/](../../localSIEM/backend/core/)）は汎用的です。ストレージ、検索、ルールエンジン、グループ化、SOC キュー、ハートビート、ヘルスは、Apache について何も知りません。サービスが意味するもの（ログの場所、ログの区切り方と解析方法、記録を1つのイベントにする方法、何をすでに対処済みとみなすか、そのルールと要件）は、モジュールの中にあります。モジュールを独自のプロジェクトに置くことで、次のことが実現されます：

- モジュールにはバージョンがあり（`version`）、必要とする最低限の localSIEM を宣言し（`core`）、localSIEM の新しいリリースなしに更新、追加、無効化できます。
- コアはモジュールを名前でインポートせず、独自のモジュールも持ちません：レジストリ（[backend/core/registry.py](../../localSIEM/backend/core/registry.py)）は、Web 画面がこのリポジトリのモジュールをインストールする `/opt/localsiem/modules/`（開発用のコピーでは `LOCALSIEM_MODULES_PATH`）だけを走査します。
- 読み込みに失敗したモジュールが、他のモジュールを止めることはありません：そのエラーは Web 画面（状態 «エラー»）と `manage.py modules` に一覧表示されます。
- モジュールがコアを変更することはありません：`backend/core/module.py` と `backend/core/registry.py` が契約のすべてです。

### 契約：module.json、locales、Module のサブクラス

**`module.json`**（`fReadManifest` がチェックします）：

| キー | 既定値 | 意味 | apache2 | privesc |
|---|---|---|---|---|
| `id` | 必須 | `mod-` 接頭辞を除いたモジュールフォルダーの名前（インストール先のフォルダー名）、`[a-z][a-z0-9_]{1,31}`。クラスの `vName` でもあります | `apache2` | `privesc` |
| `version` | `"0"` | モジュールのバージョン。Web 画面と `manage.py modules` に表示されます | `1.3.2` | `1.1.2` |
| `core` | `"0"` | 必要とする最低限の localSIEM のバージョン。インストールされている localSIEM の `cVersion` より高い場合、モジュールは読み込まれません | `2.2.0` | `2.2.0` |
| `entry` | 必須 | `"file:Class"`：`file` は `.py` を除いたもの（`[a-z][a-z0-9_]{0,63}`）、`Class` は `Module` のサブクラス | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | 管理者が決めるまで（`modules.<id>.enabled`）動作するかどうか | `true` | `true` |
| `read_paths` | `[]` | localSIEM が root として、`localsiem` ユーザーに読み取りを許可する絶対パスのフォルダー（インストール後、**再構成**の後、そしてこれらを変更する更新の後に Web 画面が表示するコマンド） | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | モジュールが必要とするソフトウェアを、root としてサーバーにインストールするコマンド。システム（`debian`、`alpine`）ごとに、1行に1コマンドで、シェルの演算子は使いません。Web 画面は先頭に `sudo` を付けた形でも表示するためです（コアの `fCheckInstallRequirements`）。モジュール › インストール可能 › 要件 に表示され、実行されることはありません | Debian：Apache、ModSecurity 2、CRS、`a2enmod`、ModSecurity の推奨設定（設定がない場合）、再起動。Alpine：Apache | Debian：auditd と rsyslog。Alpine：auditd |
| `setup_option` | — | どのモジュールも使用していません：モジュールがサーバーを変更することはないため、コアはこれを無視します（レジストリが破棄します）。古いバージョンの `module.json` ファイルには、まだ残っていることがあります | 未設定 | 未設定（`--configure-privesc` は 1.1.0 で削除されました） |
| `settings` | `[]` | 各設定の説明。Web 画面はこれをもとにフォームを作成します | 6個の設定 | 13個の設定 |

各設定には、`key`（`[a-z][a-z0-9_]{1,31}`）、`type`、通常は `default`、そしてその型の属性があります。`fValidateSettings` / `fCleanValue` / `fCleanRecords` が、管理者が保存する内容をチェックします：

| 型 | 属性 | Web のコントロール | 受け付ける値 |
|---|---|---|---|
| `boolean` | — | チェックボックス | `true` / `false` |
| `integer` | `min`、`max` | 数値フィールド | `min`..`max` の範囲内の整数 |
| `string` | `max_length`（500） | テキストフィールド | 制御文字を含まず、前後の空白を除いた、`max_length` 以内のテキスト |
| `path` | — | 等幅のテキストフィールド | 空、または絶対パス（`/` で始まる）、最大1024文字 |
| `choice` | `choices`（必須）、`required` | リスト（必須でない場合は «—» 付き） | `choices` のいずれか、または空 |
| `records` | `fields`（必須：他の型の設定）、`max_items`（50） | レコードごとに1ブロック、追加と削除付き | 最大 `max_items` 個のレコードのリスト。各フィールドがチェックされ、`required` のフィールドは空にできず、空のフィールドは破棄されます |

**`locales/<language>.json`**（de-DE、en-GB、en-US、es-AR、es-ES、fr-FR、he-IL、hi-IN、it-IT、ja-JP、ko-KR、pt-BR、pt-PT、ru-RU、zh-CN）は、`fReadTexts` が読み取り、Web 画面（`modules.js fModuleText`。en-US、次にキーへとフォールバックします）が表示します：

```json
{
  "name": "Apache + ModSecurity",
  "summary": "...",
  "settings": {
    "<key>": {"label": "...", "help": "..."},
    "<records key>": {"label": "...", "help": "...", "add": "...", "remove": "...", "empty": "...", "fields": {"<field>": "..."}}
  },
  "choices": {"<value>": "..."},
  "install_requirements": {"note": "...", "debian": "...", "alpine": "..."}
}
```

ロケールファイルがない、または壊れている場合は、その言語が失われるだけです。

**`Module` のサブクラス**（[backend/core/module.py](../../localSIEM/backend/core/module.py)）。レジストリはこれを `Class(pSettings, pMasker, pStorage, pManifest)` として作成します。フック：

| フック | 呼び出し元 | 既定 | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | コレクター（ストレージの準備ができた後に1回） | 何もしない | `apache.first_start`（学習日数の開始）を保存 | `privesc.first_start` を保存。`privesc.sessions`、`privesc.surface`、`privesc.health` を読み込む |
| `mEnabled()`、`mModuleSettings()`、`mReload()` | コレクター、Web | `module.json` の既定値の上に `modules.<id>` を重ねたもの | 継承 | 継承。`mReload` は `mSettings` のキャッシュも空にする |
| `mDiscoveryInterval()` | コレクター（有効なモジュールのうち最短、最低60秒） | `discovery_interval_seconds` または 3600 | 継承 | 継承（既定は 300） |
| `mDiscover()` | コレクター（起動時、間隔ごと、再読み込み時、診断の要求時）、`manage.py doctor` | `[]` | Apache の設定と手動のソースから得たソース `{key, path, kind, format, vhost, audit_type, storage_dir}` | `fDiscoverSources`：監査ログと syslog |
| `mCreateFramer(pSource)` | コレクター（ソースごと） | `LineFramer` | ネイティブのシリアル監査ログには `AuditFramer` | 継承（`LineFramer`） |
| `mParse(pSource, pUnit, pReceived)` | コレクター（単位ごと） | 必須 | `access`、`error`、`audit` の記録 | `audit` または `syslog` の記録 |
| `mCreateCorrelator()` | コレクター（起動時） | 必須 | `Correlator`（ウィンドウと弱い相関はコアの設定から） | `Correlator`：監査記録はシリアル番号ごと（EOE または2秒）。syslog の行はすぐに |
| `mBuildEvent(pTransaction)` | コレクター（期限に達したトランザクションごと） | 必須 | `action` と `detections` を持つイベント | ルールが照合するフラグを持つイベント。独自の検出はなし |
| `mRulesPath()` / `mRuleFunctions()` | コレクター（ルールの読み込み時） | `None` / `{}` | 自身のフォルダーの `rules/` / `{"apache2.new_php": mIsNewPhp}` | 自身のフォルダーの `rules/` / 継承した `{}` |
| `mDetectionFromSignal(pEvent, pSignal)` | コレクター（ルールのシグナルごと。任意：`hasattr` で確認） | 汎用的な検出 | リクエストの詳細と `{rule: {id, count}}` を含む検出 | ユーザー、コマンド、プログラム、セッション、親、ファイル...を含む検出 |
| `mEnrich(pDetection)` | コレクター（グループとともに、アラートの作成前） | `{}` | 過去1時間の IP のコンテキスト | セッションのコンテキスト：開始の確認、経由した手段、SSH アドレス、直近20個のコマンド |
| `mDoctor()` | コレクター（状態 `<id>.doctor`）、`manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor`（auditd とそのルールが記録したもの、syslog、snoopy、モジュールが把握できるもの、バージョン 1.0.0 のファイル、攻撃対象領域） |
| `mHealth(pNow)` | コレクター（60秒ごと、有効なモジュールのみ） | `[]` | ModSecurity の読み込み解除または Off、実際のクライアント IP がない（最大で300秒に1回） | セッションを保存。スキャン結果。300秒ごと：auditd の停止、書き込み可能な機密ファイル（1時間ごと）、setuid プログラムのスキャンの開始 |
| `mSkipped()` | コレクターの状態、`manage.py doctor` | `[]` | パイプ出力のログ、`GlobalLog` に含まれるログ、データのないアクセスログ（`format_without_data`） | 読み取られない syslog（auditd が稼働中、`syslog_mode` が never）、存在しない監査ログ |
| `mSetLowDisk(pLowDisk)` | コレクター（ディスクの残量レベル） | 何もしない | 監査記録のヘッダーと本文の保存を停止 | 継承 |
| `mDisplayRecord(pRecord)` | Web（リクエストのカード） | `{}` | 保存された監査記録のヘッダーと本文（`fAuditDisplay`） | 継承 |
| `mRequirements()` | コア（localSIEM 2.2.0 以降）：初回のインストール、コレクターの起動と再読み込み、Web 画面の**再構成**、`manage.py modules` と `doctor` | `[]`（要件なし） | `apache_config` と `modsecurity`（`fRequirementChecks`） | `command_source`：`localsiem` が読み取れるいずれかのソース、つまり監査ログ（auditd が稼働中で、コンテナ内ではない）または syslog（snoopy がインストールされていれば snoopy 付き）。ソースは存在するが読み取れない場合は `audit_log` / `syslog` |

コアには、もう `mSetupSnippet` も `mApplySetup` もありません：モジュールにはセットアップオプションがなく、サーバーを変更することもありません。

記録は、`time`、`received`、`module`（ID。コレクターはこれによってコリレーターを選びます）、`source`、`source_key`、`correlation`、`parse_status`（`ok`、`partial`、`unparsed`）、`fields`、`raw`（マスク済み）、そして任意で `search`（全文検索用にインデックスされるテキスト）を持つ dict です。イベントは、イベントテーブルの列（`storage_sqlite.py` の `lEventColumns`）に加えて、`record_ids`、`rule_hits`、`detections` を持ちます。検出は、`module`、`vhost`、`ip`、`category`、`severity`、`rule`、`type`、`description`、`search`、`details`、`time`、`uid` を持ちます。

### 要件：モジュールが監視対象をインストールすることはない

モジュールをインストールしても、それが監視するソフトウェアがインストールされることはありません：apache2 モジュールは Apache も ModSecurity もインストールせず、privesc モジュールは auditd も syslog デーモンも snoopy もインストールしません（その要件 `command_source` は、`localsiem` ユーザーが読み取れるいずれかのソース、つまりコンテナの外で auditd が稼働している場合の監査ログ、または syslog です。`mod-privesc/doctor.py` の `fRequirementChecks`）。有効にできるようになる前に何が必要かは、モジュール自体が `mRequirements()`（localSIEM 2.2.0 以降）で定義します：診断と同じ形式のチェックのリストで、状態が `error` のものが1つもなければ満たされます。apache2 モジュールは、`apache_config`（Apache の設定が見つかる：`apache2.conf`、`httpd.conf`、または設定 `config_file` のファイル）と `modsecurity`（`mod_security2` が読み込まれている。ModSecurity 3 は数えません）を返し、`fRequirementChecks` はこれらを診断の最初のチェックから取得します。Apache がない場合、両方ともエラーです。そのソフトウェアをインストールするものは、`module.json` の `install_requirements` で宣言されます：Web 画面は、モジュールをインストールする前に、サーバーのシステム向けのものを表示し（モジュール › インストール可能 › 要件）、それを実行することはありません。コアは次のように動作します：

- 初回のインストールで要件が不足しており、管理者がまだ決めていない場合、モジュールを無効の状態（`modules.<id>.enabled = false`）でインストールします。更新で `enabled` が変更されることはありません。
- 要件が不足している間は、モジュールを有効にできません：スイッチはロックされ、Web 画面は要件をその `fix` とともに表示します。
- 有効なモジュールが要件を失っても、自ら無効にすることはありません：その診断とヘルス警告（`mHealth`：«ModSecurity is no longer loaded»）がそれを報告し、無効にするとそれらが黙ってしまうためです。
- コレクターの起動時や再読み込み時、そしてモジュールのページの**再構成**（モジュールが無効のときも）で、要件を再確認します：要件が満たされていれば、スイッチのロックを解除し、管理者がモジュールを有効にします。Web 画面は、インストール後に作成されたログを `localsiem` が読み取れるようにするために root として実行するコマンド（`read_paths`）を表示します。

### 名前空間パッケージとして読み込まれる

`__init__.py` はどこにもありません（Python 3.13 の暗黙の名前空間パッケージ）。`fRegisterPackage` は、モジュールのフォルダーを `__path__` とするパッケージ `localsiem_modules` を作成し、`fLoadClass` は `localsiem_modules.<id>.<file>` をインポートして、クラスが `Module` であり、その `vName` が `id` と等しいことを確認します。モジュールのコードへの影響：

- 自身のファイルは**相対的に**インポートします（`from .parsers import AccessParser`）。
- コアは **`backend.core...`** としてインポートします（`from backend.core.module import Module`）：localSIEM のプロセスは、localSIEM のフォルダーを `sys.path` に追加します。
- 使えるのは、標準ライブラリと localSIEM の依存関係（その仮想環境 `/opt/localsiem/venv/`。例：PyYAML）だけです：localSIEM がモジュールのために何かをインストールすることはありません。

### マニフェストから作成される設定フォーム

モジュールは独自の HTML を持ちません。Web 画面は `module.json` の `settings` と `locales/` のテキストを読み取り、フォームを作成し（`modules.js fBuildSettings`、`fRecordsEditor`）、保存される内容を `fValidateSettings` で検証して、管理者が保存した値だけを `settings.json` の `modules.<id>` の下に保存します。`enabled` もそこにあります。モジュールは `mModuleSettings()` を読み取ります：`module.json` の既定値の上に、保存された値を重ねたものです。そのため、設定を追加しても、Web やコアを変更する必要はありません。

apache2 モジュールが `self.dSettings` からも読み取るコアの設定：`host`、`correlation_window_seconds`（5）、`weak_correlation_seconds`（2）、`below_threshold_severity`（`low`）、`health.single_ip_percent` / `health.single_ip_minimum_requests`（90 / 100）。`mModuleSettings()` は、`modules.apache2` の下に保存されているが `module.json` が宣言していないキーも渡します：`mDiscover` はこの方法で `document_roots`（`{vhost: folder}`。検出された DocumentRoot に優先します）を読み取ります。これは `settings.json` を編集することでしか設定できません。

### «実行されたアクション» の原則

SOC に送られるのは、まだ誰も対処していないものだけです。apache2 モジュールでは、実行されたアクションを最も信頼できるソースから読み取ります：監査ログ（ネイティブフォーマットでは `Action: Intercepted (phase N)`、JSON では `audit_data.action.intercepted/phase`）、次に error.log（`Access denied with code NNN (phase N)`）。ModSecurity の痕跡がない 403 はブロックではありません（`fields.doubtful_block`）。

| 状況 | `action` | 検出（SOC へ） |
|---|---|---|
| フェーズ 1-2 でインターセプトされた（アプリケーションは受け取っていない） | `blocked` | なし：`mAssess` は `None` を返します。後のアラートのコンテキストでカウントされます |
| フェーズ 3-4 でインターセプトされた | `none` | あり、`blocked_late`（高）、またはデータベースエラーがある場合は `success_indicator` |
| エンジンが `DetectionOnly` の状態での一致 | `none` | あり |
| 異常しきい値未満の一致 | `none` | あり、`below_threshold`（低） |
| YAML ルールのシグナル | `none` | あり |

重大度は `severity.yaml` から取得します（`fLoadSeverityTable`。ファイルがない場合や値が無効な場合は、組み込みの既定値が使われます）：`crs_not_blocked_2xx` は高、`crs_not_blocked_other` は中、`blocked_late` は高、`success_indicator` は重大（ブロックされなかった送信方向のルール 950-955、または同じリクエストでのデータベースエラー）、`below_threshold` は低（コアの設定 `below_threshold_severity` が優先されます）。«しきい値を上回る» とは、949xxx のルールが一致したか、ModSecurity が示したスコアがしきい値に達したことを意味します。ルールの重大度から計算したスコアは推定にすぎず、判断には使いません。しきい値は、メッセージ内のもの、なければ `anomaly_threshold`、なければ `crs-setup.conf` のもの、なければ 5 です。

### apache2 モジュールの仕組み

1. **検出**（`discovery.py`）：`ApacheConfig` は、`localsiem` ユーザーとして、`apache2ctl` を使わずに、設定を直接読み取ります（`Include`、`IncludeOptional`、`Define`、Debian の `envvars` の `${VARS}`、読み込まれたモジュールと照合した `<VirtualHost>`、`<IfModule>`）。`fDiscoverSources` は、`CustomLog`/`GlobalLog`/`TransferLog`、`ErrorLog`、`SecAuditLog` を、固定のキー `apache:<kind>:<real path>` を持つソースに変換します。フォーマットに `%v` を含む `GlobalLog` はすべての vhost を対象とします（他のアクセスログはスキップされます）。パイプ出力のログと syslog はスキップされ、フォーマットに `%` ディレクティブを含まないアクセスログもスキップされます（Apache は、どの `LogFormat` でも定義されていないニックネームをそのまま書き込みます：`format_without_data`。ただし、データを含む別の `CustomLog` が同じファイルに書き込む場合を除きます。ログのフォーマットが変更されることはないため、診断は修正方法なしでその旨を示します）。手動のソースが優先され、ファイルは一度だけ読み取られます。
2. **区切りと解析**（`parsers.py`、`logformat.py`、`modsec.py`）：アクセスログの行は、その `LogFormat` から生成された正規表現で解析されます（最後に成功したフォーマットが最初に試されます）。エラーログの行は分類されます（`modsecurity`、`database`、`php`、`crash`、`apache`）。監査記録は、JSON（1行。`matched_rules` の前で切り詰め）、ネイティブのシリアル（`AuditFramer` が `--id-A--` から `--id-Z--` までを結合します）、またはコンカレント（インデックスの行が `SecAuditLogStorageDir` 配下のファイルを指します）として読み取られます。すべてがマスクされ、当てはまらないものは `unparsed` として保持されます。
3. **相関**（`correlate.py`）：同じ `UNIQUE_ID` を持つ記録は1つのトランザクションになり、相関ウィンドウと、追いつき中のソースのウォーターマークを待ちます。`UNIQUE_ID` のないアクセスログの行（Apache が既定で書き込むフォーマット）は、その行またはそのリクエストの記録が期限に達したときに、`mPair` によって、アクセスログの行を持たない ModSecurity の記録と組み合わされます：同じクライアント IP、±2秒以内の時刻（行の時刻は秒単位）、そして両方がわかっている場合は同じメソッド、URI、ステータス、パス。より多くの項目が一致する候補が優先され、次に最も近いもの、次に最も古いものが選ばれ、イベントには弱い相関の印が付きます。`UNIQUE_ID` のない error.log の行は、その IP の最も近いトランザクションにすぐに結合されます。`UNIQUE_ID` と error.log の ModSecurity の行を持つトランザクションは、監査記録が届いている間（`vAuditSeen`）、自身の監査記録も待ちます（`mWaitsForAudit`）。待つのは、最初の記録から最大 `cAuditWaitSeconds`（120秒）です：ModSecurity はリクエストの実行中にルールの行を書き込み、リクエストの終了時に監査記録を書き込むため、そうしないと時間のかかるリクエストが2つのイベントになってしまいます。監査記録が届くと、アクセスログの行にはさらに `cAfterAuditSeconds`（2秒）の猶予があります。
4. **イベント**（`ApacheModule.mBuildEvent`）：フィールドは access、次に audit、次に error から選ばれます。vhost は `%v` から、それがない場合は監査記録の Host ヘッダーとローカルポートから取得します（`mVhostName`）。アクセスログの行の時刻が秒単位の場合は、監査記録の時刻を使います。`fSummarize` はルール、カテゴリ、スコア、しきい値、インターセプトをまとめ、実行されたアクションと `mAssess` が検出を決定します。
5. **ルール、エンリッチメント、診断、ヘルス**：`rules/` の YAML ルールはすべてのイベントに対して実行されます（コアのエンジン）。`mEnrich` は IP のコンテキストを追加します。`fRunDoctor` は何も変更せずに要件を確認し、ログを説明します。`mHealth` は ModSecurity と実際のクライアント IP を監視します。モジュールにはセットアップオプションはありません：localSIEM は root として、`localsiem` に `/var/log/apache2` の読み取り権限を与えるだけです。

### 知っておくべき設計上の判断

- **独自のインストーラーはない**：モジュールのインストール（モジュール › インストール可能）、更新（モジュール › インストール済み の**更新**）、アンインストール（**アンインストール**）は、localSIEM の Web 画面からのみ行います。Web 画面はこのリポジトリをダウンロードし、`backend/core/catalog.py`（安全な展開、一度に1つのインストール、フォルダーのアトミックな入れ替え）でモジュールをインストールします。root が必要なこと（`read_paths` への読み取り権限）は localSIEM が行います：インストール後（および `read_paths` を変更する更新の後）、Web 画面は root として実行するコマンドを表示します。
- **クライアントのログは読み取るだけ**：モジュールは、監視するサービスのログに書き込むことも、ローテーション、切り詰め、移動、削除をすることもなく、そのフォーマットを変更することもありません。apache2 モジュールは、Apache や ModSecurity の設定も変更しません（`setup_option` はありません）。サーバーが独自のフォーマットでログを書き込んでいる場合（独自の `LogFormat`、`mod_remoteip` のクライアント IP）、モジュールはそれに合わせます：`AccessFormat` は、各アクセスログのパーサーをその `LogFormat` から作成し、`fCanPair` / `Correlator.mPair` は `UNIQUE_ID` のない行を結合します。診断は、ログと、localSIEM がそこから読み取れるものと読み取れないものを説明するだけです：チェック `log_format`、`log_format_without_data`、`remoteip`、`audit_log`、`sanitise` には `fix` がなく、修正方法が付くのはログ以外のもの（ModSecurity、CRS、`SecRuleEngine`、`mod_unique_id`、`localsiem` の読み取り権限）だけです。`--configure-apache` はバージョン 1.3.0 で削除されました。`localsiem_combined` は、すでにそれを書き込んでいるサーバーのために `dKnownFormats` に残っており、localSIEM のインストーラーは、古いバージョンが書き込んだ `localsiem.conf` を削除します（`--uninstall`、`--reinstall`）。
- 監査ログの**パート K**（`matched_rules`）と**パート E**（レスポンス本文）は保存されません。ヘッダーと本文は、マスクされた生の記録にのみ残り、リクエストのカードがそれらを再構築します（`fAuditDisplay`）。全文検索のインデックスには、縮小したテキスト（`search`：リクエスト行、ホスト、ユーザーエージェント、各ルールの ID、メッセージ、データ）が入ります。
- **生のテキストは、マスクされた部分から再構築されます**：元の監査記録には、パスワードや Cookie が含まれている可能性があるためです。
- **Web とツールは、ストレージなしでモジュールを作成します**（`WebContext.mModule` と `manage.py` では `pStorage` は `None`）：コンストラクターと、それらが呼び出すフックは、ストレージを使ってはいけません。
- **イベントデータベース内の状態**：`apache.first_start`（学習日数）、`apache.health`（すでに報告したもの。再起動で繰り返さないため）、`apache2.doctor`（コレクターが書き込みます）。最初の2つは、ソースのキー `apache:<kind>:<real path>` と同様に、apache2 と呼ばれる前のモジュールの名前を保っています：`apache` モジュールがあったサーバーは、学習日数、ヘルスの記憶、読み取り位置を保持します（ソースのキーが新しくなると、5 MiB 未満のすべてのログが先頭から読み直されてしまいます）。ヘルスの記憶の時刻は、プロジェクトのネイティブフォーマット（`2026-10-29@13-59-59.723`、UTC）です。古いバージョンが保存した、エポック秒の状態は、読み込み時に変換されます。
- **パスの安全性**：`mIsNewPhp` は `..` を拒否し、DocumentRoot の中に留まります。`fReadConcurrentEntry` は `SecAuditLogStorageDir` の中に留まり、最大 8 MiB まで読み取ります。コリレーターが保持する保留中のトランザクションは、最大 50 000 個です。

### privesc モジュールの仕組み

問題は «誰かが `whoami` を実行したか» ではなく（管理者は毎日実行します）、«このセッションは権限昇格の道をたどっているか、そしてそこに到達したか» です。モジュールは、2つのソースを1つの意味を持つイベント（`vhost` は人、`method` は種類、`uri` はコマンド、`path` はプログラムまたはファイル、`ip` は SSH アドレス、`score` はセッションの異なる偵察コマンドの数）に変換し、それらに対してフラグを計算し、何を SOC に送るかを YAML ルールに決めさせます。

1. **検出**（`discovery.py`）：`fDiscoverSources` は、監査ログ（`fAuditLogPath`：設定、`auditd.conf` の `log_file`、`/var/log/audit/audit.log`。auditd が稼働していて `localsiem` がまだ読み取れない場合も、コアがそれを報告できるように返します）と、`syslog_mode` が指示する場合は syslog（`fSyslogPath`）を返します（`auto`：auditd が稼働していない、そのログが読み取れない、または snoopy がインストールされている）。また、診断に必要なものも収集します：コンテナ（`fContainer`。root なしで読み取れるもの：`/run/systemd/container`、`/run/.containerenv`、`/.dockerenv`、`/proc/self/cgroup`、`systemd-detect-virt`）、auditd のバイナリと PID、snoopy、各ログを読み取れるかどうか（`fReadState`：`readable`、`unreadable`、`missing`）、そしてバージョン 1.0.0 が残したファイル（`fLegacyLeftovers`）。`Accounts` は、`/etc/passwd`、`/etc/group`、`UID_MIN` が変更されるとそれらを読み直し、UID を `root`、`admin`（`admin_groups` のメンバー）、`user`、`service` に分類します。
2. **解析**（`parsers.py`）：`fParseAuditLine` は、`type=... msg=audit(<time>:<serial>): k=v ...`、ユーザー空間の部分 `msg='...'`、`\x1d` の後のエンリッチされた部分を読み取り、`EXECVE` の引数（`aN[i]` に分割されたものも含む）を結合し、16進数の値（`proctitle`、`cmd`、`cwd`、`name`、`exe`、`aN`...）をデコードして、**デコードしてマスクした値から生のテキストを再構築します**（そうしないと、パスワードの16進数表記が残ってしまうためです）。`search` にはデコードされたコマンドが入ります。`fParseSyslogLine` は ISO と従来のタイムスタンプ（busybox の `facility.priority` の有無を問わず）を読み取り、`fParseSyslogMessage` は snoopy（`uid:alice(1000)/root(0)` を含む 2.4 と 2.5 の既定のフォーマット、およびバージョン 1.0.0 が設定したフォーマット）、sudo、su（util-linux と busybox）、pkexec、doas、`pam_unix`、sshd を解釈します。`fMaskCommand` は、コアのマスカーの前に、コマンドライン内のパスワードをマスクします。
3. **相関**（`correlate.py`）：同じシリアル番号を持つ監査記録は1つのトランザクションになり、`EOE` で、1記録のユーザー空間の種類（`USER_*`、`CRED_*`、`DAEMON_*`...）ではすぐに、または記録のない状態が2秒続いた後に、期限に達します。保留中のものは最大 50 000 個です。syslog の行はすぐに期限に達します。
4. **イベント**（`PrivescModule.mBuildEvent`）：`mAuditEvent` は種類によって振り分けます：`EXECVE` → `mAuditExec`（`PATH` の記録または `stat` から得たプログラムの setuid ビット、euid が 0 で実 UID が 0 ではなく、プログラムが setuid でない場合の `suid_escape`、`BPRM_FCAPS` から得たケーパビリティ、`root_without_door`、root 以外のユーザーのインタープリターによって起動されたシェルが root として実行される場合の `parent_interpreter`、プロセスのメモリから得た親）。`USER_*`/`LOGIN` → `mAuditUser`（開始されたセッション、SSH アドレス、経由した手段：sudo、su、pkexec、doas、run0、systemd の `USER_START`/`USER_CMD`。失敗）。`CONFIG_CHANGE`（`audit_disabled`、削除されたルールごとの `audit_rule_removed`）、`DAEMON_*`（送信元が PID 1 でない場合の `auditd_stopped_manually`）、`ANOM_ABEND`（`crash_suspicious`）。それ以外の `SYSCALL` → `mAuditSyscall`。これは、ルールのキーではなく、システムコール（`fSyscallName`：エンリッチされたフォーマットの名前、またはそのアーキテクチャの表の番号）、引数、`PATH` の記録によって分類します：`denied`（人に対して `EACCES`/`EPERM` で失敗した open、exec、truncate）、`kmod`、`ptrace`（`PTRACE_ATTACH`/`PTRACE_SEIZE` の場合は `ptrace_attach`）、`chmod`（setuid または setgid ビットを含むモードで、フォルダーではないもの。`writer_allowed` 付き）、`file`（`lSensitivePaths` のパスの変更。`sensitive_group` と `writer_allowed` 付き。`dKeyHints` を通じたキーは、どのパスも解決できない場合のみ）。`mSyslogEvent` は、snoopy を `exec` として扱い（`stat` から得た `suid_escape`。`filename` がない場合は、コマンドの最初の単語からプログラムを得ます）、sudo、su、pkexec、doas、login、pam も扱います。すべてのコマンドは `mAnalyzeCommand` を通ります：偵察トークン（`fReconToken`）とウィンドウ内のセッションの異なるトークン（`recon_burst`、`recon_massive`、`score`）、シェルで実行されるダウンロード（`cDownloadOnelinerRegex`、または同じ親を持つ、ダウンローダーの後に続くシェル）、`compile_in_tmp`、セッションの直近のコマンド、そしてサービスアカウントについては、プログラム（`fProgramKey`）をその履歴と照合します（コアの `mPathFirstSeen`。`learning_days` の経過後：`new_program`）。`ignored` は無視するユーザーに印を付けます。
5. **ルール、エンリッチメント、診断、ヘルス**：`rules/` の35個の YAML ルールがすべての検出を決定します（`mDetectionFromSignal`）。`mEnrich` はセッションのコンテキストを追加します。`fRunDoctor` は、auditd とそのルールが記録したもの、syslog、snoopy、モジュールが把握できるものとできないもの、バージョン 1.0.0 のファイル、攻撃対象領域を説明します。`mHealth` は、auditd の停止、書き込み可能な機密ファイル、setuid プログラムのスキャン結果（`SurfaceScanner`、スレッド）を報告します。モジュールにはセットアップオプションがなく、サーバー上の何も変更しません。

### privesc モジュールの設計上の判断

- **2つのソース、1つの意味。** auditd はユーザーが回避できませんが、コンテナ内では動作しません（カーネルの監査は名前空間で分離されていません）。snoopy はコンテナ内のすべてのプログラムを把握できますが、syslog が必要です。syslog だけでは、sudo、su、pkexec、doas しか得られません。シェルの組み込みコマンドは、どのソースからも把握できません。ルールはソースではなく列とフラグを照合するため、ルールに手を加えずにソースを追加できます。2回確認された同じコマンドは1件のアラートになります：コアは、検出をモジュール、ユーザー、IP、カテゴリ、重大度ごとにグループ化します。
- **コマンドではなく集中実行。** 偵察は、質問の種類ごとのトークン（`whoami`、`read:/etc/passwd`、`find:-perm:`...）であり、アラートを発生させるのは、ウィンドウ内のセッションの異なるトークンの数だけです。管理者にはより高いしきい値が、スクリプトには3つ目のしきい値があります。しきい値はルールのしきい値ではなく設定です：ルールは `recon_burst` / `recon_massive` を照合するだけです。
- **最も重要なのは成功。** `suid_escape`（setuid ではないプログラムが、euid 0 と 0 ではない実 UID で実行されている）と `root_without_door`（開始が確認され、sudo、su、pkexec、doas を一度も経由していないセッションでの root）は、権限昇格が成功したことを示す2つの重大な兆候で、誤検知はほとんどありません。開始が確認されていないセッション（モジュールより前に開かれたセッション、1日操作がなく忘れられたセッション）に印が付けられることはありません。
- **セッションは再起動後も残る。** `SessionTracker` は、各セッションの開始、SSH アドレス、経由した手段を状態 `privesc.sessions` に保持します（保存は最大で1分に1回）。偵察トークンと直近のコマンドはメモリに残ります。1日アイドル状態のセッションは破棄されます。
- **サーバーにすでにあるものだけ。** モジュールは何もインストールせず、`/opt/localsiem` の外で何も変更しません：監査ルールを読み込まず、`auditd.conf` にも `snoopy.ini` にも手を加えず、フックもインストールしません。バージョン 1.0.0 はそれを行っていました（`--configure-privesc`：キー `lsiem_*` を持つ監査ルール、`log_group = adm`、bash フック、snoopy のフォーマット）。バージョン 1.1.0 でそれを削除しました。そのため、監査記録はその種類、システムコール、パスによって分類され、どのような監査ルールでも機能します（サーバーのルール、STIG のサンプルルール、1.0.0 が残した `lsiem_*` ルール）。キーは検索用に `fields.key` に保持されますが、ヒントにすぎません（`dKeyHints`）。ログにエンリッチされた名前がない場合、システムコールの番号はアーキテクチャごとに読み取られます（`dSyscallTables`：x86_64、i386、そして aarch64、riscv64、loongarch64 の汎用テーブル）。診断は、サーバーのルールが何を記録し、何を記録していないかを説明します。その `fix` は、インストールするパッケージか `localsiem` の読み取り権限だけです。
- **読み取り可能とは、実際に読み取れること。** 要件を満たすのは、存在し、`localsiem` が開けるソース（`fReadState`）であり、プログラムがインストールされていることではありません：初回のインストールでは、通常ログは root のものなので、root 用のコマンド（`manage.py setup-modules`）と**再構成**を行うまで、モジュールは無効のままです。
- **パッケージマネージャーは攻撃者ではない。** アカウントツールやパッケージツール（`sAllowedWriters`）、または既知の祖先がパッケージマネージャーであるプログラムによる、機密ファイルや setuid ビットの変更には `writer_allowed` が設定され、ルールはそれらをスキップします。
- **スキャンがコレクターをブロックすることはない。** `SurfaceScanner` は、独自のスレッドで `scan_paths` を走査します。各フォルダーのファイルシステムから出ず、`/proc`、`/sys`、コンテナのフォルダーをスキップし、最大300万ファイルまたは15分までです。`mHealth` は、結果の準備ができたときにそれを受け取ります。最初のスキャンが基準になり、以降のスキャンで新しいものを報告します。
- **Web とツールは、ストレージなしでモジュールを作成します**：`mDiscover`、`mDoctor`、`mRequirements` はストレージを使わず、`mAnalyzeCommand` は `mPathFirstSeen` が存在する場合にのみそれを呼び出します。
- **イベントデータベース内の状態**：`privesc.first_start`（学習日数）、`privesc.sessions`、`privesc.surface`（スキャンと診断の基準）、`privesc.health`（すでに報告したもの、auditd が稼働していたかどうか）、`privesc.doctor`（コレクターが書き込みます）。サービスアカウントが実行したことのあるプログラムは、vhost が `privesc:<account>` の `seen_paths` の行です。`privesc.health`（ヘルスの記憶）と `privesc.sessions`（各セッションの `last`）の時刻は、プロジェクトのネイティブフォーマット（`2026-10-29@13-59-59.723`、UTC）です。古いバージョンが保存した、エポック秒の状態は、読み込み時に変換されます。

<a id="modules"></a>
## 2. モジュールマップ

| モジュール | パス | 役割 | 依存先 | 利用元 |
|---|---|---|---|---|
| マニフェスト | [mod-apache2/module.json](../mod-apache2/module.json) | ID、バージョン、コアの最低バージョン、エントリー、読み取りパス、設定（セットアップオプションなし） | — | レジストリ、Web、`manage.py` |
| Apache モジュール | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`：フック、実行されたアクション、重大度、検出、ルール関数、エンリッチメント、ヘルス | correlate、discovery、doctor、modsec、parsers。コアの `masking`、`module`、`query`、`timeutil`、`health`。PyYAML | コレクター、Web、`manage.py` |
| 検出 | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig`（設定パーサー）、ソースとスキップされたログ、DocumentRoot | logformat（`dKnownFormats`） | module、doctor |
| 診断 | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | 要件のチェック。ログ（フォーマット、監査ログ、マスク）を、変更を提案せずに説明 | discovery | module |
| アクセスログのフォーマット | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` から正規表現へ、時刻を UTC へ、リクエスト行 | コアの `timeutil` | parsers、discovery |
| パーサー | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access、error、audit（JSON、ネイティブ、コンカレント）、`AuditFramer`、`fAuditDisplay` | logformat、modsec。コアの `masking`、`timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | メッセージ、カテゴリ、CRS の範囲、スコア、インターセプト | — | parsers、module |
| 相関 | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`、それがない場合の組み合わせ（`mPair`）、ウィンドウ、ウォーターマーク | コアの `timeutil` | module（コレクター） |
| 重大度テーブル | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | ModSecurity の検出の重大度 | — | module（`fLoadSeverityTable`） |
| ルール | [mod-apache2/rules/](../mod-apache2/rules/) | 6個の YAML ルール | コアのルールエンジン、`mIsNewPhp` | コレクター（`RulesEngine`）、Web（`fRules`） |
| テキスト | [mod-apache2/locales/](../mod-apache2/locales/) | 名前、概要、設定のラベルとヘルプ、選択肢 | — | Web |
| privesc：マニフェスト | [mod-privesc/module.json](../mod-privesc/module.json) | ID、バージョン、コアの最低バージョン、エントリー、読み取りパス、13個の設定（セットアップオプションなし） | — | レジストリ、Web、`manage.py` |
| privesc：モジュール | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`：フック、2つのソースのイベント、監査記録の分類（機密パス、アーキテクチャごとのシステムコール）、フラグ、ルールの検出、エンリッチメント、ヘルス、スキャン結果 | commands、correlate、discovery、doctor、parsers、surface。コアの `masking`、`module`、`query`、`timeutil`、`health`。PyYAML | コレクター、Web、`manage.py` |
| privesc：検出 | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | ソース、コンテナ、auditd、snoopy、syslog、各ログを読み取れるかどうか、バージョン 1.0.0 が残したファイル、`Accounts`（ユーザー、グループ、アカウントの種類） | — | module、doctor |
| privesc：パーサー | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | 監査記録（16進数、`msg='...'`、エンリッチ）、syslog の行（通常のフォーマットの snoopy、sudo、su、pkexec、doas、pam、sshd）、コマンドラインのマスク | コアの `masking`、`timeutil` | module |
| privesc：相関 | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | シリアル番号ごとの監査記録（EOE、ユーザー空間の記録、2秒）。syslog の行はすぐに | — | module（コレクター） |
| privesc：コマンド | [mod-privesc/commands.py](../mod-privesc/commands.py) | 偵察トークン、サービスアカウントのプログラム、シェル、インタープリター、ダウンローダー、経由する手段、コンパイラー。`SessionTracker` | コアの `timeutil` | module |
| privesc：攻撃対象領域 | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner`（setuid、setgid、ケーパビリティ）、GTFOBins、書き込み可能な機密ファイル、特権グループ | — | module、doctor |
| privesc：診断 | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | auditd、そのログ、そのルールが記録したもの、syslog、snoopy、モジュールが把握できるもの、バージョン 1.0.0 のファイル、攻撃対象領域を説明（修正方法：パッケージと読み取り権限のみ）。要件 `command_source`（読み取り可能ないずれかのソース） | discovery、surface。コアの `timeutil` | module |
| privesc：ルール | [mod-privesc/rules/](../mod-privesc/rules/) | 35個の YAML ルール | コアのルールエンジン | コレクター（`RulesEngine`）、Web（`fRules`） |
| privesc：重大度テーブル | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | モジュールが作成する検出（スキャン、機密ファイル）の重大度 | — | module（`fLoadSeverityTable`） |
| privesc：テキスト | [mod-privesc/locales/](../mod-privesc/locales/) | 名前、概要、設定のラベルとヘルプ、選択肢 | — | Web |
| コア：インターフェース | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`、`LineFramer` | レジストリ | モジュール |
| コア：レジストリ | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | モジュールの検索、チェック、読み込み。設定の既定値と検証 | `config` | コレクター、Web、`manage.py`、`backend/core/catalog.py` |
| コア：Web | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py)、[backend/web/app.py](../../localSIEM/backend/web/app.py)、[frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | モジュールのページ（インストール済み、インストール可能、個々のモジュールのページ）と API | レジストリ、カタログ、ルール | ブラウザー |
| コア：カタログ | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | リポジトリのダウンロードと安全な展開、各モジュールのアクション（`install`、`update`、`incompatible`、`invalid`...）と `newer` を含む一覧、アトミックなインストールまたは更新（`previous`、`access_changed`）、アンインストール、root 用のコマンド：モジュール › インストール可能 と、モジュール › インストール済み の**更新** / **アンインストール**。モジュールをインストールする唯一の方法です | レジストリ | Web |

<a id="symbols"></a>
## 3. 主要なシンボル

| シンボル | ファイル:行 | 内容 |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | apache2 モジュール（`vName = "apache2"`） |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | 組み込みの既定値の上に `severity.yaml` を重ねる |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | 設定の解析、ソース、スキップされたログ、DocumentRoot |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | 異常しきい値：設定、CRS、または 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | ソースの種類に応じて、単位を記録に変換 |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | トランザクションをイベントに変換：フィールド、実行されたアクション、スコア、検出 |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Host ヘッダーまたは ModSecurity のホスト名を、Apache が選んだ vhost（`%v` が記録するもの）に変換 |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | SOC に送られるものの重大度、ルール名、説明、詳細 |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | YAML ルールのシグナルを検出に変換 |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | ルール関数 `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | アラート用の IP のコンテキスト（過去1時間） |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity の読み込み解除または Off。実際のクライアント IP がない |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | リクエストのカード用のヘッダーと本文 |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache と ModSecurity 2：モジュールを有効にできるようになる前に必要なもの |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Apache の設定のパーサー |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | 読み取るディレクティブ（ログ、vhost、モジュール、ModSecurity） |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Host ヘッダー、ローカルアドレス、ポートから、Apache と同じ方法で選んだリクエストの vhost |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | 固定のソースキー。読み取るソースとスキップするソース |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | 要件のチェック `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | アクセスログのフォーマットを `UNIQUE_ID` なしで結合できるかどうか（クライアント IP、時刻、リクエスト行、ステータス） |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | 診断のチェック `apache_config` と `modsecurity`。Apache がない場合は、両方をエラーとし、それらをインストールするコマンドを付ける |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` から正規表現へ。既知のニックネーム |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | access.log の行を記録に変換 |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | error.log の行：ModSecurity、データベース、PHP、クラッシュ |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | 複数行にわたるネイティブの記録。安全なコミット位置 |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | JSON またはネイティブの監査記録。マスク、生のテキストとインデックス用のテキスト |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | 保存された記録のカード。コンカレントのエントリーのファイル |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | ModSecurity のメッセージ1件。ルール、カテゴリ、スコア、しきい値、インターセプト |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd`（[:148](../mod-apache2/correlate.py#L148)）、`mPair`（[:207](../mod-apache2/correlate.py#L207)）、`mDue`（[:248](../mod-apache2/correlate.py#L248)）、`mWaitsForAudit`（[:271](../mod-apache2/correlate.py#L271)）、`mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | privesc モジュール（`vName = "privesc"`） |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | ソースに応じてトランザクションをイベントに変換。`ignored`。空のフィールドは破棄（`fCleanFields` は 0 を保持） |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | セッションの偵察、シェルで実行されたダウンロード、`/tmp` でのコンパイル、最近のコマンド、サービスアカウントの新しいプログラム |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | 種類ごとの監査トランザクション。実行されたプログラム（`suid_escape`、`root_without_door`、`parent_interpreter`、ケーパビリティ）。ログイン、経由した手段、失敗 |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | その他のシステムコールを、名前、引数、パスによって分類：`denied`、`kmod`、`ptrace`、`chmod`、`file`（`sensitive_group`）、または `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | システムコールの名前（エンリッチされた名前、またはアーキテクチャごとの番号）。機密パスのグループ（`lSensitivePaths`） |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy、sudo、su、pkexec、doas、ログイン |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | 機密ファイルの書き込み元、またはその既知の祖先が、アカウントツールまたはパッケージツールであるか |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | ルールのシグナルを検出に変換。アラート用のセッションのコンテキスト |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | セッションの保存、auditd の停止、機密ファイル、スキャンの開始。新しい setuid プログラムとケーパビリティ |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | ソース、スキップするソース、診断用の情報。ログを読み取れるかどうか。バージョン 1.0.0 が残したファイル |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | コンテナの種類（root なし）。稼働中の auditd の PID |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | UID の名前、グループ、`UID_MIN`、アカウントの種類（`mAccountType`） |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | 2つのソースの記録 |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | コマンドラインのパスワード、次にコアのマスカー |
| `Correlator`（privesc） | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | シリアル番号ごとの監査記録。その他はすぐに |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | コマンドの偵察トークン。サービスアカウントのプログラム。入力されたコマンドの単語 |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | セッション（開始、IP、経由した手段、偵察、直近のコマンド）、プロセス、ダウンロード。`mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | スレッドでの setuid、setgid、ケーパビリティのスキャン。他者が書き込み可能な機密ファイル |
| `fRunDoctor` / `fRequirementChecks`（privesc） | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | 診断のチェック（説明。修正方法はパッケージと読み取り権限のみ）。要件 `command_source`：読み取り可能ないずれかのソース |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | モジュールのインターフェース。単位ごとに1行 |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | `module.json` をチェックし、テキストを読み取る |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | インストール済みのモジュール（`/opt/localsiem/modules/*`）。インスタンスとエラー |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | 名前空間パッケージ `localsiem_modules`。エントリーのインポートとチェック |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | 保存された値の下にある既定値。保存される内容の検証 |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`。`POST /api/admin/module-catalog/{name}`（インストールまたは更新。要件を満たさない初回のインストールは無効になります：`fFirstInstallation`）。`DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | インストール済みのコピーの隣にモジュールをインストールまたは更新し、名前の変更で入れ替える（`previous`、`access_changed`）。`installed`、`newer`、アクションを含むリポジトリのモジュール |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | モジュールのアンインストール（名前の変更と削除）。root 用のコマンド（`manage.py setup-modules`） |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | セクション インストール可能（インストールされていないモジュールのみ、**インストール**とそのダイアログ）。インストール済みの行の新しいバージョンの通知。**更新**（確認、同じ `POST`、`access_changed` がある場合またはコレクターが応答しなかった場合のみダイアログ） |

<a id="flows"></a>
## 4. 主な呼び出し経路

**コレクターの起動 → レジストリ → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests`（`/opt/localsiem/modules/*`）→ `fReadManifest`（id = フォルダー、entry、settings、`core` ≤ `cVersion`、`fReadTexts`）→ `fCreateModule` → `fLoadClass`（`fRegisterPackage`、`import localsiem_modules.apache2.module`、`Module` のサブクラス、`vName == id`）→ `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules`（`mRulesPath`、`mRuleFunctions`、上書き `rules.<id>` → `RulesEngine.mLoad`）→ `Collector.mDiscover`（`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`。ソースごとに `FileTailer` と `mCreateFramer`）→ 保留中の記録をコリレーターに戻す → `mPublishDoctor`（`mDoctor` → `fRunDoctor` → 状態 `apache2.doctor`）。

**読み取られた1行 → 検出**

1. `Collector.mReadSources` → `FileTailer.mPoll` → フレーマーの `mFeed`（`LineFramer`、または `mSafeCommit` が未完了の記録の前の位置を保持する `AuditFramer`）→ `ApacheModule.mParse`（`AccessParser.mParse`、`fParseErrorLine`、または `fReadConcurrentEntry` + `fParseAuditRecord` と `mObserveAudit`）→ 記録と位置を1つのトランザクションで保存 → `Correlator.mAdd`。
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent`（`fSummarize`、実行されたアクション、`mAssess`、2xx の `.php` には `mPathFirstSeen`）→ `RulesEngine.mEvaluate`（YAML ルール。`{function: apache2.new_php}` → `mIsNewPhp`）→ `mSaveEvents` → 各検出に `mDetect`、各シグナルに `mDetectionFromSignal` → `Grouper.mAdd`。
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich`（`mGetIpContext`）→ `fBuildAlert` → SOC キュー。

**管理者が設定を保存 → コレクターの再読み込み**

`modules.js fBuildSettings`（送信）→ `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings`（422 `invalid_setting:<key>` または `<key>.<field>`）→ `fSaveSettings`（`settings.json`、`modules.apache2`）→ `WebContext.mApplySettings` → コレクターのソケット `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings`（`ApacheModule.mReload`、`mLoadRules`、`mDiscover`、`mPublishDoctor`、`mPublishState`）。スイッチも同じ方法で `{enabled}` を送信し（有効にする場合：モジュールの要件が不足している間は 422 `requirements_missing`）、ルールの表は `{rules}` を送信します（`fCleanRules` → `rules.<id>`：`enabled`、`severity`、`threshold` または `first_threshold`、`window`）。ソケットが応答しない場合も、コレクターは次のサイクルで新しい `settings.json` に気づきます。

**Web 画面からのモジュールのインストール**（モジュールをインストールする唯一の方法）

`modules.js fCatalogPanel`（モジュール › インストール可能）→ **リポジトリを確認** → `GET /api/admin/module-catalog`（`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`：リポジトリの各フォルダー `mod-<name>/`。`installed`、`newer`、`action` 付き）→ `installed` が null の項目だけを一覧表示 → **要件**（`fShowRequirements` → `fRequirementsBody`：サーバーのシステム（応答の `system`）向けのモジュールの `install_requirements` を、root として、および `sudo` を付けて表示し、そのロケールの注記 `install_requirements.*` も表示します。何も実行されません）→ **インストール** → `POST /api/admin/module-catalog/{name}`（`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`：`mod-apache2/` → `/opt/localsiem/modules/apache2/`、`previous` は null、`access_changed` は true）→ `WebContext.mReloadModules` → `fFirstInstallation`（要件が不足しており、`modules.<name>.enabled` が一度も保存されていない場合：`enabled = false`）→ コレクターの `restart` → `fCreateModules` がモジュールを読み込む → ダイアログ «<module> をインストールしました» が root 用のコマンド（`fRootCommand`：`manage.py setup-modules`、`read_paths` への読み取り権限）を表示するか、要件が不足している場合は、満たされていないチェックを表示します。

**Web 画面からのモジュールの更新**

モジュール › インストール済み を開く → `fCheckRepository` → `modules.js` の `fFetchCatalog(false)`（`GET /api/admin/module-catalog` の最後の応答を600秒間再利用。モジュールをインストール、更新、アンインストールすると破棄されます）→ `newer` があり、`action` が `update` または `incompatible` の項目 → 行に `fUpdateNotice`（インストール済みのバージョンが比較対象のバージョンである間のみ）→ **更新** → `fUpdate` → 確認 → `POST /api/admin/module-catalog/{name}`（同じ `fInstallFromCatalog` → `fInstall`：新しいコピーがインストール済みのものを置き換え、`previous` は古いバージョン、`access_changed` は `read_paths` が変更されたかどうかを示します。`fFirstInstallation` は実行されないため、`enabled` と設定はそのままです）→ コレクターの `restart` → `access_changed` の場合（root 用のコマンド）またはコレクターが応答しなかった場合のみダイアログ。

**Web 画面からのモジュールのアンインストール**

**アンインストール**（モジュール › インストール済み の行、またはモジュールのページ）→ `fUninstallButton` → 確認 → `DELETE /api/admin/modules/{name}`（`fUninstallModule` → `fRemove` → `InstallLock` → `/opt/localsiem/modules/<name>/` を一時フォルダーに名前変更し、そこで削除）→ `WebContext.mReloadModules` → コレクターの `restart`。`modules.<name>` とそのルールの上書きは `settings.json` に残り、root が与えた読み取り権限も残ります。

**Apache や ModSecurity なしでの初回のインストール → 再構成**（localSIEM 2.2.0 以降）

Web 画面でインストール → `fInstall`（初回のインストール）→ インストールされたコピーから作成されたモジュール（ストレージは `None`）→ `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks`（Apache がある場合：`fRunDoctor` → `apache_config`、`modsecurity`。ない場合は両方ともエラー）→ エラーがあり、`modules.apache2.enabled` が一度も保存されていない → `modules.apache2.enabled = false`（«無効»、スイッチはロック、要件はページに表示）。その後、Apache と ModSecurity をインストールしてから：**再構成** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → 満たされている → スイッチのロック解除と root 用のコマンド（`read_paths` への読み取り権限。apache2 には `setup_option` はありません）→ 管理者がモジュールを有効にする → コレクターの再読み込み → `mDiscover` → `mPublishDoctor`。

**Web 画面からのリクエストのカードと診断**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`。**再検出して診断を実行** → `POST /api/admin/modules/apache2/doctor` → コレクターの `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`。

**ヘルス**

`Collector.mCycle`（60秒ごと）→ `mCheckHealth` → `ApacheModule.mHealth`（最大で300秒に1回。`ApacheConfig.mParse`、`mCountRecentEvents`）→ `fHealthDetection` → `mDetect`。

**privesc：実行されたコマンド → 検出**

1. auditd が1つのシリアル番号で `SYSCALL`、`EXECVE`、`CWD`、`PATH`、`PROCTITLE`、`EOE` を書き込む → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine`（16進数のデコード、`fMaskCommand`、生のテキストの再構築）→ `Correlator.mAdd`（キー `audit:<time>:<serial>`、`EOE` で期限）。
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec`（`suid_escape`、`BPRM_FCAPS`、`SessionTracker.mGet` からの `root_without_door`、`mRememberProcess`）→ `mAnalyzeCommand`（`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`。`cDownloadOnelinerRegex`、`mDownload`/`mRecentDownload`。`fCompileInTemporary`。`mCommand`。サービスアカウント：`fProgramKey` → `mPathFirstSeen` → `new_program`）→ `fCleanFields`。
3. `RulesEngine.mEvaluate`（`mod-privesc/rules/` のルール）→ `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich`（セッション：直近20個のコマンド）→ `fBuildAlert` → SOC キュー。

snoopy がある場合、同じコマンドは syslog の行としても届きます：`fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand`（セッション `snoopy:<uid>:<sid>`）。

**privesc：セッションと経由する手段**

`LOGIN`（auid と ses が割り当てられる）、または sshd や login の `USER_LOGIN`/`USER_START` → `mAuditUser` → `SessionTracker.mStart`（ユーザー、SSH アドレス）。sudo、su、pkexec、doas、run0、systemd の、結果が success の `USER_START`/`USER_CMD` → `SessionTracker.mDoor`。そのセッションのその後の、uid と euid が 0 の `EXECVE` → 開始が確認されていて、経由した手段がなかった場合のみ `root_without_door`。`mHealth` は、最大で1分に1回 `SessionTracker.mExport` を `privesc.sessions` に保存し、`mStart` がそれを読み込みます（`mImport`）。

**privesc：サーバーの監査ルールが記録したシステムコール**

auditd が `SYSCALL`（`arch`、`syscall`、`a0`-`a3`、`success`、`exit`、そしてそれを記録したルールのキー付き）、`CWD`、`PATH`... を書き込む → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`：`fSyscallName` → `EACCES`/`EPERM` で失敗し、ログイン UID を持つ open/exec/truncate → `denied`。`init_module`/`finit_module`/`delete_module` → `kmod`。`ptrace` → `ptrace`。モードに `S_ISUID`/`S_ISGID` を含み、フォルダーに対するものではない `chmod`/`fchmod`/`fchmodat`/`fchmodat2` → `chmod`（`mWriterAllowed`）。`lSensitivePaths` のパスの変更（`sChangeSyscalls` の呼び出し、書き込みフラグ付きの open、`CREATE`/`DELETE` を持つ `PATH`）→ `sensitive_group` 付きの `file`（`dKeyHints` は解決できるパスがない場合のみ）と `mWriterAllowed`。それ以外 → `syscall`。`mBuildEvent` は、診断のために種類ごとの時刻を記憶します（`dRuntime["audit_kinds"]`）。

**privesc：攻撃対象領域のスキャン**

`mHealth`（300秒ごと。起動の5分後と、`surface_scan_hours` ごと）→ `SurfaceScanner.mStart`（スレッド：`scan_paths` の `os.walk`、`os.lstat`、`os.getxattr("security.capability")` → `fCapabilities`）→ 次の `mHealth` → `mSurfaceResult`（`SurfaceScanner.mTake`。`privesc.surface` と比較：新しい setuid/setgid → `new_setuid*`、新しいケーパビリティ → `new_capabilities`）→ `mModuleDetection` → `mDetect`。結果は `privesc.surface` に保存され、`fSurfaceChecks` が表示します。1時間ごとに `fCheckSensitiveFiles` → `sensitive_file_writable`。

**privesc：要件と再構成**

`fInstall`（初回のインストール）または**再構成** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())`（`fContainer`、`fAuditdPid`、`fAuditLogPath` → `fReadState`。`syslog_mode` が `never` でなければ `fSyslogPath` → `fReadState`。`fSnoopyInstalled`）→ 読み取り可能なソースがある：`command_source` は ok（読み取れないものは警告）。存在するが読み取れないソースがある：読み取り権限（`manage.py setup-modules` または `setfacl`）付きの `audit_log` または `syslog` のエラー。何もない：インストールするパッケージ付きの `command_source` のエラー。エラーがある間、モジュールは無効のままです。

<a id="routes"></a>
## 5. エントリーポイント

| エントリーポイント | ハンドラー | ファイル |
|---|---|---|
| `module.json` の `"entry": "module:ApacheModule"` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine`（コア） | [mod-apache2/rules/](../mod-apache2/rules/) |
| ルール関数 `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Web：モジュール › インストール可能。モジュールをインストールする唯一の方法（`GET /api/admin/module-catalog`、`POST /api/admin/module-catalog/{name}`） | `fGetCatalog`、`fInstallFromCatalog`。ビュー `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py)、[frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Web：モジュール › インストール済み の行の**更新**（同じ `GET`。ブラウザーが10分間再利用します。そして同じ `POST`） | `fCheckRepository`、`fUpdateNotice`、`fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js)、[backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Web：**アンインストール**（`DELETE /api/admin/modules/{name}`） | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py)、[backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `module.json` の `read_paths` | `manage.py read-paths`：localSIEM が root として、`localsiem` に読み取りを許可するフォルダー（`fRootCommand` のコマンド） | [backend/manage.py](../../localSIEM/backend/manage.py)、[backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain`（`fModules`） | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`、`mSkipped`、`mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | すべてのマニフェストの `read_paths` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`。`/admin/dashboard/modules/`（`installed/` へ 302）、`/admin/dashboard/modules/installed/`、`/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`。ビュー `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py)、[frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/`（以前の `/admin/dashboard/modules/apache2/` は、ここへの 301 で応答します） | `fAdminModule`（301 は `fAdminModulesSection`）。ビュー `LocalsiemViews.module` | 同じファイル |
| `GET /api/modules` | `fModules`（サインインしている全員向けの状態） | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule`（設定、値、ソース、診断、ルール） | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule`（`enabled`、`settings`、`rules`） | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure`（**再構成**、localSIEM 2.2.0 以降） | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py)、[mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `mod-privesc/module.json` の `"entry": "module:PrivescModule"` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine`（コア） | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`、`GET`/`POST /api/admin/modules/privesc`、`.../privesc/doctor`、`.../privesc/reconfigure` | `fAdminModule`、`fModule`、`fSaveModule`、`fRunDoctor`、`mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py)、[mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| サーバーのルールの監査記録（任意のキー） | `mAuditEvent` → `mAuditExec`、`mAuditUser`、`mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. 影響分析

| コンポーネント | 変更した場合に影響を受けるもの |
|---|---|
| `module.json` `id` | `mod-` を除いたフォルダー名（インストール先のフォルダー名）と `vName` に等しくなければなりません。設定（`modules.<id>`）と状態（`<id>.doctor`）のキーであり、すべてのイベントの `module` です：名前を変えると、保存された設定が失われ、履歴が分断されます。 |
| `module.json` `core` | インストールされている localSIEM より高くすると、モジュールが読み込まれなくなります（状態 «エラー»）。リポジトリでは、インストール可能に «localSIEM X 以降が必要» と表示され、インストール済みには**更新**なしで新しいバージョンが表示されます。 |
| `module.json` `entry` | `Module` のサブクラスを指す必要があります。誤った値は読み込みエラーになります。 |
| `module.json` `default_enabled` | 管理者がまだ決めていないサーバーでの有効／無効（初回のインストールで要件が不足している場合は無効）。 |
| `module.json` `read_paths` | localSIEM が root として与える読み取り権限（`manage.py read-paths`）：フォルダーが不足していると、診断と状態で権限エラーになります。新しいバージョンで変更されると、**更新**の後に Web 画面が root 用のコマンドを再び表示します（`access_changed`）。 |
| `module.json` `install_requirements` | インストール可能の要件ダイアログ（`modules.js` の `fRequirementsBody`）。誤った値（`debian` と `alpine` 以外のシステム、空のリストまたは20個を超えるコマンド、シェルの演算子や改行を含むコマンド）があると、モジュールは不正とみなされます（コアの `fCheckInstallRequirements`）：インストールも読み込みもされません。 |
| `module.json` `setup_option` | 影響なし：コアはこれを無視します（apache2 1.3.0 と privesc 1.1.0 以降、これを持つモジュールはありません）。 |
| リポジトリの最上位にある、`module.json` を含むフォルダー `mod-<name>/` | Web 画面のカタログがモジュール `<name>` として一覧表示するもの：インストール可能には、まだインストールされていないものが表示され（より新しいコアが必要なものは «localSIEM X 以降が必要»、不正なものは «リポジトリのモジュールが無効です» として）、インストール済みのものより高い `version` があると、インストール済みに**更新**が表示されます。 |
| `module.json` `settings` | フォーム、検証、既定値。新しい既定値は、そのキーを一度も保存していないサーバーに適用されます。保存された値は移行されません：名前を変えたキーは値を失い、新しい型を持つ古い値は、保存されたままの形でモジュールに届きます。 |
| `locales/*.json` | Web 画面のテキストのみ。テキストがない場合は en-US、次にキーにフォールバックします。 |
| `parsers.py`（記録の dict） | 相関（`correlation`、`fields.client_ip`、`fields.path`）、リクエストのカード、全文検索のインデックス（`search`、`raw`）、未解析行のヘルス、プライバシー。 |
| `logformat.py` `dKnownFormats` | すべてのアクセスログの解析。`localsiem_combined` は、すでにそれを書き込んでいるサーバーのために残っています（モジュールのバージョン 1.2.0 以前が追加しました）：その定義を変更しないでください。 |
| `correlate.py` | リクエストごとに1つのイベント。コアは `mAdd`、`mDue(pNow, pForce, pWatermark)`、`mPendingCount` を呼び出し、再起動後にまだ保留中の記録を戻します。`UNIQUE_ID` がない場合は、記録をそのフィールド `client_ip`、`method`、`uri`、`status`、`path` で組み合わせます：これらを異なる形で書き込むパーサーは、組み合わせを壊します。監査記録の待機（`mWaitsForAudit`）には、error.log の行の `modsecurity` フィールドと、ソース `audit` の記録が必要です。 |
| `modsec.py`（カテゴリ、ラベル、範囲） | アラートのルール名（SOC の統計はこれでグループ化するため、変えないでください）、グループ化のキー、`category:` の検索。 |
| `ApacheModule.mBuildEvent`（イベントの dict） | イベントテーブルの列、YAML ルールが読み取るフィールド（`action`、`status`、`method`、`path`、`crs_matched`、`db_error`...）、検索、CSV エクスポート。 |
| `ApacheModule.mAssess` | SOC に届くものとその重大度。コアの `GenericAlert` の制限（rule は300文字、description は10 000文字）。 |
| `severity.yaml` | すべての ModSecurity の検出の重大度。重大度はグループ化のキーの一部なので、変更すると新しいグループが始まります。 |
| `rules/*.yaml` | `id` は上書き（`rules.<id>`）と検索（`rule:localsiem:<id>`）のキーです：変えないでください。フィールドはイベントに存在する必要があります。`{function: ...}` には `mRuleFunctions` が必要です。 |
| `discovery.py` | どのログを読み取るか。`fSourceKey` は保存された位置のキーです（新しいキーにすると、ファイルは保存された位置を持たない新しいソースになります）。Web シェルのルールの DocumentRoot。診断。 |
| `doctor.py` | Web 画面と `manage.py` の診断、そしてクライアントに表示されるヒント。`fix` を持てるのは、ログ以外のもの（ModSecurity、CRS、`SecRuleEngine`、`mod_unique_id`、権限）に関するチェックだけです。ログに関するチェックは、ログを説明するだけです。 |
| `mRequirements` / `fRequirementChecks` | モジュールを有効にできるかどうか、Apache や ModSecurity なしでの初回のインストール後の状態 «無効»、Web 画面が表示する要件、**再構成**。これらはストレージなしで Web 画面と `manage.py` で実行され、呼び出しのたびに Apache の設定を解析します：ストレージや遅い処理から遠ざけ、ID `apache_config` と `modsecurity` を変えないでください。 |
| privesc：イベントの列とフィールド（`mBuildEvent`、`mAnalyzeCommand`） | YAML ルールはこれらを名前で照合します（`recon_burst`、`suid_escape`、`root_without_door`、`sensitive_group`、`writer_allowed`、`ptrace_attach`、`parent_interpreter`、`account_type`、`real_uid`、`argc_zero`...）：フィールドの名前を変えると、それを使うルールが黙って機能しなくなります。`vhost` はユーザーです：アラートのグループ化のキーと `vhost:` の検索はこれに依存します。 |
| privesc：`fReconToken` | 何を偵察とみなすか、異なるコマンドをどう区別するか：トークンを変えると、セッションがしきい値に達する速さが変わります。 |
| privesc：`SessionTracker` と経由する手段（`sDoors`） | `root_without_door`：一覧に手段が欠けていると、正当な root セッションが重大になり、余分な手段があるとカーネルエクスプロイトが隠れます。`mExport`/`mImport` は `privesc.sessions` の形式です。 |
| privesc：`parsers.py` | 記録のフィールド（`args`、`command`、`kind`、snoopy の `uid`/`euid`）、パスワードのマスク、監査記録の生のテキスト。読み取る snoopy のフォーマット（モジュールが `snoopy.ini` を変更することはありません）。 |
| privesc：監査記録の分類（`lSensitivePaths`、`dSyscallTables`、`sChangeSyscalls`、`dOpenFlagArgument`、`dChmodModeArgument`、`sDeniedSyscalls`、`dKeyHints`） | 何が `file`、`chmod`、`kmod`、`ptrace`、`denied` になるか、したがってルール sensitive-file、persistence-file、monitoring-changed、suid-set、kernel-module、ptrace、denied-burst、sensitive-denied。システムコールの番号が誤っていると、そのアーキテクチャの記録が誤って分類されます。 |
| privesc：`surface.py` | スキャンのコスト（スレッド、制限）と、診断と `mSurfaceResult` が報告するもの。`privesc.surface` はその基準です。 |
| privesc：`mRequirements` / `fRequirementChecks` | モジュールを有効にできるかどうか（読み取り可能ないずれかのソース）、`localsiem` がまだログを読み取れない初回のインストール後の状態 «無効»、**再構成**。Web 画面と `manage.py` からストレージなしで呼び出されます：高速に保ち、root なしで動作させてください。ID `command_source`、`audit_log`、`syslog` を変えないでください。 |
| コアのインターフェース（localSIEM の `backend/core/module.py`、`registry.py`） | すべてのモジュール：フックのシグネチャの変更、マニフェストの新しい必須キー、記録とイベントの新しい契約は、モジュールを壊します。新しい localSIEM が必要な場合は、モジュールの `module.json` の `core` を上げてください。 |

<a id="extensions"></a>
## 7. 拡張ポイント

### 新しいモジュールの書き方

1. **フォルダー**：このプロジェクトのルートに `mod-<name>/` を作成します。モジュールの名前である `<name>` は、`[a-z][a-z0-9_]{1,31}` に一致する必要があります。`mod-` 接頭辞はフォルダーだけのものです：`module.json`、クラス、オプション、テキストは `<name>` を使います。`__init__.py` は置きません。
2. **`module.json`**、例：

   ```json
   {
     "id": "example",
     "version": "1.0.0",
     "core": "2.2.0",
     "entry": "module:ExampleModule",
     "default_enabled": false,
     "read_paths": ["/var/log/example"],
     "install_requirements": {"debian": ["apt-get -y install example"], "alpine": ["apk add example"]},
     "settings": [
       {"key": "log_file", "type": "path", "default": "/var/log/example/example.log"}
     ]
   }
   ```

3. **テキスト**：localSIEM の15の言語それぞれについて、`name`、`summary`、各設定のラベルとヘルプを含む `locales/<language>.json`。要件に関する注記は `install_requirements`（すべてのシステム向けの `note`、および `debian` と `alpine`）に入れ、要件ダイアログに表示されます。
4. **コード**：`vName` が ID である `Module` のサブクラスを持つ `module.py`。`mParse`、`mCreateCorrelator`、`mBuildEvent` を実装する必要があり、通常は `mDiscover` も実装します。その他のフックは任意です（セクション 1）。自身のファイルは相対的に、コアは `backend.core...` としてインポートします。このリポジトリの2つのモジュールは完全な例です（[mod-apache2/module.py](../mod-apache2/module.py)、[mod-privesc/module.py](../mod-privesc/module.py)）。最小限のスケッチ：

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # 各記録は、待たずにそれ自体で1つのイベントになります。

     def __init__(self):
       self.lPending = []

     def mAdd(self, pRecord: dict, pNow: float | None = None) -> None:
       self.lPending.append({"key": "x", "records": [pRecord], "weak": False, "uid": None})

     def mDue(self, pNow: float | None = None, pForce: bool = False, pWatermark: float | None = None) -> list[dict]:
       lDue = self.lPending
       self.lPending = []
       return lDue

     def mPendingCount(self) -> int:
       return len(self.lPending)


   class ExampleModule(Module):

     vName = "example"

     def mDiscover(self) -> list[dict]:
       vPath = self.mModuleSettings().get("log_file", "")
       return [{"key": "example:log:" + vPath, "path": vPath, "kind": "log", "format": "", "vhost": ""}] if vPath else []

     def mParse(self, pSource: dict, pUnit: str, pReceived: str) -> dict:
       return {
         "time": pReceived, "received": pReceived, "module": "example", "source": pSource["kind"],
         "source_key": pSource["key"], "correlation": None, "parse_status": "ok",
         "fields": {}, "raw": self.vMasker.mMaskText(pUnit)
       }

     def mCreateCorrelator(self):
       return OneEventCorrelator()

     def mBuildEvent(self, pTransaction: dict) -> dict:
       dRecord = pTransaction["records"][0]
       dEvent = {vColumn: None for vColumn in ("vhost", "method", "uri", "path", "query", "status", "bytes", "duration", "ua", "referer", "uid", "category", "phase", "score", "threshold", "engine", "severity")}
       dEvent.update({
         "time": dRecord["time"], "received": dRecord["received"], "host": self.dSettings["host"], "module": "example",
         "sources": [dRecord["source"]], "ip": None, "rules": [], "action": "none", "parse_status": dRecord["parse_status"],
         "correlation": "none", "fields": {}, "record_ids": [dRecord["id"]] if dRecord.get("id") else [],
         "rule_hits": [], "detections": []
       })
       return dEvent
   ```

5. **実行されたアクション**：そのサービスにとって «すでに対処済み» が何を意味するか（例：すでに禁止された IP）を決め、その場合は `action` を `blocked` に設定します。検出は、実行されたアクションのないイベントにのみ追加します。
6. **ルール**：`mod-<name>/rules/` の YAML ファイル。これらは `mRulesPath` が返し、ルールが呼び出す関数は `mRuleFunctions` が返します。
7. **要件**：モジュールがサーバー上のソフトウェアを必要とする場合（apache2 が Apache と ModSecurity 2 を必要とするように）、`mRequirements()` から要件ごとに1つのチェックを返し（`fCheck` の形式：`status` は `ok` または `error`、`fix` にはそれをインストールするコマンド）、そのソフトウェアをモジュールからインストールすることは決してしないでください：要件を満たさない場合、モジュールは無効の状態でインストールされます。これはストレージなしで、Web 画面と `manage.py` でも実行されます。また、`module.json` の `install_requirements` で、そのソフトウェアを Debian と Alpine にインストールするコマンドを宣言してください（1行に1コマンド、シェルの演算子なし）：Web 画面は、モジュールのインストール前に、モジュール › インストール可能 › 要件 で、それらをそのままの形と先頭に `sudo` を付けた形で表示します。
8. **インストール**：このリポジトリ（ブランチ `main`）に公開します。インストールされていない間は localSIEM の Web 画面の モジュール › インストール可能 に表示され、**インストール**はフォルダー `mod-<name>/` を `/opt/localsiem/modules/<name>/` にコピーして、コレクターを再起動します。`read_paths` への読み取り権限には root が必要です：Web 画面がそのコマンド（`manage.py setup-modules`）を表示します。モジュールにはセットアップオプションはありません：何もインストールせず、`/opt/localsiem` の外で何も変更せず、クライアントのログに書き込むことも、ローテーションや削除をすることも、そのフォーマットを変更することもありません。サーバーが独自の方法でログを書き込んでいる場合は、モジュールがそれに合わせ、サーバーに不足しているものは要件になります。新しいバージョンを公開するには、`version` を上げます：モジュール › インストール済み に通知と**更新**が表示されます。更新では、モジュールの設定と有効／無効の状態が保持され、`read_paths` が変更された場合にのみ root 用のコマンドが再び表示されます。
9. **ドキュメント**：15の言語の README、この CODE、MANUAL を更新します。

### apache2 モジュールにルールを追加する方法

[mod-apache2/rules/](../mod-apache2/rules/) に YAML ファイルを作成します（すべてのキーと演算子は、[backend/core/rules.py](../../localSIEM/backend/core/rules.py) の先頭で説明されています）：`id`、`name`、`category`、`type`、`severity`、`kind`（`match`、`threshold`、`sequence`）、条件（`when`、または `first`/`first_threshold`/`then`）、`by`、`window`、`threshold`、`lists`、`description`、`search`。フィールドは、まずイベントの列から、次に `fields` から探されます。ルールはモジュールのページのルールの表に表示され、モジュールの新しいバージョンがインストールされると、コレクターに読み込まれます：`module.json` の `version` を上げて公開し、モジュール › インストール済み で**更新**を押してください。

### apache2 モジュールに設定を追加する方法

[mod-apache2/module.json](../mod-apache2/module.json) の `settings` に、型と既定値を指定して追加し、[mod-apache2/locales/](../mod-apache2/locales/) の4つのファイルにその `label` と `help` を追加して、`self.mModuleSettings().get("<key>")` で読み取ります。フォーム、検証、再読み込みはコアが行います。

### 診断のチェックを追加する方法、または重大度を変更する方法

チェックは、`fRunDoctor`（[mod-apache2/doctor.py](../mod-apache2/doctor.py)）内の1つの `fCheck(id, status, title, detail, fix)` です。`id` を変えず、`fix` には正確な設定例またはコマンドを、ログではない要件についてのみ入れてください：クライアントのログに関するチェックは、ログと、localSIEM がそこから読み取れるものと読み取れないものを説明するだけで、`fix` はありません。ModSecurity の検出の重大度は、[mod-apache2/severity.yaml](../mod-apache2/severity.yaml) で変更します（`low`、`medium`、`high`、`critical`）。

### privesc モジュールにルールを追加する方法

Apache のものと同様に、[mod-privesc/rules/](../mod-privesc/rules/) に YAML ファイルを作成します。照合するのは列（`method`、`uri`、`path`、`vhost`、`action`）とイベントのフィールド（`sensitive_group`、`account_type`、`real_uid`、`recon`、`service_account`、`file`...）であり、監査ルールのキーは決して照合しません。無視するユーザーが決してルールを発動させないように `ignored: {not: true}` を追加し、実際に実行されたものだけが対象の場合は `action: none` を追加します。条件に状態やロジック（同じセッションのシーケンス、ファイルのチェック）が必要な場合は、`PrivescModule.mAnalyzeCommand`（すべてのソース）または `mAuditExec`/`mAuditSyscall`/`mSyslogEvent`（1つのソース）でフラグを計算し、ルールからそれを照合します。

### privesc モジュールに偵察コマンド、ツール、エクスプロイトを追加する方法

- 偵察：プログラムを `sReconSimple` に追加するか、質問の種類ごとにトークンを返す分岐を `fReconToken` に追加します（[mod-privesc/commands.py](../mod-privesc/commands.py)）。引数ごとに変わるトークンは、数を水増しします。
- ツールとエクスプロイト：[rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) または [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) のリストに正規表現を追加します（大文字と小文字を区別せず、コマンドラインと照合されます）。管理者は設定（`rules.<id>.lists`）から追加することもできます。

### privesc モジュールにソースまたは監査記録の種類を追加する方法

- 機密パス：[mod-privesc/module.py](../mod-privesc/module.py) の `lSensitivePaths` に、そのグループとともに追加します（または新しいグループと、`sensitive_group` を照合するルールを追加します）。システムコールの種類：その名前を `mAuditSyscall` の集合に、その番号を `dSyscallTables` の各テーブルに追加します。監査ルールのキーに依存せず（せいぜい `dKeyHints` に追加する程度にし）、監査ルールを決してインストールしないでください：サーバーは管理者が決めたものを記録し、診断がそれを説明します（[doctor.py](../mod-privesc/doctor.py) の `dAuditKinds`）。
- ソース：新しい `kind` で `fDiscoverSources` から返し、`mParse` で解析し、`mBuildEvent` で他と同じ列とフィールドを持つイベントを作成します。そうすれば、ルールは変更なしで機能します。
