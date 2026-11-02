# localSIEM-modules 用户手册

本 MANUAL 还提供以下语言版本：\
[de-DE](MANUAL.de-DE.md), [en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md), [fr-FR](MANUAL.fr-FR.md), [he-IL](MANUAL.he-IL.md), [hi-IN](MANUAL.hi-IN.md), [it-IT](MANUAL.it-IT.md), [ja-JP](MANUAL.ja-JP.md), [ko-KR](MANUAL.ko-KR.md), [pt-BR](MANUAL.pt-BR.md), [pt-PT](MANUAL.pt-PT.md), [ru-RU](MANUAL.ru-RU.md), zh-CN

[安装](README.zh-CN.md) · [代码参考](CODE.zh-CN.md) · [localSIEM 手册](../../localSIEM/doc/MANUAL.zh-CN.md)

## 目录

1. [什么是模块](#what)
2. [安装和更新模块](#installation)
3. [模块页面](#modules-page)
4. [Apache 模块的页面](#apache-page)
5. [Apache 模块的设置](#settings)
6. [Apache 模块发送到 SOC 的内容](#soc)
7. [Apache 和 ModSecurity 的前提条件：诊断](#doctor)
8. [从不改动客户的日志](#client-logs)
9. [Apache 模块的规则](#rules)
10. [Apache 模块的健康警告](#health)
11. [权限提升模块](#privesc)
12. [权限提升模块的设置](#privesc-settings)
13. [权限提升模块发送到 SOC 的内容：其规则](#privesc-rules)
14. [权限提升模块的前提条件：诊断](#privesc-doctor)
15. [从权限提升模块 1.0.0 版本更新而来的服务器](#privesc-legacy)
16. [权限提升模块的攻击面和健康警告](#privesc-health)
17. [命令行](#cli)

<a id="what"></a>
## 1. 什么是模块

localSIEM 由一个**核心**和若干**模块**组成。核心负责存储事件、搜索事件、运行规则、对告警进行分组、将告警发送到 SOC 并监控自身的健康状况。每个模块为服务器上的一个服务提供支持：它查找该服务的日志、读取日志、将其转换为事件、判断哪些内容已经解决、带来自己的规则，并检查该服务的前提条件。

本项目的模块安装在 `/opt/localsiem/modules/<name>/` 中。目前有两个：**apache2**（«Apache + ModSecurity»，第 4 至 10 节）和 **privesc**（«权限提升»，第 11 至 16 节）。localSIEM 没有自带的模块：模块页面只列出从本仓库安装的模块。

<a id="installation"></a>
## 2. 安装和更新模块

必须先安装 localSIEM；它的安装程序只安装核心，从不安装模块。本项目的模块**只能从 localSIEM 的 Web 界面安装**：本项目没有自己的安装程序。Web 界面从仓库 `https://github.com/PYMEHackers/localSIEM-modules`（分支 `main`）下载模块。模块需要 localSIEM 2.2.0 或更高版本。

**安装。** 以管理员身份打开 模块 › **可安装**（第 3 节），点击**检查仓库**，查看**前提条件**（模块在服务器上需要的软件以及安装这些软件的命令，需在安装模块之前运行），然后在模块上点击**安装**。随后 localSIEM 会：

1. 下载仓库并安全地解压（不会解压到其目录之外，并有大小限制）；
2. 将模块的目录（仓库中的 `mod-<name>/`）复制到 `/opt/localsiem/modules/<name>/`，不包括 `tests/`（也不包括 Python 缓存）；重新安装的模块会恢复其原有的设置；
3. 重启采集器，采集器会在几秒钟内加载该模块；
4. 将该模块从列表中移除，并打开«<模块> 已安装»对话框，其中包含需要在服务器上以 root 身份运行的命令（`manage.py setup-modules`）和一个**复制**按钮：该命令授予 `localsiem` 用户读取其 `module.json` 的 `read_paths` 中所列目录的权限（apache2 模块为 `/var/log/apache2`，privesc 模块为 `/var/log/audit`），也包括今后轮转产生的文件，并重启 localSIEM。模块只需要这一读取权限：模块没有配置选项，也从不更改服务器（第 8 节和第 11 节）。在运行该命令之前，模块可能显示«错误»：它暂时还无法读取其日志。点击«关闭»或«查看已安装模块»即可关闭对话框，后者会打开已安装页面。

**更新。** 打开 模块 › **已安装** 时，Web 界面会检查仓库；如果仓库中有某个模块的新版本，该模块会显示一条带有**更新**按钮的提示（第 3 节）。确认后，localSIEM 会下载新版本并替换已安装的版本（步骤 1 至 3），保留其设置，并保持模块原有的启用或停用状态。只有当新版本读取其他日志（`read_paths`）时，才会再次显示供 root 运行的命令；否则无需运行任何命令。更新 localSIEM 时会保留已安装的模块及其读取权限。

**重新安装。** Web 界面既不重新安装模块，也不安装模块的旧版本：要重新安装模块，请点击**卸载**（第 3 节），然后从**可安装**再次安装；其设置会被保留。

**安装模块从不会安装其监控的软件。** apache2 模块既不安装 Apache 也不安装 ModSecurity，privesc 模块既不安装 auditd、syslog 守护进程，也不安装 snoopy。如果首次安装时服务器缺少模块所需的条件（apache2 需要 Apache 和 ModSecurity；privesc 需要一个 `localsiem` 可以读取的来源，见第 14 节），模块会以**停用**状态安装：对话框会列出缺少的内容而不是命令，并且在**重新配置**检测到这些条件之前无法启用该模块（第 4 节）。更新会保持模块原有的启用或停用状态。

<a id="modules-page"></a>
## 3. 模块页面

管理员打开**管理 › 模块**，该页面有两个标签页，各有自己的地址：**已安装**（`/admin/dashboard/modules/installed/`），默认打开此标签页（`/admin/dashboard/modules/` 会跳转到这里）；以及**可安装**（`/admin/dashboard/modules/installable/`）。分析师在其仪表板中看到**模块**（`/user/dashboard/modules/`）：只有已安装模块的列表，只读，不分标签页。

**已安装**为每个已安装的模块显示一行，占满整个宽度：其名称、ID、版本、状态标签、摘要，以及下方该状态的原因。列表每 10 秒自动刷新一次。没有安装任何模块时，它显示«请从可安装标签页安装模块。»（对分析师显示：«未安装任何模块。管理员可在 模块 › 可安装 中安装。»）。

| 状态 | 含义 |
|---|---|
| **已启用，运行正常** | 已启用，已由采集器加载并正在读取其来源。诊断警告会作为备注列出，但不会改变状态。 |
| **已启用，有警告** | 已启用，但未找到可读取的日志、某个来源尚不存在，或者模块是在采集器启动后才安装的（请重启 `localsiem` 服务）。 |
| **错误** | 模块无法加载（会显示错误）、其诊断报告了错误，或者某个来源无法读取（`localsiem` 用户的权限问题）。 |
| **已停用** | 已被停用，或者在不满足其前提条件的情况下安装（apache2：缺少 Apache 或 ModSecurity；privesc：`localsiem` 既无法读取 auditd 日志也无法读取 syslog），如其原因所示。 |
| **正在应用更改…** | 刚刚启用或停用：采集器正在应用该更改。 |
| **未知** | 采集器（`localsiem` 服务）未在运行，因此没有读取任何内容。 |

模块未停用时，该行还会显示：**正在读取的来源**（已读取 / 已找到）、**行数（1 小时）**、**最新数据**、**事件（24 小时）**、**已拦截（24 小时）** 以及**诊断**计数（«n 项正常 · n 项警告 · n 项错误»）。

管理员还会在每一行看到：

- 每个模块的**开关**。停用模块时需要确认：在重新启用之前，localSIEM 将停止读取其日志并停止发送其告警；已存储的内容会保留。启用模块后会立即开始读取。在缺少模块的某项前提条件时，开关处于锁定状态（«已停用：缺少前提条件»）：**重新配置**（第 4 节）检测到这些条件后即可解锁。
- **配置**，打开模块的页面 `/admin/dashboard/modules/installed/<name>/`（第 4 节）；旧地址 `/admin/dashboard/modules/<name>/` 会跳转到这里。
- **卸载**，对无法加载的模块同样可用（模块页面上也有此按钮）。确认后，localSIEM 会删除 `/opt/localsiem/modules/<name>/` 并在不加载该模块的情况下重启采集器：它将停止读取其日志并停止发送其告警。已存储的事件仍可搜索，其设置也会保留，以便您日后重新安装。root 授予 `localsiem` 的日志读取权限不会被收回。
- **更新**，当仓库中有该模块的新版本时显示。每次打开已安装页面时，Web 界面都会检查仓库（«正在检查仓库中是否有新版本…»；浏览器会在 10 分钟内重用该结果），如果某个模块有新版本，其所在行会显示«仓库中有版本 X（已安装的版本为 Y）。»以及**更新**按钮。确认后，localSIEM 会安装新版本（第 2 节），保留其设置，保持模块原有的启用或停用状态，并重启采集器；只有当新版本读取其他日志时，才会弹出对话框显示供 root 运行的命令。如果新版本需要更新版本的 localSIEM，提示会显示«仓库中有版本 X，但它需要 localSIEM Z 或更高版本：请先更新 localSIEM 再安装。»，并且不提供按钮。

**可安装**（仅限管理员）包含«可安装模块»卡片。**检查仓库**会下载仓库并列出尚未安装在本服务器上的模块，每个模块都显示其名称、ID、版本和摘要，以及一个按钮或一条说明：

| 按钮或说明 | 含义 |
|---|---|
| **前提条件** | 显示模块在服务器上需要的软件以及安装这些软件的命令，分别以 root 身份和使用 sudo 运行（见下文） |
| **安装** | 安装该模块（第 2 节） |
| «需要 localSIEM X 或更高版本» | 无法安装：请先更新 localSIEM |
| «仓库中的模块无效» | 无法安装 |

已安装的模块从不出现在这里：它们在已安装页面中更新。如果仓库中的所有模块都已安装，卡片会显示«仓库中的所有模块均已安装。»。安装后，«<模块> 已安装»对话框会显示需要以 root 身份运行的命令，使 `localsiem` 能够读取该模块的日志（第 2 节），并带有**复制**按钮；在运行该命令之前，模块可能显示«错误»：其日志暂时还无法读取。如果服务器缺少模块所需的条件，对话框会改为列出缺少的内容，并提示在所需软件就绪后到已安装页面中打开该模块（**配置**）并点击**重新配置**。

**前提条件**会打开«<模块>：前提条件»：模块在服务器上需要的软件，以及由模块声明（其 `module.json` 的 `install_requirements`）、在本服务器的系统上安装这些软件的命令（«本服务器：…»），共显示两次，每次都带有**复制**按钮：**以 root 身份**和**使用 sudo**（相同的命令，前面加上 `sudo`）。请在安装模块之前在服务器上运行这些命令：安装模块从不会安装这些软件，localSIEM 也从不运行它们。对于 apache2 模块，在 Debian 上：`apt-get -y update`、`apt-get -y install apache2 libapache2-mod-security2 modsecurity-crs`、`a2enmod security2 unique_id`、`cp --update=none /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf`（仅在没有 ModSecurity 配置时才创建它，采用 DetectionOnly 模式）和 `systemctl restart apache2`；在 Alpine 上只能安装 Apache（`apk add apache2`，然后用 `rc-update` 和 `rc-service` 启动它），因为 Alpine 没有 ModSecurity 2 软件包：在从源码编译并加载 ModSecurity 之前，模块保持停用。对于 privesc 模块：在 Debian 上为 `apt-get -y install auditd rsyslog`，在 Alpine 上为 `apk add audit` 并设置 auditd 开机启动；只要有一个可读的来源即可，而在容器中 auditd 无法运行。

<a id="apache-page"></a>
## 4. Apache 模块的页面

`/admin/dashboard/modules/installed/apache2/`（仅限管理员；旧地址 `/admin/dashboard/modules/apache2/` 会跳转到这里）包含五个部分：

1. **页头**：名称、ID、版本、安装路径（`/opt/localsiem/modules/apache2`）、开关、状态及其原因，以及第 3 节中的统计数字。**返回已安装模块**返回已安装页面；**重新发现并运行诊断**会立即重新读取 Apache 配置并刷新诊断；**重新配置**会再次查找 Apache 和 ModSecurity（见下文）；**卸载**会卸载该模块（第 3 节）并返回已安装页面。
2. **设置**：第 5 节中的表单。**保存设置**会检查每个值，如果某个值有误，会指出是哪一个（«无效的值：…»）。
3. **来源**：正在读取的每个日志，包括**类型**（`access`、`error`、`audit`）、**路径**、**Vhost**、**行数（1 小时）**、**未解析（1 小时）**、**最新数据**（例如 `2026/10/29@13:59:59.723`）和**状态**（无法读取时为错误，尚不存在时为警告）。下方列出已找到但未读取的日志及其原因：«管道日志，不支持»、«已由写入所有 vhost 的 GlobalLog 覆盖»或«其格式不含数据：每一行都是相同的文本（引用了未定义的 LogFormat 别名）»。
4. **诊断**：第 7 节中的检查，以及其运行时间。每个缺失的前提条件（ModSecurity、CRS、`SecRuleEngine`、`mod_unique_id`、`localsiem` 的读取权限）都附带修复它的配置片段或命令，以及一个**复制**按钮。关于日志的检查只描述日志以及 localSIEM 能从中读取的内容，不提供修复：客户的日志从不被更改（第 8 节）。
5. **规则**：第 9 节中的规则，每条规则都有**启用**、**规则**（名称、ID 和类别）、**严重级别**、**阈值**和**窗口（秒）**，以及**保存规则**按钮。

**前提条件与重新配置。** 在缺少 Apache 或 ModSecurity 时，模块处于停用状态，页头会列出缺少的内容以及安装它的命令。**重新配置**（模块停用时同样可用）会使用已保存的设置再次查找它们；如果 Apache 安装在非标准位置，请先设置 **Apache 配置文件**（第 5 节）。两者都找到后，它会解锁开关——是否启用模块由您决定——并显示需要以 root 身份运行的命令，使 `localsiem` 能够读取模块安装后才创建的 Apache 日志。已启用的模块在失去 Apache 或 ModSecurity 后仍保持启用：诊断和健康警告（第 10 节）会报告这一情况。

**所有更改都会立即生效，无需重启任何服务**：Web 界面保存更改并通知采集器，采集器会重新加载其设置、重新发现来源并运行诊断。如果采集器没有响应，Web 界面会提示这一点，更改将在采集器启动时应用。

<a id="settings"></a>
## 5. Apache 模块的设置

| 设置 | 默认值 | 作用 |
|---|---|---|
| **仅使用下方的来源** | 关闭 | 不根据 Apache 配置发现日志：只读取手动添加的来源。 |
| **手动添加的来源** | 无 | 除自动发现的日志之外还要读取的日志（启用上方选项时，则替代自动发现的日志）。最多 50 个。 |
| **Apache 配置文件** | 空 | 留空：自动查找（Debian 上为 `/etc/apache2/apache2.conf`，Alpine 上为 `/etc/apache2/httpd.conf`；也能识别 `/etc/httpd/conf/httpd.conf`）。填写绝对路径时，如果该文件存在，则改用该文件。 |
| **发现间隔（秒）** | 3600 | 重新读取 Apache 配置以查找新 vhost 和新日志的频率（60 到 86400）。 |
| **ModSecurity 拦截阈值** | 0 | 0：从 CRS 配置（`crs-setup.conf` 中的 `tx.inbound_anomaly_score_threshold`）中读取，未配置时为 5。当 ModSecurity 消息本身未说明阈值时，用于区分高于拦截阈值的匹配和低于拦截阈值的匹配（0 到 1000）。 |
| **新 PHP 文件的学习天数** | 3 | 在模块首次启动后的最初这些天内，规则 `apache-webshell` 不会将从未见过的 PHP 文件报告为新文件（0 到 365）。在其 DocumentRoot 中最近一天内创建或修改的文件始终算作新文件。 |

每个**手动添加的来源**有以下字段（* 为必填）：

| 字段 | 用途 |
|---|---|
| **类型** * | `access.log`、`error.log` 或 `ModSecurity 审计日志` |
| **路径** * | 文件的绝对路径 |
| **Vhost** | 这些行所属的 vhost，用于行中未注明 vhost 的日志 |
| **LogFormat** | 用于访问日志：一个别名（`localsiem_combined`、`combined`、`vhost_combined`、`common`、`combinedio`，或 Apache 配置中定义的别名）或格式本身。留空：尝试常用格式。 |
| **审计日志类型** | `串行（单个文件）` 或 `并发（每个请求一个文件）` |
| **审计存储目录** | 用于并发类型：`SecAuditLogStorageDir` 的目录 |

一个文件只会被读取一次，即使它既被自动发现又被手动添加。localSIEM 运行期间出现的来源，如果不超过 5 MB，会从头开始读取，否则从末尾开始读取。

localSIEM 的 **管理 › 设置** 中有两项设置也作用于本模块：**关联窗口**（5 秒：等待一个请求的三条记录的时间）和**低于拦截阈值时的严重级别**（`low`）。被 ModSecurity 标记的请求还会等待其审计记录（ModSecurity 在请求结束时写入），最长 2 分钟：这样慢请求就不会被拆分为两个事件。

<a id="soc"></a>
## 6. Apache 模块发送到 SOC 的内容

对于每个请求，模块会将具有相同 `UNIQUE_ID` 的访问日志行、错误日志行和审计记录合并在一起。Apache 默认写入的访问日志（`combined`、`vhost_combined`、`common`）没有 `UNIQUE_ID`：此时，每条访问日志行会按客户端 IP、方法、URI、状态码和时间（±2 秒）与其所属请求的审计记录和错误日志行合并，即使同一请求在同一秒内重复出现也是如此，并且该事件会被标记为«弱关联»。vhost 取自 `%v`；如果格式中没有它，则取自审计记录中的 Host 请求头和端口，选择方式与 Apache 相同；时间采用审计记录中的微秒值。然后模块判断是否已经对其采取了措施（«采取的动作»），先读取审计日志（`Action: Intercepted (phase N)`），再读取 error.log（`Access denied with code NNN (phase N)`）。没有任何 ModSecurity 痕迹的 403 不会被视为拦截：它会被标记为存疑。

| 情况 | 是否发送到 SOC？ |
|---|---|
| 在阶段 1-2 被 ModSecurity 拦截（应用程序从未收到） | **否。** 保留在 localSIEM 中，可供搜索（`action:blocked`），并计入该 IP 下一条告警的上下文。 |
| 在阶段 3-4 被拦截（应用程序已经执行了它） | 是 |
| 引擎处于 `DetectionOnly` 时的规则匹配 | 是 |
| 低于拦截阈值的规则匹配 | 是 |
| 第 9 节中规则产生的信号 | 是 |

ModSecurity 匹配所产生告警的严重级别（模块的 `severity.yaml` 文件）：

| 情况 | 严重级别 |
|---|---|
| 未被拦截的匹配，响应为 3xx、4xx 或 5xx | 中 |
| 未被拦截的匹配，响应为 2xx | 高 |
| 在阶段 3-4 被拦截 | 高 |
| 成功迹象：命中了出站规则（950-955）且没有任何拦截，或者请求之后出现了数据库错误 | 严重 |
| 低于拦截阈值（通常是应用程序本身的误报） | 低（即 管理 › 设置 中低于拦截阈值时的严重级别） |

每条告警都有一个固定的名称（例如«Apache/ModSecurity: SQL injection not blocked (CRS 942)»）、一段描述（以可粘贴到 localSIEM 搜索中的查询结尾，例如 `ip:203.0.113.7 category:sqli`）以及详细信息：vhost、客户端 IP、方法、URI（已脱敏）、响应、用户代理和 ModSecurity 数据（引擎、动作、阶段、异常分数、阈值、规则和匹配的数据）。告警发出时，还会附带该 IP 的上下文：最近一小时的请求和被拦截的请求、拦截它的规则以及首次发现它的时间。

密码、cookie、`Authorization` 请求头和令牌在存储任何内容之前都会被脱敏，请求体中的也不例外，而且请求体从不会发送到 SOC。审计日志中的响应体（E 部分）和所执行规则的完整文本（K 部分）从不保存。

<a id="doctor"></a>
## 7. Apache 和 ModSecurity 的前提条件：诊断

apache2 模块的诊断会读取 Apache 配置（不做任何更改）并检查每项前提条件。它在采集器启动时、每次更改设置后、每次发现时、点击**重新发现并运行诊断**时以及运行 `manage.py doctor`（第 17 节）时运行，但仅在模块启用期间运行：当模块因缺少 Apache 或 ModSecurity 而停用时，模块页面会改为显示这些前提条件（第 4 节）。状态：正常、警告（可以工作但有局限）、错误（必须修复）和信息（仅在某些情况下重要）。

| 检查项 | 正常条件 | 否则 |
|---|---|---|
| Apache 配置 | 找到并读取了 `apache2.conf` 或 `httpd.conf`（或所配置的文件） | 错误：请手动添加来源（第 5 节）。无法读取的部分会作为警告列出。 |
| ModSecurity | 已加载 `mod_security2`（ModSecurity 2） | 错误。Debian：`apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`。Alpine 没有软件包：请从源码编译 mod_security2 2.9。不支持 ModSecurity 3（libmodsecurity）。 |
| OWASP CRS | 已包含 CRS 文件（诊断会显示文件数量和异常阈值） | 错误：`apt-get install modsecurity-crs`，或在 ModSecurity 之后包含 `crs-setup.conf` 和 `rules/*.conf` |
| SecRuleEngine | `On`（超过阈值的请求会在阶段 2 被拦截并保留在 localSIEM 中）或 `DetectionOnly`（不拦截任何请求：每个匹配都会发送到 SOC） | 为 `Off` 时报错误；如果除部分 vhost 外均为 `Off`、未设置（此时 ModSecurity 默认为 `Off`）或部分 vhost 将其设为 `Off`，则报警告 |
| mod_unique_id | 已加载：ModSecurity 正常工作，且一个请求的三个来源按 `UNIQUE_ID` 合并 | 如果已加载 ModSecurity，则报错误：没有它，ModSecurity 2 不会检查任何内容（Alpine 不加载它）；否则报警告（弱关联）。Debian：`a2enmod unique_id`；Alpine：`LoadModule unique_id_module modules/mod_unique_id.so` |
| 访问日志格式 | 访问日志包含客户端 IP、时间、请求行和状态码，与 Apache 默认写入的格式一样（正常，«Access logs in the format Apache writes»）：每一行按客户端 IP、方法、URI、状态码和时间与其所属请求的 ModSecurity 记录合并。如果格式中包含毫秒、vhost 和 `UNIQUE_ID`（例如 `localsiem_combined`，见于已在写入该格式的服务器），则按 `UNIQUE_ID` 合并（正常，«Access log with milliseconds, vhost, duration and UNIQUE_ID»） | 如果某个访问日志缺少这四项中的任何一项，报信息，不提供修复：localSIEM 按原样读取它，但无法将其各行与 ModSecurity 记录合并（这些请求可在审计日志中看到）；如果没有读取任何访问日志，报信息（请求可在错误日志和审计日志中看到）。日志格式由客户决定（第 8 节） |
| mod_remoteip | 已加载并配置了 `RemoteIPHeader` | 信息，不提供修复：如果网站位于代理或负载均衡器之后，日志中记录的是代理的 IP，告警和按 IP 的规则也是如此 |
| 审计日志 | `SecAuditEngine RelevantOnly`（或 `On`）并配置了 `SecAuditLog` | 如果未启用，则报警告：localSIEM 只能根据 error.log 做出判断，请求详情中也没有请求头和规则列表。启用时，其备注仅作描述：并发类型（每个事务一个文件；ModSecurity 通常以 600 权限创建这些文件，只要 `localsiem` 有权限，localSIEM 就会读取它们）、原生格式（按原样读取）、记录了 E 部分（它从不会发送到 SOC）、缺少 H 部分（无法从审计日志中读取所采取的动作；这是唯一会使该检查变为警告的备注）。不提供修复：审计日志由客户配置（第 8 节） |
| 源头脱敏 | 存在 `sanitise` 动作 | 信息，不提供修复（«The audit log on disk is not masked»）：ModSecurity 写入的文件可能包含密码和 cookie；localSIEM 会在存储之前将其脱敏，并且它们从不会发送到 SOC |
| 权限 | `localsiem` 可以读取每个来源 | 错误。Debian：`usermod -aG adm localsiem`；Alpine：页面显示的 `setfacl` 命令。尚不存在的来源仅报信息。 |
| 管道日志 | — | 警告：`\|/usr/bin/rotatelogs ...` 和 syslog 无法读取；请同时将日志写入文件，或手动添加该来源 |
| 无数据的访问日志 | — | 警告：某个 `CustomLog` 使用了没有任何 `LogFormat` 定义的格式（或者是不含任何 `%` 指令的 `LogFormat`），因此 Apache 在每一行都写入相同的文本，没有客户端 IP、时间或请求。localSIEM 不读取该日志，而是通过其 vhost 的错误日志和 ModSecurity 审计日志查看该 vhost 的请求。服务器日志的格式从不被更改。 |
| 检测到引擎为 Off | — | 错误：审计记录报告引擎已被禁用 |
| ModSecurity 版本 | — | 信息：从审计日志中读取的版本 |

如果配置中有一个格式包含 `%v` 的 `GlobalLog`（它会写入所有 vhost），则不读取其他访问日志：它们只会重复其中的行。诊断从不建议更改日志格式或审计日志的设置（第 8 节）。

<a id="client-logs"></a>
## 8. 从不改动客户的日志

apache2 模块只**读取** Apache 和 ModSecurity 的日志：从不写入、轮转、截断、移动或删除它们，也从不更改其格式或写入这些日志的 Apache 或 ModSecurity 配置。如果服务器以自己的格式写入日志（例如自定义的 `LogFormat`，或 `mod_remoteip` 提供的客户端 IP），模块会适应该格式：它按每个访问日志的 `CustomLog` 所使用的格式读取该日志。诊断（第 7 节）只描述日志以及 localSIEM 能或不能从中读取的内容，不建议更改日志；它只为非日志的内容提供修复：ModSecurity、CRS、`SecRuleEngine`、`mod_unique_id` 和 `localsiem` 用户的读取权限。为本模块以 root 身份执行的唯一操作就是授予该读取权限（`manage.py setup-modules`，第 2 节）。

该模块的 1.2.0 及更早版本有配置选项 `--configure-apache`，已在 1.3.0 版本中移除。应用过该选项的服务器会保留它写入的文件 `/etc/apache2/conf-available/localsiem.conf`（Debian）或 `/etc/apache2/conf.d/localsiem.conf`（Alpine），其中包含 `localsiem_combined` 格式及其 `GlobalLog`（`localsiem_access.log`）、审计日志设置，以及一个对敏感值进行脱敏的 `SecAction`。只要该文件存在，模块就会像读取其他日志一样读取这些日志。要撤销它，请删除该文件（Debian：`a2disconf localsiem`）并重新加载 Apache。在 Alpine 上，该文件还会加载 `mod_unique_id` 和 `mod_logio`：删除它之前，请在 Apache 配置的其他位置加载 `mod_unique_id`，因为没有它，ModSecurity 2 不会检查任何内容（第 7 节）。localSIEM 的安装程序在使用 `--uninstall` 或 `--reinstall` 时会删除该文件（在 Alpine 上，请先在其他位置加载 `mod_unique_id`），并将日志（`localsiem_access.log`、`modsec_audit.log`）保留在原处。

<a id="rules"></a>
## 9. Apache 模块的规则

规则会对每个事件进行评估。规则产生的信号总是会发送到 SOC。在模块页面中，每条规则都可以停用，也可以更改其严重级别、阈值（1 到 100000）和窗口（1 到 86400 秒）；阈值和窗口仅适用于阈值规则和序列规则。可以用 `rule:localsiem:<id>` 查找其事件。

| 规则 | 类型 | 严重级别 | 触发条件 | 阈值 / 窗口 |
|---|---|---|---|---|
| `apache-bruteforce` «针对登录页面的暴力破解» | 阈值 | 中 | 来自一个 IP、发往一个 vhost 登录页面的未被拦截的 POST 请求（`/wp-login.php`、`/xmlrpc.php`、`/administrator/index.php`、`/user/login`、`/login`、`/admin/login`、`/login.php`、`/admin.php`、`/signin`、`/auth/login`、`/phpmyadmin/index.php`） | 300 秒内 20 次 |
| `apache-login-after-bruteforce` «暴力破解后登录成功» | 序列 | 高 | 对某个登录页面至少 10 次登录失败（POST 响应为 200、401 或 403），随后有一次响应为 302 或 303（WordPress 对失败的登录响应 200，对成功的登录响应 302） | 10 次，1800 秒内 |
| `apache-enumeration` «枚举（404 响应突发）» | 阈值 | 中 | 一个 vhost 发给一个 IP 的未被拦截的 404 响应 | 60 秒内 30 次 |
| `apache-sensitive-file` «敏感文件被返回» | 匹配 | 高 | 对不应公开的文件返回 2xx 响应：`.env`、`.git/`、`.svn/`、`.hg/`、`.htaccess`、`.htpasswd`、转储和备份（`.sql`、`.sql.gz`、`.bak`、`.old`、`.orig`、`.swp`、`.save`、`.backup`、`.dump`、以 `~` 结尾的文件名）、`phpinfo`、`info.php`、`server-status`、`server-info`、`wp-config.php` 和 `config.php`/`config.inc` 的副本、`.DS_Store`、SSH 私钥、`composer.json`/`composer.lock`、`.aws/`、`backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «可能的 web shell（向新 PHP 文件发送 POST）» | 匹配 | 严重 | 向某个 PHP 文件发送的 POST 得到 2xx 响应，而该文件是在其 DocumentRoot 中最近一天内创建或修改的，或者是最近一小时内首次出现的（学习天数结束后） | — |
| `apache-db-error-after-attack` «可疑请求后出现数据库错误» | 序列 | 严重 | 一个命中 CRS 规则的请求，随后同一 IP 在 error.log 中出现数据库错误（SQL 或 PDO） | 1 次，30 秒内 |

<a id="health"></a>
## 10. Apache 模块的健康警告

除了 localSIEM 本身的健康警告之外，本模块最多每 5 分钟检查一次，并向 SOC 发送：

| 警告 | 严重级别 | 处理方法 |
|---|---|---|
| ModSecurity 已不再加载 | 高 | 它曾经被加载，但现在不再加载：请求不会被检查。如果不是有人有意为之，可能有人关闭了防护。 |
| ModSecurity 引擎被设为 Off | 高 | `SecRuleEngine` 已改为 `Off`，或者审计日志报告引擎已被禁用。请检查 Apache 配置及其最近的更改。 |
| 缺少真实客户端 IP（mod_remoteip） | 中 | 在最近一小时内，至少 100 个请求中有至少 90 % 来自同一个私有或本地地址：网站很可能位于代理之后，Apache 记录的是代理的 IP，因此按 IP 的规则对这些请求不起作用。每天最多发送一次。 |

已报告过的内容在重启后仍会被记住，因此更新不会再次发送。由于有这些警告，已启用的模块在 Apache 或 ModSecurity 消失时从不会自行停用。

<a id="privesc"></a>
## 11. 权限提升模块

**privesc** 模块（«权限提升»）监控用户和服务在服务器上运行的内容，并报告提权到 root 的各个步骤：侦察、搜索 setuid 程序、linpeas 等枚举工具、已知漏洞利用、反弹 shell、未经 sudo 或 su 获得 root、遗留的后门，以及试图使监控失效的行为。它还会检查服务器的攻击面：setuid 程序、capabilities 和可被他人写入的敏感文件（第 16 节）。

它只读取服务器上已有的内容：从不安装任何东西，从不加载审计规则，也从不更改 auditd、snoopy 或 shell 的配置。它最多读取两个来源：

| 来源 | 能看到的内容 | 适用环境 |
|---|---|---|
| **auditd**（`/var/log/audit/audit.log`） | sudo、su、pkexec 和 SSH 登录（PAM），以及服务器审计规则所记录的任何内容（见下文） | 物理服务器和虚拟机，只要 auditd 正在运行。**不能在容器内**（LXC、podman、systemd-nspawn、Docker）：内核审计不支持命名空间隔离，因此 auditd 只能在宿主机上运行。 |
| **syslog**（`/var/log/auth.log`、`/var/log/secure` 或 `/var/log/messages`） | sudo、su、pkexec、doas、SSH 登录，以及（如果安装了 **snoopy**）运行的每个程序 | 所有环境，包括容器。在 auditd 未运行、其日志无法读取或已安装 snoopy 时读取（设置项**读取 syslog**）。它需要一个写入文件的 syslog 守护进程：仅有 systemd 的 journal 时不会读取。 |

auditd 显示的内容取决于服务器所加载的审计规则，这些规则由服务器管理员决定；模块按原样使用这些规则，无论其键（key）是什么，并按记录的类型、系统调用和文件对每条记录进行分类：

| 模块能看到 | 当服务器的审计规则记录了 |
|---|---|
| 运行的每个程序（包括来自脚本、web shell 和漏洞利用的程序）、setuid 程序、从中继承的 root、获得的 capabilities | `execve` |
| 账户、sudoers、PAM、preload、SSH、cron、服务和 `/etc/audit` 的变更 | 对这些文件的监视（`-w ... -p wa`）或更改它们的系统调用 |
| 设置了 setuid 或 setgid 位 | `chmod`、`fchmod`、`fchmodat` |
| 加载或移除内核模块 | `init_module`、`finit_module`、`delete_module` |
| 用 ptrace 附加的进程 | `ptrace` |
| 对某人拒绝访问的文件 | 以 `EACCES` 或 `EPERM` 失败的 `open`、`openat`、`execve`... |
| 审计规则被移除、审计被关闭、auditd 被停止、程序崩溃 | 始终（由内核和 auditd 报告） |

在物理服务器或虚拟机上，auditd 是用户无法规避的来源；诊断会说明服务器的审计规则到目前为止记录了哪些内容（第 14 节）。在容器中，snoopy 是看到运行的每个程序的唯一方式。

shell 的内置命令（`pwd`、`cd`、`unset HISTFILE`、`history -c`）从不运行程序，因此任何来源都看不到它们，除非它们位于 `bash -c '...'` 这样的命令行中。单个 `whoami` 从不构成告警：模块会统计每个会话在一个窗口内运行的**不同**侦察命令，只有它们构成突发时才会告警（第 13 节）。

模块的每个事件包含什么，以及如何搜索：

| 列 | 内容 | 搜索示例 |
|---|---|---|
| `vhost` | 用户本人：登录用户（经过 sudo 和 su 后保持不变） | `module:privesc vhost:alice` |
| `method` | 事件类型：`exec`（运行的程序，来自 auditd 或 snoopy）、`sudo`、`su`、`pkexec`、`doas`、`login`、`pam`、`file`（敏感文件被更改）、`chmod`（setuid 位）、`kmod`、`ptrace`、`denied`（文件访问被拒绝）、`audit_config`、`auditd`、`crash`、`syscall`（服务器审计规则记录的其他系统调用） | `module:privesc method:sudo` |
| `uri` | 命令行（密码已脱敏） | `module:privesc uri:*linpeas*` |
| `path` | 运行的程序，或被更改的文件 | `module:privesc path:/tmp/*` |
| `ip` | 会话的 SSH 地址（如果已知） | `module:privesc ip:203.0.113.7` |
| `score` | 窗口内该会话的不同侦察命令数 | `module:privesc score:>=8` |
| `action` | 系统本身阻止了它时为 `blocked`：无法运行的程序、被拒绝的 sudo 或 su、被拒绝访问的文件 | `module:privesc action:blocked` |
| `source` | `audit` 或 `syslog` | `module:privesc source:syslog` |

关于尝试行为的规则（反复的 sudo 失败、大量文件访问被拒绝）仍会统计被阻止的事件；其他规则只关注真正运行了的内容。

模块页面 `/admin/dashboard/modules/installed/privesc/` 包含与 Apache 模块页面（第 4 节）相同的部分：页头（含**重新发现并运行诊断**、**重新配置**和**卸载**）、设置（第 12 节）、来源（`audit`、`syslog`；以及未读取的来源及其原因）、诊断（第 14 节）和规则（第 13 节）。

<a id="privesc-settings"></a>
## 12. 权限提升模块的设置

| 设置 | 默认值 | 作用 |
|---|---|---|
| **审计日志** | 空 | 留空：使用 `/etc/audit/auditd.conf` 中的 `log_file`，或 `/var/log/audit/audit.log`。 |
| **读取 syslog** | 自动 | 自动：仅当 auditd 未运行、其日志无法读取或已安装 snoopy 时读取。也可选择始终或从不。 |
| **Syslog 文件** | 空 | 留空：`/var/log/auth.log`、`/var/log/secure` 或 `/var/log/messages` 中第一个存在的文件。 |
| **忽略的用户** | 空 | 以逗号分隔。其命令会被保存且可搜索，但从不触发告警：自动化账户（ansible、备份）。`localsiem` 用户始终被忽略。 |
| **管理员组** | `sudo,wheel,admin` | 以逗号分隔。其成员（以及 root）使用较高的侦察阈值，并且可以列出自己的 sudo 权限而不触发告警。 |
| **侦察窗口（秒）** | 120 | 统计一个会话中不同侦察命令数量的窗口（10 到 3600）。 |
| **侦察阈值** | 8 | 对普通用户和服务账户而言，窗口内构成一次突发的不同侦察命令数量（2 到 500）。 |
| **管理员的侦察阈值** | 20 | 同上，适用于 root 和管理员，他们在日常工作中会运行这些命令（2 到 500）。 |
| **自动化枚举阈值** | 40 | 窗口内只有脚本才会运行的不同侦察命令数量（类似 linpeas），适用于所有人（5 到 1000）。 |
| **服务账户的学习天数** | 3 | 在模块首次启动后的最初这些天内，学习每个服务账户运行的程序（例如 `www-data` 运行 `sh -c sendmail`）而不产生告警（0 到 365）。 |
| **setuid 程序扫描间隔（小时）** | 24 | 搜索 setuid 和 setgid 程序以及文件 capabilities 的频率（第 16 节）。0：从不（0 到 168）。 |
| **扫描的目录** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | 以逗号分隔；遍历每个目录时不会跨出其所在的文件系统。容器的目录以及 `/proc` 和 `/sys` 始终会被跳过。 |
| **发现间隔（秒）** | 300 | 查找审计日志、syslog 以及 auditd 状态的频率（60 到 86400）。已启用模块中最短的间隔适用于所有这些模块。 |

被视为侦察的命令：`whoami`、`id`、`groups`、`uname`、`hostname`、`w`、`who`、`last`、`ps`、`ss`、`netstat`、`ip`、`ifconfig`、`env`、`pwd`、`history`、`getcap`、`lsmod`、`dmesg`、`mount` 等；`sudo -l`、`crontab -l`、`systemctl list-*`、软件包列表；`which`、`locate`、`command -v`；`docker ps` 等；每个不同的 `find`；读取 `/etc/passwd`、`/etc/shadow`、`/etc/sudoers`、`/etc/*-release`、`/proc/version`、`/root/...`、历史记录、SSH 密钥和 `.env` 文件；列出 `/root`、`/home`、`/opt`、`/tmp`、cron 目录……；`grep -r password`；以及 `<program> --version`。一个会话中每个不同的命令在窗口内只计一次。

<a id="privesc-rules"></a>
## 13. 权限提升模块发送到 SOC 的内容：其规则

除第 16 节中的告警外，该模块的每条告警都来自它的某条规则（无论哪个来源看到了命令，规则的工作方式都相同）。与 Apache 一样，可以在模块页面中停用每条规则，并更改其严重级别、阈值和窗口；可以用 `rule:localsiem:<id>` 查找其事件。对于**忽略的用户**，任何规则都不会触发。标注«auditd»的规则需要第 11 节中的审计记录。

| 规则 | 类型 | 严重级别 | 触发条件 | 阈值 / 窗口 |
|---|---|---|---|---|
| `privesc-recon-burst` «侦察突发» | 匹配 | 中 | 会话达到了侦察阈值（第 12 节） | — |
| `privesc-enumeration` «自动化枚举（类似 linpeas）» | 匹配 | 高 | 会话达到了自动化枚举阈值，即使脚本被重命名也是如此 | — |
| `privesc-suid-hunt` «搜索 setuid 程序或 capabilities» | 匹配 | 高 | `find ... -perm -4000`（或 `-u=s`、`/6000`、`-2000`...）、`getcap -r`、`find -writable` | — |
| `privesc-sudo-list` «非管理员列出 sudo 权限» | 匹配 | 中 | 非管理员的用户或服务账户运行 `sudo -l` | — |
| `privesc-known-tool` «已知枚举工具» | 匹配 | 高 | linpeas、LinEnum、lse.sh、linux-exploit-suggester、les.sh、pspy、unix-privesc-check、linuxprivchecker、traitor、BeRoot、GTFONow、PEASS、deepce、CDK、sudo_killer、suid3num、mimipenguin、LaZagne、pwncat、searchsploit | — |
| `privesc-exploit` «已知漏洞利用» | 匹配 | 严重 | PwnKit、DirtyPipe、Dirty COW、Baron Samedit（`sudoedit -s '\'`）、Looney Tunables（`GLIBC_TUNABLES`）、GameOver(lay)、nf_tables（CVE-2024-1086）、CVE-2023-22809（`EDITOR=... -- /...`）、polkit CVE-2021-3560（`dbus-send ... CreateUser`）、与 sudo 一起使用的 `LD_PRELOAD`、以 CVE 命名的脚本、名为 `exploit`、`getroot`、`rootme` 的程序 | — |
| `privesc-pwnkit` «PwnKit（不带参数运行 pkexec）» | 匹配 | 严重 | 以零个参数运行 `pkexec`（auditd） | — |
| `privesc-pwnkit-log` «pkexec 报告 PwnKit 尝试» | 匹配 | 严重 | pkexec 记录了 `GCONV_PATH`、«suspicious content» 或 «was not found the /etc/shells»（syslog） | — |
| `privesc-suid-escape` «从 setuid 程序继承的 root» | 匹配 | 严重 | 一个非 setuid 程序以 root 的有效 uid 和某个用户的真实 uid 运行：有 setuid 程序被滥用了（GTFOBins）。挂载辅助程序、D-Bus、polkit 和 X 除外。 | — |
| `privesc-root-without-door` «未经 sudo、su 或 pkexec 获得的 root» | 匹配 | 严重 | 一个已看到其开始的用户会话，在未经过 sudo、su、pkexec 或 doas 的情况下以 root 身份运行程序（内核漏洞利用）（auditd） | — |
| `privesc-root-shell-interpreter` «由解释器启动的 root shell» | 匹配 | 高 | 一个 shell 以 root 身份运行，由普通用户正在运行的 python、perl、ruby、awk、gdb 等启动（作为其子进程，或在同一进程中）（auditd） | — |
| `privesc-file-capabilities` «程序从其文件获得 root capabilities» | 匹配 | 高 | 用户运行了一个程序，其文件赋予它 `cap_setuid`、`cap_dac_override`、`cap_sys_admin`...（auditd） | — |
| `privesc-tmp-exec` «从所有人可写的目录运行程序» | 匹配 | 高 | 位于 `/tmp`、`/var/tmp`、`/dev/shm` 或 `/run/user/<uid>` 中的程序 | — |
| `privesc-compile-tmp` «在临时目录中编译程序» | 匹配 | 高 | 在临时目录中或针对临时目录中的文件运行 `gcc`、`cc`、`clang`、`make`... | — |
| `privesc-download-shell` «由 shell 运行下载的脚本» | 匹配 | 高 | `curl ... \| sh`、`bash -c "$(curl ...)"`、`bash <(wget ...)`，或在同一管道中下载工具后接 shell | — |
| `privesc-reverse-shell` «反弹 shell» | 匹配 | 高 | `/dev/tcp/`、`nc -e`、`ncat --exec`、`socat exec:`、`mkfifo ... \| nc`、python/perl/php/ruby/lua/node 套接字、`openssl s_client ... \| sh`、`awk /inet/tcp` | — |
| `privesc-tty-upgrade` «shell 升级为完整终端» | 匹配 | 高 | `pty.spawn`、`script ... /dev/null`、`stty raw -echo`、`socat ... pty`、`expect ... spawn sh` | — |
| `privesc-service-recon` «服务账户运行了侦察命令» | 匹配 | 高 | `www-data`、`mysql` 和其他服务账户运行 `whoami`、`id`、`uname`...（web shell） | — |
| `privesc-service-new-program` «服务账户运行了以前从未运行过的程序» | 匹配 | 高 | 学习天数结束后，某个服务账户运行了它从未运行过的 shell、解释器或工具（例如此前只运行过 `sh -c sendmail`，现在运行 `sh -c id`） | — |
| `privesc-container-escape` «利用容器以 root 身份访问宿主机» | 匹配 | 高 | 非 root 用户运行 `docker run -v /:/...`、`--privileged`、`--pid=host`、`nsenter -t 1`、`lxc config set ... security.privileged true`、`lxc config device add ... source=/`、`debugfs /dev/...` | — |
| `privesc-auth-failures` «反复的 sudo 或 su 失败» | 阈值 | 中 | 同一用户的 sudo、su、pkexec 或 doas 失败 | 600 秒内 3 次 |
| `privesc-sensitive-file` «账户、sudo、PAM 或 preload 文件被更改» | 匹配 | 高 | `/etc/passwd`、`shadow`、`group`、`gshadow`、`sudoers`、`sudoers.d`、`doas.conf`、`doas.d`、`ld.so.preload`、`ld.so.conf`、`ld.so.conf.d`、`pam.d`、`security` 被软件包或账户管理工具以外的程序更改（auditd） | — |
| `privesc-persistence-file` «SSH、cron 或服务文件被更改» | 匹配 | 中 | `/root/.ssh`、`sshd_config`、`sshd_config.d`、cron 文件、`/etc/systemd/system`、`/etc/init.d`、`rc.local`、`/etc/local.d` 被更改（auditd） | — |
| `privesc-monitoring-changed` «auditd 配置被更改» | 匹配 | 中 | `/etc/audit` 被软件包工具以外的程序更改（auditd） | — |
| `privesc-suid-set` «文件被设置了 setuid 或 setgid 位» | 匹配 | 高 | 在软件包管理器之外对文件（而非目录）执行 `chmod u+s`/`g+s`（auditd） | — |
| `privesc-setcap` «设置了文件 capabilities» | 匹配 | 高 | `setcap ... cap_...` | — |
| `privesc-kernel-module` «从会话中加载内核模块» | 匹配 | 高 | 从某个用户的会话中加载或移除模块（auditd） | — |
| `privesc-ptrace` «用 ptrace 附加进程» | 匹配 | 中 | `PTRACE_ATTACH` 或 `PTRACE_SEIZE`（auditd） | — |
| `privesc-denied-burst` «大量文件访问被拒绝（枚举）» | 阈值 | 中 | 同一用户被拒绝访问的文件（`EACCES`、`EPERM`）（auditd） | 60 秒内 30 次 |
| `privesc-sensitive-denied` «试图读取密码哈希或 root 的文件» | 匹配 | 中 | 用户被拒绝访问 `/etc/shadow`、`/etc/gshadow`、`/etc/sudoers`、`/etc/sudoers.d/` 或 `/root`（auditd） | — |
| `privesc-history-tampering` «shell 历史记录被清除或关闭» | 匹配 | 中 | `ln -s /dev/null ~/.bash_history`、`rm .bash_history`...；`unset HISTFILE`、`HISTFILE=/dev/null`、`HISTSIZE=0`、`history -c`、`set +o history` 仅在命令行（`bash -c`）中才能看到，因为内置命令不运行程序 | — |
| `privesc-audit-stop-command` «关闭 auditd 的命令» | 匹配 | 严重 | `auditctl -e 0`、`auditctl -D`、`auditctl -a never`、`systemctl stop/disable/mask auditd`、`service auditd stop`、`pkill auditd`、删除 `/var/log/audit` 或 `/etc/audit` | — |
| `privesc-audit-disabled` «审计被关闭» | 匹配 | 严重 | 内核报告 `audit_enabled=0`（auditd） | — |
| `privesc-auditd-stopped` «auditd 被某个进程停止» | 匹配 | 高 | auditd 应 init 以外的进程的请求而停止（服务器关机不会被报告） | — |
| `privesc-crash` «setuid 程序或临时程序崩溃» | 匹配 | 中 | 某个 setuid 程序或位于临时目录中的程序崩溃（auditd `ANOM_ABEND`）：通常是一次失败的漏洞利用 | — |

每条告警都有一个固定的名称、一段描述（以可粘贴到 localSIEM 搜索中的查询结尾）以及详细信息：用户、账户类型（`root`、`admin`、`user`、`service`）、真实用户和有效用户、命令、程序、目录、终端、会话、来源（`auditd`、`snoopy`、`syslog`）、客户端 IP，以及在适用时的父程序、解释器、被更改的文件及其组、统计到的侦察命令、capabilities、设置的模式、ptrace 请求和文件访问被拒绝时的错误。告警发出时，还会附带会话的上下文：是否看到了会话的开始、是否经过了 sudo 或 su、其 SSH 地址以及其**最近 20 条命令**，这样分析师无需搜索即可了解导致该告警的经过。

同一条命令可能被多个来源（auditd 和 snoopy）看到：告警按模块、用户、IP、类别和严重级别分组，因此仍只产生一条告警。命令行中的密码（`mysql -p...`、`sshpass -p`、`curl -u user:pass`、`PASSWORD=...`、带密码的 URL）在存储任何内容之前都会被脱敏，审计记录中的十六进制内容也不例外。

<a id="privesc-doctor"></a>
## 14. 权限提升模块的前提条件：诊断

**前提条件。** 该模块需要一个 `localsiem` 用户可以读取的来源（文件存在且 `localsiem` 能够打开它）：**auditd** 日志（auditd 正在运行，且不在容器中），或包含 sudo、su、pkexec 和 doas 记录的 **syslog** 文件（`/var/log/auth.log`、`/var/log/secure` 或 `/var/log/messages`，或设置项 **Syslog 文件** 中指定的文件，除非**读取 syslog** 设为从不），如果安装了 **snoopy**，它还会在其中写入运行的每个程序。其中任何一个即可。如果某个来源存在但 `localsiem` 无法读取，该前提条件会说明这一点，并附上授予读取权限的命令（对于审计日志，是模块页面上的命令 `manage.py setup-modules`；对于 syslog，是 `setfacl -m g:localsiem:r <file>`）。如果一个都没有，它会说明需要安装什么：auditd（Debian：`apt-get install auditd`；Alpine：`apk add audit && rc-update add auditd && rc-service auditd start`）、syslog 守护进程（Debian：`apt-get install rsyslog`；Alpine：`apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`）或 snoopy。在此之前，模块保持停用；**重新配置**会再次检查。它不会自行安装任何东西。首次安装时，这些日志通常属于 root：请运行 Web 界面显示的命令，然后点击**重新配置**。

诊断的运行方式与 Apache 的诊断相同（第 7 节）。它只描述模块凭借服务器现有条件能看到什么、看不到什么；它提供的修复只有需要安装的软件包和 `localsiem` 的读取权限。它从不建议更改审计规则、`auditd.conf`（`log_group` 除外，见下文）、`snoopy.ini`、shell 或任何其他配置：

| 检查项 | 正常条件 | 否则 |
|---|---|---|
| auditd | auditd 正在运行 | 如果未安装，报警告（Debian：`apt-get install auditd`；Alpine：`apk add audit && rc-update add auditd && rc-service auditd start`）；如果已安装但已停止，报警告，不提供修复（是否运行由管理员决定）。在容器内报信息：auditd 无法在其中运行。 |
| 审计日志 | `localsiem` 可以读取它 | 错误，附带模块页面上的命令；如果 auditd 正在运行，但其日志不在模块查找的位置（设置项**审计日志**），报警告 |
| 审计日志的组 | 审计日志不属于 `root` 组 | 如果属于（`auditd.conf` 中的 `log_group = root`），报警告：auditd 轮转时创建的每个日志的权限都是 600，只有 root 可读，localSIEM 将无法继续读取。修复方法是在 `/etc/audit/auditd.conf` 中添加 `log_group = adm` 这一行（然后重启 auditd）：新日志将以 640 权限创建。 |
| 审计规则的记录 | 已读取到程序运行（`EXECVE`）记录 | 如果 auditd 在写入日志，但其中没有任何程序运行记录，报警告：服务器的审计规则没有记录 `execve`，因此无法通过 auditd 看到脚本、web shell 和漏洞利用执行的命令。同时报信息，说明这些规则到目前为止还记录了哪些内容（敏感文件的变更、setuid 位、内核模块、ptrace、被拒绝访问的文件）以及哪些尚未记录 |
| syslog | 正在读取 syslog 文件 | 如果无法读取，报错误（`setfacl -m g:localsiem:r <file>`）；如果既没有可用的审计日志也没有 syslog 文件，报警告（Debian：`apt-get install rsyslog`；Alpine：`apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`） |
| snoopy | 已安装，且正在读取其日志行 | 没有 auditd 时报警告：看不到脚本和 web shell 执行的命令（Debian：`apt-get install snoopy`；Alpine 没有软件包：需从源码编译）。如果已安装但未读取 syslog，报警告。如果其日志行中没有有效 uid（`snoopy.ini` 的 `message_format`），报信息：无法通过 snoopy 看到从 setuid 程序继承的 root |
| 模块能看到的内容 | — | 信息：auditd（及其规则记录的内容）、snoopy（运行的每个程序），或者作为警告：只有 sudo、su、pkexec 和 doas（没有 snoopy 的 syslog：大多数规则无法触发）；如果什么都无法读取，报错误。它还会提醒：shell 的内置命令永远看不到 |
| 1.0.0 版本的文件 | — | 如果发现了 `--configure-privesc` 留下的文件，报信息，不提供修复（第 15 节） |
| setuid 程序和 capabilities | — | 信息：最近一次扫描（第 16 节）。对能提供 root shell 的 setuid 程序（GTFOBins）以及其 capabilities 实际上等同于 root 的程序报警告，不提供修复 |
| 敏感文件 | 没有可被 root 以外的人写入的文件 | 对每个这样的文件报错误，不提供修复（`/etc/passwd`、`sudoers`、cron、`/etc/profile.d`、root 的 `PATH` 中的目录、`docker.sock`...） |
| 特权组 | — | 列出 `docker`、`lxd`、`incus-admin`、`disk` 和 `libvirt` 组的成员，报警告，不提供修复：他们实际上等同于 root |

<a id="privesc-legacy"></a>
## 15. 从权限提升模块 1.0.0 版本更新而来的服务器

该模块的 1.0.0 版本有配置选项 `--configure-privesc` 和一个 bash 钩子；1.1.0 版本将两者都移除了，因为模块从不在 `/opt/localsiem` 之外安装或更改任何东西。应用过该选项的服务器会保留它写入的内容，localSIEM 既不使用也不删除这些内容：

- `/etc/audit/rules.d/90-localsiem-privesc.rules`：其审计规则（键为 `lsiem_*`）。只要这些规则已加载，模块就会像读取服务器上其他规则的记录一样读取它们的记录。
- `/etc/localsiem-privesc/`（钩子）、`/etc/profile.d/localsiem-privesc.sh`，以及 `/etc/bash.bashrc`（Debian）或 `/etc/bash/bashrc`（Alpine）中跟在«localSIEM privesc: command hook»之后的那一行：只要它们存在，每个交互式 bash 都会继续将其命令写入 `/var/log/localsiem-privesc/`，而没有人读取这些内容。
- `/var/log/localsiem-privesc/`：每个用户的命令文件。
- `/etc/audit/auditd.conf` 中的 `log_group = adm`、`/root/.ssh`（创建时为空）以及 `/etc/snoopy.ini` 的 `message_format`：它们可以保留（`log_group = adm` 使轮转后的审计日志保持可读，见第 14 节；模块既能读取 snoopy 的该格式，也能读取其默认格式）。

诊断会列出它能看到的这些内容（检查项«Files of version 1.0.0 of the module»）。要移除它们，请以 root 身份：删除规则文件并重新加载规则（`augenrules --load`）；删除 `/etc/profile.d/localsiem-privesc.sh`、`/etc/localsiem-privesc/` 以及 bashrc 中的那一行；如果您不想保留 `/var/log/localsiem-privesc/` 中的命令，请将其删除。

<a id="privesc-health"></a>
## 16. 权限提升模块的攻击面和健康警告

除了其规则之外，该模块还会检查服务器本身，并向 SOC 发送：

| 警告 | 严重级别 | 触发条件 |
|---|---|---|
| 新的 setuid 或 setgid 程序 | 高 | 扫描发现了上一次扫描中没有的 setuid 或 setgid 程序（第一次扫描仅作为基准）。成为 root 的攻击者常常会留下一个 setuid shell；软件包更新也可能添加这样的程序。 |
| 可写目录中的新 setuid 程序 | 严重 | 同上，位于 `/tmp`、`/var/tmp`、`/dev/shm`、`/home`、`/srv` 或 `/var/www` 中 |
| GTFOBins 中的新 setuid 程序 | 严重 | 同上，针对设置 setuid 后可提供 root shell 的程序（`bash`、`find`、`python`、`vim`、`less`、`cp`...） |
| 新的 capabilities | 高 | 某个程序获得了实际上等同于 root 的 capabilities（`cap_setuid`、`cap_dac_override`、`cap_sys_admin`...） |
| 可被 root 以外的人写入的敏感文件 | 严重 | 每小时检查一次：`/etc/passwd`、`/etc/shadow`（所有人可读也算）、`sudoers`、cron、`/etc/profile.d`、PAM、服务、`ld.so.preload`、root 的 `PATH` 中的目录、`docker.sock`...。每个文件的每个问题只报告一次。 |
| auditd 已停止（localSIEM 的健康警告） | 高 | auditd 曾经在运行，但现在不再运行（容器之外） |

扫描在后台运行，最多每隔 **setuid 程序扫描间隔（小时）** 运行一次（第一次在采集器启动五分钟后），以 `localsiem` 用户身份遍历**扫描的目录**（无法读取的内容会被跳过），并在扫描 300 万个文件或 15 分钟后停止。其结果，连同发现的 GTFOBins 程序和 capabilities，会显示在诊断中。这些警告的严重级别位于模块的 `severity.yaml` 中。已报告过的内容在重启后仍会被记住。

<a id="cli"></a>
## 17. 命令行

以 root 身份运行 `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <command>`：

| 命令 | 用途 |
|---|---|
| `modules` | 已安装的模块：ID、版本、已启用、已停用或未加载，以及目录，如果缺少前提条件，还会列出所缺少的前提条件；以及无法加载的模块及其错误 |
| `doctor` | 对于每个已启用的模块：每项检查（`✓`、`!`、`✗`、`·`）及修复它的配置片段，以及找到的来源；对于因缺少前提条件而停用的模块，列出其前提条件。`--json` 以 JSON 格式输出相同的内容。 |
| `read-paths` | 模块读取的目录，localSIEM 以 root 身份授予对这些目录的读取权限 |
| `setup-modules [--no-restart]` | 以 root 身份运行：即 Web 界面显示的命令；授予对模块目录（`read_paths`）的读取权限并重启 localSIEM（`--no-restart`：不重启）。模块没有配置选项 |

以 `localsiem` 用户身份运行诊断，以查看其实际权限：

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
