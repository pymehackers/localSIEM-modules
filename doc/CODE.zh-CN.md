# localSIEM-modules 代码参考

本 CODE 还提供以下语言版本：\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), zh-CN

## 索引

1. [架构与设计决策](#architecture)
2. [模块地图](#modules)
3. [关键符号](#symbols)
4. [主要调用路径](#flows)
5. [入口点](#routes)
6. [影响分析](#impact)
7. [扩展点](#extensions)

[安装](README.zh-CN.md) · [用户手册](MANUAL.zh-CN.md) · [localSIEM 代码参考](../../localSIEM/doc/CODE.zh-CN.md)

<a id="architecture"></a>
## 1. 架构与设计决策

本项目包含 localSIEM（同级项目 `../localSIEM`）的可安装模块。它没有自己的服务，也没有自己的安装程序：模块只能从 localSIEM 的 Web 界面安装，位于 模块 › 可安装（在 模块 › 已安装 中更新和卸载），Web 界面会下载本仓库（分支 `main`）并将每个模块的目录 `mod-<name>/` 复制到 `/opt/localsiem/modules/<name>/`；localSIEM 的安装程序只安装核心，从不安装模块，localSIEM 也没有自带的模块。localSIEM 的进程（采集器、Web 界面、`manage.py`）会加载这些模块。`mod-` 前缀只属于本仓库中的目录名：模块本身（其 `module.json` 的 `id`、其选项、其设置及其安装目录）使用不带该前缀的名称。目前有两个模块：`apache2`（目录 `mod-apache2/`）和 `privesc`（目录 `mod-privesc/`）。

### 为什么模块位于核心之外

localSIEM 的核心（[backend/core/](../../localSIEM/backend/core/)）是通用的：存储、搜索、规则引擎、分组、SOC 队列、心跳和健康检查对 Apache 一无所知。一个服务的具体含义（其日志在哪里、如何分帧和解析、记录如何组成一个事件、什么算作已解决、其规则及其前提条件）都位于模块中。将模块放在独立的项目中意味着：

- 模块有版本号（`version`），声明它所需的最低 localSIEM 版本（`core`），并且无需发布新的 localSIEM 版本即可更新、添加或停用；
- 核心不按名称导入任何模块，也没有自带的模块：注册表（[backend/core/registry.py](../../localSIEM/backend/core/registry.py)）只扫描 `/opt/localsiem/modules/`（开发副本中为 `LOCALSIEM_MODULES_PATH`），Web 界面将本仓库的模块安装在该目录中；
- 加载失败的模块从不会影响其他模块：其错误会在 Web 界面中列出（状态«错误»），`manage.py modules` 也会列出；
- 模块从不修改核心：`backend/core/module.py` 和 `backend/core/registry.py` 就是全部契约。

### 契约：module.json、locales 和一个 Module 子类

**`module.json`**（由 `fReadManifest` 检查）：

| 键 | 默认值 | 含义 | apache2 | privesc |
|---|---|---|---|---|
| `id` | 必填 | 不带 `mod-` 前缀的模块目录名（即安装目录的名称），`[a-z][a-z0-9_]{1,31}`；也是类的 `vName` | `apache2` | `privesc` |
| `version` | `"0"` | 模块的版本，在 Web 界面和 `manage.py modules` 中显示 | `1.3.2` | `1.1.2` |
| `core` | `"0"` | 所需的最低 localSIEM 版本；如果高于已安装 localSIEM 的 `cVersion`，则不加载该模块 | `2.2.0` | `2.2.0` |
| `entry` | 必填 | `"file:Class"`：`file` 为不带 `.py` 的文件名（`[a-z][a-z0-9_]{0,63}`），`Class` 为 `Module` 的子类 | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | 在管理员做出决定（`modules.<id>.enabled`）之前是否运行 | `true` | `true` |
| `read_paths` | `[]` | localSIEM 以 root 身份允许 `localsiem` 用户读取的绝对路径目录（安装后、**重新配置**后以及更改了这些目录的更新后，Web 界面显示的命令） | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | 针对每个系统（`debian`、`alpine`），以 root 身份在服务器上安装模块所需软件的命令：每行一条命令，不含 shell 运算符，因为 Web 界面还会在前面加上 `sudo` 显示它们（核心的 `fCheckInstallRequirements`）。显示在 模块 › 可安装 › 前提条件 中，从不运行 | Debian：Apache、ModSecurity 2、CRS、`a2enmod`、没有 ModSecurity 配置时使用推荐配置、重启；Alpine：Apache | Debian：auditd 和 rsyslog；Alpine：auditd |
| `setup_option` | — | 没有模块使用：核心会忽略它（注册表会丢弃它），因为模块从不更改服务器；旧版本的 `module.json` 文件中可能仍有它 | 未设置 | 未设置（`--configure-privesc` 已在 1.1.0 中移除） |
| `settings` | `[]` | 每项设置的描述：Web 界面据此构建其表单 | 6 项设置 | 13 项设置 |

每项设置都有一个 `key`（`[a-z][a-z0-9_]{1,31}`）、一个 `type`，通常还有一个 `default`，以及其类型的属性。`fValidateSettings` / `fCleanValue` / `fCleanRecords` 检查管理员保存的内容：

| 类型 | 属性 | Web 控件 | 接受的值 |
|---|---|---|---|
| `boolean` | — | 复选框 | `true` / `false` |
| `integer` | `min`、`max` | 数字字段 | `min`..`max` 范围内的整数 |
| `string` | `max_length`（500） | 文本字段 | 不含控制字符、去除首尾空白、最长 `max_length` 的文本 |
| `path` | — | 等宽文本字段 | 空或绝对路径（以 `/` 开头），最长 1024 个字符 |
| `choice` | `choices`（必填）、`required` | 列表（非必填时带有«—»） | `choices` 之一，或为空 |
| `records` | `fields`（必填：其他类型的设置）、`max_items`（50） | 每条记录一个区块，带有添加和移除 | 最多 `max_items` 条记录的列表；每个字段都会被检查，`required` 字段不能为空，空字段会被丢弃 |

**`locales/<language>.json`**（de-DE、en-GB、en-US、es-AR、es-ES、fr-FR、he-IL、hi-IN、it-IT、ja-JP、ko-KR、pt-BR、pt-PT、ru-RU、zh-CN），由 `fReadTexts` 读取并由 Web 界面显示（`modules.js fModuleText`，找不到时依次回退到 en-US 和键名）：

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

缺失或损坏的语言文件只会导致该语言的文本缺失。

**`Module` 子类**（[backend/core/module.py](../../localSIEM/backend/core/module.py)）。注册表以 `Class(pSettings, pMasker, pStorage, pManifest)` 的形式创建它。其钩子方法：

| 钩子 | 调用方 | 默认 | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | 采集器，在存储就绪后调用一次 | 无操作 | 保存 `apache.first_start`（学习天数的起点） | 保存 `privesc.first_start`；加载 `privesc.sessions`、`privesc.surface` 和 `privesc.health` |
| `mEnabled()`、`mModuleSettings()`、`mReload()` | 采集器、Web 界面 | 以 `module.json` 的默认值为基础，叠加 `modules.<id>` 中的值 | 继承 | 继承；`mReload` 还会清空 `mSettings` 的缓存 |
| `mDiscoveryInterval()` | 采集器（取已启用模块中的最短值，至少 60 秒） | `discovery_interval_seconds` 或 3600 | 继承 | 继承（默认 300） |
| `mDiscover()` | 采集器（启动、定时、重新加载、诊断请求）、`manage.py doctor` | `[]` | 根据 Apache 配置和手动来源得到的来源 `{key, path, kind, format, vhost, audit_type, storage_dir}` | `fDiscoverSources`：审计日志和 syslog |
| `mCreateFramer(pSource)` | 采集器，每个来源 | `LineFramer` | 用于原生串行审计日志的 `AuditFramer` | 继承（`LineFramer`） |
| `mParse(pSource, pUnit, pReceived)` | 采集器，每个单元 | 必须实现 | `access`、`error` 或 `audit` 记录 | `audit` 或 `syslog` 记录 |
| `mCreateCorrelator()` | 采集器，启动时 | 必须实现 | `Correlator`（窗口和弱关联取自核心设置） | `Correlator`：审计记录按序列号合并（EOE 或 2 秒）；syslog 行立即处理 |
| `mBuildEvent(pTransaction)` | 采集器，每个到期的事务 | 必须实现 | 带有 `action` 和 `detections` 的事件 | 带有规则所匹配标志的事件；没有自己的检测结果 |
| `mRulesPath()` / `mRuleFunctions()` | 采集器，加载规则时 | `None` / `{}` | 其目录下的 `rules/` / `{"apache2.new_php": mIsNewPhp}` | 其目录下的 `rules/` / 继承的 `{}` |
| `mDetectionFromSignal(pEvent, pSignal)` | 采集器，每个规则信号（可选：用 `hasattr` 查找） | 通用检测结果 | 包含请求详情和 `{rule: {id, count}}` 的检测结果 | 包含用户、命令、程序、会话、父进程、文件等的检测结果 |
| `mEnrich(pDetection)` | 采集器，在分组时、构建告警之前 | `{}` | 该 IP 最近一小时的上下文 | 会话的上下文：是否看到开始、获得 root 的途径、SSH 地址、最近 20 条命令 |
| `mDoctor()` | 采集器（状态 `<id>.doctor`）、`manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor`（auditd 及其规则记录的内容、syslog、snoopy、模块能看到的内容、1.0.0 版本的文件、攻击面） |
| `mHealth(pNow)` | 采集器，每 60 秒，仅限已启用的模块 | `[]` | ModSecurity 未加载或为 Off、缺少真实客户端 IP（最多每 300 秒一次） | 保存会话；扫描结果；每 300 秒：auditd 已停止、敏感文件可写（每小时）、启动 setuid 程序扫描 |
| `mSkipped()` | 采集器状态、`manage.py doctor` | `[]` | 管道日志、被 `GlobalLog` 覆盖的日志、无数据的访问日志（`format_without_data`） | 未读取的 syslog（auditd 正在运行、`syslog_mode` 为从不）、缺失的审计日志 |
| `mSetLowDisk(pLowDisk)` | 采集器，磁盘水位 | 无操作 | 停止存储审计请求头和请求体 | 继承 |
| `mDisplayRecord(pRecord)` | Web 界面，请求详情 | `{}` | 已存储审计记录的请求头和请求体（`fAuditDisplay`） | 继承 |
| `mRequirements()` | 核心，localSIEM 2.2.0 或更高版本：首次安装、采集器启动和重新加载、Web 界面中的**重新配置**、`manage.py modules` 和 `doctor` | `[]`（无前提条件） | `apache_config` 和 `modsecurity`（`fRequirementChecks`） | `command_source`：`localsiem` 可以读取的任意来源，即审计日志（auditd 正在运行，且不在容器中）或 syslog（如果安装了 snoopy，则包括 snoopy）；当某个来源存在但无法读取时为 `audit_log` / `syslog` |

核心中已不再有 `mSetupSnippet` 和 `mApplySetup`：模块没有配置选项，也从不更改服务器。

记录是字典，包含 `time`、`received`、`module`（即 id：采集器据此选择关联器）、`source`、`source_key`、`correlation`、`parse_status`（`ok`、`partial`、`unparsed`）、`fields` 和 `raw`（已脱敏），以及可选的 `search`（为全文搜索建立索引的文本）。事件包含事件表的列（`storage_sqlite.py` 中的 `lEventColumns`），外加 `record_ids`、`rule_hits` 和 `detections`。一个检测结果包含 `module`、`vhost`、`ip`、`category`、`severity`、`rule`、`type`、`description`、`search`、`details`、`time` 和 `uid`。

### 前提条件：模块从不安装其监控的软件

安装模块从不会安装其监控的软件：apache2 模块既不安装 Apache 也不安装 ModSecurity，privesc 模块既不安装 auditd、syslog 守护进程，也不安装 snoopy（其前提条件 `command_source` 是 `localsiem` 用户可以读取的任意来源：在容器外运行 auditd 时的审计日志，或 syslog；见 `mod-privesc/doctor.py` 的 `fRequirementChecks`）。模块自己在 `mRequirements()`（localSIEM 2.2.0 或更高版本）中定义启用前需要具备的条件：一个与诊断格式相同的检查列表，当其中没有任何一项的状态为 `error` 时即视为满足。apache2 模块返回 `apache_config`（找到了 Apache 配置：`apache2.conf`、`httpd.conf` 或设置项 `config_file` 指定的文件）和 `modsecurity`（已加载 `mod_security2`；ModSecurity 3 不算），`fRequirementChecks` 从诊断的前几项检查中获取它们；没有 Apache 时，两者都是错误。安装这些软件的命令在 `module.json` 的 `install_requirements` 中声明：Web 界面会在安装模块之前（模块 › 可安装 › 前提条件）针对服务器的系统显示这些命令，并且从不运行它们。核心：

- 当首次安装时缺少某项前提条件且管理员从未做出决定时，以停用状态安装模块（`modules.<id>.enabled = false`）；更新从不更改 `enabled`；
- 在缺少某项前提条件期间不允许启用模块：开关被锁定，Web 界面显示各项前提条件及其 `fix`；
- 从不自行停用一个已启用但失去某项前提条件的模块：其诊断和健康警告（`mHealth`：«ModSecurity is no longer loaded»）会报告这一情况，而停用模块会让它们沉默；
- 在采集器启动或重新加载时，以及在模块页面上点击**重新配置**时（模块停用时同样适用）再次检查前提条件：如果已满足，则解锁开关，由管理员启用模块，并且 Web 界面显示需要以 root 身份运行的命令，使 `localsiem` 能够读取安装后创建的日志（`read_paths`）。

### 作为命名空间包加载

任何地方都没有 `__init__.py`（Python 3.13 隐式命名空间包）。`fRegisterPackage` 创建包 `localsiem_modules`，以模块目录作为其 `__path__`，`fLoadClass` 导入 `localsiem_modules.<id>.<file>`，检查该类是否为 `Module`，以及其 `vName` 是否等于 `id`。对模块代码的影响：

- 模块自己的文件以**相对方式**导入（`from .parsers import AccessParser`）；
- 核心以 **`backend.core...`** 的形式导入（`from backend.core.module import Module`）：localSIEM 的进程会将 localSIEM 目录放到 `sys.path` 中；
- 只能使用标准库和 localSIEM 的依赖（其虚拟环境 `/opt/localsiem/venv/`，例如 PyYAML）：localSIEM 不会为模块安装任何东西。

### 根据清单构建的设置表单

模块没有自己的 HTML。Web 界面读取 `module.json` 的 `settings` 和 `locales/` 中的文本，构建表单（`modules.js fBuildSettings`、`fRecordsEditor`），用 `fValidateSettings` 验证保存的内容，并只将管理员保存的值存储在 `settings.json` 的 `modules.<id>` 下；`enabled` 也存放在那里。模块读取 `mModuleSettings()`：以 `module.json` 的默认值为基础，叠加已保存的值。因此，添加一项设置无需更改 Web 界面或核心。

apache2 模块还会从 `self.dSettings` 读取以下核心设置：`host`、`correlation_window_seconds`（5）、`weak_correlation_seconds`（2）、`below_threshold_severity`（`low`）以及 `health.single_ip_percent` / `health.single_ip_minimum_requests`（90 / 100）。`mModuleSettings()` 还会传递保存在 `modules.apache2` 下但 `module.json` 未声明的键：`mDiscover` 就是这样读取 `document_roots`（`{vhost: folder}`，覆盖自动发现的 DocumentRoot）的；它只能通过编辑 `settings.json` 来设置。

### «采取的动作»原则

只有尚未被任何人处理的内容才会发送到 SOC。在 apache2 模块中，所采取的动作从最可靠的来源读取：审计日志（原生格式中的 `Action: Intercepted (phase N)`，JSON 中的 `audit_data.action.intercepted/phase`），然后是 error.log（`Access denied with code NNN (phase N)`）。没有任何 ModSecurity 痕迹的 403 不算拦截（`fields.doubtful_block`）。

| 情况 | `action` | 检测结果（发送到 SOC） |
|---|---|---|
| 在阶段 1-2 被截获（应用程序从未收到） | `blocked` | 无：`mAssess` 返回 `None`；计入之后告警的上下文 |
| 在阶段 3-4 被截获 | `none` | 有，`blocked_late`（高），或出现数据库错误时为 `success_indicator` |
| 引擎处于 `DetectionOnly` 时的匹配 | `none` | 有 |
| 低于异常阈值的匹配 | `none` | 有，`below_threshold`（低） |
| YAML 规则产生的信号 | `none` | 有 |

严重级别来自 `severity.yaml`（`fLoadSeverityTable`；文件缺失或值无效时保留内置默认值）：`crs_not_blocked_2xx` 高，`crs_not_blocked_other` 中，`blocked_late` 高，`success_indicator` 严重（出站规则 950-955 未被拦截，或同一请求中出现数据库错误），`below_threshold` 低（核心设置 `below_threshold_severity` 优先）。«高于阈值»是指命中了 949xxx 规则，或 ModSecurity 给出的分数达到了阈值；根据规则严重级别计算出的分数只是估计值，不起决定作用。阈值取消息中的阈值，否则取 `anomaly_threshold`，否则取 `crs-setup.conf` 中的阈值，否则为 5。

### apache2 模块的工作原理

1. **发现**（`discovery.py`）：`ApacheConfig` 以 `localsiem` 用户身份直接读取配置（`Include`、`IncludeOptional`、`Define`、Debian 的 `envvars` 中的 `${VARS}`、`<VirtualHost>`、根据已加载模块判断的 `<IfModule>`），不使用 `apache2ctl`。`fDiscoverSources` 将 `CustomLog`/`GlobalLog`/`TransferLog`、`ErrorLog` 和 `SecAuditLog` 转换为具有固定键 `apache:<kind>:<real path>` 的来源。格式包含 `%v` 的 `GlobalLog` 覆盖所有 vhost（其他访问日志会被跳过）；管道日志和 syslog 会被跳过，格式中不含任何 `%` 指令的访问日志也会被跳过（Apache 会原样写入一个没有任何 `LogFormat` 定义的别名：`format_without_data`，除非另一个有数据的 `CustomLog` 写入同一文件；诊断会说明这一点，但不提供修复，因为日志格式从不被更改）；手动来源优先，且一个文件只读取一次。
2. **分帧与解析**（`parsers.py`、`logformat.py`、`modsec.py`）：访问日志行使用根据其 `LogFormat` 生成的正则表达式解析（最近一次成功的格式会被优先尝试）；错误日志行会被分类（`modsecurity`、`database`、`php`、`crash`、`apache`）；审计记录以 JSON（单行，在 `matched_rules` 之前截断）、原生串行（`AuditFramer` 将 `--id-A--` 到 `--id-Z--` 合并）或并发（索引行指向 `SecAuditLogStorageDir` 下的文件）格式读取。所有内容都会被脱敏；无法解析的内容保留为 `unparsed`。
3. **关联**（`correlate.py`）：具有相同 `UNIQUE_ID` 的记录组成一个事务，该事务会等待关联窗口以及正在追赶的来源的水位线；没有 `UNIQUE_ID` 的访问日志行（Apache 默认写入的格式）会在它或其请求的记录到期时，由 `mPair` 与没有访问日志行的 ModSecurity 记录配对：客户端 IP 相同、时间在 ±2 秒内（该行只有整秒），且在双方都已知时方法、URI、状态码和路径相同；吻合项更多的候选者胜出，其次是时间最近的，再次是最早的，并且该事件会被标记为弱关联。没有 `UNIQUE_ID` 的 error.log 行会立即合并到其 IP 最近的事务中。一个带有 `UNIQUE_ID` 且有 error.log 中 ModSecurity 行的事务，在审计记录持续到达期间（`vAuditSeen`），还会等待它自己的审计记录（`mWaitsForAudit`），从其第一条记录起最多等待 `cAuditWaitSeconds`（120 秒）：ModSecurity 在请求运行时写入其规则的日志行，在请求结束时写入审计记录，否则一个慢请求会变成两个事件；审计记录到达后，访问日志行还有 `cAfterAuditSeconds`（2 秒）的额外时间。
4. **事件**（`ApacheModule.mBuildEvent`）：字段依次从访问记录、审计记录、错误记录中选取；vhost 取自 `%v`，没有它时取自审计记录中的 Host 请求头和本地端口（`mVhostName`）；如果访问日志行只有整秒，则采用审计记录的时间；`fSummarize` 给出规则、类别、分数、阈值和截获情况；所采取的动作和 `mAssess` 决定检测结果。
5. **规则、富化、诊断和健康**：`rules/` 中的 YAML 规则对每个事件运行（核心引擎）；`mEnrich` 添加该 IP 的上下文；`fRunDoctor` 检查前提条件并描述日志，不更改任何内容；`mHealth` 监控 ModSecurity 和真实客户端 IP。该模块没有配置选项：localSIEM 以 root 身份只授予 `localsiem` 对 `/var/log/apache2` 的读取权限。

### 值得了解的设计决策

- **没有自己的安装程序**：模块只能从 localSIEM 的 Web 界面安装（模块 › 可安装）、更新（模块 › 已安装 中的**更新**）和卸载（**卸载**），Web 界面会下载本仓库，并用 `backend/core/catalog.py` 安装模块（安全解压、一次只进行一个安装、以原子方式替换目录）。需要 root 的操作（对 `read_paths` 的读取权限）由 localSIEM 完成：安装后（以及更改了 `read_paths` 的更新后），Web 界面会显示需要以 root 身份运行的命令。
- **客户的日志只读取**：模块从不写入其监控的服务的日志，也从不轮转、截断、移动或删除它们，从不更改其格式；apache2 模块也从不更改 Apache 或 ModSecurity 配置（它没有 `setup_option`）。如果服务器以自己的格式写入日志（自定义的 `LogFormat`、`mod_remoteip` 提供的客户端 IP），模块会进行适配：`AccessFormat` 根据每个访问日志的 `LogFormat` 构建其解析器，`fCanPair` / `Correlator.mPair` 合并没有 `UNIQUE_ID` 的行。诊断只描述日志以及 localSIEM 能或不能从中读取的内容：检查项 `log_format`、`log_format_without_data`、`remoteip`、`audit_log` 和 `sanitise` 没有 `fix`；只有非日志的内容（ModSecurity、CRS、`SecRuleEngine`、`mod_unique_id`、`localsiem` 的读取权限）才附带修复。`--configure-apache` 已在 1.3.0 版本中移除；`localsiem_combined` 仍保留在 `dKnownFormats` 中，供已在写入该格式的服务器使用，localSIEM 的安装程序会删除旧版本写入的 `localsiem.conf`（`--uninstall`、`--reinstall`）。
- 审计日志的 **K 部分**（`matched_rules`）和 **E 部分**（响应体）从不存储。请求头和请求体只保留在已脱敏的原始记录中；请求详情会重建它们（`fAuditDisplay`）。全文索引获得的是精简文本（`search`：请求行、主机、用户代理以及每条规则的 ID、消息和数据）。
- **原始文本由脱敏后的部分重建**：原始审计记录可能包含密码和 cookie。
- **Web 界面和工具创建的模块没有存储**（`WebContext.mModule` 和 `manage.py` 中的 `pStorage` 为 `None`）：构造函数以及它们调用的钩子不得使用存储。
- **状态保存在事件数据库中**：`apache.first_start`（学习天数）、`apache.health`（已报告过的内容，这样重启时不会重复报告）和 `apache2.doctor`（由采集器写入）。前两者以及来源键 `apache:<kind>:<real path>` 都保留了模块在改名为 apache2 之前的名称：曾经装有 `apache` 模块的服务器会保留其学习天数、健康记忆和读取位置（如果来源键改变，所有小于 5 MiB 的日志都会从头重新读取）。健康记忆中的时间采用项目的原生格式（`2026-10-29@13-59-59.723`，UTC）；旧版本保存的以纪元秒表示的状态会在加载时转换。
- **路径安全**：`mIsNewPhp` 拒绝 `..` 并保持在 DocumentRoot 之内；`fReadConcurrentEntry` 保持在 `SecAuditLogStorageDir` 之内，最多读取 8 MiB；关联器最多保留 50 000 个待处理事务。

### privesc 模块的工作原理

问题不在于«有人运行了 `whoami` 吗？»（管理员每天都这么做），而在于«这个会话是否正走在提权的路径上，它是否已经得手？»。模块将两个来源转换为含义统一的事件（`vhost` 为用户本人，`method` 为类型，`uri` 为命令，`path` 为程序或文件，`ip` 为 SSH 地址，`score` 为该会话的不同侦察命令数），在事件上计算标志，并让 YAML 规则决定哪些内容发送到 SOC。

1. **发现**（`discovery.py`）：`fDiscoverSources` 返回审计日志（`fAuditLogPath`：设置项、`auditd.conf` 的 `log_file`、`/var/log/audit/audit.log`；在 auditd 正在运行而 `localsiem` 尚无法读取时也会返回，以便核心报告这一情况），并在 `syslog_mode` 要求时返回 syslog（`fSyslogPath`）（`auto`：auditd 未运行、其日志不可读或已安装 snoopy）。它还会收集诊断所需的信息：容器（`fContainer`，无需 root 即可读取：`/run/systemd/container`、`/run/.containerenv`、`/.dockerenv`、`/proc/self/cgroup`、`systemd-detect-virt`）、auditd 二进制文件和 pid、snoopy、每个日志是否可读（`fReadState`：`readable`、`unreadable` 或 `missing`），以及 1.0.0 版本留下的文件（`fLegacyLeftovers`）。`Accounts` 在 `/etc/passwd`、`/etc/group` 和 `UID_MIN` 发生变化时重新读取它们，并将 uid 分类为 `root`、`admin`（`admin_groups` 的成员）、`user` 或 `service`。
2. **解析**（`parsers.py`）：`fParseAuditLine` 读取 `type=... msg=audit(<time>:<serial>): k=v ...`、用户空间部分 `msg='...'`、`\x1d` 之后的富化部分，合并 `EXECVE` 的参数（包括拆分为 `aN[i]` 片段的参数），解码十六进制值（`proctitle`、`cmd`、`cwd`、`name`、`exe`、`aN`...），并**根据解码和脱敏后的值重建原始文本**（否则密码的十六进制形式会保留密码）；`search` 获得解码后的命令。`fParseSyslogLine` 读取 ISO 和传统时间戳（带或不带 busybox 的 `facility.priority`），`fParseSyslogMessage` 能理解 snoopy（其 2.4 和 2.5 的默认格式，包括 `uid:alice(1000)/root(0)`，以及 1.0.0 版本设置的格式）、sudo、su（util-linux 和 busybox）、pkexec、doas、`pam_unix` 和 sshd。`fMaskCommand` 在核心的脱敏器之前对命令行中的密码进行脱敏。
3. **关联**（`correlate.py`）：具有相同序列号的审计记录组成一个事务，在 `EOE` 时到期，单条记录的用户空间类型（`USER_*`、`CRED_*`、`DAEMON_*`...）立即到期，或者在 2 秒内没有新记录后到期；最多 50 000 个待处理事务。syslog 行立即到期。
4. **事件**（`PrivescModule.mBuildEvent`）：`mAuditEvent` 按类型分派：`EXECVE` → `mAuditExec`（程序的 setuid 位取自 `PATH` 记录或 `stat`；当 euid 为 0、真实 uid 不为 0 且程序不是 setuid 时为 `suid_escape`；从 `BPRM_FCAPS` 获得的 capabilities；`root_without_door`；当一个 shell 以 root 身份运行且由非 root 用户的解释器启动时为 `parent_interpreter`；父进程取自进程内存）；`USER_*`/`LOGIN` → `mAuditUser`（会话开始、SSH 地址、途径：sudo、su、pkexec、doas、run0、systemd 的 `USER_START`/`USER_CMD`；失败）；`CONFIG_CHANGE`（`audit_disabled`，任何规则被移除时为 `audit_rule_removed`）、`DAEMON_*`（发送者不是 pid 1 时为 `auditd_stopped_manually`）、`ANOM_ABEND`（`crash_suspicious`）；其他任何 `SYSCALL` → `mAuditSyscall`，它按系统调用（`fSyscallName`：富化格式中的名称，或其架构表中的编号）、参数及其 `PATH` 记录对其分类，从不依据规则的键：`denied`（某人的 open、exec 或 truncate 因 `EACCES`/`EPERM` 失败）、`kmod`、`ptrace`（`PTRACE_ATTACH`/`PTRACE_SEIZE` 时为 `ptrace_attach`）、`chmod`（带有 setuid 或 setgid 位的模式，不针对目录，附带 `writer_allowed`）和 `file`（`lSensitivePaths` 中某个路径的变更，附带 `sensitive_group` 和 `writer_allowed`；只有在无法解析任何路径时，才通过 `dKeyHints` 使用键）。`mSyslogEvent` 将 snoopy 处理为 `exec`（`suid_escape` 取自 `stat`；没有 `filename` 时，程序取自命令的第一个词），并处理 sudo、su、pkexec、doas、login 和 pam。每条命令都会经过 `mAnalyzeCommand`：侦察标记（`fReconToken`）以及窗口内该会话的不同标记（`recon_burst`、`recon_massive`、`score`）、由 shell 运行的下载（`cDownloadOnelinerRegex`，或同一父进程下载工具后接 shell）、`compile_in_tmp`、会话的最近命令，以及（对于服务账户）将程序（`fProgramKey`）与其历史进行比对（核心的 `mPathFirstSeen`，在 `learning_days` 之后：`new_program`）。`ignored` 标记被忽略的用户。
5. **规则、富化、诊断和健康**：`rules/` 中的 35 条 YAML 规则决定每个检测结果（`mDetectionFromSignal`）；`mEnrich` 添加会话的上下文；`fRunDoctor` 描述 auditd 及其规则记录的内容、syslog、snoopy、模块能看到和看不到的内容、1.0.0 版本的文件以及攻击面；`mHealth` 报告 auditd 已停止、敏感文件可写以及 setuid 程序扫描的结果（`SurfaceScanner`，一个线程）。该模块没有配置选项，也不更改服务器上的任何内容。

### privesc 模块的设计决策

- **两个来源，统一含义。** 用户无法规避 auditd，但它不能在容器内运行（内核审计不支持命名空间隔离）；snoopy 在容器中能看到每个程序，但需要 syslog；仅有 syslog 时只能看到 sudo、su、pkexec 和 doas。任何来源都看不到 shell 的内置命令。规则匹配的是列和标志，从不匹配来源，因此可以在不改动规则的情况下添加来源。同一命令被看到两次只会产生一条告警：核心按模块、用户、IP、类别和严重级别对检测结果进行分组。
- **看突发，而不是单条命令。** 侦察以每类问题一个标记的方式表示（`whoami`、`read:/etc/passwd`、`find:-perm:`...），只有一个会话在一个窗口内不同标记的数量才会触发告警，管理员的阈值更高，脚本还有第三个阈值。这些阈值是设置项，而不是规则阈值：规则只匹配 `recon_burst` / `recon_massive`。
- **最重要的是成功与否。** `suid_escape`（一个非 setuid 程序以 euid 0 和非 0 的真实 uid 运行）和 `root_without_door`（在一个已看到其开始、且从未经过 sudo、su、pkexec 或 doas 的会话中出现 root）是提权成功的两个严重迹象，几乎没有误报。从不标记未看到其开始的会话（在模块之前就已打开的会话、闲置一天后被遗忘的会话）。
- **会话在重启后仍然保留。** `SessionTracker` 将每个会话的开始、SSH 地址和途径保存在状态 `privesc.sessions` 中（最多每分钟保存一次）；侦察标记和最近的命令保留在内存中。闲置一天的会话会被丢弃。
- **只使用服务器已有的内容。** 模块从不安装任何东西，也从不更改 `/opt/localsiem` 之外的任何内容：它不加载审计规则，不改动 `auditd.conf` 和 `snoopy.ini`，也不安装钩子。1.0.0 版本做过这些事（`--configure-privesc`：带有键 `lsiem_*` 的审计规则、`log_group = adm`、bash 钩子、snoopy 的格式）；1.1.0 版本将其移除。因此，审计记录按其类型、系统调用和路径进行分类，所以任何审计规则都可以工作（服务器自己的规则、STIG 示例规则，或 1.0.0 留下的 `lsiem_*` 规则）；键保存在 `fields.key` 中供搜索使用，只作为提示（`dKeyHints`）。当日志中没有富化的名称时，系统调用编号按架构读取（`dSyscallTables`：x86_64、i386，以及 aarch64、riscv64 和 loongarch64 的通用表）。诊断描述服务器规则记录了什么、没有记录什么；其 `fix` 只是要安装的软件包或 `localsiem` 的读取权限。
- **可读就是真正可读。** 满足前提条件的是一个存在且 `localsiem` 能够打开的来源（`fReadState`），而不是某个已安装的程序：首次安装时日志通常属于 root，因此在运行供 root 使用的命令（`manage.py setup-modules`）并点击**重新配置**之前，模块保持停用。
- **软件包管理器不是攻击者。** 由账户和软件包工具（`sAllowedWriters`）或已知祖先进程为软件包管理器的程序所做的敏感文件和 setuid 位变更会设置 `writer_allowed`，规则会跳过它们。
- **扫描从不阻塞采集器。** `SurfaceScanner` 在自己的线程中遍历 `scan_paths`，不跨出每个路径所在的文件系统，跳过 `/proc`、`/sys` 和容器的目录，最多 300 万个文件或 15 分钟；结果就绪后由 `mHealth` 获取。第一次扫描作为基准；之后的扫描报告新出现的内容。
- **Web 界面和工具创建的模块没有存储**：`mDiscover`、`mDoctor` 和 `mRequirements` 从不使用存储，`mAnalyzeCommand` 只有在 `mPathFirstSeen` 存在时才调用它。
- **状态保存在事件数据库中**：`privesc.first_start`（学习天数）、`privesc.sessions`、`privesc.surface`（扫描和诊断的基准）、`privesc.health`（已报告过的内容、auditd 是否在运行）和 `privesc.doctor`（由采集器写入）。服务账户已见过的程序是 `seen_paths` 中的行，其 vhost 为 `privesc:<account>`。`privesc.health`（健康记忆）和 `privesc.sessions`（每个会话的 `last`）中的时间采用项目的原生格式（`2026-10-29@13-59-59.723`，UTC）；旧版本保存的以纪元秒表示的状态会在加载时转换。

<a id="modules"></a>
## 2. 模块地图

| 模块 | 路径 | 职责 | 依赖 | 使用方 |
|---|---|---|---|---|
| 清单 | [mod-apache2/module.json](../mod-apache2/module.json) | id、版本、最低核心版本、入口、读取路径、设置（无配置选项） | — | 注册表、Web 界面、`manage.py` |
| Apache 模块 | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`：钩子、所采取的动作、严重级别、检测结果、规则函数、富化、健康检查 | correlate、discovery、doctor、modsec、parsers；核心的 `masking`、`module`、`query`、`timeutil`、`health`；PyYAML | 采集器、Web 界面、`manage.py` |
| 发现 | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig`（配置解析器）、来源和被跳过的日志、DocumentRoot | logformat（`dKnownFormats`） | module、doctor |
| 诊断 | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | 前提条件检查；描述日志（格式、审计日志、脱敏），不建议更改它们 | discovery | module |
| 访问日志格式 | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | 将 `LogFormat` 转换为正则表达式、将时间转换为 UTC、请求行 | 核心的 `timeutil` | parsers、discovery |
| 解析器 | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access、error、audit（JSON、原生、并发）、`AuditFramer`、`fAuditDisplay` | logformat、modsec；核心的 `masking`、`timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | 消息、类别、CRS 范围、分数、截获 | — | parsers、module |
| 关联 | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`、不依赖它的配对（`mPair`）、窗口、水位线 | 核心的 `timeutil` | module（采集器） |
| 严重级别表 | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | ModSecurity 检测结果的严重级别 | — | module（`fLoadSeverityTable`） |
| 规则 | [mod-apache2/rules/](../mod-apache2/rules/) | 六条 YAML 规则 | 核心规则引擎、`mIsNewPhp` | 采集器（`RulesEngine`）、Web 界面（`fRules`） |
| 文本 | [mod-apache2/locales/](../mod-apache2/locales/) | 名称、摘要、设置的标签和帮助、选项 | — | Web 界面 |
| privesc：清单 | [mod-privesc/module.json](../mod-privesc/module.json) | id、版本、最低核心版本、入口、读取路径、13 项设置（无配置选项） | — | 注册表、Web 界面、`manage.py` |
| privesc：模块 | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`：钩子、两个来源的事件、审计记录的分类（敏感路径、按架构区分的系统调用）、标志、规则的检测结果、富化、健康检查、扫描结果 | commands、correlate、discovery、doctor、parsers、surface；核心的 `masking`、`module`、`query`、`timeutil`、`health`；PyYAML | 采集器、Web 界面、`manage.py` |
| privesc：发现 | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | 来源、容器、auditd、snoopy、syslog、每个日志是否可读、1.0.0 版本留下的文件、`Accounts`（用户、组、账户类型） | — | module、doctor |
| privesc：解析器 | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | 审计记录（十六进制、`msg='...'`、富化格式）、syslog 行（常见格式的 snoopy、sudo、su、pkexec、doas、pam、sshd）、命令行脱敏 | 核心的 `masking`、`timeutil` | module |
| privesc：关联 | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | 审计记录按序列号合并（EOE、用户空间记录、2 秒）；syslog 行立即处理 | — | module（采集器） |
| privesc：命令 | [mod-privesc/commands.py](../mod-privesc/commands.py) | 侦察标记、服务账户的程序、shell、解释器、下载工具、途径、编译器；`SessionTracker` | 核心的 `timeutil` | module |
| privesc：攻击面 | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner`（setuid、setgid、capabilities）、GTFOBins、可写的敏感文件、特权组 | — | module、doctor |
| privesc：诊断 | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | 描述 auditd、其日志及其规则记录的内容、syslog、snoopy、模块能看到的内容、1.0.0 版本的文件和攻击面（修复：只有软件包和读取权限）；前提条件 `command_source`（任意可读的来源） | discovery、surface；核心的 `timeutil` | module |
| privesc：规则 | [mod-privesc/rules/](../mod-privesc/rules/) | 35 条 YAML 规则 | 核心规则引擎 | 采集器（`RulesEngine`）、Web 界面（`fRules`） |
| privesc：严重级别表 | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | 模块构建的检测结果（扫描、敏感文件）的严重级别 | — | module（`fLoadSeverityTable`） |
| privesc：文本 | [mod-privesc/locales/](../mod-privesc/locales/) | 名称、摘要、设置的标签和帮助、选项 | — | Web 界面 |
| 核心：接口 | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`、`LineFramer` | 注册表 | 模块 |
| 核心：注册表 | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | 查找、检查和加载模块；设置的默认值和验证 | `config` | 采集器、Web 界面、`manage.py`、`backend/core/catalog.py` |
| 核心：Web 界面 | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py)、[backend/web/app.py](../../localSIEM/backend/web/app.py)、[frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | 模块页面（已安装、可安装、单个模块的页面）和 API | 注册表、catalog、规则 | 浏览器 |
| 核心：catalog | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | 下载并安全解压仓库、列出每个模块的动作（`install`、`update`、`incompatible`、`invalid`...）和 `newer`、以原子方式安装或更新（`previous`、`access_changed`）、卸载、供 root 运行的命令：模块 › 可安装 以及 模块 › 已安装 中的**更新** / **卸载**，这是安装模块的唯一方式 | 注册表 | Web 界面 |

<a id="symbols"></a>
## 3. 关键符号

| 符号 | 文件:行 | 作用 |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | apache2 模块（`vName = "apache2"`） |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | 用 `severity.yaml` 覆盖内置默认值 |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | 解析配置、来源、被跳过的日志、DocumentRoot |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | 异常阈值：设置项、CRS 或 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | 按来源类型将单元转换为记录 |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | 将事务转换为事件：字段、所采取的动作、分数、检测结果 |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | 将 Host 请求头或 ModSecurity 主机名映射为 Apache 所选的 vhost（即 `%v` 记录的内容） |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | 发送到 SOC 的内容的严重级别、规则名称、描述和详细信息 |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | 将 YAML 规则的信号转换为检测结果 |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | 规则函数 `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | 为告警提供该 IP 的上下文（最近一小时） |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity 未加载或为 Off；缺少真实客户端 IP |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | 用于请求详情的请求头和请求体 |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache 和 ModSecurity 2：模块启用前需要具备的条件 |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Apache 配置的解析器 |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | 读取的指令（日志、vhost、模块、ModSecurity） |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | 根据请求的 Host 请求头以及本地地址和端口，按 Apache 的选择方式确定其 vhost |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | 固定的来源键；要读取的来源和被跳过的来源 |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | 前提条件检查 `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | 访问日志格式能否在没有 `UNIQUE_ID` 的情况下合并（客户端 IP、时间、请求行、状态码） |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | 诊断中的 `apache_config` 和 `modsecurity` 检查，或者在没有 Apache 时将两者都作为错误，并附带安装它们的命令 |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | 将 `LogFormat` 转换为正则表达式；已知别名 |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | 将 access.log 行转换为记录 |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | error.log 行：ModSecurity、数据库、PHP、崩溃 |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | 跨多行的原生记录；安全的提交位置 |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | JSON 或原生审计记录；脱敏、原始文本和索引文本 |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | 已存储记录的详情；并发条目的文件 |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | 单条 ModSecurity 消息；规则、类别、分数、阈值、截获 |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd`（[:148](../mod-apache2/correlate.py#L148)）、`mPair`（[:207](../mod-apache2/correlate.py#L207)）、`mDue`（[:248](../mod-apache2/correlate.py#L248)）、`mWaitsForAudit`（[:271](../mod-apache2/correlate.py#L271)）、`mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | privesc 模块（`vName = "privesc"`） |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | 按来源将事务转换为事件；`ignored`；丢弃空字段（`fCleanFields` 保留 0） |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | 会话的侦察、由 shell 运行的下载、在 `/tmp` 中编译、最近的命令、服务账户的新程序 |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | 按类型处理审计事务；运行的程序（`suid_escape`、`root_without_door`、`parent_interpreter`、capabilities）；登录、途径和失败 |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | 按名称、参数和路径处理其他任何系统调用：`denied`、`kmod`、`ptrace`、`chmod`、`file`（`sensitive_group`）或 `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | 系统调用的名称（富化名称，或按架构查到的编号）；敏感路径的组（`lSensitivePaths`） |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy、sudo、su、pkexec、doas、登录 |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | 敏感文件的写入者或其已知祖先进程是账户或软件包工具 |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | 将规则的信号转换为检测结果；为告警提供会话的上下文 |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | 保存会话、auditd 已停止、敏感文件、启动扫描；新的 setuid 程序和 capabilities |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | 来源、被跳过的来源以及诊断所需的信息；日志是否可读；1.0.0 版本留下的文件 |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | 容器类型（无需 root）；正在运行的 auditd 的 pid |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | uid 名称、组、`UID_MIN`、账户类型（`mAccountType`） |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | 两个来源的记录 |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | 先对命令行中的密码脱敏，再交给核心的脱敏器 |
| `Correlator`（privesc） | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | 审计记录按序列号合并；其他记录立即处理 |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | 命令的侦察标记；服务账户的程序；所输入命令的各个词 |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | 会话（开始、IP、途径、侦察、最近的命令）、进程、下载；`mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | 在线程中扫描 setuid、setgid 和 capabilities；可被他人写入的敏感文件 |
| `fRunDoctor` / `fRequirementChecks`（privesc） | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | 诊断的检查（仅作描述；只为软件包和读取权限提供修复）；前提条件 `command_source`：任意可读的来源 |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | 模块的接口；每行一个单元 |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | 检查 `module.json`，读取文本 |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | 已安装的模块（`/opt/localsiem/modules/*`）；实例和错误 |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | 命名空间包 `localsiem_modules`；导入并检查入口 |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | 以默认值为基础叠加已保存的值；验证保存的内容 |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`；`POST /api/admin/module-catalog/{name}`（安装或更新；首次安装时不满足前提条件的模块会被停用：`fFirstInstallation`）；`DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | 在已安装副本旁安装或更新模块，并通过重命名进行替换（`previous`、`access_changed`）；仓库中的模块及其 `installed`、`newer` 和动作 |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | 卸载模块（重命名后删除）；供 root 运行的命令（`manage.py setup-modules`） |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | 可安装标签页（只有未安装的模块、**安装**及其对话框）；已安装页面中某一行的新版本提示；**更新**（确认、相同的 `POST`，仅在 `access_changed` 或采集器没有响应时弹出对话框） |

<a id="flows"></a>
## 4. 主要调用路径

**采集器启动 → 注册表 → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests`（`/opt/localsiem/modules/*`）→ `fReadManifest`（id = 目录名、entry、settings、`core` ≤ `cVersion`、`fReadTexts`）→ `fCreateModule` → `fLoadClass`（`fRegisterPackage`、`import localsiem_modules.apache2.module`、`Module` 的子类、`vName == id`）→ `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules`（`mRulesPath`、`mRuleFunctions`、覆盖项 `rules.<id>` → `RulesEngine.mLoad`）→ `Collector.mDiscover`（`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`；每个来源一个 `FileTailer` 和 `mCreateFramer`）→ 待处理的记录送回关联器 → `mPublishDoctor`（`mDoctor` → `fRunDoctor` → 状态 `apache2.doctor`）。

**读取一行 → 检测结果**

1. `Collector.mReadSources` → `FileTailer.mPoll` → 分帧器 `mFeed`（`LineFramer`，或 `AuditFramer`，其 `mSafeCommit` 会将位置保持在未完成的记录之前）→ `ApacheModule.mParse`（`AccessParser.mParse`、`fParseErrorLine`，或 `fReadConcurrentEntry` + `fParseAuditRecord` 和 `mObserveAudit`）→ 在同一个事务中存储记录和位置 → `Correlator.mAdd`。
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent`（`fSummarize`、所采取的动作、`mAssess`、针对 2xx `.php` 的 `mPathFirstSeen`）→ `RulesEngine.mEvaluate`（YAML 规则；`{function: apache2.new_php}` → `mIsNewPhp`）→ `mSaveEvents` → 对每个检测结果调用 `mDetect`，对每个信号调用 `mDetectionFromSignal` → `Grouper.mAdd`。
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich`（`mGetIpContext`）→ `fBuildAlert` → SOC 队列。

**管理员保存设置 → 采集器重新加载**

`modules.js fBuildSettings`（提交）→ `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings`（422 `invalid_setting:<key>` 或 `<key>.<field>`）→ `fSaveSettings`（`settings.json`、`modules.apache2`）→ `WebContext.mApplySettings` → 采集器套接字 `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings`（`ApacheModule.mReload`、`mLoadRules`、`mDiscover`、`mPublishDoctor`、`mPublishState`）。开关以同样的方式发送 `{enabled}`（在缺少模块的某项前提条件时启用：422 `requirements_missing`），规则表发送 `{rules}`（`fCleanRules` → `rules.<id>`：`enabled`、`severity`、`threshold` 或 `first_threshold`、`window`）。如果套接字没有响应，采集器仍会在下一个周期发现新的 `settings.json`。

**从 Web 界面安装模块**（安装模块的唯一方式）

`modules.js fCatalogPanel`（模块 › 可安装）→ **检查仓库** → `GET /api/admin/module-catalog`（`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`：仓库中的每个 `mod-<name>/` 目录，附带 `installed`、`newer` 和 `action`）→ 只列出 `installed` 为 null 的项 → **前提条件**（`fShowRequirements` → `fRequirementsBody`：模块针对服务器系统（响应中的 `system`）的 `install_requirements`，分为以 root 身份和使用 `sudo` 两种形式，以及其 locales 中的 `install_requirements.*` 说明；不运行任何命令）→ **安装** → `POST /api/admin/module-catalog/{name}`（`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`：`mod-apache2/` → `/opt/localsiem/modules/apache2/`，`previous` 为 null，`access_changed` 为 true）→ `WebContext.mReloadModules` → `fFirstInstallation`（缺少某项前提条件且从未保存过 `modules.<name>.enabled`：`enabled = false`）→ 采集器 `restart` → `fCreateModules` 加载该模块 → «<模块> 已安装»对话框显示供 root 运行的命令（`fRootCommand`：`manage.py setup-modules`，对 `read_paths` 的读取权限），或者在缺少前提条件时显示未满足的检查。

**从 Web 界面更新模块**

打开 模块 › 已安装 → `fCheckRepository` → `modules.js` 的 `fFetchCatalog(false)`（`GET /api/admin/module-catalog` 的最近一次响应，重用 600 秒；安装、更新或卸载模块后会丢弃它）→ 带有 `newer` 且 `action` 为 `update` 或 `incompatible` 的项 → 该行上的 `fUpdateNotice`（仅当已安装版本就是被比较的版本时）→ **更新** → `fUpdate` → 确认 → `POST /api/admin/module-catalog/{name}`（同样是 `fInstallFromCatalog` → `fInstall`：新副本替换已安装的副本，`previous` 为旧版本，`access_changed` 表示 `read_paths` 是否改变；没有 `fFirstInstallation`，因此 `enabled` 和设置保持不变）→ 采集器 `restart` → 仅当 `access_changed`（供 root 运行的命令）或采集器没有响应时才弹出对话框。

**从 Web 界面卸载模块**

**卸载**（模块 › 已安装 中的行或模块页面）→ `fUninstallButton` → 确认 → `DELETE /api/admin/modules/{name}`（`fUninstallModule` → `fRemove` → `InstallLock` → 将 `/opt/localsiem/modules/<name>/` 重命名到一个暂存目录，并在那里删除）→ `WebContext.mReloadModules` → 采集器 `restart`。`modules.<name>` 及其规则的覆盖项保留在 `settings.json` 中，root 授予的读取权限也会保留。

**首次安装时没有 Apache 或 ModSecurity → 重新配置**（localSIEM 2.2.0 或更高版本）

在 Web 界面中安装 → `fInstall`（首次安装）→ 根据已安装副本创建的模块（存储为 `None`）→ `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks`（有 Apache 时：`fRunDoctor` → `apache_config`、`modsecurity`；没有时，两者都作为错误）→ 存在错误且从未保存过 `modules.apache2.enabled` → `modules.apache2.enabled = false`（«已停用»，开关被锁定，页面上显示前提条件）。之后，在安装了 Apache 和 ModSecurity 后：**重新配置** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → 已满足 → 开关解锁并显示 root 命令（对 `read_paths` 的读取权限；apache2 没有 `setup_option`）→ 管理员启用模块 → 采集器重新加载 → `mDiscover` → `mPublishDoctor`。

**Web 界面中的请求详情和诊断**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`。**重新发现并运行诊断** → `POST /api/admin/modules/apache2/doctor` → 采集器 `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`。

**健康检查**

`Collector.mCycle`（每 60 秒）→ `mCheckHealth` → `ApacheModule.mHealth`（最多每 300 秒一次；`ApacheConfig.mParse`、`mCountRecentEvents`）→ `fHealthDetection` → `mDetect`。

**privesc：运行一条命令 → 检测结果**

1. auditd 以同一序列号写入 `SYSCALL`、`EXECVE`、`CWD`、`PATH`、`PROCTITLE`、`EOE` → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine`（解码十六进制、`fMaskCommand`、重建原始文本）→ `Correlator.mAdd`（键为 `audit:<time>:<serial>`，在 `EOE` 时到期）。
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec`（`suid_escape`、`BPRM_FCAPS`、来自 `SessionTracker.mGet` 的 `root_without_door`、`mRememberProcess`）→ `mAnalyzeCommand`（`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`；`cDownloadOnelinerRegex`、`mDownload`/`mRecentDownload`；`fCompileInTemporary`；`mCommand`；服务账户：`fProgramKey` → `mPathFirstSeen` → `new_program`）→ `fCleanFields`。
3. `RulesEngine.mEvaluate`（`mod-privesc/rules/` 中的规则）→ `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich`（会话：最近 20 条命令）→ `fBuildAlert` → SOC 队列。

使用 snoopy 时，同一条命令还会以 syslog 行的形式到达：`fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand`（会话 `snoopy:<uid>:<sid>`）。

**privesc：会话和途径**

`LOGIN`（分配了 auid 和 ses）或 sshd、login 的 `USER_LOGIN`/`USER_START` → `mAuditUser` → `SessionTracker.mStart`（用户、SSH 地址）。sudo、su、pkexec、doas、run0 或 systemd 结果为成功的 `USER_START`/`USER_CMD` → `SessionTracker.mDoor`。该会话之后 uid 和 euid 都为 0 的 `EXECVE` → 只有在看到了会话开始且没有途径时才为 `root_without_door`。`mHealth` 最多每分钟将 `SessionTracker.mExport` 保存到 `privesc.sessions` 中一次；`mStart` 加载它（`mImport`）。

**privesc：服务器审计规则记录的系统调用**

auditd 写入 `SYSCALL`（包含 `arch`、`syscall`、`a0`-`a3`、`success`、`exit` 以及记录它的任意规则的键）、`CWD`、`PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`：`fSyscallName` → 带有登录 uid、因 `EACCES`/`EPERM` 失败的 open/exec/truncate → `denied`；`init_module`/`finit_module`/`delete_module` → `kmod`；`ptrace` → `ptrace`；模式中带有 `S_ISUID`/`S_ISGID` 且不针对目录的 `chmod`/`fchmod`/`fchmodat`/`fchmodat2` → `chmod`（`mWriterAllowed`）；对 `lSensitivePaths` 中某个路径的更改（`sChangeSyscalls` 中的调用、带写标志的 open、带有 `CREATE`/`DELETE` 的 `PATH`）→ 带有 `sensitive_group` 的 `file`（只有在没有可解析的路径时才使用 `dKeyHints`）和 `mWriterAllowed`；其他任何情况 → `syscall`。`mBuildEvent` 会为诊断记住每种类型的时间（`dRuntime["audit_kinds"]`）。

**privesc：攻击面扫描**

`mHealth`（每 300 秒，启动五分钟后，每隔 `surface_scan_hours`）→ `SurfaceScanner.mStart`（线程：对 `scan_paths` 执行 `os.walk`、`os.lstat`、`os.getxattr("security.capability")` → `fCapabilities`）→ 下一次 `mHealth` → `mSurfaceResult`（`SurfaceScanner.mTake`，与 `privesc.surface` 比对：新的 setuid/setgid → `new_setuid*`，新的 capabilities → `new_capabilities`）→ `mModuleDetection` → `mDetect`；结果保存在 `privesc.surface` 中，并由 `fSurfaceChecks` 显示。每小时 `fCheckSensitiveFiles` → `sensitive_file_writable`。

**privesc：前提条件和重新配置**

`fInstall`（首次安装）或**重新配置** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())`（`fContainer`、`fAuditdPid`、`fAuditLogPath` → `fReadState`；除非 `syslog_mode` 为 `never`，否则 `fSyslogPath` → `fReadState`；`fSnoopyInstalled`）→ 有可读来源：`command_source` 为 ok（不可读的来源作为警告）；来源存在但无法读取：`audit_log` 或 `syslog` 报错误，并附带读取权限（`manage.py setup-modules` 或 `setfacl`）；什么都没有：`command_source` 报错误，并附带需要安装的软件包。只要存在错误，模块就保持停用。

<a id="routes"></a>
## 5. 入口点

| 入口点 | 处理程序 | 文件 |
|---|---|---|
| `module.json` 的 `"entry": "module:ApacheModule"` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine`（核心） | [mod-apache2/rules/](../mod-apache2/rules/) |
| 规则函数 `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Web：模块 › 可安装，安装模块的唯一方式（`GET /api/admin/module-catalog`、`POST /api/admin/module-catalog/{name}`） | `fGetCatalog`、`fInstallFromCatalog`；视图 `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py)、[frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Web：模块 › 已安装 中某一行的**更新**（相同的 `GET`，浏览器重用 10 分钟，以及相同的 `POST`） | `fCheckRepository`、`fUpdateNotice`、`fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js)、[backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Web：**卸载**（`DELETE /api/admin/modules/{name}`） | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py)、[backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `module.json` 的 `read_paths` | `manage.py read-paths`：localSIEM 以 root 身份允许 `localsiem` 读取的目录（`fRootCommand` 的命令） | [backend/manage.py](../../localSIEM/backend/manage.py)、[backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain`（`fModules`） | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`、`mSkipped`、`mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | 每个清单的 `read_paths` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`；`/admin/dashboard/modules/`（302 到 `installed/`）、`/admin/dashboard/modules/installed/`、`/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`；视图 `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py)、[frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/`（旧地址 `/admin/dashboard/modules/apache2/` 以 301 跳转到这里） | `fAdminModule`（301 由 `fAdminModulesSection` 处理）；视图 `LocalsiemViews.module` | 同上 |
| `GET /api/modules` | `fModules`（所有已登录用户可见的状态） | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule`（设置、值、来源、诊断、规则） | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule`（`enabled`、`settings`、`rules`） | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure`（**重新配置**，localSIEM 2.2.0 或更高版本） | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py)、[mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `mod-privesc/module.json` 的 `"entry": "module:PrivescModule"` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine`（核心） | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`、`GET`/`POST /api/admin/modules/privesc`、`.../privesc/doctor`、`.../privesc/reconfigure` | `fAdminModule`、`fModule`、`fSaveModule`、`fRunDoctor`、`mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py)、[mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| 服务器规则产生的审计记录（任意键） | `mAuditEvent` → `mAuditExec`、`mAuditUser`、`mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. 影响分析

| 组件 | 更改后受影响的内容 |
|---|---|
| `module.json` `id` | 必须等于不带 `mod-` 的目录名（即安装目录的名称）以及 `vName`。它是设置（`modules.<id>`）和状态（`<id>.doctor`）的键，也是每个事件的 `module`：重命名会丢失已保存的设置并拆分历史记录。 |
| `module.json` `core` | 将其提高到高于已安装的 localSIEM 版本会使模块无法加载（状态«错误»）；在仓库中，可安装页面会显示«需要 localSIEM X 或更高版本»，已安装页面会显示新版本但不提供**更新**。 |
| `module.json` `entry` | 必须指向 `Module` 的子类；错误的值会导致加载错误。 |
| `module.json` `default_enabled` | 管理员从未做出决定的服务器上的启用/停用状态（如果首次安装时缺少前提条件，则为停用）。 |
| `module.json` `read_paths` | localSIEM 以 root 身份授予的读取权限（`manage.py read-paths`）：缺少某个目录会导致诊断和状态中出现权限错误。新版本中的更改会使 Web 界面在**更新**后再次显示供 root 运行的命令（`access_changed`）。 |
| `module.json` `install_requirements` | 可安装页面的前提条件对话框（`modules.js` 的 `fRequirementsBody`）。错误的值（`debian` 和 `alpine` 以外的系统、空列表或超过 20 条命令、包含 shell 运算符或换行符的命令）会使模块无效（核心的 `fCheckInstallRequirements`）：它既不会被安装也不会被加载。 |
| `module.json` `setup_option` | 没有影响：核心会忽略它（自 apache2 1.3.0 和 privesc 1.1.0 起，没有任何模块使用它）。 |
| 仓库顶层带有 `module.json` 的 `mod-<name>/` 目录 | Web 界面的模块目录作为模块 `<name>` 列出的内容：可安装页面显示尚未安装的模块（需要更新版本核心的模块显示为«需要 localSIEM X 或更高版本»，无效的模块显示为«仓库中的模块无效»），而高于已安装版本的 `version` 会使已安装页面提供**更新**。 |
| `module.json` `settings` | 表单、验证和默认值。新的默认值适用于从未保存过该键的服务器。已保存的值不会迁移：重命名的键会丢失其值，类型改变后的旧值会按其保存时的样子传给模块。 |
| `locales/*.json` | 只影响 Web 界面的文本；缺失的文本会回退到 en-US，然后回退到键名。 |
| `parsers.py`（记录字典） | 关联（`correlation`、`fields.client_ip`、`fields.path`）、请求详情、全文索引（`search`、`raw`）、未解析行的健康检查以及隐私。 |
| `logformat.py` `dKnownFormats` | 每个访问日志的解析；`localsiem_combined` 为已在写入该格式的服务器而保留（该模块的 1.2.0 及更早版本添加了它）：不要更改其定义。 |
| `correlate.py` | 每个请求一个事件；核心调用 `mAdd`、`mDue(pNow, pForce, pWatermark)` 和 `mPendingCount`，并在重启后送回仍待处理的记录。没有 `UNIQUE_ID` 时，它按 `client_ip`、`method`、`uri`、`status` 和 `path` 字段配对记录：以不同方式写入这些字段的解析器会破坏配对。等待审计记录（`mWaitsForAudit`）需要 error.log 行的 `modsecurity` 字段和来源 `audit` 的记录。 |
| `modsec.py`（类别、标签、范围） | 告警规则名称（SOC 统计按其分组：请保持稳定）、分组键、`category:` 搜索。 |
| `ApacheModule.mBuildEvent`（事件字典） | 事件表的列、YAML 规则读取的字段（`action`、`status`、`method`、`path`、`crs_matched`、`db_error`...）、搜索和 CSV 导出。 |
| `ApacheModule.mAssess` | 发送到 SOC 的内容及其严重级别；核心的 `GenericAlert` 限制（规则 300 个字符，描述 10 000 个字符）。 |
| `severity.yaml` | 每个 ModSecurity 检测结果的严重级别；严重级别是分组键的一部分，因此更改会产生新的分组。 |
| `rules/*.yaml` | `id` 是覆盖项（`rules.<id>`）和搜索（`rule:localsiem:<id>`）的键：请保持稳定。字段必须存在于事件中；`{function: ...}` 需要 `mRuleFunctions`。 |
| `discovery.py` | 读取哪些日志；`fSourceKey` 是已保存位置的键（新的键会使该文件成为一个新来源，失去其已保存的位置）；web shell 规则所用的 DocumentRoot；诊断。 |
| `doctor.py` | Web 界面和 `manage.py` 中的诊断，以及向客户显示的提示。只有关于非日志内容的检查（ModSecurity、CRS、`SecRuleEngine`、`mod_unique_id`、权限）才可以带有 `fix`；关于日志的检查只描述日志。 |
| `mRequirements` / `fRequirementChecks` | 模块能否启用、在没有 Apache 或 ModSecurity 的情况下首次安装后的«已停用»状态、Web 界面显示的前提条件以及**重新配置**。它们在 Web 界面和 `manage.py` 中以无存储的方式运行，并且每次调用都会解析 Apache 配置：请让它们远离存储和任何耗时操作，并保持 id `apache_config` 和 `modsecurity` 稳定。 |
| privesc：事件列和字段（`mBuildEvent`、`mAnalyzeCommand`） | YAML 规则按名称匹配它们（`recon_burst`、`suid_escape`、`root_without_door`、`sensitive_group`、`writer_allowed`、`ptrace_attach`、`parent_interpreter`、`account_type`、`real_uid`、`argc_zero`...）：重命名字段会悄无声息地使用到它的规则失效。`vhost` 是用户：告警的分组键和 `vhost:` 搜索都依赖于它。 |
| privesc：`fReconToken` | 什么算作侦察以及如何区分不同的命令：更改标记会改变会话达到阈值的速度。 |
| privesc：`SessionTracker` 和途径（`sDoors`） | `root_without_door`：列表中缺少某个途径会使合法的 root 会话变为严重告警；多出一个途径则会掩盖内核漏洞利用。`mExport`/`mImport` 是 `privesc.sessions` 的格式。 |
| privesc：`parsers.py` | 记录的字段（`args`、`command`、`kind`、snoopy 的 `uid`/`euid`）、密码脱敏以及审计记录的原始文本；它能读取的 snoopy 格式（模块从不更改 `snoopy.ini`）。 |
| privesc：审计记录的分类（`lSensitivePaths`、`dSyscallTables`、`sChangeSyscalls`、`dOpenFlagArgument`、`dChmodModeArgument`、`sDeniedSyscalls`、`dKeyHints`） | 哪些记录会成为 `file`、`chmod`、`kmod`、`ptrace` 和 `denied`，从而影响规则 sensitive-file、persistence-file、monitoring-changed、suid-set、kernel-module、ptrace、denied-burst 和 sensitive-denied；错误的系统调用编号会使该架构的记录被错误分类。 |
| privesc：`surface.py` | 扫描的开销（线程、限制）以及诊断和 `mSurfaceResult` 报告的内容；`privesc.surface` 是其基准。 |
| privesc：`mRequirements` / `fRequirementChecks` | 模块能否启用（任意可读的来源）、首次安装时 `localsiem` 尚无法读取日志而导致的«已停用»状态，以及**重新配置**；Web 界面和 `manage.py` 会在无存储的情况下调用它：请保持其快速且无需 root。保持 id `command_source`、`audit_log` 和 `syslog` 不变。 |
| 核心接口（localSIEM 的 `backend/core/module.py`、`registry.py`） | 所有模块：钩子签名的更改、新的必需清单键，或者记录和事件的新契约都会破坏它们；当模块需要新版 localSIEM 时，请提高其 `module.json` 中的 `core`。 |

<a id="extensions"></a>
## 7. 扩展点

### 如何编写新模块

1. **目录**：在本项目的根目录下创建 `mod-<name>/`；`<name>` 即模块的名称，需匹配 `[a-z][a-z0-9_]{1,31}`。`mod-` 前缀只用于目录：`module.json`、类、选项和文本都使用 `<name>`。不要创建 `__init__.py`。
2. **`module.json`**，例如：

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

3. **文本**：为 localSIEM 的 15 种语言各提供一个 `locales/<language>.json`，其中包含 `name`、`summary` 以及每项设置的标签和帮助。有关前提条件的说明放在 `install_requirements` 中（`note` 适用于所有系统，另有 `debian` 和 `alpine`），显示在前提条件对话框中。
4. **代码**：`module.py`，其中包含一个 `Module` 的子类，其 `vName` 为 id。它必须实现 `mParse`、`mCreateCorrelator` 和 `mBuildEvent`，通常还要实现 `mDiscover`；其他钩子是可选的（第 1 节）。以相对方式导入其自己的文件，以 `backend.core...` 的形式导入核心。本仓库的两个模块是完整的示例（[mod-apache2/module.py](../mod-apache2/module.py)、[mod-privesc/module.py](../mod-privesc/module.py)）；一个最简示意：

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # 每条记录都单独成为一个事件，无需等待。

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

5. **所采取的动作**：确定该服务中«已解决»的含义（例如某个 IP 已被封禁），并为此将 `action` 设为 `blocked`；只为没有采取动作的事件添加检测结果。
6. **规则**：位于 `mod-<name>/rules/` 中的 YAML 文件，由 `mRulesPath` 返回，规则调用的函数放在 `mRuleFunctions` 中。
7. **前提条件**：如果模块需要服务器上的软件（例如 apache2 需要 Apache 和 ModSecurity 2），请在 `mRequirements()` 中为每项前提条件返回一项检查（`fCheck` 的格式：`status` 为 `ok` 或 `error`，并在 `fix` 中给出安装它的命令），并且绝不要从模块中安装该软件：缺少前提条件时，模块会以停用状态安装。它在没有存储的情况下运行，在 Web 界面和 `manage.py` 中也是如此。还要在 `module.json` 的 `install_requirements` 中声明在 Debian 和 Alpine 上安装该软件的命令（每行一条命令，不含 shell 运算符）：Web 界面会在安装模块之前，在 模块 › 可安装 › 前提条件 中按原样以及在前面加上 `sudo` 显示这些命令。
8. **安装**：将其发布到本仓库（分支 `main`）；在未安装期间，它会出现在 localSIEM Web 界面的 模块 › 可安装 中，**安装**会将目录 `mod-<name>/` 复制到 `/opt/localsiem/modules/<name>/` 并重启采集器。对其 `read_paths` 的读取权限需要 root：Web 界面会显示相应命令（`manage.py setup-modules`）。模块没有配置选项：它从不安装任何东西，也从不更改 `/opt/localsiem` 之外的任何内容，从不写入、轮转或删除客户的日志，也从不更改其格式；如果服务器以自己的方式写入日志，模块会适应它，而服务器缺少的东西则作为前提条件。要发布新版本，请提高 `version`：模块 › 已安装 会显示提示和**更新**按钮，更新会保留模块的设置和启用/停用状态，并且只有在 `read_paths` 改变时才会再次显示供 root 运行的命令。
9. **文档**：以 15 种语言更新 README、本 CODE 和 MANUAL。

### 如何向 apache2 模块添加规则

在 [mod-apache2/rules/](../mod-apache2/rules/) 中创建一个 YAML 文件（每个键和运算符都在 [backend/core/rules.py](../../localSIEM/backend/core/rules.py) 的开头有说明）：`id`、`name`、`category`、`type`、`severity`、`kind`（`match`、`threshold` 或 `sequence`）、条件（`when`，或 `first`/`first_threshold`/`then`）、`by`、`window`、`threshold`、`lists`、`description` 和 `search`。字段先在事件列中查找，然后在 `fields` 中查找。它会出现在模块页面的规则表中，并在安装新版本的模块后由采集器加载：提高 `module.json` 中的 `version`，发布它，然后在 模块 › 已安装 中点击**更新**。

### 如何向 apache2 模块添加设置

将其添加到 [mod-apache2/module.json](../mod-apache2/module.json) 的 `settings` 中，并指定其类型和默认值，在 [mod-apache2/locales/](../mod-apache2/locales/) 的四个文件中添加其 `label` 和 `help`，然后用 `self.mModuleSettings().get("<key>")` 读取它。表单、验证和重新加载由核心提供。

### 如何添加诊断检查或更改严重级别

一项检查就是 `fRunDoctor`（[mod-apache2/doctor.py](../mod-apache2/doctor.py)）中的一个 `fCheck(id, status, title, detail, fix)`；请保持 `id` 稳定，并在 `fix` 中给出确切的配置片段或命令，且只针对非日志的前提条件：关于客户日志的检查只描述日志以及 localSIEM 能或不能从中读取的内容，不带 `fix`。ModSecurity 检测结果的严重级别在 [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) 中更改（`low`、`medium`、`high`、`critical`）。

### 如何向 privesc 模块添加规则

在 [mod-privesc/rules/](../mod-privesc/rules/) 中创建一个 YAML 文件，与 Apache 的规则类似。匹配事件的列（`method`、`uri`、`path`、`vhost`、`action`）和字段（`sensitive_group`、`account_type`、`real_uid`、`recon`、`service_account`、`file`...），绝不要匹配审计规则的键；添加 `ignored: {not: true}`，使被忽略的用户永远不会触发它；当只有真正运行的内容才算数时，添加 `action: none`。如果条件需要状态或逻辑（同一会话的序列、对某个文件的检查），请在 `PrivescModule.mAnalyzeCommand`（所有来源）或 `mAuditExec`/`mAuditSyscall`/`mSyslogEvent`（单个来源）中计算一个标志，并在规则中匹配它。

### 如何向 privesc 模块添加侦察命令、工具或漏洞利用

- 侦察：将程序添加到 `sReconSimple`，或在 `fReconToken` 中添加一个分支，为每类问题返回一个标记（[mod-privesc/commands.py](../mod-privesc/commands.py)）。随每个参数变化的标记会使计数虚高。
- 工具和漏洞利用：在 [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) 或 [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) 的列表中添加一个正则表达式（不区分大小写，与命令行匹配）；管理员也可以通过设置添加它们（`rules.<id>.lists`）。

### 如何向 privesc 模块添加来源或审计记录类型

- 敏感路径：将其连同其组添加到 [mod-privesc/module.py](../mod-privesc/module.py) 的 `lSensitivePaths` 中（或添加一个新组以及一条匹配 `sensitive_group` 的规则）。系统调用类型：将其名称添加到 `mAuditSyscall` 的集合中，并将其编号添加到 `dSyscallTables` 的每个表中。绝不要依赖审计规则的键（最多将其添加到 `dKeyHints`），也绝不要安装审计规则：服务器记录什么由其管理员决定，诊断会对其进行描述（[doctor.py](../mod-privesc/doctor.py) 的 `dAuditKinds`）。
- 来源：从 `fDiscoverSources` 中以新的 `kind` 返回它，在 `mParse` 中解析它，并在 `mBuildEvent` 中用与其他来源相同的列和字段构建其事件，这样规则无需更改即可工作。
