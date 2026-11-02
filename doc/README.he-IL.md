# localSIEM-modules

קובץ README זה זמין גם בשפות:\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), he-IL, [hi-IN](README.hi-IN.md), [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## מה זה

המודולים של [localSIEM](https://github.com/PYMEHackers/localSIEM), מערכת ה-SIEM הקלה שפועלת על אותו שרת שעליו היא מגנה. כל מודול מלמד אותה שירות אחד של השרת: היכן נמצאים הלוגים שלו, איך לקרוא אותם ואילו כללים חלים. כיום יש שניים:

- **apache2** (Apache + ModSecurity): מאחד את לוג הגישה, לוג השגיאות ולוג הביקורת של ModSecurity של כל בקשה, עם כללים ל-brute force, לסריקה, לקבצים רגישים, ל-web shells ולשגיאות מסד נתונים.
- **privesc** (הסלמת הרשאות): עוקב אחר מה שמורץ בשרת (auditd, sudo, su, pkexec, doas, snoopy) ומתריע על השלבים של הסלמה ל-root.

מודול לעולם אינו מתקין דבר בשרת: הוא עובד עם מה שכבר קיים בשרת.

## צילומי מסך

![המודול apache2 ב-localSIEM](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## התקנה

המודולים מותקנים מממשק האינטרנט של localSIEM. תחילה יש להתקין את localSIEM, בתור `root`:

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

האפשרות `--allow-from`: כתובות ה-IP המורשות לפתוח את ממשק האינטרנט (`https://<server>:10443`).

לאחר מכן, בממשק האינטרנט, יש לפתוח את **מודולים › ניתנים להתקנה**, ללחוץ על **בדיקת המאגר**, לעיין ב**דרישות** וללחוץ על **התקנה** במודול.

## קריאת התיעוד

להמשך קריאה:

- כדי ללמוד איך להתקין, להגדיר ולהשתמש בכל מודול: [doc/MANUAL.he-IL.md](MANUAL.he-IL.md).
- כדי להבין איך הם בנויים ואיך לכתוב מודול חדש (למפתחים ולמודלים של בינה מלאכותית): [doc/CODE.he-IL.md](CODE.he-IL.md).
