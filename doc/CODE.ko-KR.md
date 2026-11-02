# localSIEM-modules 코드 참조

이 CODE는 다음 언어로도 제공됩니다:\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), ko-KR, [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## 목차

1. [아키텍처와 설계 결정](#architecture)
2. [모듈 맵](#modules)
3. [주요 심볼](#symbols)
4. [주요 호출 경로](#flows)
5. [진입점](#routes)
6. [영향 분석](#impact)
7. [확장 지점](#extensions)

[설치](README.ko-KR.md) · [사용자 매뉴얼](MANUAL.ko-KR.md) · [localSIEM 코드 참조](../../localSIEM/doc/CODE.ko-KR.md)

<a id="architecture"></a>
## 1. 아키텍처와 설계 결정

이 프로젝트에는 localSIEM(형제 프로젝트 `../localSIEM`)의 설치 가능한 모듈이 들어 있습니다. 자체 서비스나 설치 프로그램은 없습니다. 모듈은 localSIEM 웹의 모듈 › 설치 가능에서만 설치하며(업데이트와 제거는 모듈 › 설치됨에서 합니다), 웹은 이 저장소(브랜치 `main`)를 내려받아 각 모듈 폴더 `mod-<name>/`를 `/opt/localsiem/modules/<name>/`에 복사합니다. localSIEM 설치 프로그램은 코어만 설치하며 모듈은 절대 설치하지 않고, localSIEM에는 자체 모듈이 없습니다. localSIEM 프로세스(수집기, 웹, `manage.py`)가 모듈을 불러옵니다. `mod-` 접두사는 이 저장소의 폴더 이름에만 붙습니다. 모듈 자체(`module.json`의 `id`, 옵션, 설정, 설치된 폴더)는 접두사 없는 이름을 유지합니다. 현재 모듈은 두 개입니다: `apache2`(폴더 `mod-apache2/`)와 `privesc`(폴더 `mod-privesc/`).

### 모듈이 코어 밖에 있는 이유

localSIEM의 코어([backend/core/](../../localSIEM/backend/core/))는 범용입니다. 스토리지, 검색, 규칙 엔진, 그룹화, SOC 대기열, 하트비트, 상태 점검은 Apache에 대해 아무것도 모릅니다. 서비스가 의미하는 것(로그가 어디에 있는지, 로그를 어떻게 나누고 파싱하는지, 레코드가 어떻게 하나의 이벤트가 되는지, 무엇을 이미 해결된 것으로 간주하는지, 그 규칙과 요구 사항)은 모듈에 있습니다. 모듈을 별도 프로젝트에 두면 다음과 같은 이점이 있습니다:

- 모듈은 버전이 매겨지고(`version`), 필요한 최소 localSIEM 버전을 선언하며(`core`), 새 localSIEM 릴리스 없이 업데이트, 추가하거나 끌 수 있습니다.
- 코어는 이름으로 모듈을 가져오지 않으며 자체 모듈도 없습니다. 레지스트리([backend/core/registry.py](../../localSIEM/backend/core/registry.py))는 웹이 이 저장소의 모듈을 설치하는 `/opt/localsiem/modules/`(개발용 사본에서는 `LOCALSIEM_MODULES_PATH`)만 검사합니다.
- 불러오지 못한 모듈이 다른 모듈을 멈추게 하는 일은 없습니다. 그 오류는 웹(상태 «오류»)과 `manage.py modules`에 표시됩니다.
- 모듈은 코어를 절대 수정하지 않습니다. `backend/core/module.py`와 `backend/core/registry.py`가 계약의 전부입니다.

### 계약: module.json, locales, Module 하위 클래스

**`module.json`**(`fReadManifest`가 확인):

| 키 | 기본값 | 의미 | apache2 | privesc |
|---|---|---|---|---|
| `id` | 필수 | `mod-` 접두사를 뺀 모듈 폴더 이름(설치된 폴더의 이름), `[a-z][a-z0-9_]{1,31}`. 클래스의 `vName`이기도 합니다 | `apache2` | `privesc` |
| `version` | `"0"` | 모듈의 버전으로, 웹과 `manage.py modules`에 표시됩니다 | `1.3.2` | `1.1.2` |
| `core` | `"0"` | 필요한 최소 localSIEM 버전. 설치된 localSIEM의 `cVersion`보다 높으면 모듈을 불러오지 않습니다 | `2.2.0` | `2.2.0` |
| `entry` | 필수 | `"file:Class"`: `file`은 `.py`를 뺀 이름(`[a-z][a-z0-9_]{0,63}`), `Class`는 `Module`의 하위 클래스 | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | 관리자가 결정할 때까지 실행되는지 여부(`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | localSIEM이 root로 `localsiem` 사용자에게 읽기를 허용하는 절대 경로 폴더(설치 후, **재구성** 후, 이 값을 바꾸는 업데이트 후 웹에 표시되는 명령) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | 모듈에 필요한 소프트웨어를 서버에 root로 설치하는 명령으로, 시스템별(`debian`, `alpine`)로 지정합니다. 한 줄에 명령 하나이며 셸 연산자는 쓸 수 없습니다. 웹은 앞에 `sudo`를 붙인 형태로도 표시하기 때문입니다(코어의 `fCheckInstallRequirements`). 모듈 › 설치 가능 › 요구 사항에 표시되며, 절대 실행되지 않습니다 | Debian: Apache, ModSecurity 2, CRS, `a2enmod`, 없는 경우 권장 ModSecurity 구성, 재시작. Alpine: Apache | Debian: auditd와 rsyslog. Alpine: auditd |
| `setup_option` | — | 어떤 모듈도 사용하지 않습니다. 모듈은 서버를 절대 변경하지 않으므로 코어는 이를 무시합니다(레지스트리가 버립니다). 이전 버전의 `module.json` 파일에는 아직 남아 있을 수 있습니다 | 설정 안 됨 | 설정 안 됨(`--configure-privesc`는 1.1.0에서 제거됨) |
| `settings` | `[]` | 각 설정의 설명. 웹은 이것으로 양식을 만듭니다 | 설정 6개 | 설정 13개 |

각 설정에는 `key`(`[a-z][a-z0-9_]{1,31}`), `type`, 대개 `default`, 그리고 유형별 속성이 있습니다. `fValidateSettings` / `fCleanValue` / `fCleanRecords`가 관리자가 저장하는 값을 확인합니다:

| 유형 | 속성 | 웹 컨트롤 | 허용되는 값 |
|---|---|---|---|
| `boolean` | — | 체크박스 | `true` / `false` |
| `integer` | `min`, `max` | 숫자 필드 | `min`..`max` 범위의 정수 |
| `string` | `max_length` (500) | 텍스트 필드 | 제어 문자가 없고 앞뒤 공백을 제거한, 최대 `max_length`자의 텍스트 |
| `path` | — | 고정폭 텍스트 필드 | 비어 있거나 절대 경로(`/`로 시작), 최대 1024자 |
| `choice` | `choices`(필수), `required` | 목록(필수가 아니면 «—» 포함) | `choices` 중 하나 또는 빈 값 |
| `records` | `fields`(필수: 다른 유형의 설정), `max_items` (50) | 레코드마다 블록 하나, 추가와 삭제 버튼 포함 | 최대 `max_items`개의 레코드 목록. 각 필드를 확인하며, `required` 필드는 비울 수 없고 빈 필드는 버립니다 |

**`locales/<language>.json`**(de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN)은 `fReadTexts`가 읽고 웹이 표시합니다(`modules.js fModuleText`, 텍스트가 없으면 en-US로, 그다음 키로 대체):

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

로캘 파일이 없거나 손상되면 그 언어만 사용할 수 없게 됩니다.

**`Module` 하위 클래스**([backend/core/module.py](../../localSIEM/backend/core/module.py)). 레지스트리는 이를 `Class(pSettings, pMasker, pStorage, pManifest)`로 생성합니다. 훅은 다음과 같습니다:

| 훅 | 호출하는 쪽 | 기본값 | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | 수집기, 스토리지가 준비되면 한 번 | 없음 | `apache.first_start` 저장(학습 기간의 시작) | `privesc.first_start` 저장. `privesc.sessions`, `privesc.surface`, `privesc.health` 로드 |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | 수집기, 웹 | `module.json` 기본값 위에 `modules.<id>` 적용 | 상속 | 상속. `mReload`는 `mSettings` 캐시도 비웁니다 |
| `mDiscoveryInterval()` | 수집기(활성화된 모듈 중 가장 짧은 값, 최소 60초) | `discovery_interval_seconds` 또는 3600 | 상속 | 상속(기본값 300) |
| `mDiscover()` | 수집기(시작, 간격, 다시 불러오기, 진단 요청), `manage.py doctor` | `[]` | Apache 구성과 직접 추가한 소스에서 얻은 소스 `{key, path, kind, format, vhost, audit_type, storage_dir}` | `fDiscoverSources`: 감사 로그와 syslog |
| `mCreateFramer(pSource)` | 수집기, 소스마다 | `LineFramer` | 네이티브 직렬 감사 로그에는 `AuditFramer` | 상속(`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | 수집기, 단위마다 | 필수 | `access`, `error` 또는 `audit` 레코드 | `audit` 또는 `syslog` 레코드 |
| `mCreateCorrelator()` | 수집기, 시작 시 | 필수 | `Correlator`(코어 설정의 기간과 약한 상관관계) | `Correlator`: 감사 레코드는 일련번호별(EOE 또는 2초), syslog 줄은 즉시 |
| `mBuildEvent(pTransaction)` | 수집기, 기한이 된 트랜잭션마다 | 필수 | `action`과 `detections`가 있는 이벤트 | 규칙이 일치시키는 플래그가 있는 이벤트. 자체 탐지는 없음 |
| `mRulesPath()` / `mRuleFunctions()` | 수집기, 규칙을 불러올 때 | `None` / `{}` | 자기 폴더의 `rules/` / `{"apache2.new_php": mIsNewPhp}` | 자기 폴더의 `rules/` / 상속된 `{}` |
| `mDetectionFromSignal(pEvent, pSignal)` | 수집기, 규칙 신호마다(선택 사항: `hasattr`로 확인) | 일반 탐지 | 요청 세부 정보와 `{rule: {id, count}}`가 있는 탐지 | 사용자, 명령, 프로그램, 세션, 부모, 파일 등이 있는 탐지 |
| `mEnrich(pDetection)` | 수집기, 그룹과 함께, 알림을 만들기 전 | `{}` | 최근 1시간 동안의 IP 컨텍스트 | 세션 컨텍스트: 시작 확인 여부, 관문, SSH 주소, 최근 명령 20개 |
| `mDoctor()` | 수집기(상태 `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor`(auditd와 그 규칙이 기록한 것, syslog, snoopy, 모듈이 보는 것, 버전 1.0.0의 파일, 공격 표면) |
| `mHealth(pNow)` | 수집기, 60초마다, 활성화된 모듈만 | `[]` | ModSecurity 언로드 또는 Off, 실제 클라이언트 IP 없음(최대 300초마다) | 세션 저장. 검사 결과. 300초마다: auditd 중지, 쓰기 가능한 민감한 파일(매시간), setuid 프로그램 검사 시작 |
| `mSkipped()` | 수집기 상태, `manage.py doctor` | `[]` | 파이프 로그, `GlobalLog`에 포함된 로그, 데이터가 없는 액세스 로그(`format_without_data`) | 읽지 않는 syslog(auditd 실행 중, `syslog_mode` never), 감사 로그 없음 |
| `mSetLowDisk(pLowDisk)` | 수집기, 디스크 수준 | 없음 | 감사 헤더와 본문 저장 중지 | 상속 |
| `mDisplayRecord(pRecord)` | 웹, 요청 카드 | `{}` | 저장된 감사 레코드의 헤더와 본문(`fAuditDisplay`) | 상속 |
| `mRequirements()` | 코어, localSIEM 2.2.0 이상: 첫 설치, 수집기 시작과 다시 불러오기, 웹의 **재구성**, `manage.py modules`와 `doctor` | `[]`(요구 사항 없음) | `apache_config`와 `modsecurity`(`fRequirementChecks`) | `command_source`: `localsiem`이 읽을 수 있는 아무 소스, 즉 감사 로그(auditd 실행 중, 컨테이너 밖) 또는 syslog(snoopy가 설치되어 있으면 snoopy 포함). 소스가 있지만 읽을 수 없으면 `audit_log` / `syslog` |

코어에는 더 이상 `mSetupSnippet`도 `mApplySetup`도 없습니다. 모듈에는 구성 옵션이 없으며 서버를 절대 변경하지 않습니다.

레코드는 `time`, `received`, `module`(ID. 수집기는 이것으로 상관 분석기를 고릅니다), `source`, `source_key`, `correlation`, `parse_status`(`ok`, `partial`, `unparsed`), `fields`, `raw`(마스킹됨)를 가진 dict이며, 선택적으로 `search`(전체 텍스트 검색용으로 색인되는 텍스트)를 가집니다. 이벤트는 events 테이블의 열(`storage_sqlite.py`의 `lEventColumns`)과 `record_ids`, `rule_hits`, `detections`를 가집니다. 탐지는 `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time`, `uid`를 가집니다.

### 요구 사항: 모듈은 감시하는 대상을 절대 설치하지 않습니다

모듈을 설치해도 모듈이 감시하는 소프트웨어는 절대 설치되지 않습니다. apache2 모듈은 Apache도 ModSecurity도 설치하지 않으며, privesc 모듈은 auditd, syslog 데몬, snoopy 중 어느 것도 설치하지 않습니다(그 요구 사항인 `command_source`는 `localsiem` 사용자가 읽을 수 있는 아무 소스, 즉 컨테이너 밖에서 auditd가 실행 중인 감사 로그 또는 syslog입니다. `mod-privesc/doctor.py`의 `fRequirementChecks`). 모듈을 켜기 전에 필요한 것은 모듈 자신이 `mRequirements()`(localSIEM 2.2.0 이상)에서 정의합니다. 진단 형식의 검사 목록이며, 상태가 `error`인 검사가 하나도 없으면 충족됩니다. apache2 모듈은 `apache_config`(Apache 구성을 찾음: `apache2.conf`, `httpd.conf` 또는 `config_file` 설정의 파일)와 `modsecurity`(`mod_security2`가 로드됨. ModSecurity 3은 해당하지 않음)를 반환하며, `fRequirementChecks`가 이를 진단의 첫 검사들에서 가져옵니다. Apache가 없으면 둘 다 오류입니다. 그 소프트웨어를 설치하는 방법은 `module.json`의 `install_requirements`에 선언합니다. 웹은 모듈을 설치하기 전에(모듈 › 설치 가능 › 요구 사항) 서버의 시스템에 맞는 명령을 표시하며, 절대 실행하지 않습니다. 코어:

- 첫 설치에서 요구 사항이 없고 관리자가 한 번도 결정하지 않았으면 모듈을 꺼진 상태로 설치합니다(`modules.<id>.enabled = false`). 업데이트는 `enabled`를 절대 바꾸지 않습니다.
- 요구 사항이 없는 동안에는 모듈을 켤 수 없게 합니다. 스위치가 잠기고 웹은 요구 사항을 그 `fix`와 함께 표시합니다.
- 켜져 있는 모듈이 요구 사항을 잃어도 스스로 끄지 않습니다. 진단과 상태 경고(`mHealth`: «ModSecurity is no longer loaded»)가 이를 보고하며, 모듈을 끄면 이 경고들이 나오지 않게 되기 때문입니다.
- 수집기가 시작되거나 다시 불러올 때, 그리고 모듈 페이지의 **재구성**으로(모듈이 꺼져 있을 때도) 요구 사항을 다시 확인합니다. 충족되면 스위치 잠금을 해제하고, 관리자가 모듈을 켜며, 웹은 설치 후에 생성된 로그를 `localsiem`이 읽을 수 있도록 root로 실행할 명령(`read_paths`)을 표시합니다.

### 네임스페이스 패키지로 로드

어디에도 `__init__.py`가 없습니다(Python 3.13의 암시적 네임스페이스 패키지). `fRegisterPackage`는 모듈 폴더를 `__path__`로 하는 `localsiem_modules` 패키지를 만들고, `fLoadClass`는 `localsiem_modules.<id>.<file>`을 가져와 클래스가 `Module`인지, 그 `vName`이 `id`와 같은지 확인합니다. 모듈 코드에 대한 결과는 다음과 같습니다:

- 모듈 자체의 파일은 **상대 경로로** 가져옵니다(`from .parsers import AccessParser`).
- 코어는 **`backend.core...`**로 가져옵니다(`from backend.core.module import Module`). localSIEM 프로세스가 localSIEM 폴더를 `sys.path`에 넣습니다.
- 표준 라이브러리와 localSIEM의 의존성(가상 환경 `/opt/localsiem/venv/`, 예: PyYAML)만 사용할 수 있습니다. localSIEM은 모듈을 위해 아무것도 설치하지 않습니다.

### 매니페스트로 만드는 설정 양식

모듈에는 자체 HTML이 없습니다. 웹은 `module.json`의 `settings`와 `locales/`의 텍스트를 읽어 양식을 만들고(`modules.js fBuildSettings`, `fRecordsEditor`), 저장되는 값을 `fValidateSettings`로 검증하며, 관리자가 저장한 값만 `settings.json`의 `modules.<id>` 아래에 저장합니다. `enabled`도 그곳에 있습니다. 모듈은 `mModuleSettings()`를 읽습니다. 즉 `module.json`의 기본값 위에 저장된 값을 덮어쓴 것입니다. 따라서 설정을 추가해도 웹이나 코어를 변경할 필요가 없습니다.

apache2 모듈이 `self.dSettings`에서 함께 읽는 코어 설정: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`), `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()`는 `module.json`이 선언하지 않은 `modules.apache2` 아래의 저장된 키도 전달합니다. `mDiscover`는 이렇게 `document_roots`(`{vhost: folder}`, 탐색된 DocumentRoot 위에 적용)를 읽으며, 이 값은 `settings.json`을 직접 편집해야만 설정할 수 있습니다.

### «수행된 조치» 원칙

SOC로는 아직 아무도 해결하지 않은 것만 보냅니다. apache2 모듈에서는 수행된 조치를 가장 신뢰할 수 있는 소스에서 읽습니다. 먼저 감사 로그(네이티브 형식은 `Action: Intercepted (phase N)`, JSON은 `audit_data.action.intercepted/phase`), 그다음 error.log(`Access denied with code NNN (phase N)`)입니다. ModSecurity의 흔적이 없는 403은 차단이 아닙니다(`fields.doubtful_block`).

| 상황 | `action` | 탐지(SOC로 보냄) |
|---|---|---|
| 1-2단계에서 가로챔(애플리케이션이 요청을 받지 못함) | `blocked` | 없음: `mAssess`가 `None`을 반환. 이후 알림의 컨텍스트에서 집계됨 |
| 3-4단계에서 가로챔 | `none` | 예, `blocked_late`(높음), 또는 데이터베이스 오류가 있으면 `success_indicator` |
| 엔진이 `DetectionOnly`일 때의 일치 | `none` | 예 |
| 이상 임계값 미만의 일치 | `none` | 예, `below_threshold`(낮음) |
| YAML 규칙의 신호 | `none` | 예 |

심각도는 `severity.yaml`에서 가져옵니다(`fLoadSeverityTable`. 파일이 없거나 값이 잘못되면 내장 기본값을 유지): `crs_not_blocked_2xx` 높음, `crs_not_blocked_other` 중간, `blocked_late` 높음, `success_indicator` 심각(차단되지 않은 아웃바운드 규칙 950-955, 또는 같은 요청의 데이터베이스 오류), `below_threshold` 낮음(코어 설정 `below_threshold_severity`가 우선). «임계값 이상»은 949xxx 규칙이 일치했거나 ModSecurity가 밝힌 점수가 임계값에 도달했다는 뜻입니다. 규칙 심각도로 계산한 점수는 추정치일 뿐 판단 기준이 되지 않습니다. 임계값은 메시지에 있는 값, 없으면 `anomaly_threshold`, 없으면 `crs-setup.conf`의 값, 없으면 5입니다.

### apache2 모듈의 동작 방식

1. **탐색**(`discovery.py`): `ApacheConfig`는 `apache2ctl` 없이 `localsiem` 사용자로 구성을 직접 읽습니다(`Include`, `IncludeOptional`, `Define`, Debian `envvars`의 `${VARS}`, `<VirtualHost>`, 로드된 모듈 기준의 `<IfModule>`). `fDiscoverSources`는 `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog`, `SecAuditLog`를 고정 키 `apache:<kind>:<real path>`를 가진 소스로 바꿉니다. 형식에 `%v`가 있는 `GlobalLog`는 모든 vhost를 포함합니다(다른 액세스 로그는 건너뜀). 파이프 로그와 syslog는 건너뛰며, 형식에 `%` 지시자가 없는 액세스 로그도 건너뜁니다(Apache는 어떤 `LogFormat`도 정의하지 않은 별칭을 그대로 기록합니다: `format_without_data`. 단, 데이터가 있는 다른 `CustomLog`가 같은 파일에 기록하면 예외. 로그 형식은 절대 변경하지 않으므로 진단은 해결 방법 없이 이를 알려 줍니다). 직접 추가한 소스가 먼저 오며, 파일은 한 번만 읽습니다.
2. **프레이밍과 파싱**(`parsers.py`, `logformat.py`, `modsec.py`): 액세스 줄은 해당 `LogFormat`으로 생성한 정규식으로 파싱합니다(마지막으로 성공한 형식을 먼저 시도). 오류 줄은 분류합니다(`modsecurity`, `database`, `php`, `crash`, `apache`). 감사 레코드는 JSON(한 줄, `matched_rules` 앞에서 자름), 네이티브 직렬(`AuditFramer`가 `--id-A--`부터 `--id-Z--`까지 결합) 또는 동시(색인 줄이 `SecAuditLogStorageDir` 아래의 파일을 가리킴)로 읽습니다. 모든 것을 마스킹하며, 맞지 않는 것은 `unparsed`로 보관합니다.
3. **상관관계**(`correlate.py`): 같은 `UNIQUE_ID`를 가진 레코드가 하나의 트랜잭션을 이루며, 트랜잭션은 상관관계 기간과 따라잡는 중인 소스의 워터마크만큼 기다립니다. `UNIQUE_ID`가 없는 액세스 줄(Apache가 기본으로 기록하는 형식)은, 그 줄이나 해당 요청의 레코드가 기한이 되면 `mPair`가 액세스 줄이 없는 ModSecurity 레코드와 짝짓습니다: 같은 클라이언트 IP, ±2초 이내의 시각(줄은 초 단위), 그리고 양쪽이 모두 알고 있으면 같은 메서드, URI, 상태, 경로. 이 중 더 많이 일치하는 후보가 이기고, 그다음은 가장 가까운 후보, 그다음은 가장 오래된 후보이며, 이벤트는 약한 상관관계로 표시됩니다. `UNIQUE_ID`가 없는 error.log 줄은 해당 IP의 가장 가까운 트랜잭션에 즉시 결합됩니다. `UNIQUE_ID`와 error.log의 ModSecurity 줄이 있는 트랜잭션은, 감사 레코드가 들어오는 동안(`vAuditSeen`) 자신의 감사 레코드도 기다리며(`mWaitsForAudit`), 첫 레코드부터 최대 `cAuditWaitSeconds`(120초)까지 기다립니다. ModSecurity는 요청이 실행되는 동안 규칙의 줄을 기록하고 요청이 끝날 때 감사 레코드를 기록하므로, 그렇지 않으면 느린 요청이 두 이벤트가 됩니다. 감사 레코드가 도착하면 액세스 줄에는 `cAfterAuditSeconds`(2초)가 더 주어집니다.
4. **이벤트**(`ApacheModule.mBuildEvent`): 필드는 액세스, 그다음 감사, 그다음 오류 순으로 고릅니다. vhost는 `%v`에서, 없으면 감사 레코드의 Host 헤더와 로컬 포트에서 가져옵니다(`mVhostName`). 액세스 줄이 초 단위이면 감사 레코드의 시각을 사용합니다. `fSummarize`가 규칙, 범주, 점수, 임계값, 가로채기를 제공하며, 수행된 조치와 `mAssess`가 탐지를 결정합니다.
5. **규칙, 보강, 진단, 상태**: `rules/`의 YAML 규칙이 모든 이벤트에 대해 실행됩니다(코어 엔진). `mEnrich`는 IP의 컨텍스트를 추가합니다. `fRunDoctor`는 아무것도 변경하지 않고 요구 사항을 확인하고 로그를 설명합니다. `mHealth`는 ModSecurity와 실제 클라이언트 IP를 감시합니다. 모듈에는 구성 옵션이 없습니다. localSIEM은 root로 `localsiem`에 `/var/log/apache2` 읽기 권한을 주기만 합니다.

### 알아 둘 만한 설계 결정

- **자체 설치 프로그램 없음**: 모듈은 localSIEM 웹에서만 설치(모듈 › 설치 가능), 업데이트(모듈 › 설치됨의 **업데이트**), 제거(**제거**)합니다. 웹은 이 저장소를 내려받아 `backend/core/catalog.py`로 모듈을 설치합니다(안전한 압축 해제, 한 번에 하나의 설치, 폴더의 원자적 교체). root가 필요한 것(`read_paths`에 대한 읽기 권한)은 localSIEM이 처리합니다. 설치 후(그리고 `read_paths`를 바꾸는 업데이트 후) 웹이 root로 실행할 명령을 표시합니다.
- **클라이언트의 로그는 읽기만 합니다**: 모듈은 감시하는 서비스의 로그에 절대 쓰지 않고, 로그를 순환, 잘라내기, 이동, 삭제하지 않으며, 형식도 절대 변경하지 않습니다. apache2 모듈은 Apache나 ModSecurity 구성도 절대 변경하지 않습니다(`setup_option`이 없음). 서버가 자체 형식으로 로그를 기록하면(자체 `LogFormat`, `mod_remoteip`의 클라이언트 IP) 모듈이 그에 맞춥니다. `AccessFormat`은 각 액세스 로그의 `LogFormat`으로 파서를 만들고, `fCanPair` / `Correlator.mPair`는 `UNIQUE_ID`가 없는 줄을 결합합니다. 진단은 로그와 localSIEM이 로그에서 읽을 수 있는 것과 없는 것을 설명할 뿐입니다. `log_format`, `log_format_without_data`, `remoteip`, `audit_log`, `sanitise` 검사에는 `fix`가 없으며, 로그가 아닌 것(ModSecurity, CRS, `SecRuleEngine`, `mod_unique_id`, `localsiem`의 읽기 권한)에만 해결 방법이 있습니다. `--configure-apache`는 버전 1.3.0에서 제거되었습니다. `localsiem_combined`는 이미 이를 기록하는 서버를 위해 `dKnownFormats`에 남아 있으며, localSIEM 설치 프로그램은 이전 버전이 기록한 `localsiem.conf`를 삭제합니다(`--uninstall`, `--reinstall`).
- 감사 로그의 **파트 K**(`matched_rules`)와 **파트 E**(응답 본문)는 절대 저장하지 않습니다. 헤더와 본문은 마스킹된 원시 레코드에만 남으며, 요청 카드가 이를 재구성합니다(`fAuditDisplay`). 전체 텍스트 색인에는 축소된 텍스트가 들어갑니다(`search`: 요청 줄, 호스트, 사용자 에이전트, 각 규칙의 ID, 메시지, 데이터).
- **원시 텍스트는 마스킹된 부분으로 재구성합니다**: 원래 감사 레코드에는 비밀번호와 쿠키가 들어 있을 수 있습니다.
- **웹과 도구는 스토리지 없이 모듈을 생성합니다**(`WebContext.mModule`과 `manage.py`에서 `pStorage`는 `None`): 생성자와 이들이 호출하는 훅은 스토리지를 사용하면 안 됩니다.
- **이벤트 데이터베이스의 상태**: `apache.first_start`(학습 기간), `apache.health`(이미 보고한 것. 다시 시작해도 반복하지 않도록), `apache2.doctor`(수집기가 기록). 앞의 둘은 소스 키 `apache:<kind>:<real path>`와 마찬가지로 모듈이 apache2라고 불리기 전의 이름을 유지합니다. `apache` 모듈이 있던 서버는 학습 기간, 상태 기록, 읽기 위치를 그대로 유지합니다(소스 키가 새로 바뀌면 5 MiB 미만의 모든 로그를 처음부터 다시 읽게 됩니다). 상태 기록의 시각은 프로젝트의 기본 형식(`2026-10-29@13-59-59.723`, UTC)입니다. 이전 버전이 epoch 초로 저장한 상태는 불러올 때 변환됩니다.
- **경로의 안전성**: `mIsNewPhp`는 `..`를 거부하고 DocumentRoot 안에 머뭅니다. `fReadConcurrentEntry`는 `SecAuditLogStorageDir` 안에 머물며 최대 8 MiB를 읽습니다. 상관 분석기는 대기 중인 트랜잭션을 최대 50 000개까지 보관합니다.

### privesc 모듈의 동작 방식

질문은 «누군가 `whoami`를 실행했는가?»(관리자는 매일 실행합니다)가 아니라 «이 세션이 권한 상승의 경로를 밟고 있으며, 목적지에 도달했는가?»입니다. 모듈은 두 소스를 하나의 의미를 가진 이벤트로 바꾸고(`vhost`는 사람, `method`는 종류, `uri`는 명령, `path`는 프로그램이나 파일, `ip`는 SSH 주소, `score`는 세션의 서로 다른 정찰 수), 그 위에서 플래그를 계산하며, SOC로 보낼 것은 YAML 규칙이 결정하게 합니다.

1. **탐색**(`discovery.py`): `fDiscoverSources`는 감사 로그(`fAuditLogPath`: 설정, `auditd.conf`의 `log_file`, `/var/log/audit/audit.log`. auditd가 실행 중이고 `localsiem`이 아직 읽을 수 없을 때도 반환하여 코어가 이를 보고하게 함)와, `syslog_mode`에 따라 syslog(`fSyslogPath`)를 반환합니다(`auto`: auditd가 실행되지 않거나, 그 로그를 읽을 수 없거나, snoopy가 설치된 경우). 또한 진단에 필요한 것도 수집합니다: 컨테이너(`fContainer`, root 없이 읽을 수 있음: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), auditd 바이너리와 pid, snoopy, 각 로그를 읽을 수 있는지 여부(`fReadState`: `readable`, `unreadable` 또는 `missing`), 버전 1.0.0이 남긴 파일(`fLegacyLeftovers`). `Accounts`는 `/etc/passwd`, `/etc/group`, `UID_MIN`이 바뀌면 다시 읽고, uid를 `root`, `admin`(`admin_groups`의 구성원), `user` 또는 `service`로 분류합니다.
2. **파싱**(`parsers.py`): `fParseAuditLine`은 `type=... msg=audit(<time>:<serial>): k=v ...`, 사용자 공간 부분 `msg='...'`, `\x1d` 뒤의 보강된 부분을 읽고, `EXECVE`의 인수를 결합하며(`aN[i]` 조각으로 나뉜 것도 포함), 16진수 값(`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...)을 디코딩하고, **디코딩되고 마스킹된 값으로 원시 텍스트를 재구성합니다**(비밀번호의 16진수 표현을 그대로 두면 비밀번호도 남기 때문입니다). `search`에는 디코딩된 명령이 들어갑니다. `fParseSyslogLine`은 ISO와 전통적인 타임스탬프를 읽으며(busybox의 `facility.priority` 유무와 관계없이), `fParseSyslogMessage`는 snoopy(`uid:alice(1000)/root(0)`를 포함한 2.4와 2.5의 기본 형식, 그리고 버전 1.0.0이 설정한 형식), sudo, su(util-linux와 busybox), pkexec, doas, `pam_unix`, sshd를 이해합니다. `fMaskCommand`는 코어의 마스커보다 먼저 명령줄의 비밀번호를 마스킹합니다.
3. **상관관계**(`correlate.py`): 같은 일련번호를 가진 감사 레코드가 하나의 트랜잭션을 이루며, `EOE`에서, 레코드가 하나인 사용자 공간 유형(`USER_*`, `CRED_*`, `DAEMON_*`...)은 즉시, 또는 2초 동안 레코드가 없으면 기한이 됩니다. 대기 중인 트랜잭션은 최대 50 000개입니다. syslog 줄은 즉시 기한이 됩니다.
4. **이벤트**(`PrivescModule.mBuildEvent`): `mAuditEvent`는 유형별로 나눕니다: `EXECVE` → `mAuditExec`(`PATH` 레코드 또는 `stat`에서 얻은 프로그램의 setuid 비트, euid가 0이고 실제 uid는 0이 아니며 프로그램이 setuid가 아닐 때 `suid_escape`, `BPRM_FCAPS`에서 획득한 capability, `root_without_door`, root가 아닌 사용자의 인터프리터가 시작한 셸이 root로 실행될 때 `parent_interpreter`, 프로세스 메모리에서 얻은 부모); `USER_*`/`LOGIN` → `mAuditUser`(세션 시작, SSH 주소, 관문: sudo, su, pkexec, doas, run0, systemd의 `USER_START`/`USER_CMD`, 실패); `CONFIG_CHANGE`(`audit_disabled`, 규칙이 하나라도 제거되면 `audit_rule_removed`), `DAEMON_*`(보낸 쪽이 pid 1이 아니면 `auditd_stopped_manually`), `ANOM_ABEND`(`crash_suspicious`); 그 밖의 모든 `SYSCALL` → `mAuditSyscall`. 이는 규칙의 키가 아니라 시스템 호출(`fSyscallName`: 보강된 형식의 이름 또는 해당 아키텍처 테이블의 번호), 인수, `PATH` 레코드로 분류합니다: `denied`(사람에 대해 `EACCES`/`EPERM`으로 실패한 open, exec 또는 truncate), `kmod`, `ptrace`(`PTRACE_ATTACH`/`PTRACE_SEIZE`이면 `ptrace_attach`), `chmod`(setuid 또는 setgid 비트가 있는 모드, 폴더가 아닌 경우, `writer_allowed` 포함), `file`(`lSensitivePaths`의 경로 변경, `sensitive_group`과 `writer_allowed` 포함. 키는 `dKeyHints`를 통해 경로를 확인할 수 없을 때만 사용). `mSyslogEvent`는 snoopy를 `exec`로 처리하고(`stat`에서 `suid_escape`. `filename`이 없으면 명령의 첫 단어에서 프로그램을 얻음) sudo, su, pkexec, doas, login, pam도 처리합니다. 모든 명령은 `mAnalyzeCommand`를 거칩니다: 정찰 토큰(`fReconToken`)과 기간 내 세션의 서로 다른 토큰(`recon_burst`, `recon_massive`, `score`), 셸이 실행한 다운로드(`cDownloadOnelinerRegex`, 또는 같은 부모에서 다운로더 뒤에 셸이 오는 경우), `compile_in_tmp`, 세션의 최근 명령, 그리고 서비스 계정의 경우 이력과 대조한 프로그램(`fProgramKey`)(코어의 `mPathFirstSeen`, `learning_days` 이후: `new_program`). `ignored`는 무시할 사용자를 표시합니다.
5. **규칙, 보강, 진단, 상태**: `rules/`의 YAML 규칙 35개가 모든 탐지를 결정합니다(`mDetectionFromSignal`). `mEnrich`는 세션의 컨텍스트를 추가합니다. `fRunDoctor`는 auditd와 그 규칙이 기록한 것, syslog, snoopy, 모듈이 볼 수 있는 것과 볼 수 없는 것, 버전 1.0.0의 파일, 공격 표면을 설명합니다. `mHealth`는 auditd 중지, 쓰기 가능한 민감한 파일, setuid 프로그램 검사 결과(`SurfaceScanner`, 스레드)를 보고합니다. 모듈에는 구성 옵션이 없으며 서버에서 아무것도 변경하지 않습니다.

### privesc 모듈의 설계 결정

- **두 소스, 하나의 의미.** auditd는 사용자가 피할 수 없지만 컨테이너 안에서는 실행되지 않습니다(커널의 감사 기능은 네임스페이스로 분리되지 않음). snoopy는 컨테이너에서 모든 프로그램을 보지만 syslog가 필요합니다. syslog만으로는 sudo, su, pkexec, doas만 얻습니다. 셸 내장 명령은 어떤 소스도 보지 못합니다. 규칙은 소스가 아니라 열과 플래그에 일치하므로, 규칙을 건드리지 않고 소스를 추가할 수 있습니다. 두 번 보인 같은 명령은 알림 하나가 됩니다. 코어가 모듈, 사용자, IP, 범주, 심각도별로 탐지를 그룹화하기 때문입니다.
- **명령이 아니라 집중 실행.** 정찰은 질문의 종류마다 하나의 토큰이며(`whoami`, `read:/etc/passwd`, `find:-perm:`...), 한 세션에서 기간 내 서로 다른 토큰의 수만이 알림을 발생시킵니다. 관리자에게는 더 높은 임계값이, 스크립트에는 세 번째 임계값이 적용됩니다. 이 임계값들은 규칙 임계값이 아니라 설정입니다. 규칙은 `recon_burst` / `recon_massive`에만 일치합니다.
- **성공이 가장 중요합니다.** `suid_escape`(setuid가 아닌 프로그램이 euid 0과 0이 아닌 실제 uid로 실행됨)와 `root_without_door`(시작이 확인되었고 sudo, su, pkexec, doas를 한 번도 거치지 않은 세션의 root)는 권한 상승이 성공했다는 두 가지 심각한 징후이며, 오탐이 거의 없습니다. 시작이 확인되지 않은 세션(모듈보다 먼저 열린 세션, 하루 동안 활동이 없어 잊힌 세션)은 절대 표시되지 않습니다.
- **세션은 다시 시작해도 유지됩니다.** `SessionTracker`는 각 세션의 시작, SSH 주소, 관문을 `privesc.sessions` 상태에 보관합니다(최대 1분마다 저장). 정찰 토큰과 최근 명령은 메모리에 남습니다. 하루 동안 유휴 상태인 세션은 버립니다.
- **서버에 이미 있는 것만.** 모듈은 `/opt/localsiem` 밖에서 아무것도 설치하거나 변경하지 않습니다. 감사 규칙을 로드하지 않고, `auditd.conf`나 `snoopy.ini`를 건드리지 않으며, 훅을 설치하지 않습니다. 버전 1.0.0은 그렇게 했으며(`--configure-privesc`: 키가 `lsiem_*`인 감사 규칙, `log_group = adm`, bash 훅, snoopy 형식), 버전 1.1.0에서 이를 제거했습니다. 따라서 감사 레코드는 유형, 시스템 호출, 경로로 분류되므로 어떤 감사 규칙(서버의 규칙, STIG 샘플 규칙, 또는 1.0.0이 남긴 `lsiem_*` 규칙)이든 작동합니다. 키는 검색용으로 `fields.key`에 보관되며 힌트일 뿐입니다(`dKeyHints`). 로그에 보강된 이름이 없으면 시스템 호출 번호를 아키텍처별로 읽습니다(`dSyscallTables`: x86_64, i386, 그리고 aarch64, riscv64, loongarch64의 범용 테이블). 진단은 서버의 규칙이 기록하는 것과 기록하지 않는 것을 설명하며, 그 `fix`는 설치할 패키지나 `localsiem`의 읽기 권한뿐입니다.
- **읽을 수 있다는 것은 실제로 읽을 수 있다는 뜻입니다.** 요구 사항은 프로그램이 설치되어 있는 것이 아니라 존재하고 `localsiem`이 열 수 있는 소스로 충족됩니다(`fReadState`). 처음 설치할 때는 대개 로그가 root 소유이므로, root용 명령(`manage.py setup-modules`)과 **재구성**을 실행할 때까지 모듈은 꺼진 상태로 유지됩니다.
- **패키지 관리자는 공격자가 아닙니다.** 계정 및 패키지 도구(`sAllowedWriters`)나 알려진 조상이 패키지 관리자인 프로그램이 수행한 민감한 파일과 setuid 비트의 변경은 `writer_allowed`를 설정하며, 규칙은 이를 건너뜁니다.
- **검사는 수집기를 절대 막지 않습니다.** `SurfaceScanner`는 자체 스레드에서 `scan_paths`를 탐색하며, 각 경로의 파일 시스템을 벗어나지 않고, `/proc`, `/sys`, 컨테이너의 폴더를 건너뛰며, 최대 300만 개의 파일 또는 15분까지 진행합니다. `mHealth`는 결과가 준비되면 가져옵니다. 첫 번째 검사가 기준이 되며, 이후 검사는 새로운 것을 보고합니다.
- **웹과 도구는 스토리지 없이 모듈을 생성합니다**: `mDiscover`, `mDoctor`, `mRequirements`는 스토리지를 절대 사용하지 않으며, `mAnalyzeCommand`는 `mPathFirstSeen`이 있을 때만 이를 호출합니다.
- **이벤트 데이터베이스의 상태**: `privesc.first_start`(학습 기간), `privesc.sessions`, `privesc.surface`(검사와 진단의 기준), `privesc.health`(이미 보고한 것, auditd가 실행 중이었는지 여부), `privesc.doctor`(수집기가 기록). 서비스 계정이 실행한 것으로 확인된 프로그램은 vhost가 `privesc:<account>`인 `seen_paths`의 행입니다. `privesc.health`(상태 기록)와 `privesc.sessions`(각 세션의 `last`)의 시각은 프로젝트의 기본 형식(`2026-10-29@13-59-59.723`, UTC)입니다. 이전 버전이 epoch 초로 저장한 상태는 불러올 때 변환됩니다.

<a id="modules"></a>
## 2. 모듈 맵

| 모듈 | 경로 | 책임 | 의존 대상 | 사용하는 쪽 |
|---|---|---|---|---|
| 매니페스트 | [mod-apache2/module.json](../mod-apache2/module.json) | ID, 버전, 최소 코어, 진입점, 읽기 경로, 설정(구성 옵션 없음) | — | 레지스트리, 웹, `manage.py` |
| Apache 모듈 | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: 훅, 수행된 조치, 심각도, 탐지, 규칙 함수, 보강, 상태 점검 | correlate, discovery, doctor, modsec, parsers; 코어 `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | 수집기, 웹, `manage.py` |
| 탐색 | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig`(구성 파서), 소스와 건너뛴 로그, DocumentRoot | logformat (`dKnownFormats`) | module, doctor |
| 진단 | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | 요구 사항 검사. 로그(형식, 감사 로그, 마스킹)를 변경하라고 제안하지 않고 설명함 | discovery | module |
| 액세스 형식 | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat`을 정규식으로, 시각을 UTC로, 요청 줄 | 코어 `timeutil` | parsers, discovery |
| 파서 | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit(JSON, 네이티브, 동시), `AuditFramer`, `fAuditDisplay` | logformat, modsec; 코어 `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | 메시지, 범주, CRS 범위, 점수, 가로채기 | — | parsers, module |
| 상관관계 | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, 이것 없이 짝짓기(`mPair`), 기간, 워터마크 | 코어 `timeutil` | module (수집기) |
| 심각도 테이블 | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | ModSecurity 탐지의 심각도 | — | module (`fLoadSeverityTable`) |
| 규칙 | [mod-apache2/rules/](../mod-apache2/rules/) | YAML 규칙 6개 | 코어 규칙 엔진, `mIsNewPhp` | 수집기(`RulesEngine`), 웹(`fRules`) |
| 텍스트 | [mod-apache2/locales/](../mod-apache2/locales/) | 이름, 요약, 설정의 레이블과 도움말, 선택지 | — | 웹 |
| privesc: 매니페스트 | [mod-privesc/module.json](../mod-privesc/module.json) | ID, 버전, 최소 코어, 진입점, 읽기 경로, 설정 13개(구성 옵션 없음) | — | 레지스트리, 웹, `manage.py` |
| privesc: 모듈 | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: 훅, 두 소스의 이벤트, 감사 레코드 분류(민감한 경로, 아키텍처별 시스템 호출), 플래그, 규칙의 탐지, 보강, 상태 점검, 검사 결과 | commands, correlate, discovery, doctor, parsers, surface; 코어 `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | 수집기, 웹, `manage.py` |
| privesc: 탐색 | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | 소스, 컨테이너, auditd, snoopy, syslog, 각 로그를 읽을 수 있는지 여부, 버전 1.0.0이 남긴 파일, `Accounts`(사용자, 그룹, 계정 종류) | — | module, doctor |
| privesc: 파서 | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | 감사 레코드(16진수, `msg='...'`, 보강된 형식), syslog 줄(일반적인 형식의 snoopy, sudo, su, pkexec, doas, pam, sshd), 명령줄 마스킹 | 코어 `masking`, `timeutil` | module |
| privesc: 상관관계 | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | 감사 레코드는 일련번호별(EOE, 사용자 공간 레코드, 2초), syslog 줄은 즉시 | — | module (수집기) |
| privesc: 명령 | [mod-privesc/commands.py](../mod-privesc/commands.py) | 정찰 토큰, 서비스 계정의 프로그램, 셸, 인터프리터, 다운로더, 관문, 컴파일러; `SessionTracker` | 코어 `timeutil` | module |
| privesc: 공격 표면 | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner`(setuid, setgid, capability), GTFOBins, 쓰기 가능한 민감한 파일, 권한 있는 그룹 | — | module, doctor |
| privesc: 진단 | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | auditd, 그 로그와 규칙이 기록한 것, syslog, snoopy, 모듈이 보는 것, 버전 1.0.0의 파일, 공격 표면을 설명(해결 방법: 패키지와 읽기 권한만); 요구 사항 `command_source`(읽을 수 있는 아무 소스) | discovery, surface; 코어 `timeutil` | module |
| privesc: 규칙 | [mod-privesc/rules/](../mod-privesc/rules/) | YAML 규칙 35개 | 코어 규칙 엔진 | 수집기(`RulesEngine`), 웹(`fRules`) |
| privesc: 심각도 테이블 | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | 모듈이 만드는 탐지(검사, 민감한 파일)의 심각도 | — | module (`fLoadSeverityTable`) |
| privesc: 텍스트 | [mod-privesc/locales/](../mod-privesc/locales/) | 이름, 요약, 설정의 레이블과 도움말, 선택지 | — | 웹 |
| 코어: 인터페이스 | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | 레지스트리 | 모듈 |
| 코어: 레지스트리 | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | 모듈 찾기, 확인, 불러오기. 설정의 기본값과 검증 | `config` | 수집기, 웹, `manage.py`, `backend/core/catalog.py` |
| 코어: 웹 | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | 모듈 페이지(설치됨, 설치 가능, 개별 모듈 페이지)와 API | 레지스트리, catalog, rules | 브라우저 |
| 코어: 카탈로그 | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | 저장소 다운로드와 안전한 압축 해제, 각 모듈의 동작(`install`, `update`, `incompatible`, `invalid`...)과 `newer`가 있는 목록, 원자적 설치 또는 업데이트(`previous`, `access_changed`), 제거, root용 명령: 모듈 › 설치 가능과 모듈 › 설치됨의 **업데이트** / **제거**, 모듈을 설치하는 유일한 방법 | 레지스트리 | 웹 |

<a id="symbols"></a>
## 3. 주요 심볼

| 심볼 | 파일:줄 | 기능 |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | apache2 모듈(`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | 내장 기본값 위에 `severity.yaml` 적용 |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | 구성 파싱, 소스, 건너뛴 로그, DocumentRoot |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | 이상 임계값: 설정, CRS 또는 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | 소스 종류별로 단위를 레코드로 변환 |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | 트랜잭션을 이벤트로: 필드, 수행된 조치, 점수, 탐지 |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Host 헤더 또는 ModSecurity 호스트 이름을 Apache가 선택한 vhost(`%v`가 기록하는 값)로 변환 |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | SOC로 보내는 것의 심각도, 규칙 이름, 설명, 세부 정보 |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | YAML 규칙의 신호를 탐지로 변환 |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | 규칙 함수 `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | 알림에 넣을 IP 컨텍스트(최근 1시간) |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity 언로드 또는 Off, 실제 클라이언트 IP 없음 |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | 요청 카드용 헤더와 본문 |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache와 ModSecurity 2: 모듈을 켜기 전에 필요한 것 |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Apache 구성 파서 |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | 읽는 지시자(로그, vhost, 모듈, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Host 헤더와 로컬 주소 및 포트로 Apache가 선택하는 방식대로 요청의 vhost를 구함 |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | 고정 소스 키. 읽을 소스와 건너뛴 소스 |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | 요구 사항 검사 `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | 액세스 형식을 `UNIQUE_ID` 없이 결합할 수 있는지 여부(클라이언트 IP, 시각, 요청 줄, 상태) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | 진단의 `apache_config`와 `modsecurity` 검사, 또는 Apache가 없으면 둘 다 오류로, 이를 설치하는 명령과 함께 반환 |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat`을 정규식으로. 알려진 별칭 |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | access.log 줄을 레코드로 |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | error.log 줄: ModSecurity, 데이터베이스, PHP, 충돌 |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | 여러 줄에 걸친 네이티브 레코드. 안전한 커밋 위치 |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | JSON 또는 네이티브 감사 레코드. 마스킹, 원시 텍스트와 색인 텍스트 |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | 저장된 레코드의 카드. 동시 항목의 파일 |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | ModSecurity 메시지 하나. 규칙, 범주, 점수, 임계값, 가로채기 |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | privesc 모듈(`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | 소스별로 트랜잭션을 이벤트로. `ignored`. 빈 필드는 버림(`fCleanFields`는 0을 유지) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | 세션의 정찰, 셸이 실행한 다운로드, `/tmp`에서의 컴파일, 최근 명령, 서비스 계정의 새 프로그램 |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | 유형별 감사 트랜잭션. 실행된 프로그램(`suid_escape`, `root_without_door`, `parent_interpreter`, capability). 로그인, 관문, 실패 |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | 그 밖의 모든 시스템 호출을 이름, 인수, 경로로 분류: `denied`, `kmod`, `ptrace`, `chmod`, `file`(`sensitive_group`) 또는 `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | 시스템 호출의 이름(보강된 이름, 또는 아키텍처별 번호). 민감한 경로의 그룹(`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, 로그인 |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | 민감한 파일을 쓴 프로그램 또는 알려진 조상이 계정 또는 패키지 도구인지 여부 |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | 규칙의 신호를 탐지로. 알림에 넣을 세션 컨텍스트 |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | 세션 저장, auditd 중지, 민감한 파일, 검사 시작. 새 setuid 프로그램과 capability |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | 소스, 건너뛴 소스, 진단용 정보. 로그를 읽을 수 있는지 여부. 버전 1.0.0이 남긴 파일 |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | 컨테이너 종류(root 없이). 실행 중인 auditd의 pid |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | uid의 이름, 그룹, `UID_MIN`, 계정 종류(`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | 두 소스의 레코드 |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | 명령줄의 비밀번호, 그다음 코어의 마스커 |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | 감사 레코드는 일련번호별, 나머지는 즉시 |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | 명령의 정찰 토큰. 서비스 계정의 프로그램. 입력된 명령의 단어 |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | 세션(시작, IP, 관문, 정찰, 최근 명령), 프로세스, 다운로드. `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | 스레드에서 setuid, setgid, capability 검사. 다른 사용자가 쓸 수 있는 민감한 파일 |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | 진단의 검사(설명. 해결 방법은 패키지와 읽기 권한만). 요구 사항 `command_source`: 읽을 수 있는 아무 소스 |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | 모듈의 인터페이스. 단위마다 한 줄 |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | `module.json`을 확인하고 텍스트를 읽음 |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | 설치된 모듈(`/opt/localsiem/modules/*`). 인스턴스와 오류 |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | 네임스페이스 패키지 `localsiem_modules`. 진입점의 가져오기와 확인 |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | 저장된 값 아래의 기본값. 저장되는 값의 검증 |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`. `POST /api/admin/module-catalog/{name}`(설치 또는 업데이트. 요구 사항 없이 처음 설치하면 꺼진 상태: `fFirstInstallation`). `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | 설치된 사본 옆에 모듈을 설치하거나 업데이트하고 이름 변경으로 교체(`previous`, `access_changed`). `installed`, `newer`와 동작이 있는 저장소의 모듈 |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | 모듈 제거(이름 변경 후 삭제). root용 명령(`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | 설치 가능 섹션(설치되지 않은 모듈만, **설치**와 그 대화 상자). 설치됨의 행에 표시되는 새 버전 안내. **업데이트**(확인, 같은 `POST`, `access_changed`가 있거나 수집기가 응답하지 않았을 때만 대화 상자) |

<a id="flows"></a>
## 4. 주요 호출 경로

**수집기 시작 → 레지스트리 → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = 폴더, entry, settings, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, `Module`의 하위 클래스, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, 재정의 `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`. 소스마다 `FileTailer`와 `mCreateFramer`) → 대기 중인 레코드를 상관 분석기에 다시 넣음 → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → 상태 `apache2.doctor`).

**읽은 줄 하나 → 탐지**

1. `Collector.mReadSources` → `FileTailer.mPoll` → 프레이머 `mFeed` (`LineFramer`, 또는 `mSafeCommit`이 완료되지 않은 레코드 앞의 위치를 유지하는 `AuditFramer`) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, 또는 `fReadConcurrentEntry` + `fParseAuditRecord`와 `mObserveAudit`) → 레코드와 위치를 하나의 트랜잭션으로 저장 → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, 수행된 조치, `mAssess`, 2xx `.php`에 대해 `mPathFirstSeen`) → `RulesEngine.mEvaluate` (YAML 규칙. `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → 각 탐지에 대해 `mDetect`, 각 신호에 대해 `mDetectionFromSignal` → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → SOC 대기열.

**관리자가 설정 저장 → 수집기 다시 불러오기**

`modules.js fBuildSettings` (제출) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` 또는 `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → 수집기 소켓 `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). 스위치는 같은 방식으로 `{enabled}`를 보내며(켤 때: 모듈의 요구 사항이 충족되지 않은 동안 422 `requirements_missing`), 규칙 테이블은 `{rules}`를 보냅니다(`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` 또는 `first_threshold`, `window`). 소켓이 응답하지 않아도 수집기는 다음 주기에 새 `settings.json`을 알아챕니다.

**웹에서 모듈 설치**(모듈을 설치하는 유일한 방법)

`modules.js fCatalogPanel` (모듈 › 설치 가능) → **저장소 확인** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: 저장소의 각 폴더 `mod-<name>/`, `installed`, `newer`, `action` 포함) → `installed`가 null인 항목만 나열 → **요구 사항** (`fShowRequirements` → `fRequirementsBody`: 서버의 시스템(응답의 `system`)에 대한 모듈의 `install_requirements`를 root로 실행하는 경우와 `sudo`를 사용하는 경우로, 그리고 로캘의 안내 `install_requirements.*`. 아무것도 실행하지 않음) → **설치** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` null, `access_changed` true) → `WebContext.mReloadModules` → `fFirstInstallation` (요구 사항이 없고 `modules.<name>.enabled`가 한 번도 저장되지 않음: `enabled = false`) → 수집기 `restart` → `fCreateModules`가 모듈을 불러옴 → «<module> 설치 완료» 대화 상자가 root용 명령(`fRootCommand`: `manage.py setup-modules`, `read_paths`에 대한 읽기 권한)을 표시하거나, 요구 사항이 없으면 충족되지 않은 검사를 표시합니다.

**웹에서 모듈 업데이트**

모듈 › 설치됨을 엶 → `fCheckRepository` → `modules.js`의 `fFetchCatalog(false)` (`GET /api/admin/module-catalog`의 마지막 응답, 600초 동안 재사용. 모듈을 설치, 업데이트, 제거하면 버림) → `newer`가 있고 `action`이 `update` 또는 `incompatible`인 항목 → 행에 `fUpdateNotice` (설치된 버전이 비교한 버전과 같은 동안에만) → **업데이트** → `fUpdate` → 확인 → `POST /api/admin/module-catalog/{name}` (같은 `fInstallFromCatalog` → `fInstall`: 새 사본이 설치된 사본을 대체하고, `previous`는 이전 버전, `access_changed`는 `read_paths`가 바뀌었는지 알려 줌. `fFirstInstallation`이 없으므로 `enabled`와 설정은 유지됨) → 수집기 `restart` → `access_changed`(root용 명령)이거나 수집기가 응답하지 않았을 때만 대화 상자.

**웹에서 모듈 제거**

**제거**(모듈 › 설치됨의 행 또는 모듈 페이지) → `fUninstallButton` → 확인 → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → `/opt/localsiem/modules/<name>/`를 임시 폴더로 이름 변경한 후 그곳에서 삭제) → `WebContext.mReloadModules` → 수집기 `restart`. `modules.<name>`과 그 규칙의 재정의는 `settings.json`에 남으며, root가 준 읽기 권한도 남습니다.

**Apache나 ModSecurity 없이 첫 설치 → 재구성**(localSIEM 2.2.0 이상)

웹에서 설치 → `fInstall` (첫 설치) → 설치된 사본으로 생성한 모듈(스토리지 `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (Apache가 있으면: `fRunDoctor` → `apache_config`, `modsecurity`. 없으면 둘 다 오류) → 오류가 있고 `modules.apache2.enabled`가 한 번도 저장되지 않음 → `modules.apache2.enabled = false` («꺼짐», 스위치 잠김, 페이지에 요구 사항 표시). 나중에 Apache와 ModSecurity를 설치하면: **재구성** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → 충족 → 스위치 잠금 해제와 root용 명령(`read_paths`에 대한 읽기 권한. apache2에는 `setup_option`이 없음) → 관리자가 모듈을 켬 → 수집기 다시 불러오기 → `mDiscover` → `mPublishDoctor`.

**웹에서 요청 카드와 진단**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **다시 탐색하고 진단 실행** → `POST /api/admin/modules/apache2/doctor` → 수집기 `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**상태 점검**

`Collector.mCycle` (60초마다) → `mCheckHealth` → `ApacheModule.mHealth` (최대 300초마다. `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc: 실행된 명령 → 탐지**

1. auditd가 하나의 일련번호로 `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE`를 기록 → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (16진수 디코딩, `fMaskCommand`, 원시 텍스트 재구성) → `Correlator.mAdd` (키 `audit:<time>:<serial>`, `EOE`에서 기한).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `SessionTracker.mGet`에서 `root_without_door`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`. `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`. `fCompileInTemporary`. `mCommand`. 서비스 계정: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (`mod-privesc/rules/`의 규칙) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (세션: 최근 명령 20개) → `fBuildAlert` → SOC 대기열.

snoopy가 있으면 같은 명령이 syslog 줄로도 도착합니다: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (세션 `snoopy:<uid>:<sid>`).

**privesc: 세션과 관문**

`LOGIN`(auid와 ses 할당) 또는 sshd나 login의 `USER_LOGIN`/`USER_START` → `mAuditUser` → `SessionTracker.mStart` (사용자, SSH 주소). sudo, su, pkexec, doas, run0 또는 systemd의 결과가 success인 `USER_START`/`USER_CMD` → `SessionTracker.mDoor`. 그 세션에서 이후 uid와 euid가 0인 `EXECVE` → 시작이 확인되었고 관문이 없었을 때만 `root_without_door`. `mHealth`는 최대 1분마다 `SessionTracker.mExport`를 `privesc.sessions`에 저장하고, `mStart`가 이를 불러옵니다(`mImport`).

**privesc: 서버의 감사 규칙이 기록한 시스템 호출**

auditd가 `SYSCALL`(`arch`, `syscall`, `a0`-`a3`, `success`, `exit`, 그리고 이를 기록한 규칙의 키 포함), `CWD`, `PATH`...를 기록 → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → `EACCES`/`EPERM`으로 실패한 open/exec/truncate와 로그인 uid → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; 모드에 `S_ISUID`/`S_ISGID`가 있는 `chmod`/`fchmod`/`fchmodat`/`fchmodat2`, 폴더가 아닌 경우 → `chmod` (`mWriterAllowed`); `lSensitivePaths`의 경로 변경(`sChangeSyscalls`의 호출, 쓰기 플래그가 있는 open, `CREATE`/`DELETE`가 있는 `PATH`) → `sensitive_group`이 있는 `file` (`dKeyHints`는 확인할 수 있는 경로가 없을 때만) 및 `mWriterAllowed`; 그 밖의 모든 것 → `syscall`. `mBuildEvent`는 진단을 위해 각 종류의 시각을 기억합니다(`dRuntime["audit_kinds"]`).

**privesc: 공격 표면 검사**

`mHealth` (300초마다, 시작 5분 후, `surface_scan_hours`마다) → `SurfaceScanner.mStart` (스레드: `scan_paths`의 `os.walk`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → 다음 `mHealth` → `mSurfaceResult` (`SurfaceScanner.mTake`, `privesc.surface`와 비교: 새 setuid/setgid → `new_setuid*`, 새 capability → `new_capabilities`) → `mModuleDetection` → `mDetect`. 결과는 `privesc.surface`에 저장되고 `fSurfaceChecks`가 표시합니다. 매시간 `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc: 요구 사항과 재구성**

`fInstall` (첫 설치) 또는 **재구성** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`. `syslog_mode`가 `never`가 아니면 `fSyslogPath` → `fReadState`. `fSnoopyInstalled`) → 읽을 수 있는 소스: `command_source` ok(읽을 수 없는 소스는 경고로). 존재하지만 읽을 수 없는 소스: 읽기 권한(`manage.py setup-modules` 또는 `setfacl`)과 함께 `audit_log` 또는 `syslog` 오류. 아무것도 없음: 설치할 패키지와 함께 `command_source` 오류. 오류가 있는 동안 모듈은 꺼진 상태로 유지됩니다.

<a id="routes"></a>
## 5. 진입점

| 진입점 | 핸들러 | 파일 |
|---|---|---|
| `module.json`의 `"entry": "module:ApacheModule"` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (코어) | [mod-apache2/rules/](../mod-apache2/rules/) |
| 규칙 함수 `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| 웹: 모듈 › 설치 가능, 모듈을 설치하는 유일한 방법(`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`. 뷰 `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| 웹: 모듈 › 설치됨의 행에 있는 **업데이트**(같은 `GET`, 브라우저가 10분 동안 재사용, 그리고 같은 `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| 웹: **제거**(`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `module.json`의 `read_paths` | `manage.py read-paths`: localSIEM이 root로 `localsiem`에 읽기를 허용하는 폴더(`fRootCommand`의 명령) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | 모든 매니페스트의 `read_paths` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (`installed/`로 302), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`. 뷰 `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/`(이전 주소 `/admin/dashboard/modules/apache2/`는 여기로 301 응답) | `fAdminModule`(301은 `fAdminModulesSection`). 뷰 `LocalsiemViews.module` | 같은 파일 |
| `GET /api/modules` | `fModules`(로그인한 모든 사용자에게 상태 제공) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule`(설정, 값, 소스, 진단, 규칙) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure`(**재구성**, localSIEM 2.2.0 이상) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `mod-privesc/module.json`의 `"entry": "module:PrivescModule"` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (코어) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| 서버 규칙의 감사 레코드(모든 키) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. 영향 분석

| 구성 요소 | 변경 시 영향을 받는 것 |
|---|---|
| `module.json` `id` | `mod-`를 뺀 폴더 이름(설치된 폴더의 이름) 및 `vName`과 같아야 합니다. 설정(`modules.<id>`)과 상태(`<id>.doctor`)의 키이며 모든 이벤트의 `module`입니다. 이름을 바꾸면 저장된 설정을 잃고 이력이 나뉩니다. |
| `module.json` `core` | 설치된 localSIEM보다 높이면 모듈을 불러오지 않습니다(상태 «오류»). 저장소에서는 설치 가능에 «localSIEM X 이상 필요»가 표시되고, 설치됨에는 **업데이트** 없이 새 버전이 표시됩니다. |
| `module.json` `entry` | `Module` 하위 클래스를 가리켜야 합니다. 잘못된 값은 로드 오류가 됩니다. |
| `module.json` `default_enabled` | 관리자가 한 번도 결정하지 않은 서버에서의 켜짐/꺼짐(첫 설치 시 요구 사항이 없으면 꺼짐). |
| `module.json` `read_paths` | localSIEM이 root로 주는 읽기 권한(`manage.py read-paths`). 폴더가 빠지면 진단과 상태에 권한 오류가 생깁니다. 새 버전에서 바뀌면 웹은 **업데이트** 후 root용 명령을 다시 표시합니다(`access_changed`). |
| `module.json` `install_requirements` | 설치 가능의 요구 사항 대화 상자(`modules.js`의 `fRequirementsBody`). 잘못된 값(`debian`과 `alpine` 이외의 시스템, 빈 목록 또는 20개를 넘는 명령, 셸 연산자나 줄 바꿈이 있는 명령)은 모듈을 유효하지 않게 만듭니다(코어의 `fCheckInstallRequirements`). 설치도 로드도 되지 않습니다. |
| `module.json` `setup_option` | 영향 없음: 코어는 이를 무시합니다(apache2 1.3.0과 privesc 1.1.0 이후 어떤 모듈에도 없습니다). |
| 저장소 최상위에 `module.json`이 있는 `mod-<name>/` 폴더 | 웹 카탈로그가 모듈 `<name>`으로 나열하는 것: 설치 가능에는 아직 설치되지 않은 것이 표시되고(더 새로운 코어가 필요한 것은 «localSIEM X 이상 필요», 유효하지 않은 것은 «저장소의 모듈이 유효하지 않습니다»로), 설치된 것보다 높은 `version`이 있으면 설치됨에 **업데이트**가 표시됩니다. |
| `module.json` `settings` | 양식, 검증, 기본값. 새 기본값은 그 키를 한 번도 저장하지 않은 서버에 적용됩니다. 저장된 값은 마이그레이션되지 않습니다. 이름을 바꾼 키는 값을 잃고, 유형이 바뀐 이전 값은 저장된 그대로 모듈에 전달됩니다. |
| `locales/*.json` | 웹의 텍스트만. 텍스트가 없으면 en-US로, 그다음 키로 대체됩니다. |
| `parsers.py`(레코드 dict) | 상관관계(`correlation`, `fields.client_ip`, `fields.path`), 요청 카드, 전체 텍스트 색인(`search`, `raw`), 파싱되지 않은 줄에 대한 상태 점검, 개인 정보 보호. |
| `logformat.py` `dKnownFormats` | 모든 액세스 로그의 파싱. `localsiem_combined`는 이미 이를 기록하는 서버를 위해 남아 있습니다(모듈 버전 1.2.0 이하가 추가함). 그 정의를 바꾸지 마십시오. |
| `correlate.py` | 요청당 이벤트 하나. 코어는 `mAdd`, `mDue(pNow, pForce, pWatermark)`, `mPendingCount`를 호출하며, 다시 시작한 후 아직 대기 중인 레코드를 다시 넣습니다. `UNIQUE_ID`가 없으면 레코드를 `client_ip`, `method`, `uri`, `status`, `path` 필드로 짝짓습니다. 이 필드를 다르게 기록하는 파서는 짝짓기를 깨뜨립니다. 감사 레코드 대기(`mWaitsForAudit`)에는 error.log 줄의 `modsecurity` 필드와 `audit` 소스의 레코드가 필요합니다. |
| `modsec.py`(범주, 레이블, 범위) | 알림의 규칙 이름(SOC 통계가 이것으로 그룹화하므로 고정해 두십시오), 그룹화 키, `category:` 검색. |
| `ApacheModule.mBuildEvent`(이벤트 dict) | events 테이블의 열, YAML 규칙이 읽는 필드(`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), 검색, CSV 내보내기. |
| `ApacheModule.mAssess` | SOC에 도달하는 것과 그 심각도. 코어의 `GenericAlert` 제한(규칙 300자, 설명 10 000자). |
| `severity.yaml` | 모든 ModSecurity 탐지의 심각도. 심각도는 그룹화 키의 일부이므로 변경하면 새 그룹이 시작됩니다. |
| `rules/*.yaml` | `id`는 재정의(`rules.<id>`)와 검색(`rule:localsiem:<id>`)의 키입니다. 고정해 두십시오. 필드는 이벤트에 존재해야 하며, `{function: ...}`에는 `mRuleFunctions`가 필요합니다. |
| `discovery.py` | 어떤 로그를 읽는지. `fSourceKey`는 저장된 위치의 키입니다(새 키는 그 파일을 저장된 위치 없는 새 소스로 만듭니다). 웹 셸 규칙의 DocumentRoot. 진단. |
| `doctor.py` | 웹과 `manage.py`의 진단, 그리고 클라이언트에게 표시되는 힌트. 로그가 아닌 것(ModSecurity, CRS, `SecRuleEngine`, `mod_unique_id`, 권한)에 관한 검사만 `fix`를 가질 수 있으며, 로그에 관한 검사는 로그를 설명할 뿐입니다. |
| `mRequirements` / `fRequirementChecks` | 모듈을 켤 수 있는지 여부, Apache나 ModSecurity 없이 첫 설치한 후의 상태 «꺼짐», 웹이 표시하는 요구 사항, **재구성**. 웹과 `manage.py`에서 스토리지 없이 실행되며 호출할 때마다 Apache 구성을 파싱합니다. 스토리지와 느린 작업에서 떼어 두고, ID `apache_config`와 `modsecurity`를 고정해 두십시오. |
| privesc: 이벤트 열과 필드(`mBuildEvent`, `mAnalyzeCommand`) | YAML 규칙은 이름으로 이들에 일치합니다(`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...). 필드 이름을 바꾸면 그 필드를 쓰는 규칙이 아무 경고 없이 비활성화됩니다. `vhost`는 사용자입니다. 알림의 그룹화 키와 `vhost:` 검색이 이에 의존합니다. |
| privesc: `fReconToken` | 무엇을 정찰로 간주하고 서로 다른 명령을 어떻게 구분하는지. 토큰을 바꾸면 세션이 임계값에 도달하는 속도가 바뀝니다. |
| privesc: `SessionTracker`와 관문(`sDoors`) | `root_without_door`: 목록에서 관문이 빠지면 정당한 root 세션이 심각으로 표시되고, 관문이 더 있으면 커널 익스플로잇이 감춰집니다. `mExport`/`mImport`는 `privesc.sessions`의 형식입니다. |
| privesc: `parsers.py` | 레코드의 필드(`args`, `command`, `kind`, snoopy의 `uid`/`euid`), 비밀번호 마스킹, 감사 레코드의 원시 텍스트. 읽을 수 있는 snoopy 형식(모듈은 `snoopy.ini`를 절대 변경하지 않음). |
| privesc: 감사 레코드 분류(`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | 무엇이 `file`, `chmod`, `kmod`, `ptrace`, `denied`가 되는지, 따라서 sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst, sensitive-denied 규칙. 시스템 호출 번호가 틀리면 해당 아키텍처의 레코드를 잘못 분류합니다. |
| privesc: `surface.py` | 검사 비용(스레드, 제한)과 진단 및 `mSurfaceResult`가 보고하는 것. `privesc.surface`가 그 기준입니다. |
| privesc: `mRequirements` / `fRequirementChecks` | 모듈을 켤 수 있는지 여부(읽을 수 있는 아무 소스), `localsiem`이 아직 로그를 읽을 수 없는 첫 설치 후의 상태 «꺼짐», **재구성**. 웹과 `manage.py`가 스토리지 없이 호출하므로 빠르고 root 없이 동작하게 유지하십시오. ID `command_source`, `audit_log`, `syslog`를 유지하십시오. |
| 코어 인터페이스(localSIEM의 `backend/core/module.py`, `registry.py`) | 모든 모듈: 훅 시그니처 변경, 새로운 필수 매니페스트 키, 레코드와 이벤트의 새로운 계약은 모듈을 깨뜨립니다. 모듈에 새 localSIEM이 필요하면 `module.json`의 `core`를 올리십시오. |

<a id="extensions"></a>
## 7. 확장 지점

### 새 모듈을 작성하는 방법

1. **폴더**: 이 프로젝트의 루트에 `mod-<name>/`을 만드십시오. 모듈의 이름인 `<name>`은 `[a-z][a-z0-9_]{1,31}`과 일치해야 합니다. `mod-` 접두사는 폴더에만 붙습니다. `module.json`, 클래스, 옵션, 텍스트는 `<name>`을 사용합니다. `__init__.py`는 만들지 않습니다.
2. **`module.json`**, 예:

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

3. **텍스트**: localSIEM의 15개 언어 각각에 대해 `name`, `summary`, 그리고 모든 설정의 레이블과 도움말이 있는 `locales/<language>.json`. 요구 사항에 관한 안내는 `install_requirements`(모든 시스템용 `note`, 그리고 `debian`과 `alpine`)에 넣으며, 요구 사항 대화 상자에 표시됩니다.
4. **코드**: `vName`이 ID인 `Module`의 하위 클래스가 있는 `module.py`. `mParse`, `mCreateCorrelator`, `mBuildEvent`를 구현해야 하며, 대개 `mDiscover`도 구현합니다. 나머지 훅은 선택 사항입니다(1절). 자체 파일은 상대 경로로, 코어는 `backend.core...`로 가져오십시오. 이 저장소의 두 모듈이 완전한 예입니다([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)). 최소한의 골격은 다음과 같습니다:

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # Each record is an event of its own, without waiting.

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

5. **수행된 조치**: 서비스에서 «이미 해결됨»이 무엇을 뜻하는지 정하고(예: 이미 차단된 IP), 그 경우 `action`을 `blocked`로 설정하십시오. 탐지는 수행된 조치가 없는 이벤트에만 추가하십시오.
6. **규칙**: `mod-<name>/rules/`의 YAML 파일로, `mRulesPath`가 반환하며, 규칙이 호출하는 함수는 `mRuleFunctions`에 있습니다.
7. **요구 사항**: 모듈에 서버의 소프트웨어가 필요하면(apache2에 Apache와 ModSecurity 2가 필요한 것처럼) `mRequirements()`에서 요구 사항마다 검사 하나를 반환하고(`fCheck` 형식: `status`는 `ok` 또는 `error`, `fix`에는 이를 설치하는 명령), 모듈에서 그 소프트웨어를 절대 설치하지 마십시오. 요구 사항이 없으면 모듈은 꺼진 상태로 설치됩니다. 이 함수는 웹과 `manage.py`에서도 스토리지 없이 실행됩니다. 또한 `module.json`의 `install_requirements`에 Debian과 Alpine에서 그 소프트웨어를 설치하는 명령을 선언하십시오(한 줄에 명령 하나, 셸 연산자 없이). 웹은 모듈을 설치하기 전에 모듈 › 설치 가능 › 요구 사항에서 이 명령을 그대로, 그리고 앞에 `sudo`를 붙인 형태로 표시합니다.
8. **설치**: 이 저장소(브랜치 `main`)에 게시하십시오. 설치되지 않은 동안 localSIEM 웹의 모듈 › 설치 가능에 나타나며, **설치**는 폴더 `mod-<name>/`을 `/opt/localsiem/modules/<name>/`에 복사하고 수집기를 다시 시작합니다. `read_paths`에 대한 읽기 권한에는 root가 필요합니다. 웹이 명령(`manage.py setup-modules`)을 표시합니다. 모듈에는 구성 옵션이 없습니다. `/opt/localsiem` 밖에서 아무것도 설치하거나 변경하지 않으며, 클라이언트의 로그에 쓰거나 로그를 순환하거나 삭제하지 않고 형식도 바꾸지 않습니다. 서버가 자기 방식으로 로그를 기록하면 모듈이 그에 맞추며, 서버에 없는 것은 요구 사항이 됩니다. 새 버전을 게시하려면 `version`을 올리십시오. 모듈 › 설치됨에 안내와 **업데이트**가 표시되며, 이는 설정과 모듈의 켜짐/꺼짐을 유지하고 `read_paths`가 바뀐 경우에만 root용 명령을 다시 표시합니다.
9. **문서**: README, 이 CODE, MANUAL을 15개 언어로 업데이트하십시오.

### apache2 모듈에 규칙을 추가하는 방법

[mod-apache2/rules/](../mod-apache2/rules/)에 YAML 파일을 만드십시오(모든 키와 연산자는 [backend/core/rules.py](../../localSIEM/backend/core/rules.py) 상단에 설명되어 있습니다): `id`, `name`, `category`, `type`, `severity`, `kind`(`match`, `threshold` 또는 `sequence`), 조건(`when`, 또는 `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description`, `search`. 필드는 먼저 이벤트 열에서, 그다음 `fields`에서 찾습니다. 규칙은 모듈 페이지의 규칙 테이블에 나타나며, 모듈의 새 버전이 설치되면 수집기가 불러옵니다. `module.json`의 `version`을 올리고, 게시한 다음, 모듈 › 설치됨에서 **업데이트**를 누르십시오.

### apache2 모듈에 설정을 추가하는 방법

[mod-apache2/module.json](../mod-apache2/module.json)의 `settings`에 유형과 기본값과 함께 추가하고, [mod-apache2/locales/](../mod-apache2/locales/)의 네 파일에 `label`과 `help`를 추가한 다음, `self.mModuleSettings().get("<key>")`로 읽으십시오. 양식, 검증, 다시 불러오기는 코어가 제공합니다.

### 진단 검사를 추가하거나 심각도를 변경하는 방법

검사는 `fRunDoctor`([mod-apache2/doctor.py](../mod-apache2/doctor.py))의 `fCheck(id, status, title, detail, fix)` 하나입니다. `id`를 고정해 두고, 로그가 아닌 요구 사항에 대해서만 `fix`에 정확한 스니펫이나 명령을 넣으십시오. 클라이언트의 로그에 관한 검사는 로그와 localSIEM이 로그에서 읽을 수 있는 것과 없는 것을 `fix` 없이 설명할 뿐입니다. ModSecurity 탐지의 심각도는 [mod-apache2/severity.yaml](../mod-apache2/severity.yaml)에서 변경합니다(`low`, `medium`, `high`, `critical`).

### privesc 모듈에 규칙을 추가하는 방법

[mod-privesc/rules/](../mod-privesc/rules/)에 Apache의 규칙과 같은 방식으로 YAML 파일을 만드십시오. 감사 규칙의 키가 아니라 열(`method`, `uri`, `path`, `vhost`, `action`)과 이벤트의 필드(`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...)에 일치시키십시오. 무시할 사용자가 이 규칙을 절대 발생시키지 않도록 `ignored: {not: true}`를 추가하고, 실제로 실행된 것만 중요하면 `action: none`을 추가하십시오. 조건에 상태나 로직이 필요하면(같은 세션의 시퀀스, 파일 확인) `PrivescModule.mAnalyzeCommand`(모든 소스) 또는 `mAuditExec`/`mAuditSyscall`/`mSyslogEvent`(한 소스)에서 플래그를 계산하고 규칙에서 그 플래그에 일치시키십시오.

### privesc 모듈에 정찰 명령, 도구 또는 익스플로잇을 추가하는 방법

- 정찰: 프로그램을 `sReconSimple`에 추가하거나, 질문의 종류마다 토큰을 반환하는 분기를 `fReconToken`에 추가하십시오([mod-privesc/commands.py](../mod-privesc/commands.py)). 인수마다 바뀌는 토큰은 개수를 부풀립니다.
- 도구와 익스플로잇: [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) 또는 [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml)의 목록에 정규식을 추가하십시오(대소문자 구분 없음, 명령줄과 대조). 관리자도 설정에서 추가할 수 있습니다(`rules.<id>.lists`).

### privesc 모듈에 소스 또는 감사 레코드 종류를 추가하는 방법

- 민감한 경로: [mod-privesc/module.py](../mod-privesc/module.py)의 `lSensitivePaths`에 그룹과 함께 추가하십시오(또는 새 그룹과 `sensitive_group`에 일치하는 규칙). 시스템 호출 종류: `mAuditSyscall`의 집합에 이름을, `dSyscallTables`의 각 테이블에 번호를 추가하십시오. 감사 규칙의 키에 절대 의존하지 말고(기껏해야 `dKeyHints`에 추가) 감사 규칙을 절대 설치하지 마십시오. 서버는 관리자가 결정한 것을 기록하며, 진단이 이를 설명합니다([doctor.py](../mod-privesc/doctor.py)의 `dAuditKinds`).
- 소스: `fDiscoverSources`에서 새 `kind`로 반환하고, `mParse`에서 파싱하며, `mBuildEvent`에서 다른 소스와 같은 열과 필드로 이벤트를 만드십시오. 그러면 규칙이 변경 없이 작동합니다.
