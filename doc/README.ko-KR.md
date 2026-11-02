# localSIEM-modules

이 README는 다음 언어로도 제공됩니다:\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), ko-KR, [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## 소개

[localSIEM](https://github.com/PYMEHackers/localSIEM)의 모듈입니다. localSIEM은 보호 대상과 같은 서버에서 실행되는 경량 SIEM입니다. 각 모듈은 서버의 서비스 하나를 다룹니다. 로그의 위치, 읽는 방법, 적용되는 규칙입니다. 현재 모듈은 두 가지입니다.

- **apache2**(Apache + ModSecurity): 각 요청의 액세스 로그, 오류 로그, ModSecurity 감사 로그를 하나로 묶으며, 무차별 대입, 열거, 민감한 파일, 웹 셸, 데이터베이스 오류에 대한 규칙이 있습니다.
- **privesc**(권한 상승): 서버에서 실행되는 것(auditd, sudo, su, pkexec, doas, snoopy)을 감시하고 root로의 권한 상승 단계를 경고합니다.

모듈은 서버에 아무것도 설치하지 않습니다. 서버에 이미 있는 것으로 동작합니다.

## 스크린샷

![localSIEM의 apache2 모듈](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## 설치

모듈은 localSIEM 웹에서 설치합니다. 먼저 localSIEM을 `root`로 설치하십시오.

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`: 웹(`https://<server>:10443`)을 열 수 있는 IP입니다.

그런 다음 웹에서 **모듈 › 설치 가능**을(를) 열고, **저장소 확인**을(를) 누르고, **요구 사항**을(를) 확인한 뒤 모듈의 **설치**을(를) 누르십시오.

## 문서 읽기

다음 문서를 참고하십시오.

- [doc/MANUAL.ko-KR.md](MANUAL.ko-KR.md): 각 모듈의 설치, 설정, 사용 방법을 설명합니다.
- [doc/CODE.ko-KR.md](CODE.ko-KR.md): 모듈의 내부 구조와 새 모듈을 작성하는 방법을 설명합니다(개발자 및 AI 모델용).
