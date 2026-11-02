# תיעוד הקוד של localSIEM-modules

קובץ CODE זה זמין גם בשפות:\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), he-IL, [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## אינדקס

1. [ארכיטקטורה והחלטות תכנון](#architecture)
2. [מפת המודולים](#modules)
3. [סמלים מרכזיים](#symbols)
4. [נתיבי הקריאה העיקריים](#flows)
5. [נקודות כניסה](#routes)
6. [ניתוח השפעה](#impact)
7. [נקודות הרחבה](#extensions)

[התקנה](README.he-IL.md) · [מדריך למשתמש](MANUAL.he-IL.md) · [תיעוד הקוד של localSIEM](../../localSIEM/doc/CODE.he-IL.md)

<a id="architecture"></a>
## 1. ארכיטקטורה והחלטות תכנון

פרויקט זה מכיל את המודולים הניתנים להתקנה של localSIEM (הפרויקט האח `../localSIEM`). אין לו שירות ואין לו תוכנית התקנה משלו: המודולים מותקנים רק מממשק האינטרנט של localSIEM, תחת מודולים › ניתנים להתקנה (הם מתעדכנים ומוסרים תחת מודולים › מותקנים), שמוריד את המאגר הזה (ענף `main`) ומעתיק כל תיקיית מודול, `mod-<name>/`, אל `/opt/localsiem/modules/<name>/`; תוכנית ההתקנה של localSIEM מתקינה רק את הליבה, לעולם לא מודול, ול-localSIEM אין מודולים משלו. התהליכים של localSIEM (רכיב האיסוף, ממשק האינטרנט, `manage.py`) טוענים את המודולים. הקידומת `mod-` שייכת רק לשם התיקייה במאגר הזה: המודול עצמו (ה-`id` של קובץ ה-`module.json` שלו, האפשרויות שלו, ההגדרות שלו והתיקייה המותקנת שלו) שומר על שמו בלעדיה. כיום יש שני מודולים: `apache2` (התיקייה `mod-apache2/`) ו-`privesc` (התיקייה `mod-privesc/`).

### למה המודולים חיים מחוץ לליבה

הליבה של localSIEM ([backend/core/](../../localSIEM/backend/core/)) היא גנרית: האחסון, החיפוש, מנוע הכללים, הקיבוץ, תור ה-SOC, אות החיים והתקינות אינם יודעים דבר על Apache. מה ששירות משמעו (היכן נמצאים הלוגים שלו, איך הם מחולקים לרשומות ומנותחים, איך רשומות הופכות לאירוע אחד, מה נחשב כבר טופל, הכללים שלו והדרישות שלו) חי במודול. החזקת המודולים בפרויקט משלהם פירושה ש:

- מודול מנוהל בגרסאות (`version`), מצהיר על גרסת localSIEM הנמוכה ביותר שהוא צריך (`core`) ומתעדכן, נוסף או נכבה בלי גרסה חדשה של localSIEM;
- הליבה אינה מייבאת אף מודול לפי שם ואין לה מודולים משלה: הרישום ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) רק סורק את `/opt/localsiem/modules/` (`LOCALSIEM_MODULES_PATH` בעותקי פיתוח), שאליה ממשק האינטרנט מתקין את המודולים של המאגר הזה;
- מודול שנכשל בטעינה לעולם אינו עוצר את האחרים: השגיאה שלו מוצגת בממשק האינטרנט (המצב «שגיאה») ועל ידי `manage.py modules`;
- מודול לעולם אינו משנה את הליבה: `backend/core/module.py` ו-`backend/core/registry.py` הם כל החוזה.

### החוזה: module.json, קובצי locale ותת-מחלקה של Module

**`module.json`** (נבדק על ידי `fReadManifest`):

| מפתח | ברירת מחדל | משמעות | apache2 | privesc |
|---|---|---|---|---|
| `id` | חובה | שם תיקיית המודול בלי הקידומת `mod-` (שם התיקייה המותקנת), `[a-z][a-z0-9_]{1,31}`; גם ה-`vName` של המחלקה | `apache2` | `privesc` |
| `version` | `"0"` | הגרסה של המודול, שמוצגת בממשק האינטרנט ועל ידי `manage.py modules` | `1.3.2` | `1.1.2` |
| `core` | `"0"` | גרסת localSIEM הנמוכה ביותר שהוא צריך; גרסה גבוהה יותר מה-`cVersion` של localSIEM המותקן פירושה שהמודול אינו נטען | `2.2.0` | `2.2.0` |
| `entry` | חובה | `"file:Class"`: `file` בלי `.py` (`[a-z][a-z0-9_]{0,63}`), `Class` היא תת-מחלקה של `Module` | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | האם הוא פועל עד שמנהל המערכת מחליט (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | תיקיות מוחלטות ש-localSIEM, בתור root, מאפשר למשתמש `localsiem` לקרוא (הפקודה שממשק האינטרנט מציג אחרי ההתקנה, אחרי **הגדרה מחדש** ואחרי עדכון שמשנה אותן) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | פקודות שמתקינות בשרת, בתור root, את התוכנה שהמודול צריך, לכל מערכת (`debian`, `alpine`): פקודה אחת בכל שורה, בלי אופרטורים של shell, כי ממשק האינטרנט מציג אותן גם עם `sudo` בתחילתן (`fCheckInstallRequirements` של הליבה). מוצגות תחת מודולים › ניתנים להתקנה › דרישות, ולעולם אינן מורצות | Debian: Apache, ModSecurity 2, ה-CRS, `a2enmod`, התצורה המומלצת של ModSecurity אם אין תצורה, הפעלה מחדש; Alpine: Apache | Debian: auditd ו-rsyslog; Alpine: auditd |
| `setup_option` | — | אף מודול אינו משתמש בו: הליבה מתעלמת ממנו (הרישום משמיט אותו), כי מודול לעולם אינו משנה את השרת; ייתכן שעדיין יופיע בקובצי `module.json` של גרסאות ישנות יותר | לא מוגדר | לא מוגדר (`--configure-privesc` הוסרה ב-1.1.0) |
| `settings` | `[]` | תיאור של כל הגדרה: ממשק האינטרנט בונה ממנו את הטופס שלו | 6 הגדרות | 13 הגדרות |

לכל הגדרה יש `key` (`[a-z][a-z0-9_]{1,31}`), `type`, בדרך כלל `default`, והמאפיינים של הסוג שלה. `fValidateSettings` / `fCleanValue` / `fCleanRecords` בודקות את מה שמנהל המערכת שומר:

| סוג | מאפיינים | פקד בממשק האינטרנט | ערכים מקובלים |
|---|---|---|---|
| `boolean` | — | תיבת סימון | `true` / `false` |
| `integer` | `min`, `max` | שדה מספר | מספר שלם בטווח `min`..`max` |
| `string` | `max_length` (500) | שדה טקסט | טקסט בלי תווי בקרה, לאחר קיצוץ רווחים, עד `max_length` |
| `path` | — | שדה טקסט ברוחב קבוע | ריק או מוחלט (מתחיל ב-`/`), עד 1024 תווים |
| `choice` | `choices` (חובה), `required` | רשימה (עם «—» כשאינו חובה) | אחד מ-`choices`, או ריק |
| `records` | `fields` (חובה: הגדרות מהסוגים האחרים), `max_items` (50) | בלוק אחד לכל רשומה עם הוספה והסרה | רשימה של עד `max_items` רשומות; כל שדה נבדק, שדות `required` אינם יכולים להיות ריקים ושדות ריקים מושמטים |

**`locales/<language>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), נקרא על ידי `fReadTexts` ומוצג בממשק האינטרנט (`modules.js fModuleText`, שחוזר ל-en-US ואז למפתח):

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

קובץ locale חסר או פגום מאבד רק את השפה שלו.

**תת-המחלקה של `Module`** ([backend/core/module.py](../../localSIEM/backend/core/module.py)). הרישום יוצר אותה בתור `Class(pSettings, pMasker, pStorage, pManifest)`. ה-hooks שלה:

| Hook | נקרא על ידי | ברירת מחדל | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | רכיב האיסוף, פעם אחת, כשהאחסון מוכן | כלום | שומר את `apache.first_start` (תחילת ימי הלמידה) | שומר את `privesc.first_start`; טוען את `privesc.sessions`, `privesc.surface` ו-`privesc.health` |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | רכיב האיסוף, ממשק האינטרנט | מתוך `modules.<id>` מעל ברירות המחדל של `module.json` | בירושה | בירושה; `mReload` גם מרוקן את המטמון של `mSettings` |
| `mDiscoveryInterval()` | רכיב האיסוף (הקצר ביותר מבין המודולים המופעלים, לפחות 60 שניות) | `discovery_interval_seconds` או 3600 | בירושה | בירושה (ברירת מחדל 300) |
| `mDiscover()` | רכיב האיסוף (הפעלה, מרווח, טעינה מחדש, בקשת אבחון), `manage.py doctor` | `[]` | מקורות `{key, path, kind, format, vhost, audit_type, storage_dir}` מהתצורה של Apache ומהמקורות הידניים | `fDiscoverSources`: לוג הביקורת ו-syslog |
| `mCreateFramer(pSource)` | רכיב האיסוף, לכל מקור | `LineFramer` | `AuditFramer` ללוג הביקורת הטורי בפורמט native | בירושה (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | רכיב האיסוף, לכל יחידה | חובה | רשומה של `access`, `error` או `audit` | רשומה של `audit` או `syslog` |
| `mCreateCorrelator()` | רכיב האיסוף, בהפעלה | חובה | `Correlator` (חלון וקורלציה חלשה מההגדרות של הליבה) | `Correlator`: רשומות ביקורת לפי מספר סידורי (EOE או 2 שניות); שורות syslog מיד |
| `mBuildEvent(pTransaction)` | רכיב האיסוף, לכל טרנזקציה שהגיע זמנה | חובה | אירוע עם `action` ו-`detections` | אירוע עם הדגלים שהכללים מתאימים להם; בלי זיהויים משלו |
| `mRulesPath()` / `mRuleFunctions()` | רכיב האיסוף, בעת טעינת הכללים | `None` / `{}` | `rules/` של התיקייה שלו / `{"apache2.new_php": mIsNewPhp}` | `rules/` של התיקייה שלו / `{}` בירושה |
| `mDetectionFromSignal(pEvent, pSignal)` | רכיב האיסוף, לכל אות של כלל (אופציונלי: מאותר עם `hasattr`) | זיהוי גנרי | זיהוי עם פרטי הבקשה ו-`{rule: {id, count}}` | זיהוי עם משתמש, פקודה, תוכנית, סשן, תהליך אב, קובץ... |
| `mEnrich(pDetection)` | רכיב האיסוף, עם הקבוצה, לפני בניית ההתראה | `{}` | ההקשר של ה-IP בשעה האחרונה | ההקשר של הסשן: תחילה שנראתה, הדלת (sudo, su...), כתובת SSH, 20 הפקודות האחרונות |
| `mDoctor()` | רכיב האיסוף (המצב `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd ומה שהכללים שלו רשמו, syslog, snoopy, מה המודול רואה, קבצים של גרסה 1.0.0, משטח התקיפה) |
| `mHealth(pNow)` | רכיב האיסוף, כל 60 שניות, רק מודולים מופעלים | `[]` | ModSecurity שכבר אינו טעון או במצב Off, ה-IP האמיתית של הלקוח חסרה (לכל היותר כל 300 שניות) | שומר את הסשנים; תוצאות סריקה; כל 300 שניות: auditd נעצר, קבצים רגישים שניתנים לכתיבה (כל שעה), מתחיל את הסריקה של תוכניות setuid |
| `mSkipped()` | מצב רכיב האיסוף, `manage.py doctor` | `[]` | לוגים דרך צינור, לוגים שמכוסים על ידי ה-`GlobalLog`, לוגי גישה ללא נתונים (`format_without_data`) | syslog שאינו נקרא (auditd פועל, `syslog_mode` במצב never), לוג ביקורת חסר |
| `mSetLowDisk(pLowDisk)` | רכיב האיסוף, רמת הדיסק | כלום | מפסיק לשמור כותרות וגופים של הביקורת | בירושה |
| `mDisplayRecord(pRecord)` | ממשק האינטרנט, כרטיס הבקשה | `{}` | הכותרות והגוף של רשומת הביקורת השמורה (`fAuditDisplay`) | בירושה |
| `mRequirements()` | הליבה, localSIEM 2.2.0 ומעלה: התקנה ראשונה, הפעלה וטעינה מחדש של רכיב האיסוף, **הגדרה מחדש** בממשק האינטרנט, `manage.py modules` ו-`doctor` | `[]` (אין דרישות) | `apache_config` ו-`modsecurity` (`fRequirementChecks`) | `command_source`: כל מקור ש-`localsiem` יכול לקרוא, לוג הביקורת (auditd פועל, לא בקונטיינר) או syslog (עם snoopy, אם מותקן); `audit_log` / `syslog` כשמקור קיים אבל לא ניתן לקרוא אותו |

בליבה כבר אין `mSetupSnippet` או `mApplySetup`: למודולים אין אפשרויות הגדרה והם לעולם אינם משנים את השרת.

רשומות הן מילונים (dicts) עם `time`, `received`, `module` (המזהה: רכיב האיסוף בוחר לפיו את מנגנון הקורלציה), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` ו-`raw` (ממוסך), ובאופן אופציונלי גם `search` (הטקסט שמאונדקס לחיפוש טקסט מלא). לאירועים יש את העמודות של טבלת האירועים (`lEventColumns` ב-`storage_sqlite.py`) ובנוסף `record_ids`, `rule_hits` ו-`detections`. לזיהוי יש `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` ו-`uid`.

### דרישות: מודול לעולם אינו מתקין את מה שהוא מנטר

התקנת מודול לעולם אינה מתקינה את התוכנה שהוא מנטר: המודול apache2 אינו מתקין את Apache או את ModSecurity, והמודול privesc אינו מתקין את auditd, דמון syslog או snoopy (הדרישה שלו, `command_source`, היא כל מקור שהמשתמש `localsiem` יכול לקרוא: לוג הביקורת כש-auditd פועל מחוץ לקונטיינר, או syslog; `fRequirementChecks` של `mod-privesc/doctor.py`). המודול עצמו מגדיר מה הוא צריך לפני שניתן להפעיל אותו, ב-`mRequirements()` (localSIEM 2.2.0 ומעלה): רשימה של בדיקות בפורמט של האבחון, שמתקיימת כשלאף אחת מהן אין הסטטוס `error`. המודול apache2 מחזיר את `apache_config` (נמצאה תצורת Apache: `apache2.conf`, `httpd.conf` או הקובץ של ההגדרה `config_file`) ואת `modsecurity` (`mod_security2` טעון; ModSecurity 3 אינו נחשב), ש-`fRequirementChecks` לוקחת מהבדיקות הראשונות של האבחון; בלי Apache, שתיהן שגיאות. מה שמתקין את התוכנה הזו מוצהר ב-`install_requirements` של `module.json`: ממשק האינטרנט מציג זאת לפני התקנת המודול (מודולים › ניתנים להתקנה › דרישות), עבור המערכת של השרת, ולעולם אינו מריץ זאת. הליבה:

- מתקינה את המודול במצב כבוי (`modules.<id>.enabled = false`) כשחסרה דרישה בהתקנה הראשונה שלו ומנהל המערכת מעולם לא החליט; עדכון לעולם אינו משנה את `enabled`;
- אינה מאפשרת להפעיל אותו כל עוד חסרה דרישה: המתג נעול וממשק האינטרנט מציג את הדרישות עם ה-`fix` שלהן;
- לעולם אינה מכבה מעצמה מודול פעיל שמאבד דרישה: האבחון שלו ואזהרות התקינות שלו (`mHealth`: «ModSecurity is no longer loaded») מדווחים על כך, וכיבויו היה משתיק אותם;
- בודקת שוב את הדרישות כשרכיב האיסוף מופעל או נטען מחדש, ועם **הגדרה מחדש** בדף המודול (גם כשהוא כבוי): אם הן מתקיימות, היא משחררת את המתג, מנהל המערכת מפעיל את המודול, וממשק האינטרנט מציג את הפקודה שיש להריץ בתור root שמאפשרת ל-`localsiem` לקרוא את הלוגים שנוצרו אחרי ההתקנה (`read_paths`).

### נטען כ-namespace package

אין `__init__.py` בשום מקום (namespace packages מרומזים של Python 3.13). `fRegisterPackage` יוצרת את החבילה `localsiem_modules` עם תיקיית המודולים בתור ה-`__path__` שלה, ו-`fLoadClass` מייבאת את `localsiem_modules.<id>.<file>`, ובודקת שהמחלקה היא `Module` ושה-`vName` שלה שווה ל-`id`. ההשלכות על הקוד של מודול:

- הקבצים שלו עצמו מיובאים **באופן יחסי** (`from .parsers import AccessParser`);
- הליבה מיובאת בתור **`backend.core...`** (`from backend.core.module import Module`): התהליכים של localSIEM מוסיפים את התיקייה של localSIEM ל-`sys.path`;
- זמינות רק הספרייה הסטנדרטית והתלויות של localSIEM (הסביבה הווירטואלית שלו `/opt/localsiem/venv/`, לדוגמה PyYAML): localSIEM אינו מתקין דבר עבור מודול.

### טופס ההגדרות נבנה מתוך המניפסט

למודול אין HTML משלו. ממשק האינטרנט קורא את `settings` של `module.json` ואת הטקסטים של `locales/`, בונה את הטופס (`modules.js fBuildSettings`, `fRecordsEditor`), מאמת את מה שנשמר עם `fValidateSettings` ושומר ב-`settings.json` תחת `modules.<id>` רק את הערכים שמנהל המערכת שמר; גם `enabled` נמצא שם. המודול קורא את `mModuleSettings()`: ברירות המחדל של `module.json` כשהערכים השמורים מעליהן. לכן הוספת הגדרה אינה דורשת שום שינוי בממשק האינטרנט או בליבה.

הגדרות של הליבה שהמודול apache2 קורא גם הוא מ-`self.dSettings`: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) ו-`health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()` מעביר גם מפתחות שנשמרו תחת `modules.apache2` ש-`module.json` אינו מצהיר עליהם: כך `mDiscover` קורא את `document_roots` (`{vhost: folder}`, מעל ה-DocumentRoots שהתגלו); ניתן להגדיר אותו רק בעריכה של `settings.json`.

### העיקרון של «הפעולה שננקטה»

רק מה שאיש עדיין לא טיפל בו נשלח ל-SOC. במודול apache2 הפעולה שננקטה נקראת מהמקור האמין ביותר: לוג הביקורת (`Action: Intercepted (phase N)` בפורמט native, `audit_data.action.intercepted/phase` ב-JSON), ואז error.log (`Access denied with code NNN (phase N)`). קוד 403 בלי שום עקבה של ModSecurity אינו חסימה (`fields.doubtful_block`).

| מצב | `action` | זיהוי (ל-SOC) |
|---|---|---|
| יורט בשלבים 1-2 (האפליקציה לא קיבלה אותו מעולם) | `blocked` | אין: `mAssess` מחזירה `None`; נספר בהקשר של התראות מאוחרות יותר |
| יורט בשלבים 3-4 | `none` | כן, `blocked_late` (גבוהה), או `success_indicator` עם שגיאת מסד נתונים |
| התאמות כשהמנוע במצב `DetectionOnly` | `none` | כן |
| התאמות מתחת לסף החריגה | `none` | כן, `below_threshold` (נמוכה) |
| אותות של כללי ה-YAML | `none` | כן |

החומרות מגיעות מ-`severity.yaml` (`fLoadSeverityTable`; קובץ חסר או ערך לא חוקי שומרים את ברירת המחדל המובנית): `crs_not_blocked_2xx` גבוהה, `crs_not_blocked_other` בינונית, `blocked_late` גבוהה, `success_indicator` קריטית (כלל יוצא 950-955 שלא נחסם, או שגיאת מסד נתונים באותה בקשה), `below_threshold` נמוכה (להגדרת הליבה `below_threshold_severity` יש קדימות). «מעל הסף» פירושו שכלל 949xxx התאים או שהציון שציין ModSecurity הגיע לסף; ציון שמחושב מהחומרות של הכללים הוא רק הערכה ואינו מכריע. הסף הוא זה שבהודעות, אחרת `anomaly_threshold`, אחרת זה של `crs-setup.conf`, אחרת 5.

### איך המודול apache2 עובד

1. **גילוי** (`discovery.py`): `ApacheConfig` קורא את התצורה ישירות (`Include`, `IncludeOptional`, `Define`, `${VARS}` של `envvars` של Debian, `<VirtualHost>`, `<IfModule>` מול המודולים הטעונים), בתור המשתמש `localsiem` ובלי `apache2ctl`. `fDiscoverSources` הופכת את `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` ו-`SecAuditLog` למקורות עם המפתח הקבוע `apache:<kind>:<real path>`. `GlobalLog` שהפורמט שלו כולל `%v` מכסה את כל ה-vhosts (לוגי הגישה האחרים מדולגים); לוגים דרך צינור ו-syslog מדולגים, וכך גם לוגי הגישה שהפורמט שלהם אינו כולל אף הנחיית `%` (Apache כותב כמות שהוא כינוי שאף `LogFormat` אינו מגדיר: `format_without_data`, אלא אם `CustomLog` אחר עם נתונים כותב לאותו קובץ; האבחון מציין זאת, בלי תיקון, כי הפורמט של הלוגים לעולם אינו משתנה); מקורות ידניים באים ראשונים וקובץ נקרא פעם אחת.
2. **חלוקה וניתוח** (`parsers.py`, `logformat.py`, `modsec.py`): שורות גישה מנותחות עם ביטוי רגולרי שנוצר מה-`LogFormat` שלהן (הפורמט האחרון שעבד נבדק ראשון); שורות שגיאה מסווגות (`modsecurity`, `database`, `php`, `crash`, `apache`); רשומות ביקורת נקראות כ-JSON (שורה אחת, שנחתכת לפני `matched_rules`), כטוריות בפורמט native (`AuditFramer` מחבר את `--id-A--` עד `--id-Z--`) או כמקביליות (שורת האינדקס מצביעה על קובץ תחת `SecAuditLogStorageDir`). הכול ממוסך; מה שאינו מתאים נשמר כ-`unparsed`.
3. **קורלציה** (`correlate.py`): רשומות עם אותו `UNIQUE_ID` יוצרות טרנזקציה אחת, שממתינה לחלון הקורלציה ולסימן המים (watermark) של המקורות שמדביקים את הפער; שורת גישה בלי `UNIQUE_ID` (הפורמטים ש-Apache כותב כברירת מחדל) מוצמדת על ידי `mPair`, כשמגיע הזמן שלה או של הרשומות של הבקשה שלה, לרשומות של ModSecurity שאין להן שורת גישה: אותה IP של לקוח, זמן בטווח של ±2 שניות (בשורה יש שניות שלמות) ואותם שיטה, URI, סטטוס ונתיב כששני הצדדים יודעים אותם; המועמד שמסכים ביותר מהם מנצח, אחריו הקרוב ביותר, ואחריו הוותיק ביותר, והאירוע מסומן כחלש. שורות של error.log בלי `UNIQUE_ID` מצטרפות מיד לטרנזקציה הקרובה ביותר של ה-IP שלהן. טרנזקציה עם `UNIQUE_ID` ועם שורת ModSecurity של error.log, בזמן שרשומות ביקורת מגיעות (`vAuditSeen`), ממתינה גם לרשומת הביקורת שלה עצמה (`mWaitsForAudit`), לכל היותר `cAuditWaitSeconds` (120 שניות) מהרשומה הראשונה שלה: ModSecurity כותב את השורות של הכללים שלו בזמן שהבקשה רצה ואת רשומת הביקורת כשהיא מסתיימת, כך שאחרת בקשה איטית הייתה הופכת לשני אירועים; ברגע שרשומת הביקורת מגיעה, לשורת הגישה יש עוד `cAfterAuditSeconds` (2 שניות).
4. **אירוע** (`ApacheModule.mBuildEvent`): שדות שנבחרים מהגישה, אחר כך מהביקורת, אחר כך מהשגיאה; ה-vhost מ-`%v` או, בלעדיו, מכותרת ה-Host ומהפורט המקומי של רשומת הביקורת (`mVhostName`); עם שורת גישה של שניות שלמות, הזמן של רשומת הביקורת; `fSummarize` נותנת כללים, קטגוריות, ציון, סף ויירוט; הפעולה שננקטה ו-`mAssess` מחליטות על הזיהוי.
5. **כללים, העשרה, אבחון ותקינות**: כללי ה-YAML של `rules/` רצים על כל אירוע (מנוע הליבה); `mEnrich` מוסיפה את ההקשר של ה-IP; `fRunDoctor` בודקת את הדרישות ומתארת את הלוגים, בלי לשנות דבר; `mHealth` מנטרת את ModSecurity ואת ה-IP האמיתית של הלקוח. למודול אין אפשרות הגדרה: בתור root, localSIEM רק נותן ל-`localsiem` הרשאת קריאה ל-`/var/log/apache2`.

### החלטות תכנון שכדאי להכיר

- **אין תוכנית התקנה משלו**: המודולים מותקנים (מודולים › ניתנים להתקנה), מתעדכנים (**עדכון**, תחת מודולים › מותקנים) ומוסרים (**הסרת התקנה**) רק מממשק האינטרנט של localSIEM, שמוריד את המאגר הזה ומתקין אותם עם `backend/core/catalog.py` (פריסה בטוחה, התקנה אחת בכל פעם, החלפה אטומית של התיקייה). מה שדורש root (הרשאת קריאה ל-`read_paths`) נעשה על ידי localSIEM: אחרי ההתקנה (ואחרי עדכון שמשנה את `read_paths`), ממשק האינטרנט מציג את הפקודה שיש להריץ בתור root.
- **הלוגים של הלקוח רק נקראים**: מודול לעולם אינו כותב בלוגים של השירותים שהוא מנטר, אינו מבצע להם רוטציה, אינו קוטם, מעביר או מוחק אותם, ולעולם אינו משנה את הפורמט שלהם; גם המודול apache2 לעולם אינו משנה את התצורה של Apache או של ModSecurity (אין לו `setup_option`). אם שרת כותב את הלוגים שלו בפורמט משלו (`LogFormat` משלו, ה-IP של הלקוח מ-`mod_remoteip`), המודול מסתגל: `AccessFormat` בונה את המנתח של כל לוג גישה מתוך ה-`LogFormat` שלו, ו-`fCanPair` / `Correlator.mPair` מצרפות את השורות בלי `UNIQUE_ID`. האבחון רק מתאר את הלוגים ואת מה ש-localSIEM יכול או אינו יכול לקרוא מהם: לבדיקות `log_format`, `log_format_without_data`, `remoteip`, `audit_log` ו-`sanitise` אין `fix`; רק מה שאינו לוג (ModSecurity, ה-CRS, `SecRuleEngine`, `mod_unique_id`, הרשאות הקריאה של `localsiem`) מגיע עם תיקון. `--configure-apache` הוסרה בגרסה 1.3.0; `localsiem_combined` נשאר ב-`dKnownFormats` עבור השרתים שכבר כותבים אותו, ותוכנית ההתקנה של localSIEM מוחקת את `localsiem.conf` שגרסאות ישנות יותר כתבו (`--uninstall`, `--reinstall`).
- **חלק K** (`matched_rules`) ו-**חלק E** (גוף התגובה) של לוג הביקורת לעולם אינם נשמרים. הכותרות והגוף נשארים רק ברשומה הגולמית הממוסכת; כרטיס הבקשה בונה אותם מחדש (`fAuditDisplay`). אינדקס הטקסט המלא מקבל טקסט מצומצם (`search`: שורת הבקשה, host, user agent והמזהה, ההודעה והנתונים של כל כלל).
- **הטקסט הגולמי נבנה מחדש מהחלקים הממוסכים**: רשומת הביקורת המקורית עלולה להכיל סיסמאות וקובצי cookie.
- **ממשק האינטרנט והכלים יוצרים את המודול בלי אחסון** (`pStorage` הוא `None` ב-`WebContext.mModule` וב-`manage.py`): הבנאי וה-hooks שהם קוראים להם אסור שישתמשו באחסון.
- **מצב במסד הנתונים של האירועים**: `apache.first_start` (ימי הלמידה), `apache.health` (מה שכבר דווח, כדי שהפעלה מחדש לא תחזור עליו) ו-`apache2.doctor` (נכתב על ידי רכיב האיסוף). השניים הראשונים, כמו מפתחות המקור `apache:<kind>:<real path>`, שומרים על השם שהיה למודול לפני שנקרא apache2: שרת שהיה בו המודול `apache` שומר את ימי הלמידה שלו, את זיכרון התקינות שלו ואת מיקומי הקריאה שלו (עם מפתח מקור חדש, כל לוג מתחת ל-5 MiB היה נקרא שוב מההתחלה). הזמנים של זיכרון התקינות נמצאים בפורמט המקורי של הפרויקט (`2026-10-29@13-59-59.723`, UTC); מצב שנשמר על ידי גרסה ישנה יותר, עם שניות epoch, מומר בעת הטעינה.
- **בטיחות הנתיבים**: `mIsNewPhp` דוחה `..` ונשארת בתוך ה-DocumentRoot; `fReadConcurrentEntry` נשארת בתוך `SecAuditLogStorageDir` וקוראת לכל היותר 8 MiB; מנגנון הקורלציה מחזיק לכל היותר 50 000 טרנזקציות ממתינות.

### איך המודול privesc עובד

השאלה אינה «האם מישהו הריץ `whoami`?» (מנהלי מערכת עושים זאת כל יום) אלא «האם הסשן הזה צועד בדרך של הסלמה, והאם הוא הגיע לשם?». המודול הופך שני מקורות לאירועים בעלי משמעות אחת (`vhost` האדם, `method` הסוג, `uri` הפקודה, `path` התוכנית או הקובץ, `ip` כתובת ה-SSH, `score` הסיור השונה של הסשן), מחשב עליהם דגלים, ומניח לכללי YAML להחליט מה נשלח ל-SOC.

1. **גילוי** (`discovery.py`): `fDiscoverSources` מחזירה את לוג הביקורת (`fAuditLogPath`: ההגדרה, `log_file` של `auditd.conf`, `/var/log/audit/audit.log`; גם כש-auditd פועל ו-`localsiem` עדיין אינו יכול לקרוא אותו, כדי שהליבה תדווח על כך) ואת syslog (`fSyslogPath`) כש-`syslog_mode` קובע זאת (`auto`: auditd אינו פועל, לא ניתן לקרוא את הלוג שלו, או ש-snoopy מותקן). היא גם אוספת את מה שהאבחון צריך: קונטיינר (`fContainer`, קריא בלי root: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), הקובץ הבינארי וה-pid של auditd, snoopy, האם ניתן לקרוא כל לוג (`fReadState`: `readable`, `unreadable` או `missing`) והקבצים שגרסה 1.0.0 השאירה (`fLegacyLeftovers`). `Accounts` קוראת שוב את `/etc/passwd`, `/etc/group` ו-`UID_MIN` כשהם משתנים, ומסווגת uid בתור `root`, `admin` (חבר ב-`admin_groups`), `user` או `service`.
2. **ניתוח** (`parsers.py`): `fParseAuditLine` קוראת את `type=... msg=audit(<time>:<serial>): k=v ...`, את החלק של מרחב המשתמש `msg='...'`, את החלק המועשר שאחרי `\x1d`, מחברת את הארגומנטים של `EXECVE` (גם אלה שמפוצלים לחלקי `aN[i]`), מפענחת את הערכים ההקסדצימליים (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) ו**בונה מחדש את הטקסט הגולמי מהערכים המפוענחים והממוסכים** (הייצוג ההקסדצימלי של סיסמה היה שומר אותה); `search` מקבל את הפקודה המפוענחת. `fParseSyslogLine` קוראת חותמות זמן ISO וקלאסיות (עם או בלי ה-`facility.priority` של busybox) ו-`fParseSyslogMessage` מבינה את snoopy (פורמטי ברירת המחדל שלו בגרסאות 2.4 ו-2.5, כולל `uid:alice(1000)/root(0)`, ואת זה שגרסה 1.0.0 הגדירה), sudo, su (util-linux ו-busybox), pkexec, doas, `pam_unix` ו-sshd. `fMaskCommand` ממסכת סיסמאות בשורות פקודה לפני רכיב המיסוך של הליבה.
3. **קורלציה** (`correlate.py`): רשומות ביקורת עם אותו מספר סידורי יוצרות טרנזקציה אחת, שזמנה מגיע ב-`EOE`, מיד עבור סוגים של מרחב המשתמש בעלי רשומה אחת (`USER_*`, `CRED_*`, `DAEMON_*`...), או אחרי 2 שניות בלי רשומות; לכל היותר 50 000 ממתינות. זמנן של שורות syslog מגיע מיד.
4. **אירוע** (`PrivescModule.mBuildEvent`): `mAuditEvent` מפצלת לפי סוג: `EXECVE` → `mAuditExec` (ביט ה-setuid של התוכנית מרשומת ה-`PATH` או מ-`stat`, `suid_escape` כשה-euid הוא 0, ה-uid האמיתי אינו 0 והתוכנית אינה setuid, capabilities שהושגו מ-`BPRM_FCAPS`, `root_without_door`, `parent_interpreter` כש-shell רץ בתור root לאחר שהופעל על ידי מפרש של משתמש שאינו root, תהליך האב מזיכרון התהליכים); `USER_*`/`LOGIN` → `mAuditUser` (סשן שהתחיל, כתובת SSH, דלתות: `USER_START`/`USER_CMD` של sudo, su, pkexec, doas, run0, systemd; כשלים); `CONFIG_CHANGE` (`audit_disabled`, `audit_rule_removed` לכל כלל שהוסר), `DAEMON_*` (`auditd_stopped_manually` כשהשולח אינו pid 1), `ANOM_ABEND` (`crash_suspicious`); כל `SYSCALL` אחר → `mAuditSyscall`, שמסווגת אותו לפי קריאת המערכת שלו (`fSyscallName`: השם של הפורמט המועשר, או המספר בטבלה של הארכיטקטורה שלו), הארגומנטים שלו ורשומות ה-`PATH` שלו, לעולם לא לפי המפתח של הכלל: `denied` (פתיחה, הרצה או קיטום שנכשלו עם `EACCES`/`EPERM` עבור אדם), `kmod`, `ptrace` (`ptrace_attach` עבור `PTRACE_ATTACH`/`PTRACE_SEIZE`), `chmod` (הרשאות עם ביט setuid או setgid, לא על תיקייה, עם `writer_allowed`) ו-`file` (שינוי של נתיב מ-`lSensitivePaths`, עם `sensitive_group` ו-`writer_allowed`; המפתח, דרך `dKeyHints`, רק כשלא ניתן לפענח אף נתיב). `mSyslogEvent` מטפלת ב-snoopy בתור `exec` (`suid_escape` מ-`stat`; בלי `filename`, התוכנית מהמילה הראשונה של הפקודה) וב-sudo, su, pkexec, doas, login ו-pam. כל פקודה עוברת דרך `mAnalyzeCommand`: אסימון סיור (`fReconToken`) והאסימונים השונים של הסשן בחלון (`recon_burst`, `recon_massive`, `score`), הורדות שמורצות על ידי shell (`cDownloadOnelinerRegex`, או כלי הורדה ואחריו shell עם אותו תהליך אב), `compile_in_tmp`, הפקודות האחרונות של הסשן ועבור חשבונות שירות, התוכנית (`fProgramKey`) מול ההיסטוריה שלה (`mPathFirstSeen` של הליבה, אחרי `learning_days`: `new_program`). `ignored` מסמן את המשתמשים שמתעלמים מהם.
5. **כללים, העשרה, אבחון ותקינות**: 35 כללי ה-YAML של `rules/` מחליטים על כל זיהוי (`mDetectionFromSignal`); `mEnrich` מוסיפה את ההקשר של הסשן; `fRunDoctor` מתארת את auditd ואת מה שהכללים שלו רשמו, את syslog, את snoopy, את מה שהמודול רואה ומה שאינו רואה, את הקבצים של גרסה 1.0.0 ואת משטח התקיפה; `mHealth` מדווחת על auditd שנעצר, על הקבצים הרגישים שניתנים לכתיבה ועל התוצאה של הסריקה של תוכניות setuid (`SurfaceScanner`, ב-thread נפרד). למודול אין אפשרות הגדרה והוא אינו משנה דבר בשרת.

### החלטות תכנון של המודול privesc

- **שני מקורות, משמעות אחת.** משתמש אינו יכול להתחמק מ-auditd, אבל auditd אינו פועל בתוך קונטיינרים (הביקורת של הקרנל אינה מופרדת ל-namespaces); snoopy רואה כל תוכנית בקונטיינרים אבל צריך syslog; syslog לבדו נותן רק את sudo, su, pkexec ו-doas. אף מקור אינו רואה את הפקודות המובנות של ה-shell. הכללים מתאימים לעמודות ולדגלים, לעולם לא למקור, כך שניתן להוסיף מקור בלי לגעת בהם. אותה פקודה שנראתה פעמיים יוצרת התראה אחת: הליבה מקבצת זיהויים לפי מודול, משתמש, IP, קטגוריה וחומרה.
- **פרצים, לא פקודות.** סיור הוא אסימון לכל סוג של שאלה (`whoami`, `read:/etc/passwd`, `find:-perm:`...), ורק מספר האסימונים השונים של סשן בחלון מפיק התראה, עם סף גבוה יותר למנהלי מערכת וסף שלישי לסקריפטים. הספים הם הגדרות, לא ספים של כללים: הכלל רק מתאים ל-`recon_burst` / `recon_massive`.
- **הצלחה היא מה שחשוב ביותר.** `suid_escape` (תוכנית שאינה setuid שרצה עם euid 0 ו-uid אמיתי שאינו 0) ו-`root_without_door` (root בסשן שתחילתו נראתה ושמעולם לא עבר דרך sudo, su, pkexec או doas) הם שני הסימנים הקריטיים לכך שהסלמה הצליחה, כמעט בלי תוצאות חיוביות שגויות. סשן שתחילתו לא נראתה (סשנים שנפתחו לפני המודול, סשנים שנשכחו אחרי יום של חוסר פעילות) לעולם אינו מסומן.
- **סשנים שורדים הפעלה מחדש.** `SessionTracker` שומר את ההתחלה, את כתובת ה-SSH ואת הדלת של כל סשן במצב `privesc.sessions` (נשמר לכל היותר פעם בדקה); אסימוני הסיור והפקודות האחרונות נשארים בזיכרון. סשנים שאינם פעילים במשך יום מושמטים.
- **רק מה שכבר קיים בשרת.** המודול לעולם אינו מתקין דבר או משנה דבר מחוץ ל-`/opt/localsiem`: הוא אינו טוען כללי ביקורת, אינו נוגע ב-`auditd.conf` או ב-`snoopy.ini` ואינו מתקין hook. גרסה 1.0.0 כן עשתה זאת (`--configure-privesc`: כללי ביקורת עם המפתחות `lsiem_*`, `log_group = adm`, hook של bash, הפורמט של snoopy); גרסה 1.1.0 הסירה זאת. לכן רשומות הביקורת מסווגות לפי הסוג שלהן, קריאת המערכת שלהן והנתיבים שלהן, כך שכל כללי ביקורת עובדים (אלה של השרת, כללי הדוגמה של STIG, או כללי ה-`lsiem_*` שגרסה 1.0.0 השאירה); המפתח נשמר ב-`fields.key` לחיפושים והוא רק רמז (`dKeyHints`). המספרים של קריאות המערכת נקראים לפי ארכיטקטורה (`dSyscallTables`: x86_64, i386 והטבלה הגנרית של aarch64, riscv64 ו-loongarch64) כשבלוג אין שמות מועשרים. האבחון מתאר מה הכללים של השרת רושמים ומה לא; ה-`fix` שלו הוא רק חבילה להתקנה או הרשאת הקריאה של `localsiem`.
- **קריא פירושו קריא.** הדרישה מתקיימת על ידי מקור שקיים וש-`localsiem` יכול לפתוח (`fReadState`), לא על ידי תוכנית שמותקנת: בהתקנה ראשונה הלוגים בדרך כלל שייכים ל-root, ולכן המודול נשאר כבוי עד הרצת הפקודה עבור root (`manage.py setup-modules`) ו-**הגדרה מחדש**.
- **מנהלי חבילות אינם תוקפים.** שינויים בקבצים רגישים ובביטי setuid שנעשים על ידי כלי החשבונות והחבילות (`sAllowedWriters`), או על ידי תוכניות שהאבות הידועים שלהן הם מנהלי חבילות, מגדירים את `writer_allowed`, והכללים מדלגים עליהם.
- **הסריקה לעולם אינה חוסמת את רכיב האיסוף.** `SurfaceScanner` עובר על `scan_paths` ב-thread משלו, בלי לצאת ממערכת הקבצים של כל אחת, מדלג על `/proc`, `/sys` ועל התיקיות של קונטיינרים, עד 3 מיליון קבצים או 15 דקות; `mHealth` לוקחת את התוצאה כשהיא מוכנה. הסריקה הראשונה היא נקודת הייחוס; הסריקות הבאות מדווחות על מה שחדש.
- **ממשק האינטרנט והכלים יוצרים את המודול בלי אחסון**: `mDiscover`, `mDoctor` ו-`mRequirements` לעולם אינן משתמשות בו, ו-`mAnalyzeCommand` קוראת ל-`mPathFirstSeen` רק כשהיא קיימת.
- **מצב במסד הנתונים של האירועים**: `privesc.first_start` (ימי הלמידה), `privesc.sessions`, `privesc.surface` (נקודת הייחוס של הסריקה והאבחון), `privesc.health` (מה שכבר דווח, האם auditd פעל) ו-`privesc.doctor` (נכתב על ידי רכיב האיסוף). התוכניות שנראו של חשבונות השירות הן שורות של `seen_paths` עם ה-vhost `privesc:<account>`. הזמנים של `privesc.health` (זיכרון התקינות) ושל `privesc.sessions` (`last` של כל סשן) נמצאים בפורמט המקורי של הפרויקט (`2026-10-29@13-59-59.723`, UTC); מצב שנשמר על ידי גרסה ישנה יותר, עם שניות epoch, מומר בעת הטעינה.

<a id="modules"></a>
## 2. מפת המודולים

| מודול | נתיב | תחום אחריות | תלוי ב | בשימוש על ידי |
|---|---|---|---|---|
| מניפסט | [mod-apache2/module.json](../mod-apache2/module.json) | מזהה, גרסה, ליבה מינימלית, נקודת כניסה, נתיבי קריאה, הגדרות (ללא אפשרות הגדרה) | — | הרישום, ממשק האינטרנט, `manage.py` |
| המודול של Apache | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: hooks, הפעולה שננקטה, חומרה, זיהויים, פונקציית כלל, העשרה, תקינות | correlate, discovery, doctor, modsec, parsers; הליבה `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | רכיב האיסוף, ממשק האינטרנט, `manage.py` |
| גילוי | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (מנתח התצורה), מקורות ולוגים שדולגו, DocumentRoots | logformat (`dKnownFormats`) | module, doctor |
| אבחון | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | בדיקות דרישות; מתאר את הלוגים (פורמט, לוג ביקורת, מיסוך) בלי להציע לשנות אותם | discovery | module |
| פורמטי גישה | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` לביטוי רגולרי, זמנים ל-UTC, שורת בקשה | הליבה `timeutil` | parsers, discovery |
| מנתחים | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, native, מקבילי), `AuditFramer`, `fAuditDisplay` | logformat, modsec; הליבה `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | הודעות, קטגוריות, טווחי CRS, ציונים, יירוט | — | parsers, module |
| קורלציה | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, הצמדה בלעדיו (`mPair`), חלון, סימן מים | הליבה `timeutil` | module (רכיב האיסוף) |
| טבלת חומרות | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | החומרות של הזיהויים של ModSecurity | — | module (`fLoadSeverityTable`) |
| כללים | [mod-apache2/rules/](../mod-apache2/rules/) | שישה כללי YAML | מנוע הכללים של הליבה, `mIsNewPhp` | רכיב האיסוף (`RulesEngine`), ממשק האינטרנט (`fRules`) |
| טקסטים | [mod-apache2/locales/](../mod-apache2/locales/) | שם, תקציר, תוויות ועזרה של ההגדרות, אפשרויות בחירה | — | ממשק האינטרנט |
| privesc: מניפסט | [mod-privesc/module.json](../mod-privesc/module.json) | מזהה, גרסה, ליבה מינימלית, נקודת כניסה, נתיבי קריאה, 13 הגדרות (ללא אפשרות הגדרה) | — | הרישום, ממשק האינטרנט, `manage.py` |
| privesc: מודול | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: hooks, אירועים משני המקורות, סיווג רשומות הביקורת (נתיבים רגישים, קריאות מערכת לפי ארכיטקטורה), דגלים, זיהויים של הכללים, העשרה, תקינות, תוצאות סריקה | commands, correlate, discovery, doctor, parsers, surface; הליבה `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | רכיב האיסוף, ממשק האינטרנט, `manage.py` |
| privesc: גילוי | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | מקורות, קונטיינר, auditd, snoopy, syslog, האם ניתן לקרוא כל לוג, קבצים שגרסה 1.0.0 השאירה, `Accounts` (משתמשים, קבוצות, סוג חשבון) | — | module, doctor |
| privesc: מנתחים | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | רשומות ביקורת (הקסדצימלי, `msg='...'`, מועשר), שורות syslog (snoopy בפורמטים הרגילים שלו, sudo, su, pkexec, doas, pam, sshd), מיסוך של שורות פקודה | הליבה `masking`, `timeutil` | module |
| privesc: קורלציה | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | רשומות ביקורת לפי מספר סידורי (EOE, רשומות של מרחב המשתמש, 2 שניות); שורות syslog מיד | — | module (רכיב האיסוף) |
| privesc: פקודות | [mod-privesc/commands.py](../mod-privesc/commands.py) | אסימוני סיור, תוכנית של חשבון שירות, shells, מפרשים, כלי הורדה, דלתות, מהדרים; `SessionTracker` | הליבה `timeutil` | module |
| privesc: משטח התקיפה | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, capabilities), GTFOBins, קבצים רגישים שניתנים לכתיבה, קבוצות בעלות הרשאות | — | module, doctor |
| privesc: אבחון | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | מתאר את auditd, את הלוג שלו ואת מה שהכללים שלו רשמו, את syslog, את snoopy, את מה שהמודול רואה, את הקבצים של גרסה 1.0.0 ואת משטח התקיפה (תיקונים: רק חבילות והרשאת קריאה); הדרישה `command_source` (כל מקור קריא) | discovery, surface; הליבה `timeutil` | module |
| privesc: כללים | [mod-privesc/rules/](../mod-privesc/rules/) | 35 כללי YAML | מנוע הכללים של הליבה | רכיב האיסוף (`RulesEngine`), ממשק האינטרנט (`fRules`) |
| privesc: טבלת חומרות | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | החומרות של הזיהויים שהמודול בונה (סריקה, קבצים רגישים) | — | module (`fLoadSeverityTable`) |
| privesc: טקסטים | [mod-privesc/locales/](../mod-privesc/locales/) | שם, תקציר, תוויות ועזרה של ההגדרות, אפשרויות בחירה | — | ממשק האינטרנט |
| הליבה: ממשק התכנות | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | הרישום | המודולים |
| הליבה: רישום | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | מציאה, בדיקה וטעינה של מודולים; ברירות מחדל ואימות של הגדרות | `config` | רכיב האיסוף, ממשק האינטרנט, `manage.py`, `backend/core/catalog.py` |
| הליבה: ממשק האינטרנט | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | דפי המודולים (מותקנים, ניתנים להתקנה, הדף של מודול אחד) ו-API | הרישום, הקטלוג, הכללים | דפדפנים |
| הליבה: קטלוג | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | הורדה ופריסה בטוחה של המאגר, רשימה עם הפעולה של כל מודול (`install`, `update`, `incompatible`, `invalid`...) ו-`newer`, התקנה או עדכון אטומיים (`previous`, `access_changed`), הסרת התקנה, פקודה עבור root: מודולים › ניתנים להתקנה ו-**עדכון** / **הסרת התקנה** של מודולים › מותקנים, הדרך היחידה להתקין מודולים | הרישום | ממשק האינטרנט |

<a id="symbols"></a>
## 3. סמלים מרכזיים

| סמל | קובץ:שורה | מה הוא עושה |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | המודול apache2 (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | `severity.yaml` מעל ברירות המחדל המובנות |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | מנתחת את התצורה, מקורות, לוגים שדולגו, DocumentRoots |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | סף החריגה: הגדרה, CRS, או 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | יחידה לרשומה לפי סוג המקור |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | טרנזקציה לאירוע: שדות, הפעולה שננקטה, ציונים, זיהוי |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | כותרת Host או ה-hostname של ModSecurity ל-vhost ש-Apache בחר (מה ש-`%v` רושם) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | חומרה, שם הכלל, תיאור ופרטים של מה שנשלח ל-SOC |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | אות של כלל YAML לזיהוי |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | פונקציית הכלל `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | ההקשר של ה-IP (השעה האחרונה) עבור ההתראה |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity שכבר אינו טעון או במצב Off; ה-IP האמיתית של הלקוח חסרה |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | כותרות וגוף עבור כרטיס הבקשה |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache ו-ModSecurity 2: מה המודול צריך לפני שניתן להפעיל אותו |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | המנתח של התצורה של Apache |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | ההנחיות שנקראות (לוגים, vhosts, מודולים, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | ה-vhost של בקשה מכותרת ה-Host שלה ומהכתובת והפורט המקומיים, כפי ש-Apache בוחר אותו |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | מפתח מקור קבוע; מקורות לקריאה ומקורות שדולגו |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | בדיקות דרישות `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | האם ניתן לצרף פורמט גישה בלי `UNIQUE_ID` (IP של הלקוח, זמן, שורת בקשה, סטטוס) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | הבדיקות `apache_config` ו-`modsecurity` של האבחון או, בלי Apache, שתיהן כשגיאות, עם הפקודה שמתקינה אותם |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` לביטוי רגולרי; כינויים מוכרים |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | שורה של access.log לרשומה |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | שורה של error.log: ModSecurity, מסד נתונים, PHP, קריסה |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | רשומות native שמשתרעות על כמה שורות; מיקום שמירה בטוח |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | רשומת ביקורת ב-JSON או ב-native; מיסוך, טקסט גולמי וטקסט מאונדקס |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | הכרטיס של רשומה שמורה; הקובץ של רשומה מקבילית |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | הודעת ModSecurity אחת; כללים, קטגוריות, ציון, סף, יירוט |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | המודול privesc (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | טרנזקציה לאירוע, לפי מקור; `ignored`; שדות ריקים מושמטים (`fCleanFields` שומרת 0) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | הסיור של הסשן, הורדה שהורצה על ידי shell, הידור ב-`/tmp`, פקודות אחרונות, תוכנית חדשה של חשבון שירות |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | טרנזקציית ביקורת לפי סוג; תוכניות שהורצו (`suid_escape`, `root_without_door`, `parent_interpreter`, capabilities); התחברויות, דלתות וכשלים |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | כל קריאת מערכת אחרת לפי השם, הארגומנטים והנתיבים שלה: `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) או `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | השם של קריאת מערכת (שם מועשר, או מספר לפי ארכיטקטורה); הקבוצה של נתיב רגיש (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, התחברויות |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | מי שכתב לקובץ רגיש, או אב קדמון ידוע שלו, הוא כלי חשבונות או חבילות |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | אות של כלל לזיהוי; ההקשר של הסשן עבור ההתראה |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | סשנים שנשמרו, auditd שנעצר, קבצים רגישים, סריקה שהתחילה; תוכניות setuid ו-capabilities חדשות |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | מקורות, מקורות שדולגו ומידע עבור האבחון; האם ניתן לקרוא לוג; קבצים שגרסה 1.0.0 השאירה |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | סוג הקונטיינר (בלי root); ה-pid של auditd שפועל |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | שמות של uids, קבוצות, `UID_MIN`, סוג החשבון (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | הרשומות של שני המקורות |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | סיסמאות של שורות פקודה, ואז רכיב המיסוך של הליבה |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | רשומות ביקורת לפי מספר סידורי; האחרות מיד |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | אסימון הסיור של פקודה; התוכנית של חשבון שירות; המילים של פקודה שהוקלדה |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | סשנים (התחלה, IP, דלת, סיור, פקודות אחרונות), תהליכים, הורדות; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | סריקה של setuid, setgid ו-capabilities ב-thread; קבצים רגישים שאחרים יכולים לכתוב אליהם |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | בדיקות האבחון (תיאורים; תיקונים רק לחבילות ולהרשאת קריאה); הדרישה `command_source`: כל מקור קריא |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | הממשק של מודול; שורה אחת לכל יחידה |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | בודקת את `module.json`, קוראת את הטקסטים |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | המודולים המותקנים (`/opt/localsiem/modules/*`); מופעים ושגיאות |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | ה-namespace package `localsiem_modules`; ייבוא ובדיקות של נקודת הכניסה |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | ברירות מחדל מתחת לערכים השמורים; אימות של מה שנשמר |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`; `POST /api/admin/module-catalog/{name}` (התקנה או עדכון; התקנה ראשונה בלי הדרישות שלה מכובה: `fFirstInstallation`); `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | מתקינה או מעדכנת מודול לצד העותק המותקן ומחליפה ביניהם עם שינוי שם (`previous`, `access_changed`); המודולים של המאגר עם `installed`, `newer` והפעולה שלהם |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | מסירה את התקנת מודול (שינוי שם ומחיקה); הפקודה עבור root (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | החלק ניתנים להתקנה (רק המודולים שאינם מותקנים, **התקנה** ותיבת הדו-שיח שלה); הודעה על גרסה חדשה יותר בשורה של מותקנים; **עדכון** (אישור, אותו `POST`, תיבת דו-שיח רק עם `access_changed` או כשרכיב האיסוף לא הגיב) |

<a id="flows"></a>
## 4. נתיבי הקריאה העיקריים

**הפעלת רכיב האיסוף → הרישום → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = תיקייה, entry, הגדרות, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, תת-מחלקה של `Module`, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, הדריסות `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`; `FileTailer` ו-`mCreateFramer` לכל מקור) → הרשומות הממתינות חוזרות למנגנון הקורלציה → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → המצב `apache2.doctor`).

**שורה שנקראה → זיהויים**

1. `Collector.mReadSources` → `FileTailer.mPoll` → framer `mFeed` (`LineFramer`, או `AuditFramer` שה-`mSafeCommit` שלו שומר את המיקום לפני רשומה שלא הושלמה) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, או `fReadConcurrentEntry` + `fParseAuditRecord` ו-`mObserveAudit`) → רשומות ומיקומים נשמרים בטרנזקציה אחת → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, הפעולה שננקטה, `mAssess`, `mPathFirstSeen` עבור `.php` עם 2xx) → `RulesEngine.mEvaluate` (כללי YAML; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → `mDetect` לכל זיהוי ו-`mDetectionFromSignal` לכל אות → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → תור ה-SOC.

**מנהל המערכת שומר את ההגדרות → טעינה מחדש של רכיב האיסוף**

`modules.js fBuildSettings` (שליחה) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` או `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → ה-socket של רכיב האיסוף `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). המתג שולח את `{enabled}` באותה דרך (הפעלה: 422 `requirements_missing` כל עוד חסרה דרישה של המודול) וטבלת הכללים שולחת את `{rules}` (`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` או `first_threshold`, `window`). אם ה-socket אינו עונה, רכיב האיסוף בכל זאת מבחין ב-`settings.json` החדש במחזור הבא שלו.

**התקנת מודול מממשק האינטרנט** (הדרך היחידה להתקין מודולים)

`modules.js fCatalogPanel` (מודולים › ניתנים להתקנה) → **בדיקת המאגר** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: כל תיקייה `mod-<name>/` של המאגר, עם `installed`, `newer` ו-`action`) → רק הפריטים שה-`installed` שלהם null מוצגים → **דרישות** (`fShowRequirements` → `fRequirementsBody`: ה-`install_requirements` של המודול עבור המערכת של השרת, ה-`system` של התשובה, בתור root ועם `sudo`, וההערות `install_requirements.*` מקובצי ה-locale שלו; שום דבר אינו מורץ) → **התקנה** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` null, `access_changed` true) → `WebContext.mReloadModules` → `fFirstInstallation` (דרישה חסרה ו-`modules.<name>.enabled` מעולם לא נשמר: `enabled = false`) → `restart` של רכיב האיסוף → `fCreateModules` טוענת את המודול → תיבת הדו-שיח «<module> הותקן» מציגה את הפקודה עבור root (`fRootCommand`: `manage.py setup-modules`, הרשאת קריאה ל-`read_paths`) או, אם חסרה דרישה, את הבדיקות שלא התקיימו.

**עדכון מודול מממשק האינטרנט**

מודולים › מותקנים נפתח → `fCheckRepository` → `fFetchCatalog(false)` של `modules.js` (התשובה האחרונה של `GET /api/admin/module-catalog`, בשימוש חוזר במשך 600 שניות; התקנה, עדכון או הסרת התקנה של מודול שוכחים אותה) → פריטים עם `newer` ועם `action` שערכו `update` או `incompatible` → `fUpdateNotice` בשורה (רק כל עוד הגרסה המותקנת היא זו שהושוותה) → **עדכון** → `fUpdate` → אישור → `POST /api/admin/module-catalog/{name}` (אותה `fInstallFromCatalog` → `fInstall`: העותק החדש מחליף את המותקן, `previous` היא הגרסה הישנה, `access_changed` מציין אם `read_paths` השתנו; בלי `fFirstInstallation`, כך ש-`enabled` וההגדרות נשארים) → `restart` של רכיב האיסוף → תיבת דו-שיח רק אם `access_changed` (הפקודה עבור root) או אם רכיב האיסוף לא הגיב.

**הסרת התקנה של מודול מממשק האינטרנט**

**הסרת התקנה** (שורה של מודולים › מותקנים או דף המודול) → `fUninstallButton` → אישור → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → שינוי שם של `/opt/localsiem/modules/<name>/` לתיקיית ביניים, ומחיקה שם) → `WebContext.mReloadModules` → `restart` של רכיב האיסוף. `modules.<name>` והדריסות של הכללים שלו נשארים ב-`settings.json`, והרשאת הקריאה ש-root נתן נשארת.

**התקנה ראשונה בלי Apache או ModSecurity → הגדרה מחדש** (localSIEM 2.2.0 ומעלה)

התקנה בממשק האינטרנט → `fInstall` (התקנה ראשונה) → המודול נוצר מהעותק המותקן (אחסון `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (עם Apache: `fRunDoctor` → `apache_config`, `modsecurity`; בלעדיו, שתיהן כשגיאות) → שגיאה ו-`modules.apache2.enabled` מעולם לא נשמר → `modules.apache2.enabled = false` («כבוי», מתג נעול, דרישות בדף). מאוחר יותר, כש-Apache ו-ModSecurity מותקנים: **הגדרה מחדש** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → מתקיימות → המתג משוחרר והפקודה עבור root (הרשאת קריאה ל-`read_paths`; ל-apache2 אין `setup_option`) → מנהל המערכת מפעיל את המודול → טעינה מחדש של רכיב האיסוף → `mDiscover` → `mPublishDoctor`.

**כרטיס הבקשה והאבחון מממשק האינטרנט**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **גילוי מחדש והרצת האבחון** → `POST /api/admin/modules/apache2/doctor` → רכיב האיסוף `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**תקינות**

`Collector.mCycle` (כל 60 שניות) → `mCheckHealth` → `ApacheModule.mHealth` (לכל היותר כל 300 שניות; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc: פקודה שהורצה → זיהויים**

1. auditd כותב `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE` עם מספר סידורי אחד → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (פענוח הקסדצימלי, `fMaskCommand`, בנייה מחדש של הטקסט הגולמי) → `Correlator.mAdd` (המפתח `audit:<time>:<serial>`, הזמן מגיע ב-`EOE`).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `root_without_door` מ-`SessionTracker.mGet`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`; `fCompileInTemporary`; `mCommand`; חשבון שירות: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (הכללים של `mod-privesc/rules/`) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (סשן: 20 הפקודות האחרונות) → `fBuildAlert` → תור ה-SOC.

עם snoopy, אותה פקודה מגיעה גם כשורת syslog: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (הסשן `snoopy:<uid>:<sid>`).

**privesc: סשנים ודלתות**

`LOGIN` (auid ו-ses הוקצו) או `USER_LOGIN`/`USER_START` של sshd או login → `mAuditUser` → `SessionTracker.mStart` (משתמש, כתובת SSH). `USER_START`/`USER_CMD` עם תוצאת הצלחה של sudo, su, pkexec, doas, run0 או systemd → `SessionTracker.mDoor`. `EXECVE` מאוחר יותר של אותו סשן עם uid ו-euid 0 → `root_without_door` רק אם ההתחלה נראתה ולא הייתה דלת. `mHealth` שומרת את `SessionTracker.mExport` ב-`privesc.sessions` לכל היותר פעם בדקה; `mStart` טוענת אותו (`mImport`).

**privesc: קריאת מערכת שנרשמה על ידי כללי הביקורת של השרת**

auditd כותב `SYSCALL` (עם `arch`, `syscall`, `a0`-`a3`, `success`, `exit` והמפתח של הכלל שרשם אותה, יהיה אשר יהיה), `CWD`, `PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → open/exec/truncate שנכשלו עם `EACCES`/`EPERM` ו-uid התחברות → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; `chmod`/`fchmod`/`fchmodat`/`fchmodat2` עם `S_ISUID`/`S_ISGID` בהרשאות, לא על תיקייה → `chmod` (`mWriterAllowed`); שינוי (קריאה מ-`sChangeSyscalls`, פתיחה עם דגלי כתיבה, `PATH` עם `CREATE`/`DELETE`) של נתיב מ-`lSensitivePaths` → `file` עם `sensitive_group` (`dKeyHints` רק כשאין נתיב שניתן לפענח) ו-`mWriterAllowed`; כל דבר אחר → `syscall`. `mBuildEvent` זוכרת את הזמן של כל סוג (`dRuntime["audit_kinds"]`) עבור האבחון.

**privesc: סריקה של משטח התקיפה**

`mHealth` (כל 300 שניות, חמש דקות אחרי ההפעלה, כל `surface_scan_hours`) → `SurfaceScanner.mStart` (thread: `os.walk` של `scan_paths`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → `mHealth` הבאה → `mSurfaceResult` (`SurfaceScanner.mTake`, מול `privesc.surface`: setuid/setgid חדשים → `new_setuid*`, capabilities חדשות → `new_capabilities`) → `mModuleDetection` → `mDetect`; התוצאה נשמרת ב-`privesc.surface` ומוצגת על ידי `fSurfaceChecks`. כל שעה `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc: דרישות והגדרה מחדש**

`fInstall` (התקנה ראשונה) או **הגדרה מחדש** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`; `fSyslogPath` → `fReadState` אלא אם `syslog_mode` הוא `never`; `fSnoopyInstalled`) → מקור קריא: `command_source` תקין (אלה שאינם קריאים כאזהרות); מקור שקיים אבל לא ניתן לקרוא אותו: שגיאת `audit_log` או `syslog` עם הרשאת הקריאה (`manage.py setup-modules` או `setfacl`); כלום: שגיאת `command_source` עם החבילה שיש להתקין. המודול נשאר כבוי כל עוד יש שגיאה.

<a id="routes"></a>
## 5. נקודות כניסה

| נקודת כניסה | מטפל | קובץ |
|---|---|---|
| `"entry": "module:ApacheModule"` של `module.json` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (הליבה) | [mod-apache2/rules/](../mod-apache2/rules/) |
| פונקציית הכלל `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| ממשק האינטרנט: מודולים › ניתנים להתקנה, הדרך היחידה להתקין מודולים (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`; התצוגה `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| ממשק האינטרנט: **עדכון** בשורה של מודולים › מותקנים (אותו `GET`, שהדפדפן משתמש בו שוב במשך 10 דקות, ואותו `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| ממשק האינטרנט: **הסרת התקנה** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `read_paths` של `module.json` | `manage.py read-paths`: התיקיות ש-localSIEM מאפשר ל-`localsiem` לקרוא, בתור root (הפקודה של `fRootCommand`) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | `read_paths` של כל מניפסט | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (302 ל-`installed/`), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`; התצוגה `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (הכתובת הישנה יותר `/admin/dashboard/modules/apache2/` עונה עם 301 אליה) | `fAdminModule` (ה-301: `fAdminModulesSection`); התצוגה `LocalsiemViews.module` | אותם קבצים |
| `GET /api/modules` | `fModules` (מצב עבור כל מי שמחובר) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (הגדרות, ערכים, מקורות, אבחון, כללים) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**הגדרה מחדש**, localSIEM 2.2.0 ומעלה) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `"entry": "module:PrivescModule"` של `mod-privesc/module.json` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (הליבה) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| רשומות ביקורת של הכללים של השרת (כל מפתח) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. ניתוח השפעה

| רכיב | מה מושפע אם הוא משתנה |
|---|---|
| `module.json` `id` | חייב להיות שווה לשם התיקייה בלי `mod-` (שם התיקייה המותקנת) ול-`vName`. הוא המפתח של ההגדרות (`modules.<id>`), של המצב (`<id>.doctor`) וה-`module` של כל אירוע: שינוי שם מאבד את ההגדרות השמורות ומפצל את ההיסטוריה. |
| `module.json` `core` | העלאתו מעל localSIEM המותקן מונעת את טעינת המודול (המצב «שגיאה»); במאגר, ניתנים להתקנה מציג «דורש localSIEM X ומעלה» ומותקנים מציג את הגרסה החדשה יותר בלי **עדכון**. |
| `module.json` `entry` | חייב להצביע על תת-מחלקה של `Module`; ערך שגוי הוא שגיאת טעינה. |
| `module.json` `default_enabled` | פעיל או כבוי בשרתים שבהם מנהל המערכת מעולם לא החליט (אם הדרישות שלו חסרות בהתקנה הראשונה, כבוי). |
| `module.json` `read_paths` | הרשאת הקריאה ש-localSIEM נותן בתור root (`manage.py read-paths`): תיקייה חסרה פירושה שגיאות הרשאה באבחון ובמצב. שינוי בגרסה חדשה גורם לממשק האינטרנט להציג שוב את הפקודה עבור root אחרי **עדכון** (`access_changed`). |
| `module.json` `install_requirements` | תיבת הדו-שיח דרישות של ניתנים להתקנה (`fRequirementsBody` של `modules.js`). ערך שגוי (מערכת שאינה `debian` או `alpine`, רשימה ריקה או יותר מ-20 פקודות, פקודה עם אופרטור של shell או מעבר שורה) הופך את המודול ללא חוקי (`fCheckInstallRequirements` של הליבה): הוא אינו מותקן ואינו נטען. |
| `module.json` `setup_option` | כלום: הליבה מתעלמת ממנו (לאף מודול אין אותו מאז apache2 1.3.0 ו-privesc 1.1.0). |
| תיקיות `mod-<name>/` עם `module.json` בשורש המאגר | מה שהקטלוג של ממשק האינטרנט מציג, בתור המודול `<name>`: ניתנים להתקנה מציג את אלה שעדיין לא מותקנים (מודול שדורש ליבה חדשה יותר בתור «דורש localSIEM X ומעלה», מודול לא חוקי בתור «המודול שבמאגר אינו חוקי»), ו-`version` גבוהה מזו המותקנת גורמת למותקנים להציע **עדכון**. |
| `module.json` `settings` | הטופס, האימות וברירות המחדל. ברירת מחדל חדשה חלה על שרתים שמעולם לא שמרו את המפתח הזה. ערכים שמורים אינם מועברים: מפתח ששמו שונה מאבד את הערך שלו, וערך ישן עם סוג חדש מגיע למודול כפי שנשמר. |
| `locales/*.json` | רק הטקסטים של ממשק האינטרנט; טקסט חסר חוזר ל-en-US, ואז למפתח. |
| `parsers.py` (מילון הרשומה) | הקורלציה (`correlation`, `fields.client_ip`, `fields.path`), כרטיס הבקשה, אינדקס הטקסט המלא (`search`, `raw`), התקינות של השורות שלא נותחו והפרטיות. |
| `logformat.py` `dKnownFormats` | הניתוח של כל לוג גישה; `localsiem_combined` נשאר עבור השרתים שכבר כותבים אותו (גרסאות 1.2.0 ומטה של המודול הוסיפו אותו): אין לשנות את ההגדרה שלו. |
| `correlate.py` | אירוע אחד לכל בקשה; הליבה קוראת ל-`mAdd`, ל-`mDue(pNow, pForce, pWatermark)` ול-`mPendingCount`, ומחזירה את הרשומות שעדיין ממתינות אחרי הפעלה מחדש. בלי `UNIQUE_ID` הוא מצמיד רשומות לפי השדות `client_ip`, `method`, `uri`, `status` ו-`path` שלהן: מנתח שכותב אותם אחרת שובר את ההצמדה. ההמתנה לרשומת הביקורת (`mWaitsForAudit`) צריכה את השדה `modsecurity` של שורות error.log ואת הרשומות של המקור `audit`. |
| `modsec.py` (קטגוריות, תוויות, טווחים) | שמות כללי ההתראה (הסטטיסטיקות של ה-SOC מקובצות לפיהם: יש לשמור עליהם קבועים), מפתחות הקיבוץ, חיפושי `category:`. |
| `ApacheModule.mBuildEvent` (מילון האירוע) | העמודות של טבלת האירועים, השדות שכללי ה-YAML קוראים (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), החיפושים וייצוא ה-CSV. |
| `ApacheModule.mAssess` | מה מגיע ל-SOC והחומרה שלו; המגבלות של `GenericAlert` בליבה (כלל 300, תיאור 10 000 תווים). |
| `severity.yaml` | החומרה של כל זיהוי של ModSecurity; החומרה היא חלק ממפתח הקיבוץ, כך ששינוי מתחיל קבוצות חדשות. |
| `rules/*.yaml` | ה-`id` הוא המפתח של הדריסות (`rules.<id>`) ושל החיפושים (`rule:localsiem:<id>`): יש לשמור עליו קבוע. השדות חייבים להתקיים באירועים; `{function: ...}` צריך את `mRuleFunctions`. |
| `discovery.py` | אילו לוגים נקראים; `fSourceKey` הוא המפתח של המיקומים השמורים (מפתח חדש הופך את הקובץ למקור חדש, בלי המיקום השמור שלו); ה-DocumentRoots של כלל ה-web shell; האבחון. |
| `doctor.py` | האבחון של ממשק האינטרנט ושל `manage.py` והרמזים שמוצגים ללקוח. רק הבדיקות של מה שאינו לוג (ModSecurity, ה-CRS, `SecRuleEngine`, `mod_unique_id`, הרשאות) רשאיות לשאת `fix`; הבדיקות של הלוגים רק מתארות אותם. |
| `mRequirements` / `fRequirementChecks` | האם ניתן להפעיל את המודול, המצב «כבוי» אחרי התקנה ראשונה בלי Apache או ModSecurity, הדרישות שממשק האינטרנט מציג ו-**הגדרה מחדש**. הן רצות בממשק האינטרנט וב-`manage.py` בלי אחסון ומנתחות את התצורה של Apache בכל קריאה: יש להרחיק אותן מהאחסון ומכל דבר איטי, ולשמור על המזהים `apache_config` ו-`modsecurity` קבועים. |
| privesc: עמודות ושדות של האירוע (`mBuildEvent`, `mAnalyzeCommand`) | כללי ה-YAML מתאימים להם לפי שם (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...): שדה ששמו שונה משבית בשקט את הכללים שמשתמשים בו. `vhost` הוא המשתמש: מפתח הקיבוץ של ההתראות והחיפושים `vhost:` תלויים בו. |
| privesc: `fReconToken` | מה נחשב סיור ואיך מבחינים בין פקודות שונות: שינוי אסימון משנה את המהירות שבה סשן מגיע לספים. |
| privesc: `SessionTracker` והדלתות (`sDoors`) | `root_without_door`: דלת שחסרה ברשימה הופכת סשנים לגיטימיים של root לקריטיים; דלת מיותרת מסתירה ניצולי קרנל. `mExport`/`mImport` הוא הפורמט של `privesc.sessions`. |
| privesc: `parsers.py` | השדות של הרשומות (`args`, `command`, `kind`, `uid`/`euid` של snoopy), מיסוך הסיסמאות והטקסט הגולמי של רשומות הביקורת; הפורמטים של snoopy שהוא קורא (המודול לעולם אינו משנה את `snoopy.ini`). |
| privesc: סיווג רשומות הביקורת (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | מה הופך ל-`file`, `chmod`, `kmod`, `ptrace` ו-`denied`, ולכן הכללים sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst ו-sensitive-denied; מספר syscall שגוי מסווג באופן שגוי את הרשומות של אותה ארכיטקטורה. |
| privesc: `surface.py` | העלות של הסריקה (thread, מגבלות) ומה שהאבחון ו-`mSurfaceResult` מדווחים; `privesc.surface` הוא נקודת הייחוס שלה. |
| privesc: `mRequirements` / `fRequirementChecks` | האם ניתן להפעיל את המודול (כל מקור קריא), המצב «כבוי» אחרי התקנה ראשונה שאת הלוגים שלה `localsiem` עדיין אינו יכול לקרוא, ו-**הגדרה מחדש**; נקראות בלי אחסון על ידי ממשק האינטרנט ו-`manage.py`: יש לשמור עליהן מהירות ובלי root. יש לשמור על המזהים `command_source`, `audit_log` ו-`syslog`. |
| ממשק התכנות של הליבה (`backend/core/module.py`, `registry.py` של localSIEM) | כל מודול: שינוי בחתימה של hook, מפתח מניפסט חובה חדש או חוזה חדש של רשומות ואירועים שוברים אותם; יש להעלות את `core` ב-`module.json` שלהם כשהם צריכים את localSIEM החדש. |

<a id="extensions"></a>
## 7. נקודות הרחבה

### איך לכתוב מודול חדש

1. **תיקייה**: יש ליצור את `mod-<name>/` בשורש הפרויקט הזה; `<name>`, שם המודול, תואם ל-`[a-z][a-z0-9_]{1,31}`. הקידומת `mod-` היא רק עבור התיקייה: `module.json`, המחלקה, האפשרויות והטקסטים משתמשים ב-`<name>`. בלי `__init__.py`.
2. **`module.json`**, לדוגמה:

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

3. **טקסטים**: `locales/<language>.json` לכל אחת מ-15 השפות של localSIEM עם `name`, `summary` והתווית והעזרה של כל הגדרה. ההערות על הדרישות נכנסות ל-`install_requirements` (`note`, לכל מערכת, ו-`debian` ו-`alpine`), שמוצגות בתיבת הדו-שיח דרישות.
4. **קוד**: `module.py` עם תת-מחלקה של `Module` שה-`vName` שלה הוא המזהה. עליה לממש את `mParse`, `mCreateCorrelator` ו-`mBuildEvent`, ובדרך כלל גם את `mDiscover`; שאר ה-hooks אופציונליים (סעיף 1). יש לייבא את הקבצים של המודול עצמו באופן יחסי ואת הליבה בתור `backend.core...`. שני המודולים של המאגר הזה הם דוגמאות מלאות ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)); שלד מינימלי:

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

5. **הפעולה שננקטה**: יש להחליט מה «כבר טופל» פירושו עבור השירות (לדוגמה, IP שכבר נחסמה) ולהגדיר עבורו את `action` ל-`blocked`; יש להוסיף זיהוי רק לאירועים שאין להם פעולה שננקטה.
6. **כללים**: קובצי YAML ב-`mod-<name>/rules/`, שמוחזרים על ידי `mRulesPath`, והפונקציות שהם קוראים להן ב-`mRuleFunctions`.
7. **דרישות**: אם המודול צריך תוכנה בשרת (כמו ש-apache2 צריך את Apache ואת ModSecurity 2), יש להחזיר בדיקה אחת לכל דרישה מ-`mRequirements()` (הפורמט של `fCheck`: `status` שהוא `ok` או `error`, וב-`fix` הפקודה שמתקינה אותה) ולעולם לא להתקין את התוכנה הזו מהמודול: בלי הדרישות שלו המודול מותקן במצב כבוי. היא רצה בלי אחסון, גם בממשק האינטרנט וב-`manage.py`. יש להצהיר גם, ב-`install_requirements` של `module.json`, על הפקודות שמתקינות את התוכנה הזו ב-Debian וב-Alpine (פקודה אחת בכל שורה, בלי אופרטורים של shell): ממשק האינטרנט מציג אותן תחת מודולים › ניתנים להתקנה › דרישות, כפי שהן ועם `sudo` בתחילתן, לפני שהמודול מותקן.
8. **התקנה**: יש לפרסם אותו במאגר הזה (ענף `main`); הוא מופיע תחת מודולים › ניתנים להתקנה בממשק האינטרנט של localSIEM כל עוד אינו מותקן, ו-**התקנה** מעתיקה את התיקייה `mod-<name>/` אל `/opt/localsiem/modules/<name>/` ומפעילה מחדש את רכיב האיסוף. הרשאת קריאה ל-`read_paths` שלו דורשת root: ממשק האינטרנט מציג את הפקודה (`manage.py setup-modules`). למודול אין אפשרות הגדרה: הוא לעולם אינו מתקין דבר או משנה דבר מחוץ ל-`/opt/localsiem`, ולעולם אינו כותב בלוגים של הלקוח, אינו מבצע להם רוטציה או מוחק אותם ואינו משנה את הפורמט שלהם; אם שרת כותב את הלוגים שלו בדרך משלו, המודול מסתגל אליו, ומה שחסר לשרת הוא דרישה. כדי לפרסם גרסה חדשה, יש להעלות את `version`: מודולים › מותקנים מציג את ההודעה ואת **עדכון**, ששומר את ההגדרות ואת המצב הפעיל או הכבוי של המודול ומציג שוב את הפקודה עבור root רק אם `read_paths` השתנו.
9. **תיעוד**: יש לעדכן את ה-README, את קובץ CODE זה ואת ה-MANUAL ב-15 השפות.

### איך להוסיף כלל למודול apache2

יש ליצור קובץ YAML ב-[mod-apache2/rules/](../mod-apache2/rules/) (כל מפתח ואופרטור מתוארים בראש [backend/core/rules.py](../../localSIEM/backend/core/rules.py)): `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` או `sequence`), התנאים (`when`, או `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` ו-`search`. השדות נבדקים קודם בעמודות האירוע ואחר כך ב-`fields`. הכלל מופיע בטבלת הכללים של דף המודול ונטען על ידי רכיב האיסוף אחרי שהגרסה החדשה של המודול מותקנת: יש להעלות את `version` ב-`module.json`, לפרסם אותה וללחוץ על **עדכון** תחת מודולים › מותקנים.

### איך להוסיף הגדרה למודול apache2

יש להוסיף אותה ל-`settings` של [mod-apache2/module.json](../mod-apache2/module.json) עם הסוג וברירת המחדל שלה, להוסיף את ה-`label` וה-`help` שלה לארבעת הקבצים של [mod-apache2/locales/](../mod-apache2/locales/), ולקרוא אותה עם `self.mModuleSettings().get("<key>")`. הטופס, האימות והטעינה מחדש מגיעים מהליבה.

### איך להוסיף בדיקת אבחון או לשנות חומרה

בדיקה היא `fCheck(id, status, title, detail, fix)` אחת ב-`fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)); יש לשמור על ה-`id` קבוע ולשים ב-`fix` את קטע התצורה או הפקודה המדויקים, רק עבור דרישות שאינן לוגים: בדיקה של הלוגים של הלקוח רק מתארת אותם ואת מה ש-localSIEM יכול או אינו יכול לקרוא מהם, בלי `fix`. החומרות של הזיהויים של ModSecurity משתנות ב-[mod-apache2/severity.yaml](../mod-apache2/severity.yaml) (`low`, `medium`, `high`, `critical`).

### איך להוסיף כלל למודול privesc

יש ליצור קובץ YAML ב-[mod-privesc/rules/](../mod-privesc/rules/), כמו אלה של Apache. יש להתאים לעמודות (`method`, `uri`, `path`, `vhost`, `action`) ולשדות של האירועים (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...), לעולם לא למפתח של כלל ביקורת; יש להוסיף `ignored: {not: true}` כדי שהמשתמשים שמתעלמים מהם לעולם לא יפעילו אותו, ו-`action: none` כשרק מה שבאמת רץ נחשב. אם התנאי צריך מצב או לוגיקה (רצף של אותו סשן, בדיקה של קובץ), יש לחשב דגל ב-`PrivescModule.mAnalyzeCommand` (כל מקור) או ב-`mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (מקור אחד) ולהתאים אליו מהכלל.

### איך להוסיף למודול privesc פקודת סיור, כלי או ניצול

- סיור: יש להוסיף את התוכנית ל-`sReconSimple`, או ענף ל-`fReconToken` שמחזיר אסימון לכל סוג של שאלה ([mod-privesc/commands.py](../mod-privesc/commands.py)). אסימון שמשתנה עם כל ארגומנט מנפח את הספירות.
- כלים וניצולים: יש להוסיף ביטוי רגולרי לרשימה של [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) או של [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) (ללא תלות באותיות רישיות, מותאם מול שורת הפקודה); מנהל המערכת יכול גם להוסיף אותם מההגדרות (`rules.<id>.lists`).

### איך להוסיף למודול privesc מקור או סוג של רשומת ביקורת

- נתיב רגיש: יש להוסיף אותו ל-`lSensitivePaths` של [mod-privesc/module.py](../mod-privesc/module.py) עם הקבוצה שלו (או קבוצה חדשה וכלל שמתאים ל-`sensitive_group`). סוג של קריאת מערכת: יש להוסיף את השם שלה לקבוצות של `mAuditSyscall` ואת המספר שלה לכל טבלה של `dSyscallTables`. לעולם אין להסתמך על המפתח של כלל ביקורת (לכל היותר להוסיף אותו ל-`dKeyHints`) ולעולם אין להתקין כללי ביקורת: השרת רושם את מה שמנהל המערכת שלו מחליט, והאבחון מתאר זאת (`dAuditKinds` של [doctor.py](../mod-privesc/doctor.py)).
- מקור: יש להחזיר אותו מ-`fDiscoverSources` עם `kind` חדש, לנתח אותו ב-`mParse` ולבנות את האירועים שלו ב-`mBuildEvent` עם אותן עמודות ושדות כמו האחרים, כך שהכללים יעבדו בלי שינויים.
