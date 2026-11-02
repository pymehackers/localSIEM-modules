# localSIEM-modules 사용자 매뉴얼

이 MANUAL은 다음 언어로도 제공됩니다:\
[de-DE](MANUAL.de-DE.md), [en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md), [fr-FR](MANUAL.fr-FR.md), [he-IL](MANUAL.he-IL.md), [hi-IN](MANUAL.hi-IN.md), [it-IT](MANUAL.it-IT.md), [ja-JP](MANUAL.ja-JP.md), ko-KR, [pt-BR](MANUAL.pt-BR.md), [pt-PT](MANUAL.pt-PT.md), [ru-RU](MANUAL.ru-RU.md), [zh-CN](MANUAL.zh-CN.md)

[설치](README.ko-KR.md) · [코드 참조](CODE.ko-KR.md) · [localSIEM 매뉴얼](../../localSIEM/doc/MANUAL.ko-KR.md)

## 목차

1. [모듈이란 무엇인가](#what)
2. [모듈 설치 및 업데이트](#installation)
3. [모듈 페이지](#modules-page)
4. [Apache 모듈 페이지](#apache-page)
5. [Apache 모듈 설정](#settings)
6. [Apache 모듈이 SOC로 보내는 것](#soc)
7. [Apache와 ModSecurity 요구 사항: 진단](#doctor)
8. [클라이언트의 로그는 절대 건드리지 않습니다](#client-logs)
9. [Apache 모듈 규칙](#rules)
10. [Apache 모듈 상태 경고](#health)
11. [권한 상승 모듈](#privesc)
12. [권한 상승 모듈 설정](#privesc-settings)
13. [권한 상승 모듈이 SOC로 보내는 것: 규칙](#privesc-rules)
14. [권한 상승 모듈 요구 사항: 진단](#privesc-doctor)
15. [권한 상승 모듈 버전 1.0.0에서 업데이트된 서버](#privesc-legacy)
16. [권한 상승 모듈의 공격 표면과 상태 경고](#privesc-health)
17. [명령줄](#cli)

<a id="what"></a>
## 1. 모듈이란 무엇인가

localSIEM은 **코어**와 **모듈**로 이루어져 있습니다. 코어는 이벤트를 저장하고, 검색하고, 규칙을 실행하고, 알림을 그룹화하여 SOC로 보내며, 자신의 상태를 감시합니다. 각 모듈은 서버의 서비스 하나를 추가합니다. 즉 그 서비스의 로그를 찾고, 읽고, 이벤트로 바꾸고, 무엇이 이미 해결되었는지 판단하고, 자체 규칙을 제공하며, 그 서비스의 요구 사항을 확인합니다.

이 프로젝트의 모듈은 `/opt/localsiem/modules/<name>/`에 설치됩니다. 현재 모듈은 두 개입니다: **apache2**(«Apache + ModSecurity», 4~10절)와 **privesc**(«권한 상승», 11~16절). localSIEM에는 자체 모듈이 없습니다. 모듈 페이지에는 이 저장소에서 설치한 모듈만 나열됩니다.

<a id="installation"></a>
## 2. 모듈 설치 및 업데이트

먼저 localSIEM을 설치해야 합니다. localSIEM 설치 프로그램은 코어만 설치하며 모듈은 절대 설치하지 않습니다. 이 프로젝트의 모듈은 **localSIEM 웹에서만** 설치합니다. 이 프로젝트에는 자체 설치 프로그램이 없습니다. 웹은 저장소 `https://github.com/PYMEHackers/localSIEM-modules`(브랜치 `main`)에서 모듈을 내려받습니다. 모듈에는 localSIEM 2.2.0 이상이 필요합니다.

**설치.** 관리자로 모듈 › **설치 가능**(3절)을 열고, **저장소 확인**을 누르고, **요구 사항**(모듈이 서버에서 필요로 하는 것과 이를 설치하는 명령으로, 모듈을 설치하기 전에 실행합니다)을 확인한 다음, 모듈에서 **설치**를 누르십시오. 그러면 localSIEM은 다음을 수행합니다:

1. 저장소를 내려받아 안전하게 압축을 풉니다(폴더 밖에는 아무것도 풀지 않으며 크기 제한을 적용합니다).
2. 모듈 폴더(저장소의 `mod-<name>/`)를 `tests/`(및 Python 캐시)를 제외하고 `/opt/localsiem/modules/<name>/`에 복사합니다. 다시 설치한 모듈은 이전에 있던 설정을 되찾습니다.
3. 수집기를 다시 시작하며, 수집기는 몇 초 안에 모듈을 불러옵니다.
4. 모듈을 목록에서 빼고 «<module> 설치 완료» 대화 상자를 엽니다. 이 대화 상자에는 서버에서 root로 실행할 명령(`manage.py setup-modules`)과 **복사** 버튼이 있습니다. 이 명령은 `localsiem` 사용자에게 `module.json`의 `read_paths`에 나열된 폴더(apache2 모듈은 `/var/log/apache2`, privesc 모듈은 `/var/log/audit`)와 앞으로 순환될 파일에 대한 읽기 권한을 주고 localSIEM을 다시 시작합니다. 모듈에 필요한 것은 이 읽기 권한이 전부입니다. 모듈에는 구성 옵션이 없으며 서버를 절대 변경하지 않습니다(8절과 11절). 이 명령을 실행할 때까지 모듈은 «오류»를 표시할 수 있습니다. 아직 로그를 읽을 수 없기 때문입니다. 대화 상자는 «닫기» 또는 «설치된 모듈 보기»로 닫으며, «설치된 모듈 보기»를 누르면 설치됨이 열립니다.

**업데이트.** 모듈 › **설치됨**을 열면 웹이 저장소를 확인하며, 저장소에 더 새로운 버전이 있는 모듈에는 **업데이트** 버튼이 있는 안내가 표시됩니다(3절). 확인하면 localSIEM은 새 버전을 내려받아 설치된 버전 대신 배치하고(1~3단계), 설정을 유지하며, 모듈을 켜짐 또는 꺼짐 상태 그대로 둡니다. root용 명령은 새 버전이 다른 로그(`read_paths`)를 읽는 경우에만 다시 표시되며, 그렇지 않으면 실행할 것이 없습니다. localSIEM을 업데이트해도 설치된 모듈과 그 읽기 권한은 유지됩니다.

**재설치.** 웹은 모듈을 재설치하지도, 모듈의 이전 버전을 설치하지도 않습니다. 모듈을 재설치하려면 **제거**(3절)를 누른 다음 **설치 가능**에서 다시 설치하십시오. 설정은 유지됩니다.

**모듈을 설치해도 모듈이 감시하는 소프트웨어는 절대 설치되지 않습니다.** apache2 모듈은 Apache도 ModSecurity도 설치하지 않으며, privesc 모듈은 auditd, syslog 데몬, snoopy 중 어느 것도 설치하지 않습니다. 처음 설치할 때 서버에 모듈에 필요한 것(apache2는 Apache와 ModSecurity, privesc는 `localsiem`이 읽을 수 있는 소스, 14절)이 없으면 모듈은 **꺼진 상태로** 설치됩니다. 대화 상자에는 명령 대신 없는 것이 나열되며, **재구성**이 이를 찾을 때까지 모듈을 켤 수 없습니다(4절). 업데이트는 모듈을 켜짐 또는 꺼짐 상태 그대로 둡니다.

<a id="modules-page"></a>
## 3. 모듈 페이지

관리자는 **관리 › 모듈**을 엽니다. 이 페이지에는 각각 고유한 주소를 가진 두 섹션이 있습니다. 기본으로 열리는 **설치됨**(`/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/`를 열면 여기로 이동합니다)과 **설치 가능**(`/admin/dashboard/modules/installable/`)입니다. 분석가는 자신의 대시보드에서 **모듈**(`/user/dashboard/modules/`)을 봅니다. 섹션 없이 설치된 모듈 목록만 읽기 전용으로 표시됩니다.

**설치됨**에는 설치된 모듈마다 한 행이 전체 너비로 표시됩니다. 이름, ID, 버전, 상태 배지, 요약, 그리고 그 아래에 해당 상태의 이유가 표시됩니다. 목록은 10초마다 자동으로 새로 고쳐집니다. 설치된 모듈이 없으면 «설치 가능 탭에서 모듈을 설치하십시오.»라고 표시됩니다(분석가에게는 «설치된 모듈이 없습니다. 관리자가 모듈 › 설치 가능에서 설치합니다.»).

| 상태 | 의미 |
|---|---|
| **켜짐, 정상 작동** | 켜져 있고, 수집기가 불러왔으며, 소스를 읽고 있습니다. 진단 경고는 참고 사항으로 나열되지만 상태를 바꾸지는 않습니다. |
| **켜짐, 경고 있음** | 켜져 있지만, 읽을 로그를 찾지 못했거나, 아직 존재하지 않는 소스가 있거나, 수집기가 시작된 후에 모듈이 설치되었습니다(`localsiem` 서비스를 다시 시작하십시오). |
| **오류** | 모듈을 불러올 수 없거나(오류가 표시됩니다), 진단에서 오류가 보고되었거나, 읽을 수 없는 소스가 있습니다(`localsiem` 사용자의 권한). |
| **꺼짐** | 꺼져 있거나, 요구 사항 없이 설치되었습니다(apache2: Apache 또는 ModSecurity가 없음, privesc: `localsiem`이 auditd 로그도 syslog도 읽을 수 없음). 이유에 그 내용이 표시됩니다. |
| **변경 사항 적용 중…** | 방금 켜거나 껐으며, 수집기가 변경 사항을 적용하는 중입니다. |
| **알 수 없음** | 수집기(`localsiem` 서비스)가 실행 중이 아니므로 아무것도 읽고 있지 않습니다. |

모듈이 꺼져 있지 않으면 행에는 다음도 표시됩니다: **읽고 있는 소스**(읽는 소스 / 찾은 소스), **줄(1시간)**, **마지막 데이터**, **이벤트(24시간)**, **차단됨(24시간)**, 그리고 **진단** 개수(«정상 n · 경고 n · 오류 n»).

관리자에게는 각 행에 다음도 표시됩니다:

- 각 모듈의 **스위치**. 모듈을 끌 때는 확인을 요청합니다. 다시 켤 때까지 localSIEM은 이 모듈의 로그 읽기와 알림 전송을 중지하며, 이미 저장된 데이터는 유지됩니다. 켜면 즉시 읽기 시작합니다. 모듈의 요구 사항이 충족되지 않은 동안에는 스위치가 잠겨 있습니다(«꺼짐: 요구 사항 누락»). **재구성**(4절)이 요구 사항을 찾으면 잠금이 해제됩니다.
- **구성**: 모듈 페이지 `/admin/dashboard/modules/installed/<name>/`(4절)를 엽니다. 이전 주소 `/admin/dashboard/modules/<name>/`도 이 페이지로 이동합니다.
- **제거**: 불러올 수 없는 모듈에도 표시됩니다(모듈 페이지에도 있습니다). 확인하면 localSIEM은 `/opt/localsiem/modules/<name>/`를 삭제하고 해당 모듈 없이 수집기를 다시 시작합니다. 이 모듈의 로그 읽기와 알림 전송이 중지됩니다. 이미 저장된 이벤트는 계속 검색할 수 있으며, 다시 설치할 경우를 대비해 설정도 유지됩니다. root가 `localsiem`에 준 로그 읽기 권한은 회수되지 않습니다.
- **업데이트**: 저장소에 모듈의 더 새로운 버전이 있을 때 표시됩니다. 설치됨을 열 때마다 웹은 저장소를 확인하며(«저장소에서 새 버전을 확인하는 중…», 브라우저는 응답을 10분 동안 재사용합니다), 모듈의 더 새로운 버전이 있는 행에는 «저장소에 X 버전이 있습니다(설치된 버전: Y).»라는 안내와 **업데이트** 버튼이 표시됩니다. 확인하면 localSIEM은 새 버전을 설치하고(2절), 설정을 유지하며, 모듈을 켜짐 또는 꺼짐 상태 그대로 두고 수집기를 다시 시작합니다. 새 버전이 다른 로그를 읽는 경우에만 대화 상자에 root용 명령이 표시됩니다. 새 버전에 더 새로운 localSIEM이 필요하면 안내에 «저장소에 X 버전이 있지만 localSIEM Z 이상이 필요합니다. 설치하려면 localSIEM을 업데이트하십시오.»라고 표시되며 버튼은 없습니다.

**설치 가능**(관리자 전용)에는 «설치 가능한 모듈» 카드가 있습니다. **저장소 확인**은 저장소를 내려받아 이 서버에 아직 설치되지 않은 모듈을 나열합니다. 각 모듈에는 이름, ID, 버전, 요약과 함께 버튼이나 안내가 표시됩니다:

| 버튼 또는 안내 | 의미 |
|---|---|
| **요구 사항** | 모듈이 서버에서 필요로 하는 것과 이를 설치하는 명령을 root로 실행하는 경우와 sudo를 사용하는 경우로 나누어 표시합니다(아래 참조) |
| **설치** | 모듈을 설치합니다(2절) |
| «localSIEM X 이상 필요» | 설치할 수 없습니다. 먼저 localSIEM을 업데이트하십시오 |
| «저장소의 모듈이 유효하지 않습니다» | 설치할 수 없습니다 |

이미 설치된 모듈은 여기에 절대 나타나지 않습니다. 이러한 모듈은 설치됨에서 업데이트합니다. 저장소의 모든 모듈이 설치되어 있으면 카드에 «저장소의 모든 모듈이 이미 설치되어 있습니다.»라고 표시됩니다. 설치 후 «<module> 설치 완료» 대화 상자에는 `localsiem`이 모듈의 로그를 읽을 수 있도록 root로 실행할 명령(2절)이 **복사** 버튼과 함께 표시됩니다. 이 명령을 실행할 때까지 모듈은 «오류»를 표시할 수 있습니다. 아직 로그를 읽을 수 없기 때문입니다. 서버에 모듈에 필요한 것이 없으면 대화 상자에는 그 대신 없는 것이 나열되며, 필요한 것이 갖춰지면 설치됨에서 모듈을 열고(**구성**) **재구성**을 누르라는 안내가 함께 표시됩니다.

**요구 사항**을 누르면 «<module>: 요구 사항»이 열립니다. 여기에는 모듈이 서버에서 필요로 하는 것과 이 서버의 시스템(«이 서버: …»)에 이를 설치하는 명령이 표시됩니다. 이 명령은 모듈이 선언한 것(`module.json`의 `install_requirements`)으로, **root로 실행**과 **sudo를 사용하여 실행**(앞에 `sudo`를 붙인 같은 명령)의 두 가지로 각각 **복사** 버튼과 함께 표시됩니다. 모듈을 설치하기 전에 서버에서 이 명령을 실행하십시오. 모듈을 설치해도 해당 소프트웨어는 절대 설치되지 않으며, localSIEM은 이 명령을 절대 실행하지 않습니다. apache2 모듈의 경우 Debian에서는 `apt-get -y update`, `apt-get -y install apache2 libapache2-mod-security2 modsecurity-crs`, `a2enmod security2 unique_id`, `cp --update=none /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf`(ModSecurity 구성이 없을 때만 DetectionOnly 구성을 만듭니다), `systemctl restart apache2`이며, Alpine에서는 Apache만 해당합니다(`apk add apache2`, 그다음 이를 시작하는 `rc-update`와 `rc-service`). Alpine에는 ModSecurity 2 패키지가 없기 때문입니다. ModSecurity를 소스에서 빌드하여 로드할 때까지 모듈은 꺼진 상태로 유지됩니다. privesc 모듈의 경우 Debian에서는 `apt-get -y install auditd rsyslog`, Alpine에서는 `apk add audit`와 부팅 시 auditd 시작입니다. 읽을 수 있는 소스가 하나만 있으면 되며, 컨테이너에서는 auditd를 실행할 수 없습니다.

<a id="apache-page"></a>
## 4. Apache 모듈 페이지

`/admin/dashboard/modules/installed/apache2/`(관리자 전용, 이전 주소 `/admin/dashboard/modules/apache2/`도 여기로 이동합니다)는 다섯 부분으로 이루어져 있습니다:

1. **헤더**: 이름, ID, 버전, 설치 경로(`/opt/localsiem/modules/apache2`), 스위치, 상태와 그 이유, 3절의 수치. **설치된 모듈로 돌아가기**는 설치됨으로 돌아갑니다. **다시 탐색하고 진단 실행**은 Apache 구성을 즉시 다시 읽고 진단을 새로 고칩니다. **재구성**은 Apache와 ModSecurity를 다시 찾습니다(아래 참조). **제거**는 모듈을 제거하고(3절) 설치됨으로 돌아갑니다.
2. **설정**: 5절의 양식. **설정 저장**은 모든 값을 확인하며, 잘못된 값이 있으면 어느 값인지 알려 줍니다(«잘못된 값입니다: …»).
3. **소스**: 읽고 있는 모든 로그와 함께 **종류**(`access`, `error`, `audit`), **경로**, **Vhost**, **줄(1시간)**, **파싱 안 됨(1시간)**, **마지막 데이터**(예: `2026/10/29@13:59:59.723`), **상태**(읽을 수 없으면 오류, 아직 존재하지 않으면 경고)가 표시됩니다. 그 아래에는 찾았지만 읽지 않는 로그가 이유와 함께 표시됩니다: «파이프 로그, 지원되지 않음», «모든 vhost를 기록하는 GlobalLog에 포함됨» 또는 «형식에 데이터가 없음: 모든 줄이 같은 텍스트임(정의되지 않은 LogFormat 별칭)».
4. **진단**: 7절의 검사와 그 실행 시각. 충족되지 않은 각 요구 사항(ModSecurity, CRS, `SecRuleEngine`, `mod_unique_id`, `localsiem`의 읽기 권한)에는 이를 해결하는 스니펫이나 명령과 **복사** 버튼이 함께 표시됩니다. 로그에 관한 검사는 로그와 localSIEM이 로그에서 읽을 수 있는 것을 설명할 뿐 해결 방법은 제시하지 않습니다. 클라이언트의 로그는 절대 변경하지 않습니다(8절).
5. **규칙**: 9절의 규칙. 각 규칙에는 **켜짐**, **규칙**(이름, ID, 범주), **심각도**, **임계값**, **기간(초)**이 있으며, **규칙 저장**이 있습니다.

**요구 사항과 재구성.** Apache 또는 ModSecurity가 없는 동안 모듈은 꺼져 있으며, 헤더에 없는 것이 이를 설치하는 명령과 함께 나열됩니다. **재구성**(모듈이 꺼져 있을 때도 사용 가능)은 저장된 설정으로 이를 다시 찾습니다. Apache가 표준이 아닌 위치에 있으면 먼저 **Apache 구성 파일**을 설정하십시오(5절). 둘 다 찾으면 스위치 잠금을 해제하고(모듈을 켜는 것은 사용자가 결정합니다), 모듈을 설치한 후에 생성된 Apache 로그를 `localsiem`이 읽을 수 있도록 root로 실행할 명령을 표시합니다. 켜져 있는 모듈은 Apache나 ModSecurity가 사라져도 켜진 상태로 유지됩니다. 진단과 상태 경고(10절)가 이를 보고합니다.

**모든 변경 사항은 아무것도 다시 시작하지 않고 즉시 적용됩니다**. 웹이 변경 사항을 저장하고 수집기에 알리면, 수집기는 설정을 다시 불러오고, 소스를 다시 탐색하고, 진단을 실행합니다. 수집기가 응답하지 않으면 웹이 그 사실을 알려 주며, 변경 사항은 수집기가 시작될 때 적용됩니다.

<a id="settings"></a>
## 5. Apache 모듈 설정

| 설정 | 기본값 | 기능 |
|---|---|---|
| **아래 소스만 사용** | 꺼짐 | Apache 구성에서 로그를 탐색하지 않고 직접 추가한 소스만 읽습니다. |
| **직접 추가한 소스** | 없음 | 탐색된 로그 외에(또는 위 옵션을 사용하면 탐색된 로그 대신) 읽을 로그입니다. 최대 50개. |
| **Apache 구성 파일** | 비어 있음 | 비워 두면 자동으로 찾습니다(Debian은 `/etc/apache2/apache2.conf`, Alpine은 `/etc/apache2/httpd.conf`이며, `/etc/httpd/conf/httpd.conf`도 인식합니다). 절대 경로를 입력하면 그 파일이 있을 경우 그 파일을 대신 사용합니다. |
| **탐색 간격(초)** | 3600 | 새 vhost와 로그를 찾기 위해 Apache 구성을 다시 읽는 주기입니다(60~86400). |
| **ModSecurity 차단 임계값** | 0 | 0: CRS 구성(`crs-setup.conf`의 `tx.inbound_anomaly_score_threshold`)에서 읽으며, 값이 없으면 5를 사용합니다. ModSecurity 메시지 자체에 임계값이 표시되지 않을 때 차단 임계값 이상의 일치와 미만의 일치를 구분하는 데 사용합니다(0~1000). |
| **새 PHP 파일 학습 기간(일)** | 3 | 모듈이 처음 시작된 후 처음 며칠 동안은 처음 보는 PHP 파일을 `apache-webshell` 규칙이 새 파일로 보고하지 않습니다(0~365). DocumentRoot에서 최근 하루 안에 생성되거나 수정된 파일은 항상 새 파일로 간주합니다. |

**직접 추가한 소스**에는 각각 다음 필드가 있습니다(*는 필수):

| 필드 | 용도 |
|---|---|
| **종류** * | `access.log`, `error.log` 또는 `ModSecurity audit log` |
| **경로** * | 파일의 절대 경로 |
| **Vhost** | 줄에 vhost가 표시되지 않는 로그의 경우, 그 줄들의 vhost |
| **LogFormat** | 액세스 로그의 경우: 별칭(`localsiem_combined`, `combined`, `vhost_combined`, `common`, `combinedio` 또는 Apache 구성에 정의된 별칭) 또는 형식 자체. 비워 두면 일반적인 형식을 차례로 시도합니다. |
| **감사 로그 유형** | `Serial (one file)` 또는 `Concurrent (one file per request)` |
| **감사 저장 폴더** | 동시 유형의 경우: `SecAuditLogStorageDir`의 폴더 |

파일은 탐색되면서 동시에 직접 추가되었더라도 한 번만 읽습니다. localSIEM이 실행 중일 때 나타난 소스는 크기가 5 MB 이하이면 처음부터, 그렇지 않으면 끝부터 읽습니다.

localSIEM의 **관리 › 설정**에 있는 두 설정도 이 모듈에 영향을 줍니다: **상관관계 기간**(5초: 요청의 세 레코드를 기다리는 시간)과 **차단 임계값 미만의 심각도**(`low`). ModSecurity가 표시한 요청은 ModSecurity가 요청이 끝날 때 기록하는 감사 레코드도 최대 2분 동안 기다립니다. 따라서 느린 요청이 두 이벤트로 나뉘지 않습니다.

<a id="soc"></a>
## 6. Apache 모듈이 SOC로 보내는 것

모듈은 각 요청에 대해 같은 `UNIQUE_ID`를 가진 액세스 줄, 오류 줄, 감사 레코드를 결합합니다. Apache가 기본으로 기록하는 액세스 로그(`combined`, `vhost_combined`, `common`)에는 `UNIQUE_ID`가 없습니다. 이 경우 각 액세스 줄은 클라이언트 IP, 메서드, URI, 상태, 시각(±2초)으로 자신의 요청의 감사 레코드 및 오류 줄과 결합되며, 같은 요청이 같은 초에 반복되어도 마찬가지이고, 이벤트는 «약한 상관관계»로 표시됩니다. vhost는 `%v`에서 가져오며, 형식에 없으면 Apache가 선택하는 방식대로 감사 레코드의 Host 헤더와 포트에서 가져옵니다. 시각은 감사 레코드의 마이크로초를 사용합니다. 그런 다음 이미 조치가 취해졌는지(«수행된 조치») 판단하는데, 먼저 감사 로그(`Action: Intercepted (phase N)`)를 읽고, 그다음 error.log(`Access denied with code NNN (phase N)`)를 읽습니다. ModSecurity의 흔적이 없는 403은 차단으로 간주하지 않으며 의심스러운 것으로 표시합니다.

| 상황 | SOC로 보내나요? |
|---|---|
| ModSecurity가 1-2단계에서 차단함(애플리케이션이 요청을 받지 못함) | **아니요.** localSIEM에 남아 검색할 수 있으며(`action:blocked`), 그 IP의 다음 알림 컨텍스트에서 집계됩니다. |
| 3-4단계에서 차단됨(애플리케이션이 이미 요청을 실행함) | 예 |
| 엔진이 `DetectionOnly`일 때의 규칙 일치 | 예 |
| 차단 임계값 미만의 규칙 일치 | 예 |
| 9절 규칙의 신호 | 예 |

ModSecurity 일치로 발생한 알림의 심각도(모듈의 `severity.yaml` 파일):

| 상황 | 심각도 |
|---|---|
| 차단되지 않은 일치, 응답 3xx, 4xx 또는 5xx | 중간 |
| 차단되지 않은 일치, 응답 2xx | 높음 |
| 3-4단계에서 차단됨 | 높음 |
| 성공의 징후: 아웃바운드 규칙(950-955)이 일치했는데 아무것도 차단되지 않았거나, 요청 후에 데이터베이스 오류가 발생함 | 심각 |
| 차단 임계값 미만(대개 애플리케이션 자체의 오탐) | 낮음(관리 › 설정의 차단 임계값 미만의 심각도) |

각 알림에는 고정된 이름(예: «Apache/ModSecurity: SQL injection not blocked (CRS 942)»), localSIEM 검색에 붙여 넣을 쿼리로 끝나는 설명(예: `ip:203.0.113.7 category:sqli`), 그리고 세부 정보(vhost, 클라이언트 IP, 메서드, URI(마스킹됨), 응답, 사용자 에이전트, ModSecurity 데이터(엔진, 조치, 단계, 이상 점수, 임계값, 규칙, 일치한 데이터))가 있습니다. 알림을 보낼 때는 IP의 컨텍스트도 함께 보냅니다: 최근 1시간의 요청과 차단된 요청, 이를 차단한 규칙, 처음 발견된 시각.

비밀번호, 쿠키, `Authorization` 헤더, 토큰은 요청 본문 안에 있는 것까지 포함하여 무엇이든 저장되기 전에 마스킹되며, 요청 본문은 절대 SOC로 전송되지 않습니다. 감사 로그의 응답 본문(파트 E)과 실행된 규칙의 전체 텍스트(파트 K)는 절대 보관하지 않습니다.

<a id="doctor"></a>
## 7. Apache와 ModSecurity 요구 사항: 진단

apache2 모듈의 진단은 Apache 구성을 (변경하지 않고) 읽고 각 요구 사항을 확인합니다. 진단은 수집기가 시작될 때, 설정을 변경할 때마다, 탐색할 때마다, **다시 탐색하고 진단 실행**을 누를 때, 그리고 `manage.py doctor`(17절)로 실행되며, 모듈이 켜져 있을 때만 실행됩니다. Apache나 ModSecurity가 없어서 꺼져 있는 동안에는 모듈 페이지에 그 요구 사항이 대신 표시됩니다(4절). 상태: 정상, 경고(제한적으로 작동함), 오류(반드시 해결해야 함), 정보(일부 상황에서만 중요함).

| 검사 | 정상인 경우 | 그렇지 않은 경우 |
|---|---|---|
| Apache 구성 | `apache2.conf` 또는 `httpd.conf`(또는 구성된 파일)를 찾아 읽음 | 오류: 소스를 직접 추가하십시오(5절). 읽을 수 없는 부분은 경고로 나열됩니다. |
| ModSecurity | `mod_security2`(ModSecurity 2)가 로드됨 | 오류. Debian: `apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`. Alpine에는 패키지가 없습니다: mod_security2 2.9를 소스에서 빌드하십시오. ModSecurity 3(libmodsecurity)은 지원하지 않습니다. |
| OWASP CRS | CRS 파일이 포함됨(진단에 파일 수와 이상 임계값이 표시됩니다) | 오류: `apt-get install modsecurity-crs`를 실행하거나, ModSecurity 다음에 `crs-setup.conf`와 `rules/*.conf`를 포함하십시오 |
| SecRuleEngine | `On`(임계값을 넘는 요청은 2단계에서 차단되어 localSIEM에 남음) 또는 `DetectionOnly`(아무것도 차단되지 않으며 모든 일치가 SOC로 감) | `Off`이면 오류. 일부 vhost를 제외하고 `Off`이거나, 설정이 없거나(이 경우 ModSecurity의 기본값은 `Off`), 일부 vhost에서 `Off`로 설정하면 경고 |
| mod_unique_id | 로드됨: ModSecurity가 작동하고 요청의 세 소스가 `UNIQUE_ID`로 결합됨 | ModSecurity가 로드되어 있으면 오류: ModSecurity 2는 이것 없이는 아무것도 검사하지 않습니다(Alpine은 이를 로드하지 않습니다). 그렇지 않으면 경고(약한 상관관계). Debian: `a2enmod unique_id`, Alpine: `LoadModule unique_id_module modules/mod_unique_id.so` |
| 액세스 로그 형식 | 액세스 로그에 Apache가 기본으로 기록하는 형식처럼 클라이언트 IP, 시각, 요청 줄, 상태가 있음(정상, «Access logs in the format Apache writes»): 각 줄은 클라이언트 IP, 메서드, URI, 상태, 시각으로 해당 요청의 ModSecurity 레코드와 결합됩니다. 형식에 밀리초, vhost, `UNIQUE_ID`가 있으면(예: 이미 이를 기록하는 서버의 `localsiem_combined`) `UNIQUE_ID`로 결합됩니다(정상, «Access log with milliseconds, vhost, duration and UNIQUE_ID») | 액세스 로그에 네 가지 중 하나라도 없으면 해결 방법 없이 정보: localSIEM은 그 로그를 있는 그대로 읽지만 그 줄을 ModSecurity 레코드와 결합할 수 없습니다(그 요청은 감사 로그에서 볼 수 있습니다). 읽는 액세스 로그가 없으면 정보(요청은 오류 로그와 감사 로그에서 볼 수 있습니다). 로그 형식은 클라이언트가 정합니다(8절) |
| mod_remoteip | `RemoteIPHeader`와 함께 로드됨 | 해결 방법 없이 정보: 웹이 프록시나 로드 밸런서 뒤에 있으면 로그에 프록시의 IP가 기록되며, 알림과 IP 기반 규칙도 마찬가지입니다 |
| 감사 로그 | `SecAuditLog`와 함께 `SecAuditEngine RelevantOnly`(또는 `On`) | 꺼져 있으면 경고: localSIEM은 error.log만으로 판단하며, 요청 카드에 헤더나 규칙 목록이 없습니다. 켜져 있으면 참고 사항은 감사 로그를 설명할 뿐입니다: 동시 유형(트랜잭션마다 파일 하나. ModSecurity는 대개 모드 600으로 파일을 만들며, `localsiem`이 읽을 수 있으면 localSIEM이 읽습니다), 네이티브 형식(있는 그대로 읽음), 파트 E 기록됨(SOC로는 절대 보내지 않음), 파트 H 없음(감사 로그에서 수행된 조치를 읽을 수 없음. 검사를 경고로 만드는 유일한 참고 사항입니다). 해결 방법 없음: 감사 로그는 클라이언트가 구성합니다(8절) |
| 원본에서의 마스킹 | `sanitise` 동작이 있음 | 해결 방법 없이 정보(«The audit log on disk is not masked»): ModSecurity가 기록한 파일에 비밀번호와 쿠키가 들어 있을 수 있습니다. localSIEM은 저장하기 전에 이를 마스킹하며, SOC로는 절대 보내지 않습니다 |
| 권한 | `localsiem`이 모든 소스를 읽을 수 있음 | 오류. Debian: `usermod -aG adm localsiem`, Alpine: 표시된 `setfacl` 명령. 아직 존재하지 않는 소스는 정보일 뿐입니다. |
| 파이프 로그 | — | 경고: `\|/usr/bin/rotatelogs ...`와 syslog는 읽을 수 없습니다. 로그를 파일에도 기록하거나 소스를 직접 추가하십시오 |
| 데이터가 없는 액세스 로그 | — | 경고: `CustomLog`가 어떤 `LogFormat`에도 정의되지 않은 형식(또는 `%` 지시자가 없는 `LogFormat`)을 사용하므로, Apache가 모든 줄에 클라이언트 IP, 시각, 요청 없이 같은 텍스트를 기록합니다. localSIEM은 그 로그를 읽지 않으며, 해당 vhost의 요청은 오류 로그와 ModSecurity 감사 로그에서 봅니다. 서버의 로그 형식은 절대 변경하지 않습니다. |
| 엔진 Off 감지 | — | 오류: 감사 레코드에 엔진이 비활성화된 것으로 보고됨 |
| ModSecurity 버전 | — | 정보: 감사 로그에서 읽은 버전 |

구성에 형식에 `%v`가 있는(모든 vhost를 기록하는) `GlobalLog`가 있으면 다른 액세스 로그는 읽지 않습니다. 그 로그의 줄을 반복할 뿐이기 때문입니다. 진단은 로그 형식이나 감사 로그 설정을 변경하라고 절대 제안하지 않습니다(8절).

<a id="client-logs"></a>
## 8. 클라이언트의 로그는 절대 건드리지 않습니다

apache2 모듈은 Apache와 ModSecurity의 로그를 **읽기만** 합니다. 로그에 쓰거나 로그를 순환, 잘라내기, 이동, 삭제하지 않으며, 로그 형식이나 로그를 기록하는 Apache 또는 ModSecurity 구성을 절대 변경하지 않습니다. 서버가 자체 형식으로 로그를 기록하면(예: 자체 `LogFormat`이나 `mod_remoteip`가 제공하는 클라이언트 IP) 모듈이 그 형식에 맞춥니다. 각 액세스 로그를 해당 `CustomLog`가 사용하는 형식으로 읽습니다. 진단(7절)은 로그와 localSIEM이 로그에서 읽을 수 있는 것과 읽을 수 없는 것을 설명할 뿐 로그를 변경하라고 제안하지 않습니다. 해결 방법은 로그가 아닌 것, 즉 ModSecurity, CRS, `SecRuleEngine`, `mod_unique_id`, `localsiem` 사용자의 읽기 권한에 대해서만 제시합니다. 이 모듈을 위해 root로 수행하는 유일한 작업은 그 읽기 권한 부여(`manage.py setup-modules`, 2절)입니다.

모듈 버전 1.2.0 이하에는 구성 옵션 `--configure-apache`가 있었으며, 버전 1.3.0에서 제거되었습니다. 이를 적용한 서버에는 그 옵션이 기록한 파일 `/etc/apache2/conf-available/localsiem.conf`(Debian) 또는 `/etc/apache2/conf.d/localsiem.conf`(Alpine)가 남아 있습니다. 이 파일에는 `localsiem_combined` 형식과 그 `GlobalLog`(`localsiem_access.log`), 감사 로그 설정, 민감한 값을 마스킹하는 `SecAction`이 들어 있습니다. 이 파일이 있는 동안 모듈은 그 로그를 다른 로그와 마찬가지로 읽습니다. 되돌리려면 이 파일을 삭제하고(Debian: `a2disconf localsiem`) Apache를 다시 로드하십시오. Alpine에서는 이 파일이 `mod_unique_id`와 `mod_logio`도 로드했습니다. 이 파일을 삭제하기 전에 Apache 구성의 다른 곳에서 `mod_unique_id`를 로드하십시오. ModSecurity 2는 이 모듈 없이는 아무것도 검사하지 않기 때문입니다(7절). localSIEM 설치 프로그램은 `--uninstall` 또는 `--reinstall`로 이 파일을 삭제하며(Alpine에서는 먼저 다른 곳에서 `mod_unique_id`를 로드하십시오), 로그(`localsiem_access.log`, `modsec_audit.log`)는 그 자리에 그대로 둡니다.

<a id="rules"></a>
## 9. Apache 모듈 규칙

규칙은 모든 이벤트에 대해 평가됩니다. 규칙의 신호는 항상 SOC로 보냅니다. 모듈 페이지에서 각 규칙을 끌 수 있고, 심각도, 임계값(1~100000), 기간(1~86400초)을 변경할 수 있습니다. 임계값과 기간은 임계값 규칙과 시퀀스 규칙에만 적용됩니다. 규칙의 이벤트는 `rule:localsiem:<id>`로 찾을 수 있습니다.

| 규칙 | 종류 | 심각도 | 조건 | 임계값 / 기간 |
|---|---|---|---|---|
| `apache-bruteforce` «brute force against a login page» | 임계값 | 중간 | 한 IP에서 한 vhost의 로그인 페이지(`/wp-login.php`, `/xmlrpc.php`, `/administrator/index.php`, `/user/login`, `/login`, `/admin/login`, `/login.php`, `/admin.php`, `/signin`, `/auth/login`, `/phpmyadmin/index.php`)로 보낸 차단되지 않은 POST 요청 | 300초에 20회 |
| `apache-login-after-bruteforce` «successful login after a brute force» | 시퀀스 | 높음 | 로그인 페이지에 대한 로그인 실패(200, 401 또는 403으로 응답한 POST)가 10회 이상 발생한 후 302 또는 303으로 응답한 로그인이 발생함(WordPress는 로그인 실패에 200, 성공한 로그인에 302로 응답합니다) | 10회, 1800초 이내 |
| `apache-enumeration` «enumeration (burst of 404 answers)» | 임계값 | 중간 | 한 vhost가 한 IP에 보낸 차단되지 않은 404 응답 | 60초에 30회 |
| `apache-sensitive-file` «sensitive file served» | 일치 | 높음 | 공개되어서는 안 되는 파일에 대한 2xx 응답: `.env`, `.git/`, `.svn/`, `.hg/`, `.htaccess`, `.htpasswd`, 덤프와 백업(`.sql`, `.sql.gz`, `.bak`, `.old`, `.orig`, `.swp`, `.save`, `.backup`, `.dump`, `~`로 끝나는 이름), `phpinfo`, `info.php`, `server-status`, `server-info`, `wp-config.php`와 `config.php`/`config.inc`의 사본, `.DS_Store`, SSH 개인 키, `composer.json`/`composer.lock`, `.aws/`, `backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «possible web shell (POST to a new PHP file)» | 일치 | 심각 | DocumentRoot에서 최근 하루 안에 생성되거나 수정된 PHP 파일, 또는 (학습 기간이 지난 후) 최근 1시간 안에 처음 발견된 PHP 파일에 대해 2xx로 응답한 POST | — |
| `apache-db-error-after-attack` «database error after a suspicious request» | 시퀀스 | 심각 | CRS 규칙과 일치한 요청과, 같은 IP에서 발생한 error.log의 데이터베이스 오류(SQL 또는 PDO) | 1회, 30초 이내 |

<a id="health"></a>
## 10. Apache 모듈 상태 경고

localSIEM 자체의 상태 경고 외에도, 모듈은 최대 5분마다 다음을 확인하여 SOC로 보냅니다:

| 경고 | 심각도 | 조치 |
|---|---|---|
| ModSecurity가 더 이상 로드되어 있지 않음 | 높음 | 로드되어 있었지만 더 이상 로드되어 있지 않습니다. 요청이 검사되지 않습니다. 아무도 의도적으로 한 일이 아니라면 누군가 보호 기능을 껐을 수 있습니다. |
| ModSecurity 엔진이 Off로 바뀜 | 높음 | `SecRuleEngine`이 `Off`로 바뀌었거나, 감사 로그에 엔진이 비활성화된 것으로 보고됩니다. Apache 구성과 최근 변경 사항을 확인하십시오. |
| 실제 클라이언트 IP 없음(mod_remoteip) | 중간 | 최근 1시간 동안 100개 이상의 요청 중 90 % 이상이 하나의 사설 또는 로컬 주소에서 왔습니다. 웹이 프록시 뒤에 있고 Apache가 프록시의 IP를 기록하고 있을 가능성이 높으므로, IP 기반 규칙이 이 요청들에 대해 작동하지 않습니다. 하루에 최대 한 번 보냅니다. |

이미 보고한 것은 다시 시작한 후에도 기억하므로 업데이트해도 다시 보내지 않습니다. 이러한 경고가 있기 때문에, 켜져 있는 모듈은 Apache나 ModSecurity가 사라져도 스스로 꺼지지 않습니다.

<a id="privesc"></a>
## 11. 권한 상승 모듈

**privesc** 모듈(«권한 상승»)은 사용자와 서비스가 서버에서 실행하는 것을 감시하고 root로 가는 권한 상승의 단계를 보고합니다: 정찰, setuid 프로그램 탐색, linpeas 같은 열거 도구, 알려진 익스플로잇, 리버스 셸, sudo나 su 없이 획득한 root, 남겨진 백도어, 감시를 무력화하려는 시도. 또한 서버의 공격 표면도 검토합니다: setuid 프로그램, capability, 다른 사용자가 쓸 수 있는 민감한 파일(16절).

서버에 이미 있는 것만 읽습니다. 아무것도 설치하지 않고, 감사 규칙을 로드하지 않으며, auditd, snoopy 또는 셸의 구성을 절대 변경하지 않습니다. 최대 두 개의 소스를 읽습니다:

| 소스 | 보는 것 | 작동하는 곳 |
|---|---|---|
| **auditd** (`/var/log/audit/audit.log`) | sudo, su, pkexec, SSH 로그인(PAM), 그리고 서버의 감사 규칙이 기록하는 모든 것(아래 참조) | auditd가 실행 중인 베어메탈과 가상 머신. **컨테이너 안에서는 작동하지 않습니다**(LXC, podman, systemd-nspawn, Docker). 커널의 감사 기능은 네임스페이스로 분리되지 않으므로 auditd는 호스트에서만 실행됩니다. |
| **syslog** (`/var/log/auth.log`, `/var/log/secure` 또는 `/var/log/messages`) | sudo, su, pkexec, doas, SSH 로그인, 그리고 **snoopy**가 설치되어 있으면 실행되는 모든 프로그램 | 컨테이너를 포함한 모든 곳. auditd가 실행되지 않거나, auditd 로그를 읽을 수 없거나, snoopy가 설치된 경우에 읽습니다(**syslog 읽기** 설정). 파일에 기록하는 syslog 데몬이 필요합니다. systemd 저널만으로는 읽지 않습니다. |

auditd가 보여 주는 것은 서버가 로드하는 감사 규칙에 따라 달라지며, 이는 서버 관리자가 결정합니다. 모듈은 키와 관계없이 감사 규칙을 있는 그대로 사용하고, 각 레코드를 종류, 시스템 호출, 파일에 따라 분류합니다:

| 모듈이 보는 것 | 서버의 감사 규칙이 기록하는 것 |
|---|---|
| 실행되는 모든 프로그램(스크립트, 웹 셸, 익스플로잇에서 실행된 것 포함), setuid 프로그램, 이로부터 상속된 root, 획득한 capability | `execve` |
| 계정, sudoers, PAM, preload, SSH, cron, 서비스, `/etc/audit`의 변경 | 해당 파일에 대한 감시(`-w ... -p wa`) 또는 이를 변경하는 시스템 호출 |
| 설정된 setuid 또는 setgid 비트 | `chmod`, `fchmod`, `fchmodat` |
| 로드되거나 제거된 커널 모듈 | `init_module`, `finit_module`, `delete_module` |
| ptrace로 연결된 프로세스 | `ptrace` |
| 사용자에게 거부된 파일 | `EACCES` 또는 `EPERM`으로 실패한 `open`, `openat`, `execve`... |
| 감사 규칙 제거, 감사 끄기, auditd 중지, 충돌한 프로그램 | 항상(커널과 auditd가 보고함) |

베어메탈 서버나 가상 머신에서는 auditd가 사용자가 피할 수 없는 소스입니다. 진단은 서버의 감사 규칙이 지금까지 무엇을 기록했는지 알려 줍니다(14절). 컨테이너에서는 snoopy만이 실행되는 모든 프로그램을 볼 수 있는 방법입니다.

셸 내장 명령(`pwd`, `cd`, `unset HISTFILE`, `history -c`)은 프로그램을 실행하지 않으므로, `bash -c '...'` 같은 명령줄 안에서 실행되는 경우를 제외하고는 어떤 소스에서도 보이지 않습니다. `whoami` 하나는 절대 알림이 되지 않습니다. 모듈은 각 세션의 **서로 다른** 정찰 명령을 기간 안에서 세며, 그 명령들이 집중적으로 실행될 때만 알림이 됩니다(13절).

모듈의 각 이벤트에 들어 있는 것과 검색 방법:

| 열 | 내용 | 검색 예 |
|---|---|---|
| `vhost` | 사람: 로그인 사용자(sudo와 su를 거쳐도 그대로 유지됨) | `module:privesc vhost:alice` |
| `method` | 이벤트 종류: `exec`(실행된 프로그램, auditd 또는 snoopy), `sudo`, `su`, `pkexec`, `doas`, `login`, `pam`, `file`(변경된 민감한 파일), `chmod`(setuid 비트), `kmod`, `ptrace`, `denied`(거부된 파일), `audit_config`, `auditd`, `crash`, `syscall`(서버의 감사 규칙이 기록한 다른 시스템 호출) | `module:privesc method:sudo` |
| `uri` | 명령줄(비밀번호는 마스킹됨) | `module:privesc uri:*linpeas*` |
| `path` | 실행된 프로그램 또는 변경된 파일 | `module:privesc path:/tmp/*` |
| `ip` | 세션의 SSH 주소(알려진 경우) | `module:privesc ip:203.0.113.7` |
| `score` | 기간 내 세션의 서로 다른 정찰 명령 수 | `module:privesc score:>=8` |
| `action` | 시스템 자체가 막은 경우 `blocked`: 실행할 수 없었던 프로그램, 거부된 sudo나 su, 거부된 파일 | `module:privesc action:blocked` |
| `source` | `audit` 또는 `syslog` | `module:privesc source:syslog` |

시도에 관한 규칙(반복된 sudo 실패, 많은 파일 거부)은 차단된 이벤트도 셉니다. 나머지 규칙은 실제로 실행된 것만 봅니다.

모듈 페이지 `/admin/dashboard/modules/installed/privesc/`는 Apache 모듈 페이지(4절)와 같은 부분으로 이루어져 있습니다: 헤더(**다시 탐색하고 진단 실행**, **재구성**, **제거** 포함), 설정(12절), 소스(`audit`, `syslog`, 그리고 읽지 않는 소스와 그 이유), 진단(14절), 규칙(13절).

<a id="privesc-settings"></a>
## 12. 권한 상승 모듈 설정

| 설정 | 기본값 | 기능 |
|---|---|---|
| **감사 로그** | 비어 있음 | 비워 두면 `/etc/audit/auditd.conf`의 `log_file` 또는 `/var/log/audit/audit.log`를 사용합니다. |
| **syslog 읽기** | 자동 | 자동: auditd가 실행되지 않거나, auditd 로그를 읽을 수 없거나, snoopy가 설치된 경우에만 읽습니다. 그 밖에 항상 또는 안 함. |
| **syslog 파일** | 비어 있음 | 비워 두면 `/var/log/auth.log`, `/var/log/secure`, `/var/log/messages` 중 처음으로 존재하는 파일을 사용합니다. |
| **무시할 사용자** | 비어 있음 | 쉼표로 구분합니다. 이 사용자의 명령은 저장되고 검색할 수 있지만 알림을 발생시키지 않습니다: 자동화 계정(ansible, 백업). `localsiem` 사용자는 항상 무시됩니다. |
| **관리자 그룹** | `sudo,wheel,admin` | 쉼표로 구분합니다. 이 그룹의 구성원(과 root)에게는 더 높은 정찰 임계값이 적용되며, 알림 없이 자신의 sudo 권한을 조회할 수 있습니다. |
| **정찰 기간(초)** | 120 | 세션의 서로 다른 정찰 명령을 세는 기간입니다(10~3600). |
| **정찰 임계값** | 8 | 사용자와 서비스 계정에 대해 집중 실행으로 판단하는, 기간 내 서로 다른 정찰 명령의 수입니다(2~500). |
| **관리자용 정찰 임계값** | 20 | root와 관리자에게 적용되는 같은 값입니다. 이들은 업무상 이러한 명령을 실행합니다(2~500). |
| **자동 열거 임계값** | 40 | 스크립트만이 실행할 만한(linpeas 유형), 기간 내 서로 다른 정찰 명령의 수입니다. 모든 사용자에게 적용됩니다(5~1000). |
| **서비스 계정 학습 기간(일)** | 3 | 모듈이 처음 시작된 후 처음 며칠 동안은 각 서비스 계정이 실행하는 프로그램(`sh -c sendmail`을 실행하는 `www-data`)을 알림 없이 학습합니다(0~365). |
| **setuid 프로그램 검사 간격(시간)** | 24 | setuid 및 setgid 프로그램과 파일 capability를 검색하는 주기입니다(16절). 0: 검사 안 함(0~168). |
| **검사할 폴더** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | 쉼표로 구분합니다. 각 폴더는 해당 파일 시스템을 벗어나지 않고 탐색합니다. 컨테이너의 폴더와 `/proc`, `/sys`는 항상 건너뜁니다. |
| **탐색 간격(초)** | 300 | 감사 로그, syslog, auditd 상태를 찾는 주기입니다(60~86400). 켜져 있는 모듈 중 가장 짧은 간격이 모든 모듈에 적용됩니다. |

정찰로 간주하는 것: `whoami`, `id`, `groups`, `uname`, `hostname`, `w`, `who`, `last`, `ps`, `ss`, `netstat`, `ip`, `ifconfig`, `env`, `pwd`, `history`, `getcap`, `lsmod`, `dmesg`, `mount` 및 유사한 명령; `sudo -l`, `crontab -l`, `systemctl list-*`, 패키지 목록; `which`, `locate`, `command -v`; `docker ps` 및 유사한 명령; 서로 다른 모든 `find`; `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/*-release`, `/proc/version`, `/root/...`, 셸 기록, SSH 키, `.env` 파일 읽기; `/root`, `/home`, `/opt`, `/tmp`, cron 폴더 등의 목록 보기...; `grep -r password`; 그리고 `<program> --version`. 세션의 서로 다른 각 명령은 기간 안에서 한 번만 셉니다.

<a id="privesc-rules"></a>
## 13. 권한 상승 모듈이 SOC로 보내는 것: 규칙

16절의 알림을 제외하면 모듈의 모든 알림은 규칙 중 하나에서 발생합니다(어떤 소스가 명령을 보았든 규칙은 똑같이 작동합니다). Apache와 마찬가지로 모듈 페이지에서 각 규칙을 끌 수 있고 심각도, 임계값, 기간을 변경할 수 있습니다. 규칙의 이벤트는 `rule:localsiem:<id>`로 찾을 수 있습니다. **무시할 사용자**에 대해서는 어떤 규칙도 발생하지 않습니다. «auditd»로 표시된 규칙에는 11절의 감사 레코드가 필요합니다.

| 규칙 | 종류 | 심각도 | 조건 | 임계값 / 기간 |
|---|---|---|---|---|
| `privesc-recon-burst` «reconnaissance burst» | 일치 | 중간 | 세션이 정찰 임계값(12절)에 도달함 | — |
| `privesc-enumeration` «automated enumeration (linpeas-like)» | 일치 | 높음 | 스크립트 이름을 바꾸더라도 세션이 자동 열거 임계값에 도달함 | — |
| `privesc-suid-hunt` «search for setuid programs or capabilities» | 일치 | 높음 | `find ... -perm -4000`(또는 `-u=s`, `/6000`, `-2000`...), `getcap -r`, `find -writable` | — |
| `privesc-sudo-list` «sudo rights listed by a non-administrator» | 일치 | 중간 | 관리자가 아닌 사용자 또는 서비스 계정의 `sudo -l` | — |
| `privesc-known-tool` «known enumeration tool» | 일치 | 높음 | linpeas, LinEnum, lse.sh, linux-exploit-suggester, les.sh, pspy, unix-privesc-check, linuxprivchecker, traitor, BeRoot, GTFONow, PEASS, deepce, CDK, sudo_killer, suid3num, mimipenguin, LaZagne, pwncat, searchsploit | — |
| `privesc-exploit` «known exploit» | 일치 | 심각 | PwnKit, DirtyPipe, Dirty COW, Baron Samedit (`sudoedit -s '\'`), Looney Tunables (`GLIBC_TUNABLES`), GameOver(lay), nf_tables (CVE-2024-1086), CVE-2023-22809 (`EDITOR=... -- /...`), polkit CVE-2021-3560 (`dbus-send ... CreateUser`), sudo와 함께 사용한 `LD_PRELOAD`, CVE 이름을 딴 스크립트, `exploit`, `getroot`, `rootme`라는 이름의 프로그램 | — |
| `privesc-pwnkit` «PwnKit (pkexec run without arguments)» | 일치 | 심각 | 인수 없이 실행된 `pkexec`(auditd) | — |
| `privesc-pwnkit-log` «pkexec reports a PwnKit attempt» | 일치 | 심각 | pkexec가 `GCONV_PATH`, «suspicious content» 또는 «was not found the /etc/shells»를 기록함(syslog) | — |
| `privesc-suid-escape` «root inherited from a setuid program» | 일치 | 심각 | setuid가 아닌 프로그램이 root의 유효 uid와 사용자의 실제 uid로 실행됨: setuid 프로그램이 악용되었습니다(GTFOBins). 마운트 도우미, D-Bus, polkit, X는 제외됩니다. | — |
| `privesc-root-without-door` «root without sudo, su or pkexec» | 일치 | 심각 | 시작이 확인된 사람의 세션이 sudo, su, pkexec, doas를 거치지 않고 root로 프로그램을 실행함(커널 익스플로잇)(auditd) | — |
| `privesc-root-shell-interpreter` «root shell started by an interpreter» | 일치 | 높음 | 일반 사용자가 실행하던 python, perl, ruby, awk, gdb 등이 시작한 셸이 root로 실행됨(그 자식 프로세스 또는 같은 프로세스)(auditd) | — |
| `privesc-file-capabilities` «program gained root capabilities from its file» | 일치 | 높음 | 사용자가 파일에서 `cap_setuid`, `cap_dac_override`, `cap_sys_admin` 등을 부여받는 프로그램을 실행함(auditd) | — |
| `privesc-tmp-exec` «program run from a world-writable folder» | 일치 | 높음 | `/tmp`, `/var/tmp`, `/dev/shm` 또는 `/run/user/<uid>`에 있는 프로그램 | — |
| `privesc-compile-tmp` «program compiled in a temporary folder» | 일치 | 높음 | 임시 폴더 안에서 또는 임시 폴더의 파일에 대해 실행된 `gcc`, `cc`, `clang`, `make` 등 | — |
| `privesc-download-shell` «downloaded script run by a shell» | 일치 | 높음 | `curl ... \| sh`, `bash -c "$(curl ...)"`, `bash <(wget ...)`, 또는 같은 파이프라인에서 다운로더 뒤에 셸이 오는 경우 | — |
| `privesc-reverse-shell` «reverse shell» | 일치 | 높음 | `/dev/tcp/`, `nc -e`, `ncat --exec`, `socat exec:`, `mkfifo ... \| nc`, python/perl/php/ruby/lua/node 소켓, `openssl s_client ... \| sh`, `awk /inet/tcp` | — |
| `privesc-tty-upgrade` «shell upgraded to a full terminal» | 일치 | 높음 | `pty.spawn`, `script ... /dev/null`, `stty raw -echo`, `socat ... pty`, `expect ... spawn sh` | — |
| `privesc-service-recon` «service account ran reconnaissance commands» | 일치 | 높음 | `whoami`, `id`, `uname` 등을 실행하는 `www-data`, `mysql` 및 기타 서비스 계정(웹 셸) | — |
| `privesc-service-new-program` «service account ran a program it never ran before» | 일치 | 높음 | 학습 기간이 지난 후 서비스 계정이 한 번도 실행한 적 없는 셸, 인터프리터 또는 도구를 실행함(`sh -c sendmail`만 실행하던 곳에서 `sh -c id` 실행) | — |
| `privesc-container-escape` «container used to reach the host as root» | 일치 | 높음 | root가 아닌 사람이 `docker run -v /:/...`, `--privileged`, `--pid=host`, `nsenter -t 1`, `lxc config set ... security.privileged true`, `lxc config device add ... source=/`, `debugfs /dev/...`를 실행함 | — |
| `privesc-auth-failures` «repeated sudo or su failures» | 임계값 | 중간 | 한 사용자의 sudo, su, pkexec 또는 doas 실패 | 600초에 3회 |
| `privesc-sensitive-file` «account, sudo, PAM or preload file changed» | 일치 | 높음 | 패키지 또는 계정 도구가 아닌 프로그램이 `/etc/passwd`, `shadow`, `group`, `gshadow`, `sudoers`, `sudoers.d`, `doas.conf`, `doas.d`, `ld.so.preload`, `ld.so.conf`, `ld.so.conf.d`, `pam.d`, `security`를 변경함(auditd) | — |
| `privesc-persistence-file` «SSH, cron or service file changed» | 일치 | 중간 | `/root/.ssh`, `sshd_config`, `sshd_config.d`, cron 파일, `/etc/systemd/system`, `/etc/init.d`, `rc.local`, `/etc/local.d`가 변경됨(auditd) | — |
| `privesc-monitoring-changed` «auditd configuration changed» | 일치 | 중간 | 패키지 도구가 아닌 프로그램이 `/etc/audit`를 변경함(auditd) | — |
| `privesc-suid-set` «setuid or setgid bit set on a file» | 일치 | 높음 | 패키지 관리자 밖에서 (폴더가 아닌) 파일에 대해 실행된 `chmod u+s`/`g+s`(auditd) | — |
| `privesc-setcap` «file capabilities set» | 일치 | 높음 | `setcap ... cap_...` | — |
| `privesc-kernel-module` «kernel module loaded from a session» | 일치 | 높음 | 사람의 세션에서 로드되거나 제거된 모듈(auditd) | — |
| `privesc-ptrace` «process attached with ptrace» | 일치 | 중간 | `PTRACE_ATTACH` 또는 `PTRACE_SEIZE`(auditd) | — |
| `privesc-denied-burst` «many files refused (enumeration)» | 임계값 | 중간 | 한 사용자에게 거부된 파일(`EACCES`, `EPERM`)(auditd) | 60초에 30회 |
| `privesc-sensitive-denied` «attempt to read the password hashes or files of root» | 일치 | 중간 | 사용자에게 `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` 또는 `/root`가 거부됨(auditd) | — |
| `privesc-history-tampering` «shell history erased or turned off» | 일치 | 중간 | `ln -s /dev/null ~/.bash_history`, `rm .bash_history` 등. `unset HISTFILE`, `HISTFILE=/dev/null`, `HISTSIZE=0`, `history -c`, `set +o history`는 내장 명령이 프로그램을 실행하지 않으므로 명령줄(`bash -c`) 안에서만 감지됨 | — |
| `privesc-audit-stop-command` «command to turn auditd off» | 일치 | 심각 | `auditctl -e 0`, `auditctl -D`, `auditctl -a never`, `systemctl stop/disable/mask auditd`, `service auditd stop`, `pkill auditd`, `/var/log/audit` 또는 `/etc/audit` 삭제 | — |
| `privesc-audit-disabled` «auditing turned off» | 일치 | 심각 | 커널이 `audit_enabled=0`을 보고함(auditd) | — |
| `privesc-auditd-stopped` «auditd stopped by a process» | 일치 | 높음 | init 이외의 프로세스의 요청으로 auditd가 중지됨(서버 종료는 보고하지 않음) | — |
| `privesc-crash` «setuid or temporary program crashed» | 일치 | 중간 | setuid 프로그램 또는 임시 폴더에 있는 프로그램이 충돌함(auditd `ANOM_ABEND`): 대개 실패한 익스플로잇 | — |

각 알림에는 고정된 이름, localSIEM 검색에 붙여 넣을 쿼리로 끝나는 설명, 그리고 세부 정보가 있습니다: 사용자, 계정 종류(`root`, `admin`, `user`, `service`), 실제 사용자와 유효 사용자, 명령, 프로그램, 폴더, 터미널, 세션, 소스(`auditd`, `snoopy`, `syslog`), 클라이언트 IP, 그리고 해당하는 경우 부모 프로그램, 인터프리터, 변경된 파일과 그 그룹, 집계된 정찰 명령, capability, 설정된 모드, ptrace 요청, 거부된 파일의 오류. 알림을 보낼 때는 세션의 컨텍스트도 함께 보냅니다: 세션의 시작이 확인되었는지, sudo나 su를 거쳤는지, SSH 주소, **최근 명령 20개**. 따라서 분석가는 검색하지 않고도 알림에 이르게 된 과정을 읽을 수 있습니다.

같은 명령을 둘 이상의 소스(auditd와 snoopy)가 볼 수 있습니다. 알림은 모듈, 사용자, IP, 범주, 심각도별로 그룹화되므로 그래도 알림 하나가 됩니다. 명령줄의 비밀번호(`mysql -p...`, `sshpass -p`, `curl -u user:pass`, `PASSWORD=...`, 비밀번호가 들어 있는 URL)는 감사 레코드의 16진수 표현까지 포함하여 무엇이든 저장되기 전에 마스킹됩니다.

<a id="privesc-doctor"></a>
## 14. 권한 상승 모듈 요구 사항: 진단

**요구 사항.** 모듈에는 `localsiem` 사용자가 읽을 수 있는(파일이 존재하고 `localsiem`이 열 수 있는) 소스가 하나 필요합니다: **auditd** 로그(auditd가 컨테이너 밖에서 실행 중) 또는 sudo, su, pkexec, doas가 기록되는 **syslog** 파일(`/var/log/auth.log`, `/var/log/secure` 또는 `/var/log/messages`, 또는 **syslog 파일** 설정. 단, **syslog 읽기**가 안 함이면 제외)이며, **snoopy**가 설치되어 있으면 실행되는 모든 프로그램도 이 파일에 기록됩니다. 이 중 하나만 있으면 됩니다. 소스가 존재하지만 `localsiem`이 읽을 수 없으면 요구 사항에 그 내용이 읽기 권한을 주는 명령과 함께 표시됩니다(감사 로그는 모듈 페이지의 명령 `manage.py setup-modules`, syslog는 `setfacl -m g:localsiem:r <file>`). 어느 것도 없으면 무엇을 설치해야 하는지 알려 줍니다: auditd(Debian: `apt-get install auditd`, Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`), syslog 데몬(Debian: `apt-get install rsyslog`, Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) 또는 snoopy. 그때까지 모듈은 꺼진 상태로 유지되며, **재구성**으로 다시 확인합니다. 모듈은 스스로 아무것도 설치하지 않습니다. 처음 설치할 때는 대개 로그가 root 소유입니다. 웹에 표시되는 명령을 실행한 다음 **재구성**을 누르십시오.

진단은 Apache 진단과 같은 방식으로 실행됩니다(7절). 서버에 있는 것으로 모듈이 볼 수 있는 것과 볼 수 없는 것을 설명할 뿐이며, 해결 방법은 설치할 패키지와 `localsiem`의 읽기 권한뿐입니다. 감사 규칙, `auditd.conf`(아래의 `log_group` 제외), `snoopy.ini`, 셸 또는 그 밖의 어떤 구성도 변경하라고 절대 제안하지 않습니다:

| 검사 | 정상인 경우 | 그렇지 않은 경우 |
|---|---|---|
| auditd | auditd가 실행 중 | 설치되어 있지 않으면 경고(Debian: `apt-get install auditd`, Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`). 설치되어 있지만 중지되어 있으면 해결 방법 없이 경고(실행 여부는 관리자가 결정합니다). 컨테이너 안에서는 정보: auditd를 실행할 수 없습니다. |
| 감사 로그 | `localsiem`이 읽을 수 있음 | 오류, 모듈 페이지의 명령과 함께. auditd가 실행 중인데 그 로그가 모듈이 찾는 위치에 없으면 경고(**감사 로그** 설정) |
| 감사 로그의 그룹 | 감사 로그가 `root` 그룹 소유가 아님 | 그 그룹 소유이면 경고(`auditd.conf`의 `log_group = root`): auditd가 순환할 때 만드는 모든 로그의 모드가 600이 되어 root만 읽을 수 있으므로 localSIEM이 읽기를 멈춥니다. 해결 방법은 `/etc/audit/auditd.conf`에 `log_group = adm` 줄을 넣는 것입니다(그다음 auditd를 다시 시작하십시오). 새 로그는 모드 640으로 만들어집니다. |
| 감사 규칙의 레코드 | 실행된 프로그램(`EXECVE`)을 읽음 | auditd가 기록하고 있지만 레코드 중 실행된 프로그램이 하나도 없으면 경고: 서버의 감사 규칙이 `execve`를 기록하지 않으므로 스크립트, 웹 셸, 익스플로잇의 명령을 auditd로 볼 수 없습니다. 감사 규칙이 지금까지 기록한 그 밖의 것(민감한 파일 변경, setuid 비트, 커널 모듈, ptrace, 거부된 파일)과 아직 기록하지 않은 것을 정보로 표시 |
| syslog | syslog 파일을 읽음 | 읽을 수 없으면 오류(`setfacl -m g:localsiem:r <file>`). 사용할 수 있는 감사 로그도 syslog 파일도 없으면 경고(Debian: `apt-get install rsyslog`, Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) |
| snoopy | 설치되어 있고 그 줄을 읽음 | auditd가 없으면 경고: 스크립트와 웹 셸의 명령이 보이지 않습니다(Debian: `apt-get install snoopy`, Alpine에는 패키지가 없으므로 소스에서 빌드합니다). 설치되어 있지만 syslog를 읽지 않으면 경고. 줄에 유효 uid가 없으면 정보(`snoopy.ini`의 `message_format`): setuid 프로그램에서 상속된 root를 snoopy로 볼 수 없습니다 |
| 모듈이 보는 것 | — | 정보: auditd(와 그 규칙이 기록하는 것), snoopy(실행되는 모든 프로그램), 또는 경고로 sudo, su, pkexec, doas만(snoopy 없는 syslog: 대부분의 규칙이 발생할 수 없음). 아무것도 읽을 수 없으면 오류. 셸 내장 명령은 절대 보이지 않는다는 점도 알려 줍니다 |
| 버전 1.0.0의 파일 | — | `--configure-privesc`가 남긴 파일이 발견되면 해결 방법 없이 정보(15절) |
| setuid 프로그램과 capability | — | 정보: 마지막 검사(16절). root 셸을 얻게 해 주는 setuid 프로그램(GTFOBins)과 capability가 사실상 root인 프로그램이 있으면 해결 방법 없이 경고 |
| 민감한 파일 | root 이외의 사용자가 쓸 수 있는 파일이 없음 | 해당 파일마다 해결 방법 없이 오류(`/etc/passwd`, `sudoers`, cron, `/etc/profile.d`, root의 `PATH` 폴더, `docker.sock`...) |
| 권한 있는 그룹 | — | `docker`, `lxd`, `incus-admin`, `disk`, `libvirt`의 구성원이 있으면 해결 방법 없이 경고: 이들은 사실상 root입니다 |

<a id="privesc-legacy"></a>
## 15. 권한 상승 모듈 버전 1.0.0에서 업데이트된 서버

모듈 버전 1.0.0에는 구성 옵션 `--configure-privesc`와 bash 훅이 있었습니다. 모듈은 `/opt/localsiem` 밖에서 아무것도 설치하거나 변경하지 않으므로 버전 1.1.0에서 둘 다 제거되었습니다. 이를 적용한 서버에는 그것이 기록한 것이 남아 있으며, localSIEM은 이를 사용하지도 삭제하지도 않습니다:

- `/etc/audit/rules.d/90-localsiem-privesc.rules`: 그 감사 규칙(키 `lsiem_*`). 이 규칙이 로드되어 있는 동안 모듈은 서버의 다른 규칙과 마찬가지로 그 레코드를 읽습니다.
- `/etc/localsiem-privesc/`(훅), `/etc/profile.d/localsiem-privesc.sh`, 그리고 `/etc/bash.bashrc`(Debian) 또는 `/etc/bash/bashrc`(Alpine)에서 «localSIEM privesc: command hook» 다음에 오는 줄: 이것들이 있는 동안 모든 대화형 bash는 계속 `/var/log/localsiem-privesc/`에 명령을 기록하지만, 아무도 이를 읽지 않습니다.
- `/var/log/localsiem-privesc/`: 각 사용자의 명령 파일.
- `/etc/audit/auditd.conf`의 `log_group = adm`, `/root/.ssh`(빈 폴더로 생성됨), `/etc/snoopy.ini`의 `message_format`: 그대로 두어도 됩니다(`log_group = adm`은 순환된 감사 로그를 계속 읽을 수 있게 해 주며(14절), 모듈은 snoopy의 그 형식도 기본 형식과 마찬가지로 읽습니다).

진단은 볼 수 있는 것을 나열합니다(검사 «Files of version 1.0.0 of the module»). 제거하려면 root로 다음을 수행하십시오: 규칙 파일을 삭제하고 규칙을 다시 로드하십시오(`augenrules --load`). `/etc/profile.d/localsiem-privesc.sh`, `/etc/localsiem-privesc/`, bashrc의 해당 줄을 삭제하십시오. 그리고 들어 있는 명령을 보관할 필요가 없으면 `/var/log/localsiem-privesc/`를 삭제하십시오.

<a id="privesc-health"></a>
## 16. 권한 상승 모듈의 공격 표면과 상태 경고

모듈은 규칙 외에도 서버 자체를 살펴보고 다음을 SOC로 보냅니다:

| 경고 | 심각도 | 조건 |
|---|---|---|
| 새 setuid 또는 setgid 프로그램 | 높음 | 검사에서 이전 검사에는 없던 setuid 또는 setgid 프로그램을 발견함(첫 번째 검사는 기준으로만 사용됩니다). root가 된 공격자는 setuid 셸을 남겨 두는 경우가 많으며, 패키지 업데이트로 추가될 수도 있습니다. |
| 쓰기 가능한 폴더의 새 setuid 프로그램 | 심각 | 위와 같으며, `/tmp`, `/var/tmp`, `/dev/shm`, `/home`, `/srv` 또는 `/var/www`에 있는 경우 |
| GTFOBins의 새 setuid 프로그램 | 심각 | 위와 같으며, setuid일 때 root 셸을 얻게 해 주는 프로그램(`bash`, `find`, `python`, `vim`, `less`, `cp`...)인 경우 |
| 새 capability | 높음 | 프로그램이 사실상 root인 capability(`cap_setuid`, `cap_dac_override`, `cap_sys_admin`...)를 얻음 |
| root 이외의 사용자가 쓸 수 있는 민감한 파일 | 심각 | 매시간 확인: `/etc/passwd`, `/etc/shadow`(모든 사용자가 읽을 수 있는 경우도 포함), `sudoers`, cron, `/etc/profile.d`, PAM, 서비스, `ld.so.preload`, root의 `PATH` 폴더, `docker.sock`... 파일과 문제별로 한 번만 보고합니다. |
| auditd 중지됨(localSIEM 상태) | 높음 | auditd가 실행 중이었는데 더 이상 실행되지 않음(컨테이너 밖에서) |

검사는 백그라운드에서 최대 **setuid 프로그램 검사 간격(시간)**마다 실행되며(첫 번째 검사는 수집기가 시작되고 5분 후), **검사할 폴더**를 `localsiem` 사용자로 탐색하고(읽을 수 없는 것은 건너뜀), 300만 개의 파일 또는 15분이 지나면 멈춥니다. 발견된 GTFOBins와 capability를 포함한 결과는 진단에 표시됩니다. 이러한 경고의 심각도는 모듈의 `severity.yaml`에 있습니다. 이미 보고한 것은 다시 시작한 후에도 기억합니다.

<a id="cli"></a>
## 17. 명령줄

root로 `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <command>`를 실행합니다:

| 명령 | 용도 |
|---|---|
| `modules` | 설치된 모듈: ID, 버전, 활성화됨, 비활성화됨 또는 불러오지 않음, 폴더, 그리고 충족되지 않은 요구 사항이 있으면 그 요구 사항. 또한 불러올 수 없었던 모듈과 그 오류 |
| `doctor` | 활성화된 각 모듈에 대해: 각 검사(`✓`, `!`, `✗`, `·`)와 이를 해결하는 스니펫, 그리고 찾은 소스. 요구 사항이 충족되지 않아 꺼져 있는 모듈은 그 요구 사항. `--json`은 같은 내용을 JSON으로 출력합니다. |
| `read-paths` | 모듈이 읽는 폴더로, localSIEM이 root로 읽기 권한을 줍니다 |
| `setup-modules [--no-restart]` | root로 실행: 웹에 표시되는 명령. 모듈의 폴더(`read_paths`)에 대한 읽기 권한 부여와 localSIEM 재시작(`--no-restart`: 재시작하지 않음). 모듈에는 구성 옵션이 없습니다 |

실제 권한을 확인하려면 `localsiem` 사용자로 진단을 실행하십시오:

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
