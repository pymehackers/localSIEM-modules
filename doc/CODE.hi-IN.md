# localSIEM-modules कोड संदर्भ

यह CODE इन भाषाओं में भी उपलब्ध है:\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), hi-IN, [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## अनुक्रमणिका

1. [आर्किटेक्चर और डिज़ाइन निर्णय](#architecture)
2. [मॉड्यूल मैप](#modules)
3. [मुख्य सिंबल](#symbols)
4. [मुख्य कॉल पाथ](#flows)
5. [एंट्री पॉइंट](#routes)
6. [प्रभाव विश्लेषण](#impact)
7. [विस्तार बिंदु](#extensions)

[इंस्टॉलेशन](README.hi-IN.md) · [उपयोगकर्ता मैनुअल](MANUAL.hi-IN.md) · [localSIEM कोड संदर्भ](../../localSIEM/doc/CODE.hi-IN.md)

<a id="architecture"></a>
## 1. आर्किटेक्चर और डिज़ाइन निर्णय

इस प्रोजेक्ट में localSIEM (साथ वाला प्रोजेक्ट `../localSIEM`) के इंस्टॉल किए जा सकने वाले मॉड्यूल हैं। इसकी अपनी कोई सेवा और कोई इंस्टॉलर नहीं है: मॉड्यूल केवल localSIEM वेब से, मॉड्यूल › इंस्टॉल योग्य में इंस्टॉल किए जाते हैं (वे मॉड्यूल › इंस्टॉल किए गए में अपडेट और अनइंस्टॉल किए जाते हैं), जो इस रिपॉज़िटरी (ब्रांच `main`) को डाउनलोड करता है और हर मॉड्यूल फ़ोल्डर, `mod-<name>/`, को `/opt/localsiem/modules/<name>/` में कॉपी करता है; localSIEM का इंस्टॉलर केवल कोर इंस्टॉल करता है, कभी कोई मॉड्यूल नहीं, और localSIEM के अपने कोई मॉड्यूल नहीं हैं। localSIEM के प्रोसेस (कलेक्टर, वेब, `manage.py`) इसे लोड करते हैं। `mod-` प्रीफ़िक्स केवल इस रिपॉज़िटरी में फ़ोल्डर के नाम का हिस्सा है: मॉड्यूल स्वयं (उसके `module.json` का `id`, उसके विकल्प, उसकी सेटिंग्स और उसका इंस्टॉल किया गया फ़ोल्डर) बिना इसके अपना नाम रखता है। आज दो मॉड्यूल हैं: `apache2` (फ़ोल्डर `mod-apache2/`) और `privesc` (फ़ोल्डर `mod-privesc/`)।

### मॉड्यूल कोर से बाहर क्यों रहते हैं

localSIEM का कोर ([backend/core/](../../localSIEM/backend/core/)) सामान्य है: स्टोरेज, खोज, नियम इंजन, ग्रुपिंग, SOC कतार, हार्टबीट और स्वास्थ्य Apache के बारे में कुछ नहीं जानते। किसी सेवा का क्या अर्थ है (उसके लॉग कहाँ हैं, उन्हें कैसे फ़्रेम और पार्स किया जाता है, रिकॉर्ड एक इवेंट कैसे बनते हैं, पहले ही निपटाया गया किसे माना जाता है, उसके नियम और उसकी आवश्यकताएँ), यह एक मॉड्यूल में रहता है। मॉड्यूल को उनके अपने प्रोजेक्ट में रखने का अर्थ है कि:

- मॉड्यूल का संस्करण होता है (`version`), वह localSIEM का वह न्यूनतम संस्करण घोषित करता है जिसकी उसे ज़रूरत है (`core`) और localSIEM की नई रिलीज़ के बिना अपडेट किया, जोड़ा या बंद किया जाता है;
- कोर किसी मॉड्यूल को नाम से इम्पोर्ट नहीं करता और उसका अपना कोई मॉड्यूल नहीं है: रजिस्ट्री ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) केवल `/opt/localsiem/modules/` को स्कैन करती है (डेवलपमेंट कॉपियों में `LOCALSIEM_MODULES_PATH`), जहाँ वेब इस रिपॉज़िटरी के मॉड्यूल इंस्टॉल करता है;
- जो मॉड्यूल लोड होने में विफल रहता है, वह दूसरों को कभी नहीं रोकता: उसकी त्रुटि वेब में (स्थिति «त्रुटि») और `manage.py modules` द्वारा सूचीबद्ध की जाती है;
- मॉड्यूल कभी कोर को संशोधित नहीं करता: `backend/core/module.py` और `backend/core/registry.py` ही पूरा अनुबंध हैं।

### अनुबंध: module.json, locales और एक Module सबक्लास

**`module.json`** (`fReadManifest` द्वारा जाँचा जाता है):

| कुंजी | डिफ़ॉल्ट | अर्थ | apache2 | privesc |
|---|---|---|---|---|
| `id` | आवश्यक | `mod-` प्रीफ़िक्स के बिना मॉड्यूल फ़ोल्डर का नाम (इंस्टॉल किए गए फ़ोल्डर का नाम), `[a-z][a-z0-9_]{1,31}`; क्लास का `vName` भी | `apache2` | `privesc` |
| `version` | `"0"` | मॉड्यूल का संस्करण, वेब में और `manage.py modules` द्वारा दिखाया जाता है | `1.3.2` | `1.1.2` |
| `core` | `"0"` | localSIEM का वह न्यूनतम संस्करण जिसकी इसे ज़रूरत है; इंस्टॉल किए गए localSIEM के `cVersion` से ऊँचा होने का अर्थ है कि मॉड्यूल लोड नहीं होता | `2.2.0` | `2.2.0` |
| `entry` | आवश्यक | `"file:Class"`: `.py` के बिना `file` (`[a-z][a-z0-9_]{0,63}`), `Class` `Module` का एक सबक्लास | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | व्यवस्थापक के निर्णय लेने तक यह चलता है या नहीं (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | पूर्ण फ़ोल्डर जिन्हें localSIEM, root के रूप में, `localsiem` उपयोगकर्ता को पढ़ने देता है (वह कमांड जो वेब इंस्टॉल करने के बाद, **पुनः कॉन्फ़िगर करें** के बाद और इन्हें बदलने वाले अपडेट के बाद दिखाता है) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | वे कमांड जो सर्वर पर, root के रूप में, मॉड्यूल को चाहिए वह सॉफ़्टवेयर इंस्टॉल करते हैं, हर सिस्टम (`debian`, `alpine`) के लिए: प्रति पंक्ति एक कमांड, शेल ऑपरेटरों के बिना, क्योंकि वेब उन्हें आगे `sudo` लगाकर भी दिखाता है (कोर का `fCheckInstallRequirements`)। मॉड्यूल › इंस्टॉल योग्य › आवश्यकताएँ में दिखाए जाते हैं, कभी चलाए नहीं जाते | Debian: Apache, ModSecurity 2, CRS, `a2enmod`, कोई न हो तो ModSecurity का अनुशंसित कॉन्फ़िगरेशन, रीस्टार्ट; Alpine: Apache | Debian: auditd और rsyslog; Alpine: auditd |
| `setup_option` | — | किसी भी मॉड्यूल द्वारा उपयोग नहीं किया जाता: कोर इसे नज़रअंदाज़ करता है (रजिस्ट्री इसे हटा देती है), क्योंकि मॉड्यूल कभी सर्वर नहीं बदलता; पुराने संस्करणों की `module.json` फ़ाइलों में यह अब भी हो सकता है | सेट नहीं | सेट नहीं (`--configure-privesc` 1.1.0 में हटा दिया गया) |
| `settings` | `[]` | हर सेटिंग का विवरण: वेब इससे अपना फ़ॉर्म बनाता है | 6 सेटिंग्स | 13 सेटिंग्स |

हर सेटिंग में एक `key` (`[a-z][a-z0-9_]{1,31}`), एक `type`, आमतौर पर एक `default`, और उसके प्रकार के एट्रिब्यूट होते हैं। `fValidateSettings` / `fCleanValue` / `fCleanRecords` जाँचते हैं कि व्यवस्थापक क्या सहेजता है:

| प्रकार | एट्रिब्यूट | वेब कंट्रोल | स्वीकृत मान |
|---|---|---|---|
| `boolean` | — | चेकबॉक्स | `true` / `false` |
| `integer` | `min`, `max` | संख्या फ़ील्ड | `min`..`max` के भीतर एक पूर्णांक |
| `string` | `max_length` (500) | टेक्स्ट फ़ील्ड | कंट्रोल कैरेक्टर के बिना टेक्स्ट, ट्रिम किया हुआ, `max_length` तक |
| `path` | — | मोनोस्पेस टेक्स्ट फ़ील्ड | खाली या पूर्ण (`/` से शुरू), 1024 कैरेक्टर तक |
| `choice` | `choices` (आवश्यक), `required` | सूची (आवश्यक न होने पर «—» के साथ) | `choices` में से एक, या खाली |
| `records` | `fields` (आवश्यक: अन्य प्रकारों की सेटिंग्स), `max_items` (50) | हर रिकॉर्ड के लिए एक ब्लॉक, जोड़ें और हटाएँ के साथ | अधिकतम `max_items` रिकॉर्ड की सूची; हर फ़ील्ड जाँचा जाता है, `required` फ़ील्ड खाली नहीं हो सकते और खाली फ़ील्ड हटा दिए जाते हैं |

**`locales/<language>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), `fReadTexts` द्वारा पढ़ा जाता है और वेब द्वारा दिखाया जाता है (`modules.js fModuleText`, जो en-US पर और फिर कुंजी पर लौट आता है):

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

गुम या टूटी हुई लोकेल फ़ाइल से केवल उसकी भाषा खोती है।

**`Module` सबक्लास** ([backend/core/module.py](../../localSIEM/backend/core/module.py))। रजिस्ट्री इसे `Class(pSettings, pMasker, pStorage, pManifest)` के रूप में बनाती है। इसके हुक:

| हुक | कौन कॉल करता है | डिफ़ॉल्ट | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | कलेक्टर, एक बार, स्टोरेज तैयार होने पर | कुछ नहीं | `apache.first_start` सहेजता है (लर्निंग दिनों की शुरुआत) | `privesc.first_start` सहेजता है; `privesc.sessions`, `privesc.surface` और `privesc.health` लोड करता है |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | कलेक्टर, वेब | `module.json` के डिफ़ॉल्ट के ऊपर `modules.<id>` से | विरासत में मिला | विरासत में मिला; `mReload` `mSettings` का कैश भी खाली करता है |
| `mDiscoveryInterval()` | कलेक्टर (चालू मॉड्यूल में सबसे छोटा, कम से कम 60 s) | `discovery_interval_seconds` या 3600 | विरासत में मिला | विरासत में मिला (डिफ़ॉल्ट 300) |
| `mDiscover()` | कलेक्टर (शुरुआत, अंतराल, रीलोड, डॉक्टर अनुरोध), `manage.py doctor` | `[]` | Apache कॉन्फ़िगरेशन और मैन्युअल स्रोतों से स्रोत `{key, path, kind, format, vhost, audit_type, storage_dir}` | `fDiscoverSources`: ऑडिट लॉग और syslog |
| `mCreateFramer(pSource)` | कलेक्टर, प्रति स्रोत | `LineFramer` | नेटिव सीरियल ऑडिट लॉग के लिए `AuditFramer` | विरासत में मिला (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | कलेक्टर, प्रति यूनिट | आवश्यक | `access`, `error` या `audit` का रिकॉर्ड | `audit` या `syslog` का रिकॉर्ड |
| `mCreateCorrelator()` | कलेक्टर, शुरुआत में | आवश्यक | `Correlator` (कोर सेटिंग्स से विंडो और कमज़ोर सहसंबंध) | `Correlator`: सीरियल के आधार पर ऑडिट रिकॉर्ड (EOE या 2 s); syslog पंक्तियाँ तुरंत |
| `mBuildEvent(pTransaction)` | कलेक्टर, हर देय ट्रांज़ैक्शन के लिए | आवश्यक | `action` और `detections` के साथ इवेंट | उन फ़्लैग के साथ इवेंट जिनसे नियम मेल खाते हैं; अपने कोई डिटेक्शन नहीं |
| `mRulesPath()` / `mRuleFunctions()` | कलेक्टर, नियम लोड करते समय | `None` / `{}` | उसके फ़ोल्डर का `rules/` / `{"apache2.new_php": mIsNewPhp}` | उसके फ़ोल्डर का `rules/` / विरासत में मिला `{}` |
| `mDetectionFromSignal(pEvent, pSignal)` | कलेक्टर, हर नियम सिग्नल के लिए (वैकल्पिक: `hasattr` से खोजा जाता है) | सामान्य डिटेक्शन | अनुरोध के ब्योरे और `{rule: {id, count}}` के साथ डिटेक्शन | उपयोगकर्ता, कमांड, प्रोग्राम, सत्र, पैरेंट, फ़ाइल... के साथ डिटेक्शन |
| `mEnrich(pDetection)` | कलेक्टर, ग्रुप के साथ, अलर्ट बनाने से पहले | `{}` | पिछले घंटे में IP का संदर्भ | सत्र का संदर्भ: शुरुआत देखी गई, प्रवेश का रास्ता, SSH पता, अंतिम 20 कमांड |
| `mDoctor()` | कलेक्टर (स्थिति `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd और उसके नियमों ने क्या रिकॉर्ड किया, syslog, snoopy, मॉड्यूल क्या देखता है, संस्करण 1.0.0 की फ़ाइलें, अटैक सरफ़ेस) |
| `mHealth(pNow)` | कलेक्टर, हर 60 s, केवल चालू मॉड्यूल | `[]` | ModSecurity अनलोड या Off, असली क्लाइंट IP नहीं (अधिकतम हर 300 s) | सत्र सहेजता है; स्कैन परिणाम; हर 300 s: auditd रुका, लिखने योग्य संवेदनशील फ़ाइलें (हर घंटे), setuid प्रोग्रामों का स्कैन शुरू करता है |
| `mSkipped()` | कलेक्टर की स्थिति, `manage.py doctor` | `[]` | पाइप किए गए लॉग, `GlobalLog` में शामिल लॉग, बिना डेटा वाले access लॉग (`format_without_data`) | syslog नहीं पढ़ा गया (auditd चल रहा है, `syslog_mode` never), ऑडिट लॉग मौजूद नहीं |
| `mSetLowDisk(pLowDisk)` | कलेक्टर, डिस्क स्तर | कुछ नहीं | ऑडिट हेडर और बॉडी सहेजना बंद करता है | विरासत में मिला |
| `mDisplayRecord(pRecord)` | वेब, अनुरोध कार्ड | `{}` | सहेजे गए ऑडिट रिकॉर्ड के हेडर और बॉडी (`fAuditDisplay`) | विरासत में मिला |
| `mRequirements()` | कोर, localSIEM 2.2.0 या उससे नया: पहली इंस्टॉलेशन, कलेक्टर की शुरुआत और रीलोड, वेब में **पुनः कॉन्फ़िगर करें**, `manage.py modules` और `doctor` | `[]` (कोई आवश्यकता नहीं) | `apache_config` और `modsecurity` (`fRequirementChecks`) | `command_source`: कोई भी स्रोत जिसे `localsiem` पढ़ सके, ऑडिट लॉग (auditd चलता हुआ, कंटेनर में नहीं) या syslog (snoopy के साथ, अगर इंस्टॉल हो); `audit_log` / `syslog` जब कोई स्रोत मौजूद हो लेकिन पढ़ा न जा सके |

कोर में अब न `mSetupSnippet` है न `mApplySetup`: मॉड्यूल के कोई सेटअप विकल्प नहीं होते और वे सर्वर को कभी नहीं बदलते।

रिकॉर्ड dict होते हैं जिनमें `time`, `received`, `module` (id: कलेक्टर इसी से कोरिलेटर चुनता है), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` और `raw` (मास्क किया हुआ) होते हैं, साथ में वैकल्पिक रूप से `search` (पूर्ण-टेक्स्ट खोज के लिए इंडेक्स किया गया टेक्स्ट)। इवेंट में events टेबल के कॉलम होते हैं (`storage_sqlite.py` में `lEventColumns`), साथ में `record_ids`, `rule_hits` और `detections`। एक डिटेक्शन में `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` और `uid` होते हैं।

### आवश्यकताएँ: मॉड्यूल कभी वह इंस्टॉल नहीं करता जिस पर वह नज़र रखता है

मॉड्यूल इंस्टॉल करने से वह सॉफ़्टवेयर कभी इंस्टॉल नहीं होता जिस पर वह नज़र रखता है: apache2 मॉड्यूल न Apache इंस्टॉल करता है न ModSecurity, और privesc मॉड्यूल न auditd, न कोई syslog डेमन, न snoopy इंस्टॉल करता है (उसकी आवश्यकता, `command_source`, कोई भी ऐसा स्रोत है जिसे `localsiem` उपयोगकर्ता पढ़ सके: कंटेनर के बाहर चलते auditd के साथ ऑडिट लॉग, या syslog; `mod-privesc/doctor.py` का `fRequirementChecks`)। मॉड्यूल स्वयं `mRequirements()` (localSIEM 2.2.0 या उससे नया) में परिभाषित करता है कि उसे चालू किए जाने से पहले क्या चाहिए: डॉक्टर के फ़ॉर्मेट में जाँचों की एक सूची, जो तब पूरी मानी जाती है जब किसी की भी स्थिति `error` न हो। apache2 मॉड्यूल `apache_config` (कोई Apache कॉन्फ़िगरेशन मिला: `apache2.conf`, `httpd.conf` या सेटिंग `config_file` की फ़ाइल) और `modsecurity` (`mod_security2` लोड है; ModSecurity 3 नहीं गिना जाता) लौटाता है, जिन्हें `fRequirementChecks` डॉक्टर की पहली जाँचों से लेता है; Apache के बिना, दोनों त्रुटियाँ हैं। उस सॉफ़्टवेयर को इंस्टॉल करने वाले कमांड `module.json` के `install_requirements` में घोषित होते हैं: वेब उन्हें मॉड्यूल इंस्टॉल करने से पहले (मॉड्यूल › इंस्टॉल योग्य › आवश्यकताएँ), सर्वर के सिस्टम के लिए दिखाता है, और उन्हें कभी नहीं चलाता। कोर:

- जब पहली इंस्टॉलेशन पर कोई आवश्यकता अधूरी हो और व्यवस्थापक ने कभी निर्णय न लिया हो, तो मॉड्यूल को बंद स्थिति में इंस्टॉल करता है (`modules.<id>.enabled = false`); अपडेट कभी `enabled` नहीं बदलता;
- जब तक कोई आवश्यकता अधूरी है, उसे चालू नहीं होने देता: स्विच लॉक रहता है और वेब आवश्यकताओं को उनके `fix` के साथ दिखाता है;
- जो मॉड्यूल चालू है और कोई आवश्यकता खो देता है, उसे कभी अपने आप बंद नहीं करता: उसका डॉक्टर और उसकी स्वास्थ्य चेतावनियाँ (`mHealth`: «ModSecurity is no longer loaded») इसकी सूचना देती हैं, और उसे बंद करने से वे चुप हो जातीं;
- कलेक्टर के शुरू या रीलोड होने पर, और मॉड्यूल के पेज पर **पुनः कॉन्फ़िगर करें** से (बंद होने पर भी), आवश्यकताएँ फिर से जाँचता है: अगर वे पूरी हैं, तो यह स्विच अनलॉक करता है, व्यवस्थापक मॉड्यूल चालू करता है, और वेब root के रूप में चलाने वाला वह कमांड दिखाता है जिससे `localsiem` इंस्टॉलेशन के बाद बने लॉग पढ़ सके (`read_paths`)।

### नेमस्पेस पैकेज के रूप में लोड किया जाता है

कहीं भी `__init__.py` नहीं है (Python 3.13 के अंतर्निहित नेमस्पेस पैकेज)। `fRegisterPackage` पैकेज `localsiem_modules` बनाता है, जिसका `__path__` मॉड्यूल फ़ोल्डर होता है, और `fLoadClass` `localsiem_modules.<id>.<file>` इम्पोर्ट करता है, जाँचता है कि क्लास एक `Module` है और उसका `vName` `id` के बराबर है। किसी मॉड्यूल के कोड के लिए परिणाम:

- उसकी अपनी फ़ाइलें **रिलेटिव** रूप से इम्पोर्ट की जाती हैं (`from .parsers import AccessParser`);
- कोर **`backend.core...`** के रूप में इम्पोर्ट किया जाता है (`from backend.core.module import Module`): localSIEM के प्रोसेस localSIEM फ़ोल्डर को `sys.path` पर रखते हैं;
- केवल स्टैंडर्ड लाइब्रेरी और localSIEM की डिपेंडेंसी (उसका वर्चुअल एनवायरनमेंट `/opt/localsiem/venv/`, उदाहरण के लिए PyYAML) उपलब्ध हैं: localSIEM किसी मॉड्यूल के लिए कुछ भी इंस्टॉल नहीं करता।

### मैनिफ़ेस्ट से बनाया गया सेटिंग्स फ़ॉर्म

मॉड्यूल का अपना कोई HTML नहीं होता। वेब `module.json` का `settings` और `locales/` के टेक्स्ट पढ़ता है, फ़ॉर्म बनाता है (`modules.js fBuildSettings`, `fRecordsEditor`), जो सहेजा जाता है उसे `fValidateSettings` से जाँचता है और `settings.json` में `modules.<id>` के अंतर्गत केवल वे मान रखता है जो व्यवस्थापक ने सहेजे; `enabled` भी वहीं रहता है। मॉड्यूल `mModuleSettings()` पढ़ता है: `module.json` के डिफ़ॉल्ट, उनके ऊपर सहेजे गए मान। इसलिए कोई सेटिंग जोड़ने के लिए वेब या कोर में कोई बदलाव नहीं चाहिए।

कोर की वे सेटिंग्स जिन्हें apache2 मॉड्यूल भी `self.dSettings` से पढ़ता है: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) और `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100)। `mModuleSettings()` `modules.apache2` के अंतर्गत सहेजी गई वे कुंजियाँ भी देता है जिन्हें `module.json` घोषित नहीं करता: `mDiscover` इसी तरह `document_roots` (`{vhost: folder}`, डिस्कवर किए गए DocumentRoot के ऊपर) पढ़ता है; इसे केवल `settings.json` संपादित करके सेट किया जा सकता है।

### «की गई कार्रवाई» का सिद्धांत

SOC को केवल वही जाता है जिसे अभी तक किसी ने निपटाया नहीं है। apache2 मॉड्यूल में की गई कार्रवाई सबसे भरोसेमंद स्रोत से पढ़ी जाती है: ऑडिट लॉग (नेटिव फ़ॉर्मेट में `Action: Intercepted (phase N)`, JSON में `audit_data.action.intercepted/phase`), फिर error.log (`Access denied with code NNN (phase N)`)। ModSecurity के किसी निशान के बिना 403 ब्लॉक नहीं है (`fields.doubtful_block`)।

| स्थिति | `action` | डिटेक्शन (SOC को) |
|---|---|---|
| चरण 1-2 में इंटरसेप्ट किया गया (एप्लिकेशन को यह कभी नहीं मिला) | `blocked` | कोई नहीं: `mAssess` `None` लौटाता है; बाद के अलर्ट के संदर्भ में गिना जाता है |
| चरण 3-4 में इंटरसेप्ट किया गया | `none` | हाँ, `blocked_late` (उच्च), या डेटाबेस त्रुटि के साथ `success_indicator` |
| इंजन `DetectionOnly` में होने पर मैच | `none` | हाँ |
| विसंगति थ्रेशोल्ड से नीचे मैच | `none` | हाँ, `below_threshold` (निम्न) |
| YAML नियमों के सिग्नल | `none` | हाँ |

गंभीरताएँ `severity.yaml` से आती हैं (`fLoadSeverityTable`; फ़ाइल न होने या कोई मान अमान्य होने पर बिल्ट-इन डिफ़ॉल्ट बना रहता है): `crs_not_blocked_2xx` उच्च, `crs_not_blocked_other` मध्यम, `blocked_late` उच्च, `success_indicator` क्रिटिकल (आउटबाउंड नियम 950-955 ब्लॉक नहीं हुआ, या उसी अनुरोध में डेटाबेस त्रुटि), `below_threshold` निम्न (कोर सेटिंग `below_threshold_severity` को प्राथमिकता मिलती है)। «थ्रेशोल्ड से ऊपर» का अर्थ है कि कोई 949xxx नियम मेल खाया या ModSecurity द्वारा बताया गया स्कोर थ्रेशोल्ड तक पहुँच गया; नियमों की गंभीरताओं से गणना किया गया स्कोर केवल एक अनुमान है और निर्णय नहीं करता। थ्रेशोल्ड वह है जो संदेशों में है, नहीं तो `anomaly_threshold`, नहीं तो `crs-setup.conf` वाला, नहीं तो 5।

### apache2 मॉड्यूल कैसे काम करता है

1. **डिस्कवरी** (`discovery.py`): `ApacheConfig` कॉन्फ़िगरेशन को सीधे पढ़ता है (`Include`, `IncludeOptional`, `Define`, Debian के `envvars` के `${VARS}`, `<VirtualHost>`, लोड किए गए मॉड्यूल के विरुद्ध `<IfModule>`), `localsiem` उपयोगकर्ता के रूप में और `apache2ctl` के बिना। `fDiscoverSources` `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` और `SecAuditLog` को स्थिर कुंजी `apache:<kind>:<real path>` वाले स्रोतों में बदलता है। जिस `GlobalLog` के फ़ॉर्मेट में `%v` है, वह हर vhost को कवर करता है (दूसरे access लॉग छोड़ दिए जाते हैं); पाइप किए गए लॉग और syslog छोड़ दिए जाते हैं, और वे access लॉग भी जिनके फ़ॉर्मेट में कोई `%` डायरेक्टिव नहीं है (Apache ऐसा उपनाम जिसे कोई `LogFormat` परिभाषित नहीं करता, जैसा है वैसा लिखता है: `format_without_data`, जब तक डेटा वाला कोई दूसरा `CustomLog` उसी फ़ाइल में न लिखता हो; डॉक्टर यह बताता है, बिना समाधान के, क्योंकि लॉग का फ़ॉर्मेट कभी नहीं बदला जाता); मैन्युअल स्रोत पहले आते हैं और कोई फ़ाइल एक ही बार पढ़ी जाती है।
2. **फ़्रेमिंग और पार्सिंग** (`parsers.py`, `logformat.py`, `modsec.py`): access पंक्तियाँ उनके `LogFormat` से बने रेगुलर एक्सप्रेशन से पार्स की जाती हैं (जो फ़ॉर्मेट पिछली बार काम आया था, उसे पहले आज़माया जाता है); error पंक्तियाँ वर्गीकृत की जाती हैं (`modsecurity`, `database`, `php`, `crash`, `apache`); ऑडिट रिकॉर्ड JSON (एक पंक्ति, `matched_rules` से पहले काटी गई), नेटिव सीरियल (`AuditFramer` `--id-A--` से `--id-Z--` तक जोड़ता है) या कॉन्करेंट (इंडेक्स पंक्ति `SecAuditLogStorageDir` के अंतर्गत किसी फ़ाइल की ओर इशारा करती है) के रूप में पढ़े जाते हैं। सब कुछ मास्क किया जाता है; जो फ़िट नहीं होता, उसे `unparsed` के रूप में रखा जाता है।
3. **सहसंबंध** (`correlate.py`): एक ही `UNIQUE_ID` वाले रिकॉर्ड एक ट्रांज़ैक्शन बनाते हैं, जो सहसंबंध विंडो और पीछे चल रहे स्रोतों के वॉटरमार्क का इंतज़ार करता है; `UNIQUE_ID` के बिना access पंक्ति (Apache के डिफ़ॉल्ट फ़ॉर्मेट) को `mPair` द्वारा, जब वह या उसके अनुरोध के रिकॉर्ड देय होते हैं, उन ModSecurity रिकॉर्ड के साथ जोड़ा जाता है जिनकी कोई access पंक्ति नहीं है: वही क्लाइंट IP, ±2 s के भीतर समय (पंक्ति में पूरे सेकंड होते हैं) और वही मेथड, URI, स्टेटस और पाथ, जब दोनों पक्ष उन्हें जानते हों; जो उम्मीदवार इनमें से अधिक में मेल खाता है वह जीतता है, फिर सबसे निकट वाला, फिर सबसे पुराना, और इवेंट को कमज़ोर के रूप में चिह्नित किया जाता है। `UNIQUE_ID` के बिना error.log पंक्तियाँ तुरंत अपने IP के सबसे निकट ट्रांज़ैक्शन से जुड़ जाती हैं। `UNIQUE_ID` और error.log की ModSecurity पंक्ति वाला ट्रांज़ैक्शन, जब तक ऑडिट रिकॉर्ड आ रहे हों (`vAuditSeen`), अपने ऑडिट रिकॉर्ड का भी इंतज़ार करता है (`mWaitsForAudit`), अपने पहले रिकॉर्ड से अधिकतम `cAuditWaitSeconds` (120 s): ModSecurity अपने नियमों की पंक्तियाँ अनुरोध चलते समय लिखता है और ऑडिट रिकॉर्ड उसके समाप्त होने पर, इसलिए अन्यथा धीमा अनुरोध दो इवेंट बन जाता; ऑडिट रिकॉर्ड आने के बाद, access पंक्ति को `cAfterAuditSeconds` (2 s) और मिलते हैं।
4. **इवेंट** (`ApacheModule.mBuildEvent`): फ़ील्ड पहले access से, फिर audit से, फिर error से लिए जाते हैं; vhost `%v` से या, उसके बिना, ऑडिट रिकॉर्ड के Host हेडर और लोकल पोर्ट से (`mVhostName`); पूरे सेकंड वाली access पंक्ति के साथ, ऑडिट रिकॉर्ड का समय; `fSummarize` नियम, श्रेणियाँ, स्कोर, थ्रेशोल्ड और इंटरसेप्शन देता है; की गई कार्रवाई और `mAssess` डिटेक्शन तय करते हैं।
5. **नियम, संवर्धन, डॉक्टर और स्वास्थ्य**: `rules/` के YAML नियम हर इवेंट पर चलते हैं (कोर इंजन); `mEnrich` IP का संदर्भ जोड़ता है; `fRunDoctor` आवश्यकताएँ जाँचता है और लॉग का विवरण देता है, बिना कुछ बदले; `mHealth` ModSecurity और असली क्लाइंट IP पर नज़र रखता है। मॉड्यूल का कोई सेटअप विकल्प नहीं है: root के रूप में, localSIEM केवल `localsiem` को `/var/log/apache2` पढ़ने की अनुमति देता है।

### जानने योग्य डिज़ाइन निर्णय

- **अपना कोई इंस्टॉलर नहीं**: मॉड्यूल केवल localSIEM वेब से इंस्टॉल (मॉड्यूल › इंस्टॉल योग्य), अपडेट (**अपडेट करें**, मॉड्यूल › इंस्टॉल किए गए में) और अनइंस्टॉल (**अनइंस्टॉल करें**) किए जाते हैं, जो इस रिपॉज़िटरी को डाउनलोड करता है और उन्हें `backend/core/catalog.py` से इंस्टॉल करता है (सुरक्षित अनपैकिंग, एक समय में एक इंस्टॉलेशन, फ़ोल्डर का एटॉमिक स्वैप)। जिसके लिए root चाहिए (`read_paths` को पढ़ने की अनुमति), वह localSIEM करता है: इंस्टॉल करने के बाद (और `read_paths` बदलने वाले अपडेट के बाद), वेब root के रूप में चलाने वाला कमांड दिखाता है।
- **क्लाइंट के लॉग केवल पढ़े जाते हैं**: मॉड्यूल उन सेवाओं के लॉग में कभी नहीं लिखता जिन पर वह नज़र रखता है, न उन्हें रोटेट, ट्रंकेट, मूव या डिलीट करता है, और न कभी उनका फ़ॉर्मेट बदलता है; apache2 मॉड्यूल कभी Apache या ModSecurity का कॉन्फ़िगरेशन भी नहीं बदलता (इसका कोई `setup_option` नहीं है)। अगर कोई सर्वर अपने लॉग अपने ही फ़ॉर्मेट में लिखता है (अपना ही `LogFormat`, `mod_remoteip` का क्लाइंट IP), तो मॉड्यूल उसके अनुसार ढल जाता है: `AccessFormat` हर access लॉग का पार्सर उसके `LogFormat` से बनाता है, और `fCanPair` / `Correlator.mPair` `UNIQUE_ID` के बिना पंक्तियों को जोड़ते हैं। डॉक्टर केवल लॉग का विवरण देता है और बताता है कि localSIEM उनसे क्या पढ़ सकता है और क्या नहीं: जाँचों `log_format`, `log_format_without_data`, `remoteip`, `audit_log` और `sanitise` का कोई `fix` नहीं है; केवल जो लॉग नहीं है (ModSecurity, CRS, `SecRuleEngine`, `mod_unique_id`, `localsiem` की पढ़ने की अनुमतियाँ) उसके साथ समाधान आता है। `--configure-apache` संस्करण 1.3.0 में हटा दिया गया; `localsiem_combined` उन सर्वरों के लिए `dKnownFormats` में बना रहता है जो इसे पहले से लिखते हैं, और localSIEM का इंस्टॉलर वह `localsiem.conf` हटा देता है जो पुराने संस्करणों ने लिखा था (`--uninstall`, `--reinstall`)।
- ऑडिट लॉग का **भाग K** (`matched_rules`) और **भाग E** (प्रतिक्रिया बॉडी) कभी सहेजे नहीं जाते। हेडर और बॉडी केवल मास्क किए गए कच्चे रिकॉर्ड में रहते हैं; अनुरोध कार्ड उन्हें फिर से बनाता है (`fAuditDisplay`)। पूर्ण-टेक्स्ट इंडेक्स को एक घटाया हुआ टेक्स्ट मिलता है (`search`: अनुरोध पंक्ति, होस्ट, यूज़र एजेंट और हर नियम का id, संदेश और डेटा)।
- **कच्चा टेक्स्ट मास्क किए गए हिस्सों से फिर से बनाया जाता है**: मूल ऑडिट रिकॉर्ड में पासवर्ड और कुकी हो सकती हैं।
- **वेब और टूल मॉड्यूल को स्टोरेज के बिना बनाते हैं** (`WebContext.mModule` और `manage.py` में `pStorage` `None` होता है): कंस्ट्रक्टर और जिन हुक को वे कॉल करते हैं, उन्हें स्टोरेज का उपयोग नहीं करना चाहिए।
- **इवेंट डेटाबेस में स्थिति**: `apache.first_start` (लर्निंग दिन), `apache.health` (जो पहले ही रिपोर्ट किया जा चुका है, ताकि रीस्टार्ट उसे दोहराए नहीं) और `apache2.doctor` (कलेक्टर द्वारा लिखा गया)। पहले दो, स्रोत कुंजियों `apache:<kind>:<real path>` की तरह, वह नाम रखते हैं जो मॉड्यूल का apache2 कहलाने से पहले था: जिस सर्वर पर `apache` मॉड्यूल था, वह अपने लर्निंग दिन, अपनी स्वास्थ्य स्मृति और अपनी पढ़ने की स्थितियाँ बनाए रखता है (नई स्रोत कुंजी के साथ, 5 MiB से छोटा हर लॉग फिर से शुरू से पढ़ा जाता)। स्वास्थ्य स्मृति के समय प्रोजेक्ट के नेटिव फ़ॉर्मेट (`2026-10-29@13-59-59.723`, UTC) में होते हैं; किसी पुराने संस्करण द्वारा epoch सेकंड के साथ सहेजी गई स्थिति लोड होने पर बदल दी जाती है।
- **पाथ की सुरक्षा**: `mIsNewPhp` `..` को अस्वीकार करता है और DocumentRoot के अंदर ही रहता है; `fReadConcurrentEntry` `SecAuditLogStorageDir` के अंदर रहता है और अधिकतम 8 MiB पढ़ता है; कोरिलेटर अधिकतम 50 000 लंबित ट्रांज़ैक्शन रखता है।

### privesc मॉड्यूल कैसे काम करता है

सवाल यह नहीं है कि «क्या किसी ने `whoami` चलाया?» (व्यवस्थापक यह हर दिन करते हैं), बल्कि यह कि «क्या यह सत्र एस्केलेशन के रास्ते पर चल रहा है, और क्या वह वहाँ पहुँच गया?»। मॉड्यूल दो स्रोतों को एक ही अर्थ वाले इवेंट में बदलता है (`vhost` व्यक्ति, `method` प्रकार, `uri` कमांड, `path` प्रोग्राम या फ़ाइल, `ip` SSH पता, `score` सत्र की अलग-अलग टोही), उन पर फ़्लैग की गणना करता है, और YAML नियमों को तय करने देता है कि SOC को क्या जाता है।

1. **डिस्कवरी** (`discovery.py`): `fDiscoverSources` ऑडिट लॉग (`fAuditLogPath`: सेटिंग, `auditd.conf` का `log_file`, `/var/log/audit/audit.log`; तब भी जब auditd चलता है और `localsiem` उसे अभी पढ़ नहीं सकता, ताकि कोर इसकी सूचना दे) और syslog (`fSyslogPath`) लौटाता है जब `syslog_mode` ऐसा कहता है (`auto`: auditd नहीं चल रहा, उसका लॉग पढ़ने योग्य नहीं, या snoopy इंस्टॉल है)। यह वह भी इकट्ठा करता है जो डॉक्टर को चाहिए: कंटेनर (`fContainer`, root के बिना पढ़ने योग्य: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), auditd बाइनरी और pid, snoopy, हर लॉग पढ़ा जा सकता है या नहीं (`fReadState`: `readable`, `unreadable` या `missing`) और वे फ़ाइलें जो संस्करण 1.0.0 ने छोड़ीं (`fLegacyLeftovers`)। `Accounts` `/etc/passwd`, `/etc/group` और `UID_MIN` को उनके बदलने पर फिर से पढ़ता है, और किसी uid को `root`, `admin` (`admin_groups` का सदस्य), `user` या `service` के रूप में वर्गीकृत करता है।
2. **पार्सिंग** (`parsers.py`): `fParseAuditLine` `type=... msg=audit(<time>:<serial>): k=v ...`, यूज़र-स्पेस भाग `msg='...'`, `\x1d` के बाद का समृद्ध भाग पढ़ता है, `EXECVE` के आर्ग्युमेंट जोड़ता है (`aN[i]` टुकड़ों में बँटे आर्ग्युमेंट भी), हेक्साडेसिमल मान (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) डिकोड करता है और **डिकोड और मास्क किए गए मानों से कच्चा टेक्स्ट फिर से बनाता है** (पासवर्ड का हेक्साडेसिमल उसे बनाए रखता); `search` को डिकोड किया गया कमांड मिलता है। `fParseSyslogLine` ISO और क्लासिक टाइमस्टैम्प पढ़ता है (busybox के `facility.priority` के साथ या उसके बिना) और `fParseSyslogMessage` snoopy (2.4 और 2.5 के उसके डिफ़ॉल्ट फ़ॉर्मेट, `uid:alice(1000)/root(0)` सहित, और वह फ़ॉर्मेट जो संस्करण 1.0.0 ने सेट किया था), sudo, su (util-linux और busybox), pkexec, doas, `pam_unix` और sshd को समझता है। `fMaskCommand` कोर के मास्कर से पहले कमांड लाइनों में पासवर्ड मास्क करता है।
3. **सहसंबंध** (`correlate.py`): एक ही सीरियल वाले ऑडिट रिकॉर्ड एक ट्रांज़ैक्शन बनाते हैं, जो `EOE` पर देय होता है, एक-रिकॉर्ड वाले यूज़र-स्पेस प्रकारों (`USER_*`, `CRED_*`, `DAEMON_*`...) के लिए तुरंत, या रिकॉर्ड के बिना 2 s के बाद; अधिकतम 50 000 लंबित। syslog पंक्तियाँ तुरंत देय होती हैं।
4. **इवेंट** (`PrivescModule.mBuildEvent`): `mAuditEvent` प्रकार के आधार पर बाँटता है: `EXECVE` → `mAuditExec` (`PATH` रिकॉर्ड या `stat` से प्रोग्राम का setuid बिट, `suid_escape` जब euid 0 हो, real uid 0 न हो और प्रोग्राम setuid न हो, `BPRM_FCAPS` से हासिल कैपेबिलिटी, `root_without_door`, `parent_interpreter` जब root के रूप में चलने वाला शेल root के अलावा किसी उपयोगकर्ता के इंटरप्रेटर द्वारा शुरू किया गया हो, प्रोसेस मेमोरी से पैरेंट); `USER_*`/`LOGIN` → `mAuditUser` (शुरू हुआ सत्र, SSH पता, प्रवेश के रास्ते: sudo, su, pkexec, doas, run0, systemd के `USER_START`/`USER_CMD`; विफलताएँ); `CONFIG_CHANGE` (`audit_disabled`, हटाए गए किसी भी नियम के लिए `audit_rule_removed`), `DAEMON_*` (`auditd_stopped_manually` जब भेजने वाला pid 1 न हो), `ANOM_ABEND` (`crash_suspicious`); कोई भी अन्य `SYSCALL` → `mAuditSyscall`, जो उसे उसके सिस्टम कॉल (`fSyscallName`: समृद्ध फ़ॉर्मेट का नाम, या उसके आर्किटेक्चर की तालिका में संख्या), उसके आर्ग्युमेंट और उसके `PATH` रिकॉर्ड से वर्गीकृत करता है, कभी नियम की कुंजी से नहीं: `denied` (किसी व्यक्ति के लिए open, exec या truncate `EACCES`/`EPERM` के साथ विफल), `kmod`, `ptrace` (`PTRACE_ATTACH`/`PTRACE_SEIZE` के लिए `ptrace_attach`), `chmod` (setuid या setgid बिट वाला मोड, फ़ोल्डर पर नहीं, `writer_allowed` के साथ) और `file` (`lSensitivePaths` के किसी पाथ में बदलाव, `sensitive_group` और `writer_allowed` के साथ; कुंजी, `dKeyHints` के ज़रिए, केवल तब जब कोई पाथ रिज़ॉल्व न हो सके)। `mSyslogEvent` snoopy को `exec` के रूप में संभालता है (`stat` से `suid_escape`; `filename` के बिना, कमांड के पहले शब्द से प्रोग्राम) और sudo, su, pkexec, doas, login और pam को। हर कमांड `mAnalyzeCommand` से गुज़रता है: टोही टोकन (`fReconToken`) और विंडो में सत्र के अलग-अलग टोकन (`recon_burst`, `recon_massive`, `score`), शेल द्वारा चलाए गए डाउनलोड (`cDownloadOnelinerRegex`, या एक डाउनलोडर जिसके बाद उसी पैरेंट वाला शेल आता है), `compile_in_tmp`, सत्र के अंतिम कमांड और, सेवा खातों के लिए, प्रोग्राम (`fProgramKey`) की उसके इतिहास से तुलना (कोर का `mPathFirstSeen`, `learning_days` के बाद: `new_program`)। `ignored` नज़रअंदाज़ किए गए उपयोगकर्ताओं को चिह्नित करता है।
5. **नियम, संवर्धन, डॉक्टर और स्वास्थ्य**: `rules/` के 35 YAML नियम हर डिटेक्शन तय करते हैं (`mDetectionFromSignal`); `mEnrich` सत्र का संदर्भ जोड़ता है; `fRunDoctor` auditd और उसके नियमों ने क्या रिकॉर्ड किया, syslog, snoopy, मॉड्यूल क्या देखता है और क्या नहीं, संस्करण 1.0.0 की फ़ाइलें और अटैक सरफ़ेस का विवरण देता है; `mHealth` रुके हुए auditd, लिखने योग्य संवेदनशील फ़ाइलों और setuid प्रोग्रामों के स्कैन (`SurfaceScanner`, एक थ्रेड) के परिणाम की रिपोर्ट करता है। मॉड्यूल का कोई सेटअप विकल्प नहीं है और यह सर्वर पर कुछ नहीं बदलता।

### privesc मॉड्यूल के डिज़ाइन निर्णय

- **दो स्रोत, एक अर्थ।** auditd से कोई उपयोगकर्ता बच नहीं सकता, लेकिन यह कंटेनरों के अंदर नहीं चलता (कर्नेल का ऑडिट नेमस्पेस में बँटा नहीं होता); snoopy कंटेनरों में हर प्रोग्राम देखता है लेकिन उसे syslog चाहिए; अकेला syslog केवल sudo, su, pkexec और doas देता है। कोई भी स्रोत शेल के बिल्टइन नहीं देखता। नियम कॉलम और फ़्लैग से मेल खाते हैं, कभी स्रोत से नहीं, इसलिए उन्हें छुए बिना कोई स्रोत जोड़ा जा सकता है। दो बार देखा गया वही कमांड एक ही अलर्ट बनाता है: कोर डिटेक्शन को मॉड्यूल, उपयोगकर्ता, IP, श्रेणी और गंभीरता के आधार पर समूहित करता है।
- **बर्स्ट, कमांड नहीं।** टोही हर प्रकार के सवाल के लिए एक टोकन है (`whoami`, `read:/etc/passwd`, `find:-perm:`...), और केवल एक विंडो में किसी सत्र के अलग-अलग टोकन की संख्या अलर्ट बनाती है, व्यवस्थापकों के लिए ऊँचे थ्रेशोल्ड और स्क्रिप्ट के लिए तीसरे थ्रेशोल्ड के साथ। थ्रेशोल्ड सेटिंग्स हैं, नियम थ्रेशोल्ड नहीं: नियम केवल `recon_burst` / `recon_massive` से मेल खाता है।
- **सफलता सबसे ज़्यादा मायने रखती है।** `suid_escape` (ऐसा प्रोग्राम जो setuid नहीं है, euid 0 और 0 से अलग real uid के साथ चल रहा है) और `root_without_door` (ऐसे सत्र में root जिसकी शुरुआत देखी गई थी और जो कभी sudo, su, pkexec या doas से नहीं गुज़रा) दो क्रिटिकल संकेत हैं कि एस्केलेशन सफल हुआ, लगभग बिना फ़ॉल्स पॉज़िटिव के। जिस सत्र की शुरुआत नहीं देखी गई (मॉड्यूल से पहले खुले सत्र, एक दिन की निष्क्रियता के बाद भुलाए गए सत्र), उसे कभी चिह्नित नहीं किया जाता।
- **सत्र रीस्टार्ट के बाद भी बने रहते हैं।** `SessionTracker` हर सत्र की शुरुआत, SSH पता और प्रवेश का रास्ता स्थिति `privesc.sessions` में रखता है (अधिकतम हर मिनट सहेजा जाता है); टोही टोकन और अंतिम कमांड मेमोरी में रहते हैं। एक दिन से निष्क्रिय सत्र हटा दिए जाते हैं।
- **केवल वही जो सर्वर पर पहले से है।** मॉड्यूल `/opt/localsiem` के बाहर कभी कुछ इंस्टॉल नहीं करता और न कुछ बदलता है: यह कोई ऑडिट नियम लोड नहीं करता, `auditd.conf` या `snoopy.ini` को नहीं छूता और कोई हुक इंस्टॉल नहीं करता। संस्करण 1.0.0 ऐसा करता था (`--configure-privesc`: `lsiem_*` कुंजियों वाले ऑडिट नियम, `log_group = adm`, एक bash हुक, snoopy का फ़ॉर्मेट); संस्करण 1.1.0 ने इसे हटा दिया। इसलिए ऑडिट रिकॉर्ड उनके प्रकार, उनके सिस्टम कॉल और उनके पाथ से वर्गीकृत किए जाते हैं, ताकि कोई भी ऑडिट नियम काम करें (सर्वर के, STIG के नमूना नियम, या वे `lsiem_*` नियम जो 1.0.0 ने छोड़े); कुंजी खोजों के लिए `fields.key` में रखी जाती है और केवल एक संकेत है (`dKeyHints`)। जब लॉग में समृद्ध नाम नहीं होते, तो सिस्टम कॉल की संख्याएँ प्रति आर्किटेक्चर पढ़ी जाती हैं (`dSyscallTables`: x86_64, i386 और aarch64, riscv64 और loongarch64 की सामान्य तालिका)। डॉक्टर बताता है कि सर्वर के नियम क्या रिकॉर्ड करते हैं और क्या नहीं; उसका `fix` केवल इंस्टॉल करने वाला पैकेज या `localsiem` की पढ़ने की अनुमति है।
- **पढ़ने योग्य का अर्थ है पढ़ने योग्य।** आवश्यकता उस स्रोत से पूरी होती है जो मौजूद है और जिसे `localsiem` खोल सकता है (`fReadState`), किसी प्रोग्राम के इंस्टॉल होने से नहीं: पहली इंस्टॉलेशन पर लॉग आमतौर पर root के होते हैं, इसलिए मॉड्यूल root वाले कमांड (`manage.py setup-modules`) और **पुनः कॉन्फ़िगर करें** तक बंद रहता है।
- **पैकेज मैनेजर हमलावर नहीं हैं।** खाता और पैकेज टूल (`sAllowedWriters`) द्वारा, या ऐसे प्रोग्रामों द्वारा जिनके ज्ञात पूर्वज पैकेज मैनेजर हैं, संवेदनशील फ़ाइलों और setuid बिट में किए गए बदलाव `writer_allowed` सेट करते हैं, और नियम उन्हें छोड़ देते हैं।
- **स्कैन कभी कलेक्टर को नहीं रोकता।** `SurfaceScanner` अपने अलग थ्रेड में `scan_paths` को खंगालता है, हर एक के फ़ाइल सिस्टम से बाहर गए बिना, `/proc`, `/sys` और कंटेनरों के फ़ोल्डर छोड़ते हुए, 30 लाख फ़ाइलों या 15 मिनट तक; `mHealth` परिणाम तैयार होने पर उसे लेता है। पहला स्कैन संदर्भ है; बाद वाले वह रिपोर्ट करते हैं जो नया है।
- **वेब और टूल मॉड्यूल को स्टोरेज के बिना बनाते हैं**: `mDiscover`, `mDoctor` और `mRequirements` कभी इसका उपयोग नहीं करते, और `mAnalyzeCommand` `mPathFirstSeen` को केवल तब कॉल करता है जब वह मौजूद हो।
- **इवेंट डेटाबेस में स्थिति**: `privesc.first_start` (लर्निंग दिन), `privesc.sessions`, `privesc.surface` (स्कैन और डॉक्टर का संदर्भ), `privesc.health` (जो पहले ही रिपोर्ट किया जा चुका है, auditd चल रहा था या नहीं) और `privesc.doctor` (कलेक्टर द्वारा लिखा गया)। सेवा खातों के देखे गए प्रोग्राम `seen_paths` की पंक्तियाँ हैं, vhost `privesc:<account>` के साथ। `privesc.health` (स्वास्थ्य स्मृति) और `privesc.sessions` (हर सत्र का `last`) के समय प्रोजेक्ट के नेटिव फ़ॉर्मेट (`2026-10-29@13-59-59.723`, UTC) में होते हैं; किसी पुराने संस्करण द्वारा epoch सेकंड के साथ सहेजी गई स्थिति लोड होने पर बदल दी जाती है।

<a id="modules"></a>
## 2. मॉड्यूल मैप

| मॉड्यूल | पाथ | ज़िम्मेदारी | किस पर निर्भर | किसके द्वारा उपयोग |
|---|---|---|---|---|
| मैनिफ़ेस्ट | [mod-apache2/module.json](../mod-apache2/module.json) | id, संस्करण, न्यूनतम कोर, entry, पढ़ने के पाथ, सेटिंग्स (कोई सेटअप विकल्प नहीं) | — | रजिस्ट्री, वेब, `manage.py` |
| Apache मॉड्यूल | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: हुक, की गई कार्रवाई, गंभीरता, डिटेक्शन, नियम फ़ंक्शन, संवर्धन, स्वास्थ्य | correlate, discovery, doctor, modsec, parsers; कोर `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | कलेक्टर, वेब, `manage.py` |
| डिस्कवरी | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (कॉन्फ़िगरेशन पार्सर), स्रोत और छोड़े गए लॉग, DocumentRoot | logformat (`dKnownFormats`) | module, doctor |
| डॉक्टर | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | आवश्यकता जाँच; लॉग का विवरण देता है (फ़ॉर्मेट, ऑडिट लॉग, मास्किंग), उन्हें बदलने का प्रस्ताव दिए बिना | discovery | module |
| access फ़ॉर्मेट | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` से रेगुलर एक्सप्रेशन, समय से UTC, अनुरोध पंक्ति | कोर `timeutil` | parsers, discovery |
| पार्सर | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, नेटिव, कॉन्करेंट), `AuditFramer`, `fAuditDisplay` | logformat, modsec; कोर `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | संदेश, श्रेणियाँ, CRS रेंज, स्कोर, इंटरसेप्शन | — | parsers, module |
| सहसंबंध | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, उसके बिना जोड़ी बनाना (`mPair`), विंडो, वॉटरमार्क | कोर `timeutil` | module (कलेक्टर) |
| गंभीरता तालिका | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | ModSecurity डिटेक्शन की गंभीरताएँ | — | module (`fLoadSeverityTable`) |
| नियम | [mod-apache2/rules/](../mod-apache2/rules/) | छह YAML नियम | कोर नियम इंजन, `mIsNewPhp` | कलेक्टर (`RulesEngine`), वेब (`fRules`) |
| टेक्स्ट | [mod-apache2/locales/](../mod-apache2/locales/) | नाम, सारांश, सेटिंग्स के लेबल और सहायता, विकल्प | — | वेब |
| privesc: मैनिफ़ेस्ट | [mod-privesc/module.json](../mod-privesc/module.json) | id, संस्करण, न्यूनतम कोर, entry, पढ़ने के पाथ, 13 सेटिंग्स (कोई सेटअप विकल्प नहीं) | — | रजिस्ट्री, वेब, `manage.py` |
| privesc: मॉड्यूल | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: हुक, दोनों स्रोतों के इवेंट, ऑडिट रिकॉर्ड का वर्गीकरण (संवेदनशील पाथ, प्रति आर्किटेक्चर सिस्टम कॉल), फ़्लैग, नियमों के डिटेक्शन, संवर्धन, स्वास्थ्य, स्कैन परिणाम | commands, correlate, discovery, doctor, parsers, surface; कोर `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | कलेक्टर, वेब, `manage.py` |
| privesc: डिस्कवरी | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | स्रोत, कंटेनर, auditd, snoopy, syslog, हर लॉग पढ़ा जा सकता है या नहीं, संस्करण 1.0.0 द्वारा छोड़ी गई फ़ाइलें, `Accounts` (उपयोगकर्ता, ग्रुप, खाते का प्रकार) | — | module, doctor |
| privesc: पार्सर | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | ऑडिट रिकॉर्ड (हेक्साडेसिमल, `msg='...'`, समृद्ध), syslog पंक्तियाँ (अपने सामान्य फ़ॉर्मेट में snoopy, sudo, su, pkexec, doas, pam, sshd), कमांड लाइनों की मास्किंग | कोर `masking`, `timeutil` | module |
| privesc: सहसंबंध | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | सीरियल के आधार पर ऑडिट रिकॉर्ड (EOE, यूज़र-स्पेस रिकॉर्ड, 2 s); syslog पंक्तियाँ तुरंत | — | module (कलेक्टर) |
| privesc: कमांड | [mod-privesc/commands.py](../mod-privesc/commands.py) | टोही टोकन, सेवा खाते का प्रोग्राम, शेल, इंटरप्रेटर, डाउनलोडर, प्रवेश के रास्ते, कंपाइलर; `SessionTracker` | कोर `timeutil` | module |
| privesc: अटैक सरफ़ेस | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, कैपेबिलिटी), GTFOBins, लिखने योग्य संवेदनशील फ़ाइलें, विशेषाधिकार प्राप्त ग्रुप | — | module, doctor |
| privesc: डॉक्टर | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | auditd, उसके लॉग और उसके नियमों ने क्या रिकॉर्ड किया, syslog, snoopy, मॉड्यूल क्या देखता है, संस्करण 1.0.0 की फ़ाइलें और सरफ़ेस का विवरण देता है (समाधान: केवल पैकेज और पढ़ने की अनुमति); आवश्यकता `command_source` (कोई भी पढ़ने योग्य स्रोत) | discovery, surface; कोर `timeutil` | module |
| privesc: नियम | [mod-privesc/rules/](../mod-privesc/rules/) | 35 YAML नियम | कोर नियम इंजन | कलेक्टर (`RulesEngine`), वेब (`fRules`) |
| privesc: गंभीरता तालिका | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | मॉड्यूल द्वारा बनाए गए डिटेक्शन की गंभीरताएँ (स्कैन, संवेदनशील फ़ाइलें) | — | module (`fLoadSeverityTable`) |
| privesc: टेक्स्ट | [mod-privesc/locales/](../mod-privesc/locales/) | नाम, सारांश, सेटिंग्स के लेबल और सहायता, विकल्प | — | वेब |
| कोर: इंटरफ़ेस | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | रजिस्ट्री | मॉड्यूल |
| कोर: रजिस्ट्री | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | मॉड्यूल ढूँढना, जाँचना और लोड करना; सेटिंग्स के डिफ़ॉल्ट और सत्यापन | `config` | कलेक्टर, वेब, `manage.py`, `backend/core/catalog.py` |
| कोर: वेब | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | मॉड्यूल पेज (इंस्टॉल किए गए, इंस्टॉल योग्य, किसी एक मॉड्यूल का पेज) और API | रजिस्ट्री, कैटलॉग, नियम | ब्राउज़र |
| कोर: कैटलॉग | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | रिपॉज़िटरी का डाउनलोड और सुरक्षित अनपैकिंग, हर मॉड्यूल की कार्रवाई (`install`, `update`, `incompatible`, `invalid`...) और `newer` के साथ सूची, एटॉमिक इंस्टॉलेशन या अपडेट (`previous`, `access_changed`), अनइंस्टॉलेशन, root के लिए कमांड: मॉड्यूल › इंस्टॉल योग्य और मॉड्यूल › इंस्टॉल किए गए के **अपडेट करें** / **अनइंस्टॉल करें**, मॉड्यूल इंस्टॉल करने का एकमात्र तरीका | रजिस्ट्री | वेब |

<a id="symbols"></a>
## 3. मुख्य सिंबल

| सिंबल | फ़ाइल:पंक्ति | यह क्या करता है |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | apache2 मॉड्यूल (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | बिल्ट-इन डिफ़ॉल्ट के ऊपर `severity.yaml` |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | कॉन्फ़िगरेशन पार्स करता है, स्रोत, छोड़े गए लॉग, DocumentRoot |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | विसंगति थ्रेशोल्ड: सेटिंग, CRS, या 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | स्रोत के प्रकार के अनुसार यूनिट से रिकॉर्ड |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | ट्रांज़ैक्शन से इवेंट: फ़ील्ड, की गई कार्रवाई, स्कोर, डिटेक्शन |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Host हेडर या ModSecurity hostname से वह vhost जो Apache ने चुना (जो `%v` लॉग करता है) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | SOC को जाने वाली चीज़ की गंभीरता, नियम का नाम, विवरण और ब्योरे |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | YAML नियम के सिग्नल से डिटेक्शन |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | नियम फ़ंक्शन `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | अलर्ट के लिए IP का संदर्भ (पिछला घंटा) |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity अनलोड या Off; असली क्लाइंट IP नहीं |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | अनुरोध कार्ड के लिए हेडर और बॉडी |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache और ModSecurity 2: मॉड्यूल को चालू किए जाने से पहले क्या चाहिए |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Apache कॉन्फ़िगरेशन का पार्सर |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | पढ़े गए डायरेक्टिव (लॉग, vhost, मॉड्यूल, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | किसी अनुरोध का vhost, उसके Host हेडर और लोकल पते और पोर्ट से, जैसे Apache उसे चुनता है |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | स्थिर स्रोत कुंजी; पढ़े जाने वाले और छोड़े गए स्रोत |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | आवश्यकता जाँच `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | क्या किसी access फ़ॉर्मेट को `UNIQUE_ID` के बिना जोड़ा जा सकता है (क्लाइंट IP, समय, अनुरोध पंक्ति, स्टेटस) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | डॉक्टर की जाँचें `apache_config` और `modsecurity` या, Apache के बिना, दोनों त्रुटि के रूप में, उन्हें इंस्टॉल करने वाले कमांड के साथ |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` से रेगुलर एक्सप्रेशन; ज्ञात उपनाम |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | access.log पंक्ति से रिकॉर्ड |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | error.log पंक्ति: ModSecurity, डेटाबेस, PHP, क्रैश |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | कई पंक्तियों में फैले नेटिव रिकॉर्ड; सुरक्षित कमिट स्थिति |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | JSON या नेटिव ऑडिट रिकॉर्ड; मास्किंग, कच्चा और इंडेक्स किया गया टेक्स्ट |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | सहेजे गए रिकॉर्ड का कार्ड; कॉन्करेंट एंट्री की फ़ाइल |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | एक ModSecurity संदेश; नियम, श्रेणियाँ, स्कोर, थ्रेशोल्ड, इंटरसेप्शन |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | privesc मॉड्यूल (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | स्रोत के अनुसार ट्रांज़ैक्शन से इवेंट; `ignored`; खाली फ़ील्ड हटा दिए जाते हैं (`fCleanFields` 0 रखता है) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | सत्र की टोही, शेल द्वारा चलाया गया डाउनलोड, `/tmp` में कंपाइल, हाल के कमांड, सेवा खाते का नया प्रोग्राम |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | प्रकार के अनुसार ऑडिट ट्रांज़ैक्शन; चलाए गए प्रोग्राम (`suid_escape`, `root_without_door`, `parent_interpreter`, कैपेबिलिटी); लॉगिन, प्रवेश के रास्ते और विफलताएँ |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | कोई भी अन्य सिस्टम कॉल, उसके नाम, आर्ग्युमेंट और पाथ के आधार पर: `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) या `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | सिस्टम कॉल का नाम (समृद्ध नाम, या आर्किटेक्चर के अनुसार संख्या); संवेदनशील पाथ का समूह (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, लॉगिन |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | किसी संवेदनशील फ़ाइल को लिखने वाला, या कोई ज्ञात पूर्वज, खाता या पैकेज टूल है |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | नियम के सिग्नल से डिटेक्शन; अलर्ट के लिए सत्र का संदर्भ |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | सहेजे गए सत्र, रुका हुआ auditd, संवेदनशील फ़ाइलें, शुरू किया गया स्कैन; नए setuid प्रोग्राम और कैपेबिलिटी |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | स्रोत, छोड़े गए स्रोत और डॉक्टर के लिए जानकारी; कोई लॉग पढ़ा जा सकता है या नहीं; संस्करण 1.0.0 द्वारा छोड़ी गई फ़ाइलें |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | कंटेनर का प्रकार (root के बिना); चल रहे auditd का pid |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | uid के नाम, ग्रुप, `UID_MIN`, खाते का प्रकार (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | दोनों स्रोतों के रिकॉर्ड |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | कमांड लाइनों के पासवर्ड, फिर कोर का मास्कर |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | सीरियल के आधार पर ऑडिट रिकॉर्ड; बाकी तुरंत |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | किसी कमांड का टोही टोकन; सेवा खाते का प्रोग्राम; टाइप किए गए कमांड के शब्द |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | सत्र (शुरुआत, IP, प्रवेश का रास्ता, टोही, अंतिम कमांड), प्रोसेस, डाउनलोड; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | एक थ्रेड में setuid, setgid और कैपेबिलिटी का स्कैन; दूसरों द्वारा लिखने योग्य संवेदनशील फ़ाइलें |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | डॉक्टर की जाँचें (विवरण; समाधान केवल पैकेज और पढ़ने की अनुमति के लिए); आवश्यकता `command_source`: कोई भी पढ़ने योग्य स्रोत |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | मॉड्यूल का इंटरफ़ेस; प्रति यूनिट एक पंक्ति |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | `module.json` जाँचता है, टेक्स्ट पढ़ता है |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | इंस्टॉल किए गए मॉड्यूल (`/opt/localsiem/modules/*`); इंस्टेंस और त्रुटियाँ |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | नेमस्पेस पैकेज `localsiem_modules`; entry का इम्पोर्ट और जाँच |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | सहेजे गए मानों के नीचे डिफ़ॉल्ट; जो सहेजा जाता है उसका सत्यापन |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`; `POST /api/admin/module-catalog/{name}` (इंस्टॉल या अपडेट; अपनी आवश्यकताओं के बिना पहली इंस्टॉलेशन बंद स्थिति में होती है: `fFirstInstallation`); `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | इंस्टॉल की गई कॉपी के बगल में किसी मॉड्यूल को इंस्टॉल या अपडेट करता है और नाम बदलकर उन्हें आपस में बदल देता है (`previous`, `access_changed`); `installed`, `newer` और उनकी कार्रवाई के साथ रिपॉज़िटरी के मॉड्यूल |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | किसी मॉड्यूल को अनइंस्टॉल करता है (नाम बदलना और हटाना); root के लिए कमांड (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | इंस्टॉल योग्य खंड (केवल वे मॉड्यूल जो इंस्टॉल नहीं हैं, **इंस्टॉल करें** और उसका डायलॉग); इंस्टॉल किए गए की किसी पंक्ति पर नए संस्करण की सूचना; **अपडेट करें** (पुष्टि, वही `POST`, डायलॉग केवल `access_changed` के साथ या जब कलेक्टर ने जवाब न दिया हो) |

<a id="flows"></a>
## 4. मुख्य कॉल पाथ

**कलेक्टर की शुरुआत → रजिस्ट्री → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = फ़ोल्डर, entry, सेटिंग्स, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, `Module` का सबक्लास, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, ओवरराइड `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`; हर स्रोत के लिए एक `FileTailer` और `mCreateFramer`) → लंबित रिकॉर्ड वापस कोरिलेटर में → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → स्थिति `apache2.doctor`)।

**पढ़ी गई एक पंक्ति → डिटेक्शन**

1. `Collector.mReadSources` → `FileTailer.mPoll` → फ़्रेमर `mFeed` (`LineFramer`, या `AuditFramer` जिसका `mSafeCommit` अधूरे रिकॉर्ड से पहले की स्थिति रखता है) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, या `fReadConcurrentEntry` + `fParseAuditRecord` और `mObserveAudit`) → रिकॉर्ड और स्थितियाँ एक ही ट्रांज़ैक्शन में सहेजी जाती हैं → `Correlator.mAdd`।
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, की गई कार्रवाई, `mAssess`, 2xx `.php` के लिए `mPathFirstSeen`) → `RulesEngine.mEvaluate` (YAML नियम; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → हर डिटेक्शन के लिए `mDetect` और हर सिग्नल के लिए `mDetectionFromSignal` → `Grouper.mAdd`।
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → SOC कतार।

**व्यवस्थापक सेटिंग्स सहेजता है → कलेक्टर रीलोड**

`modules.js fBuildSettings` (सबमिट) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` या `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → कलेक्टर सॉकेट `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`)। स्विच इसी तरह `{enabled}` भेजता है (चालू करते समय: जब तक मॉड्यूल की कोई आवश्यकता अधूरी है, 422 `requirements_missing`) और नियम तालिका `{rules}` भेजती है (`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` या `first_threshold`, `window`)। अगर सॉकेट जवाब नहीं देता, तो भी कलेक्टर अपने अगले चक्र में नया `settings.json` देख लेता है।

**वेब से मॉड्यूल इंस्टॉल करना** (मॉड्यूल इंस्टॉल करने का एकमात्र तरीका)

`modules.js fCatalogPanel` (मॉड्यूल › इंस्टॉल योग्य) → **रिपॉज़िटरी जाँचें** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: रिपॉज़िटरी का हर फ़ोल्डर `mod-<name>/`, `installed`, `newer` और `action` के साथ) → केवल `installed` null वाले आइटम सूचीबद्ध होते हैं → **आवश्यकताएँ** (`fShowRequirements` → `fRequirementsBody`: सर्वर के सिस्टम के लिए मॉड्यूल का `install_requirements`, जवाब का `system`, root के रूप में और `sudo` के साथ, और उसके locales के नोट `install_requirements.*`; कुछ भी चलाया नहीं जाता) → **इंस्टॉल करें** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` null, `access_changed` true) → `WebContext.mReloadModules` → `fFirstInstallation` (कोई आवश्यकता अधूरी और `modules.<name>.enabled` कभी सहेजा नहीं गया: `enabled = false`) → कलेक्टर `restart` → `fCreateModules` मॉड्यूल लोड करता है → डायलॉग «<मॉड्यूल> इंस्टॉल किया गया» root के लिए कमांड दिखाता है (`fRootCommand`: `manage.py setup-modules`, `read_paths` को पढ़ने की अनुमति) या, अगर कोई आवश्यकता अधूरी है, तो वे जाँचें जो पूरी नहीं हुईं।

**वेब से मॉड्यूल अपडेट करना**

मॉड्यूल › इंस्टॉल किए गए खुलता है → `fCheckRepository` → `modules.js` का `fFetchCatalog(false)` (`GET /api/admin/module-catalog` का अंतिम जवाब, 600 s तक दोबारा उपयोग किया जाता है; किसी मॉड्यूल को इंस्टॉल, अपडेट या अनइंस्टॉल करने पर वह भुला दिया जाता है) → `newer` और `action` `update` या `incompatible` वाले आइटम → पंक्ति पर `fUpdateNotice` (केवल तब तक जब तक इंस्टॉल किया गया संस्करण वही है जिससे तुलना की गई) → **अपडेट करें** → `fUpdate` → पुष्टि → `POST /api/admin/module-catalog/{name}` (वही `fInstallFromCatalog` → `fInstall`: नई कॉपी इंस्टॉल की गई कॉपी की जगह लेती है, `previous` पुराना संस्करण है, `access_changed` बताता है कि `read_paths` बदला या नहीं; कोई `fFirstInstallation` नहीं, इसलिए `enabled` और सेटिंग्स बनी रहती हैं) → कलेक्टर `restart` → डायलॉग केवल तब जब `access_changed` (root के लिए कमांड) हो या कलेक्टर ने जवाब न दिया हो।

**वेब से मॉड्यूल अनइंस्टॉल करना**

**अनइंस्टॉल करें** (मॉड्यूल › इंस्टॉल किए गए की पंक्ति या मॉड्यूल का पेज) → `fUninstallButton` → पुष्टि → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → `/opt/localsiem/modules/<name>/` को नाम बदलकर एक स्टेजिंग फ़ोल्डर में ले जाया जाता है, जहाँ उसे हटाया जाता है) → `WebContext.mReloadModules` → कलेक्टर `restart`। `modules.<name>` और उसके नियमों के ओवरराइड `settings.json` में बने रहते हैं, और root द्वारा दी गई पढ़ने की अनुमति भी बनी रहती है।

**Apache या ModSecurity के बिना पहली इंस्टॉलेशन → पुनः कॉन्फ़िगर करें** (localSIEM 2.2.0 या उससे नया)

वेब में इंस्टॉल करें → `fInstall` (पहली इंस्टॉलेशन) → इंस्टॉल की गई कॉपी से बनाया गया मॉड्यूल (स्टोरेज `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (Apache के साथ: `fRunDoctor` → `apache_config`, `modsecurity`; उसके बिना, दोनों त्रुटि के रूप में) → एक त्रुटि और `modules.apache2.enabled` कभी सहेजा नहीं गया → `modules.apache2.enabled = false` («बंद», स्विच लॉक, पेज पर आवश्यकताएँ)। बाद में, Apache और ModSecurity इंस्टॉल होने पर: **पुनः कॉन्फ़िगर करें** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → पूरी → स्विच अनलॉक और root कमांड (`read_paths` को पढ़ने की अनुमति; apache2 का कोई `setup_option` नहीं है) → व्यवस्थापक मॉड्यूल चालू करता है → कलेक्टर रीलोड → `mDiscover` → `mPublishDoctor`।

**वेब से अनुरोध कार्ड और डॉक्टर**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`। **फिर से डिस्कवर करें और डॉक्टर चलाएँ** → `POST /api/admin/modules/apache2/doctor` → कलेक्टर `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`।

**स्वास्थ्य**

`Collector.mCycle` (हर 60 s) → `mCheckHealth` → `ApacheModule.mHealth` (अधिकतम हर 300 s; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`।

**privesc: चलाया गया एक कमांड → डिटेक्शन**

1. auditd एक ही सीरियल के साथ `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE` लिखता है → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (हेक्साडेसिमल डिकोड किया गया, `fMaskCommand`, कच्चा टेक्स्ट फिर से बनाया गया) → `Correlator.mAdd` (कुंजी `audit:<time>:<serial>`, `EOE` पर देय)।
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `SessionTracker.mGet` से `root_without_door`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`; `fCompileInTemporary`; `mCommand`; सेवा खाता: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`।
3. `RulesEngine.mEvaluate` (`mod-privesc/rules/` के नियम) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (सत्र: अंतिम 20 कमांड) → `fBuildAlert` → SOC कतार।

snoopy के साथ, वही कमांड syslog पंक्ति के रूप में भी आता है: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (सत्र `snoopy:<uid>:<sid>`)।

**privesc: सत्र और प्रवेश के रास्ते**

`LOGIN` (auid और ses असाइन किए गए) या sshd या login का `USER_LOGIN`/`USER_START` → `mAuditUser` → `SessionTracker.mStart` (उपयोगकर्ता, SSH पता)। sudo, su, pkexec, doas, run0 या systemd का सफल परिणाम वाला `USER_START`/`USER_CMD` → `SessionTracker.mDoor`। उस सत्र का बाद का `EXECVE` जिसमें uid और euid 0 हों → `root_without_door` केवल तब जब शुरुआत देखी गई हो और कोई प्रवेश का रास्ता न रहा हो। `mHealth` `SessionTracker.mExport` को `privesc.sessions` में अधिकतम हर मिनट सहेजता है; `mStart` उसे लोड करता है (`mImport`)।

**privesc: सर्वर के ऑडिट नियमों द्वारा रिकॉर्ड किया गया सिस्टम कॉल**

auditd `SYSCALL` (`arch`, `syscall`, `a0`-`a3`, `success`, `exit` और उसे रिकॉर्ड करने वाले किसी भी नियम की कुंजी के साथ), `CWD`, `PATH`... लिखता है → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → `EACCES`/`EPERM` और लॉगिन uid के साथ विफल open/exec/truncate → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; मोड में `S_ISUID`/`S_ISGID` के साथ `chmod`/`fchmod`/`fchmodat`/`fchmodat2`, फ़ोल्डर पर नहीं → `chmod` (`mWriterAllowed`); `lSensitivePaths` के किसी पाथ में बदलाव (`sChangeSyscalls` का कोई कॉल, लिखने वाले फ़्लैग के साथ open, `CREATE`/`DELETE` वाला `PATH`) → `sensitive_group` (`dKeyHints` केवल रिज़ॉल्व होने योग्य पाथ के बिना) और `mWriterAllowed` के साथ `file`; कुछ और → `syscall`। `mBuildEvent` डॉक्टर के लिए हर प्रकार का समय याद रखता है (`dRuntime["audit_kinds"]`)।

**privesc: अटैक सरफ़ेस का स्कैन**

`mHealth` (हर 300 s, शुरुआत के पाँच मिनट बाद, हर `surface_scan_hours`) → `SurfaceScanner.mStart` (थ्रेड: `scan_paths` का `os.walk`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → अगला `mHealth` → `mSurfaceResult` (`SurfaceScanner.mTake`, `privesc.surface` के विरुद्ध: नया setuid/setgid → `new_setuid*`, नई कैपेबिलिटी → `new_capabilities`) → `mModuleDetection` → `mDetect`; परिणाम `privesc.surface` में सहेजा जाता है और `fSurfaceChecks` द्वारा दिखाया जाता है। हर घंटे `fCheckSensitiveFiles` → `sensitive_file_writable`।

**privesc: आवश्यकताएँ और पुनः कॉन्फ़िगर करें**

`fInstall` (पहली इंस्टॉलेशन) या **पुनः कॉन्फ़िगर करें** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`; `fSyslogPath` → `fReadState` जब तक `syslog_mode` `never` न हो; `fSnoopyInstalled`) → एक पढ़ने योग्य स्रोत: `command_source` ok (न पढ़े जा सकने वाले चेतावनी के रूप में); ऐसा स्रोत जो मौजूद है लेकिन पढ़ा नहीं जा सकता: पढ़ने की अनुमति (`manage.py setup-modules` या `setfacl`) के साथ `audit_log` या `syslog` त्रुटि; कुछ नहीं: इंस्टॉल करने वाले पैकेज के साथ `command_source` त्रुटि। जब तक कोई त्रुटि है, मॉड्यूल बंद रहता है।

<a id="routes"></a>
## 5. एंट्री पॉइंट

| एंट्री पॉइंट | हैंडलर | फ़ाइल |
|---|---|---|
| `module.json` का `"entry": "module:ApacheModule"` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (कोर) | [mod-apache2/rules/](../mod-apache2/rules/) |
| नियम फ़ंक्शन `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| वेब: मॉड्यूल › इंस्टॉल योग्य, मॉड्यूल इंस्टॉल करने का एकमात्र तरीका (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`; व्यू `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| वेब: मॉड्यूल › इंस्टॉल किए गए की किसी पंक्ति पर **अपडेट करें** (वही `GET`, ब्राउज़र द्वारा 10 मिनट तक दोबारा उपयोग किया जाता है, और वही `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| वेब: **अनइंस्टॉल करें** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `module.json` का `read_paths` | `manage.py read-paths`: वे फ़ोल्डर जिन्हें localSIEM, root के रूप में, `localsiem` को पढ़ने देता है (`fRootCommand` का कमांड) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | हर मैनिफ़ेस्ट का `read_paths` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (`installed/` पर 302), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`; व्यू `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (पुराना `/admin/dashboard/modules/apache2/` इस पर 301 देता है) | `fAdminModule` (301: `fAdminModulesSection`); व्यू `LocalsiemViews.module` | वही फ़ाइलें |
| `GET /api/modules` | `fModules` (साइन इन किए हुए सभी के लिए स्थिति) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (सेटिंग्स, मान, स्रोत, डॉक्टर, नियम) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**पुनः कॉन्फ़िगर करें**, localSIEM 2.2.0 या उससे नया) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `mod-privesc/module.json` का `"entry": "module:PrivescModule"` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (कोर) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| सर्वर के नियमों के ऑडिट रिकॉर्ड (कोई भी कुंजी) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. प्रभाव विश्लेषण

| घटक | बदलने पर क्या प्रभावित होता है |
|---|---|
| `module.json` `id` | `mod-` के बिना फ़ोल्डर के नाम (इंस्टॉल किए गए फ़ोल्डर का नाम) और `vName` के बराबर होना चाहिए। यह सेटिंग्स (`modules.<id>`) और स्थिति (`<id>.doctor`) की कुंजी है और हर इवेंट का `module` है: नाम बदलने से सहेजी गई सेटिंग्स खो जाती हैं और इतिहास बँट जाता है। |
| `module.json` `core` | इसे इंस्टॉल किए गए localSIEM से ऊपर बढ़ाने पर मॉड्यूल लोड होना बंद हो जाता है (स्थिति «त्रुटि»); रिपॉज़िटरी में, इंस्टॉल योग्य «localSIEM X या उससे नया चाहिए» दिखाता है और इंस्टॉल किए गए नया संस्करण **अपडेट करें** के बिना दिखाता है। |
| `module.json` `entry` | किसी `Module` सबक्लास की ओर इशारा करना चाहिए; गलत मान लोड त्रुटि है। |
| `module.json` `default_enabled` | उन सर्वरों पर चालू/बंद जहाँ व्यवस्थापक ने कभी निर्णय नहीं लिया (अगर पहली इंस्टॉलेशन पर इसकी आवश्यकताएँ अधूरी हैं, तो बंद)। |
| `module.json` `read_paths` | localSIEM root के रूप में जो पढ़ने की अनुमति देता है (`manage.py read-paths`): कोई फ़ोल्डर छूटने का अर्थ है डॉक्टर और स्थिति में अनुमति त्रुटियाँ। नए संस्करण में बदलाव होने पर वेब **अपडेट करें** के बाद root के लिए कमांड फिर से दिखाता है (`access_changed`)। |
| `module.json` `install_requirements` | इंस्टॉल योग्य का आवश्यकताएँ डायलॉग (`modules.js` का `fRequirementsBody`)। गलत मान (`debian` और `alpine` के अलावा कोई सिस्टम, खाली सूची या 20 से अधिक कमांड, शेल ऑपरेटर या लाइन ब्रेक वाला कमांड) मॉड्यूल को अमान्य बना देता है (कोर का `fCheckInstallRequirements`): वह न इंस्टॉल होता है न लोड। |
| `module.json` `setup_option` | कुछ नहीं: कोर इसे नज़रअंदाज़ करता है (apache2 1.3.0 और privesc 1.1.0 के बाद से किसी मॉड्यूल में यह नहीं है)। |
| रिपॉज़िटरी के शीर्ष पर `module.json` वाले फ़ोल्डर `mod-<name>/` | वेब का कैटलॉग जो सूचीबद्ध करता है, मॉड्यूल `<name>` के रूप में: इंस्टॉल योग्य वे दिखाता है जो अभी इंस्टॉल नहीं हैं (नए कोर की ज़रूरत वाला «localSIEM X या उससे नया चाहिए» के रूप में, अमान्य वाला «रिपॉज़िटरी का मॉड्यूल मान्य नहीं है» के रूप में), और इंस्टॉल किए गए से ऊँचा `version` इंस्टॉल किए गए में **अपडेट करें** का विकल्प देता है। |
| `module.json` `settings` | फ़ॉर्म, सत्यापन और डिफ़ॉल्ट। नया डिफ़ॉल्ट उन सर्वरों पर लागू होता है जिन्होंने वह कुंजी कभी नहीं सहेजी। सहेजे गए मान माइग्रेट नहीं होते: नाम बदली गई कुंजी अपना मान खो देती है और नए प्रकार वाला पुराना मान मॉड्यूल तक वैसा ही पहुँचता है जैसा सहेजा गया था। |
| `locales/*.json` | केवल वेब के टेक्स्ट; गुम टेक्स्ट en-US पर, फिर कुंजी पर लौट आता है। |
| `parsers.py` (रिकॉर्ड dict) | सहसंबंध (`correlation`, `fields.client_ip`, `fields.path`), अनुरोध कार्ड, पूर्ण-टेक्स्ट इंडेक्स (`search`, `raw`), पार्स न हुई पंक्तियों का स्वास्थ्य और निजता। |
| `logformat.py` `dKnownFormats` | हर access लॉग की पार्सिंग; `localsiem_combined` उन सर्वरों के लिए बना रहता है जो इसे पहले से लिखते हैं (मॉड्यूल के संस्करण 1.2.0 और उससे पहले के संस्करणों ने इसे जोड़ा था): इसकी परिभाषा न बदलें। |
| `correlate.py` | प्रति अनुरोध एक इवेंट; कोर `mAdd`, `mDue(pNow, pForce, pWatermark)` और `mPendingCount` कॉल करता है, और रीस्टार्ट के बाद भी लंबित रिकॉर्ड वापस देता है। `UNIQUE_ID` के बिना यह रिकॉर्ड को उनके `client_ip`, `method`, `uri`, `status` और `path` फ़ील्ड से जोड़ता है: जो पार्सर इन्हें अलग तरह से लिखता है, वह जोड़ी बनाना तोड़ देता है। ऑडिट रिकॉर्ड के इंतज़ार (`mWaitsForAudit`) के लिए error.log पंक्तियों का `modsecurity` फ़ील्ड और स्रोत `audit` के रिकॉर्ड चाहिए। |
| `modsec.py` (श्रेणियाँ, लेबल, रेंज) | अलर्ट नियमों के नाम (SOC के आँकड़े इन्हीं के आधार पर समूहित होते हैं: इन्हें स्थिर रखें), ग्रुपिंग कुंजियाँ, `category:` खोजें। |
| `ApacheModule.mBuildEvent` (इवेंट dict) | events टेबल के कॉलम, YAML नियमों द्वारा पढ़े जाने वाले फ़ील्ड (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), खोजें और CSV एक्सपोर्ट। |
| `ApacheModule.mAssess` | SOC तक क्या पहुँचता है और उसकी गंभीरता; कोर की `GenericAlert` सीमाएँ (नियम 300, विवरण 10 000 कैरेक्टर)। |
| `severity.yaml` | हर ModSecurity डिटेक्शन की गंभीरता; गंभीरता ग्रुपिंग कुंजी का हिस्सा है, इसलिए बदलाव से नए ग्रुप शुरू होते हैं। |
| `rules/*.yaml` | `id` ओवरराइड (`rules.<id>`) और खोजों (`rule:localsiem:<id>`) की कुंजी है: इसे स्थिर रखें। फ़ील्ड इवेंट में मौजूद होने चाहिए; `{function: ...}` के लिए `mRuleFunctions` चाहिए। |
| `discovery.py` | कौन-से लॉग पढ़े जाते हैं; `fSourceKey` सहेजी गई स्थितियों की कुंजी है (नई कुंजी फ़ाइल को नया स्रोत बना देती है, उसकी सहेजी गई स्थिति के बिना); वेब शेल नियम के DocumentRoot; डॉक्टर। |
| `doctor.py` | वेब और `manage.py` का डॉक्टर और क्लाइंट को दिखाए जाने वाले संकेत। केवल उन चीज़ों की जाँचें जो लॉग नहीं हैं (ModSecurity, CRS, `SecRuleEngine`, `mod_unique_id`, अनुमतियाँ) `fix` रख सकती हैं; लॉग से जुड़ी जाँचें केवल उनका विवरण देती हैं। |
| `mRequirements` / `fRequirementChecks` | मॉड्यूल चालू किया जा सकता है या नहीं, Apache या ModSecurity के बिना पहली इंस्टॉलेशन के बाद स्थिति «बंद», वेब द्वारा दिखाई जाने वाली आवश्यकताएँ और **पुनः कॉन्फ़िगर करें**। ये वेब में और `manage.py` में स्टोरेज के बिना चलते हैं और हर कॉल पर Apache कॉन्फ़िगरेशन पार्स करते हैं: इन्हें स्टोरेज से और किसी भी धीमी चीज़ से दूर रखें, और ids `apache_config` और `modsecurity` को स्थिर रखें। |
| privesc: इवेंट कॉलम और फ़ील्ड (`mBuildEvent`, `mAnalyzeCommand`) | YAML नियम इन्हें नाम से मिलाते हैं (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...): नाम बदला गया फ़ील्ड उसका उपयोग करने वाले नियमों को चुपचाप निष्क्रिय कर देता है। `vhost` उपयोगकर्ता है: अलर्ट की ग्रुपिंग कुंजी और `vhost:` खोजें इस पर निर्भर हैं। |
| privesc: `fReconToken` | टोही किसे माना जाता है और अलग-अलग कमांड कैसे पहचाने जाते हैं: कोई टोकन बदलने से बदल जाता है कि कोई सत्र कितनी जल्दी थ्रेशोल्ड तक पहुँचता है। |
| privesc: `SessionTracker` और प्रवेश के रास्ते (`sDoors`) | `root_without_door`: सूची से छूटा कोई रास्ता वैध root सत्रों को क्रिटिकल बना देता है; एक अतिरिक्त रास्ता कर्नेल एक्सप्लॉइट को छिपा देता है। `mExport`/`mImport` `privesc.sessions` का फ़ॉर्मेट है। |
| privesc: `parsers.py` | रिकॉर्ड के फ़ील्ड (`args`, `command`, `kind`, snoopy के `uid`/`euid`), पासवर्ड की मास्किंग और ऑडिट रिकॉर्ड का कच्चा टेक्स्ट; snoopy के वे फ़ॉर्मेट जिन्हें यह पढ़ता है (मॉड्यूल कभी `snoopy.ini` नहीं बदलता)। |
| privesc: ऑडिट रिकॉर्ड का वर्गीकरण (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | क्या `file`, `chmod`, `kmod`, `ptrace` और `denied` बनता है, और इसलिए नियम sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst और sensitive-denied; गलत syscall संख्या उस आर्किटेक्चर के रिकॉर्ड का गलत वर्गीकरण करती है। |
| privesc: `surface.py` | स्कैन की लागत (थ्रेड, सीमाएँ) और डॉक्टर तथा `mSurfaceResult` क्या रिपोर्ट करते हैं; `privesc.surface` इसका संदर्भ है। |
| privesc: `mRequirements` / `fRequirementChecks` | मॉड्यूल चालू किया जा सकता है या नहीं (कोई भी पढ़ने योग्य स्रोत), ऐसी पहली इंस्टॉलेशन के बाद स्थिति «बंद» जिसके लॉग `localsiem` अभी नहीं पढ़ सकता, और **पुनः कॉन्फ़िगर करें**; वेब और `manage.py` द्वारा स्टोरेज के बिना कॉल किया जाता है: इसे तेज़ और root के बिना रखें। ids `command_source`, `audit_log` और `syslog` बनाए रखें। |
| कोर इंटरफ़ेस (localSIEM का `backend/core/module.py`, `registry.py`) | हर मॉड्यूल: बदला हुआ हुक सिग्नेचर, नई आवश्यक मैनिफ़ेस्ट कुंजी या रिकॉर्ड और इवेंट का नया अनुबंध उन्हें तोड़ देता है; जब उन्हें नया localSIEM चाहिए, तो उनके `module.json` में `core` बढ़ाएँ। |

<a id="extensions"></a>
## 7. विस्तार बिंदु

### नया मॉड्यूल कैसे लिखें

1. **फ़ोल्डर**: इस प्रोजेक्ट की रूट में `mod-<name>/` बनाएँ; `<name>`, मॉड्यूल का नाम, `[a-z][a-z0-9_]{1,31}` से मेल खाता है। `mod-` प्रीफ़िक्स केवल फ़ोल्डर के लिए है: `module.json`, क्लास, विकल्प और टेक्स्ट `<name>` का उपयोग करते हैं। कोई `__init__.py` नहीं।
2. **`module.json`**, उदाहरण के लिए:

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

3. **टेक्स्ट**: localSIEM की 15 भाषाओं में से हर एक के लिए `locales/<language>.json`, जिसमें `name`, `summary` और हर सेटिंग का लेबल और सहायता हो। आवश्यकताओं के बारे में नोट `install_requirements` (`note`, हर सिस्टम के लिए, और `debian` और `alpine`) में जाते हैं, जो आवश्यकताएँ डायलॉग में दिखाए जाते हैं।
4. **कोड**: `module.py` जिसमें `Module` का एक सबक्लास हो जिसका `vName` id हो। इसे `mParse`, `mCreateCorrelator` और `mBuildEvent` लागू करने होंगे, और आमतौर पर `mDiscover`; बाकी हुक वैकल्पिक हैं (खंड 1)। अपनी फ़ाइलें रिलेटिव रूप से और कोर को `backend.core...` के रूप में इम्पोर्ट करें। इस रिपॉज़िटरी के दोनों मॉड्यूल पूरे उदाहरण हैं ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)); एक न्यूनतम खाका:

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # हर रिकॉर्ड अपने आप में एक इवेंट है, बिना इंतज़ार के।

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

5. **की गई कार्रवाई**: तय करें कि सेवा के लिए «पहले ही निपटाया गया» का क्या अर्थ है (उदाहरण के लिए, पहले से प्रतिबंधित IP) और उसके लिए `action` को `blocked` पर सेट करें; डिटेक्शन केवल उन इवेंट में जोड़ें जिन पर कोई कार्रवाई नहीं की गई।
6. **नियम**: `mod-<name>/rules/` में YAML फ़ाइलें, जिन्हें `mRulesPath` लौटाता है, और वे फ़ंक्शन जिन्हें वे `mRuleFunctions` में कॉल करते हैं।
7. **आवश्यकताएँ**: अगर मॉड्यूल को सर्वर पर सॉफ़्टवेयर चाहिए (जैसे apache2 को Apache और ModSecurity 2 चाहिए), तो `mRequirements()` से हर आवश्यकता के लिए एक जाँच लौटाएँ (`fCheck` का फ़ॉर्मेट: `status` `ok` या `error`, और `fix` में उसे इंस्टॉल करने वाला कमांड) और वह सॉफ़्टवेयर मॉड्यूल से कभी इंस्टॉल न करें: अपनी आवश्यकताओं के बिना मॉड्यूल बंद स्थिति में इंस्टॉल होता है। यह स्टोरेज के बिना चलता है, वेब में और `manage.py` में भी। `module.json` के `install_requirements` में वे कमांड भी घोषित करें जो वह सॉफ़्टवेयर Debian और Alpine पर इंस्टॉल करते हैं (प्रति पंक्ति एक कमांड, शेल ऑपरेटरों के बिना): वेब उन्हें मॉड्यूल › इंस्टॉल योग्य › आवश्यकताएँ में, जैसे हैं वैसे और आगे `sudo` लगाकर, मॉड्यूल इंस्टॉल होने से पहले दिखाता है।
8. **इंस्टॉल करना**: इसे इस रिपॉज़िटरी (ब्रांच `main`) में प्रकाशित करें; जब तक यह इंस्टॉल नहीं होता, यह localSIEM वेब के मॉड्यूल › इंस्टॉल योग्य में दिखता है, और **इंस्टॉल करें** फ़ोल्डर `mod-<name>/` को `/opt/localsiem/modules/<name>/` में कॉपी करता है और कलेक्टर को रीस्टार्ट करता है। इसके `read_paths` को पढ़ने की अनुमति के लिए root चाहिए: वेब कमांड (`manage.py setup-modules`) दिखाता है। मॉड्यूल का कोई सेटअप विकल्प नहीं होता: यह `/opt/localsiem` के बाहर कभी कुछ इंस्टॉल नहीं करता और न कुछ बदलता है, और क्लाइंट के लॉग में कभी नहीं लिखता, न उन्हें रोटेट या डिलीट करता है और न उनका फ़ॉर्मेट बदलता है; अगर कोई सर्वर अपने लॉग अपने तरीके से लिखता है, तो मॉड्यूल उसके अनुसार ढल जाता है, और सर्वर पर जो नहीं है वह एक आवश्यकता है। नया संस्करण प्रकाशित करने के लिए `version` बढ़ाएँ: मॉड्यूल › इंस्टॉल किए गए सूचना और **अपडेट करें** दिखाता है, जो सेटिंग्स और मॉड्यूल की चालू/बंद स्थिति बनाए रखता है और root के लिए कमांड फिर से केवल तभी दिखाता है जब `read_paths` बदला हो।
9. **दस्तावेज़ीकरण**: 15 भाषाओं में README, यह CODE और MANUAL अपडेट करें।

### apache2 मॉड्यूल में नियम कैसे जोड़ें

[mod-apache2/rules/](../mod-apache2/rules/) में एक YAML फ़ाइल बनाएँ (हर कुंजी और ऑपरेटर का विवरण [backend/core/rules.py](../../localSIEM/backend/core/rules.py) के शीर्ष पर है): `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` या `sequence`), शर्तें (`when`, या `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` और `search`। फ़ील्ड पहले इवेंट कॉलम में और फिर `fields` में खोजे जाते हैं। यह मॉड्यूल पेज की नियम तालिका में दिखता है और मॉड्यूल का नया संस्करण इंस्टॉल होते ही कलेक्टर इसे लोड कर लेता है: `module.json` में `version` बढ़ाएँ, उसे प्रकाशित करें और मॉड्यूल › इंस्टॉल किए गए में **अपडेट करें** दबाएँ।

### apache2 मॉड्यूल में सेटिंग कैसे जोड़ें

इसे [mod-apache2/module.json](../mod-apache2/module.json) के `settings` में उसके प्रकार और डिफ़ॉल्ट के साथ जोड़ें, इसका `label` और `help` [mod-apache2/locales/](../mod-apache2/locales/) की चार फ़ाइलों में जोड़ें, और इसे `self.mModuleSettings().get("<key>")` से पढ़ें। फ़ॉर्म, सत्यापन और रीलोड कोर से आते हैं।

### डॉक्टर जाँच कैसे जोड़ें या गंभीरता कैसे बदलें

एक जाँच `fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)) में एक `fCheck(id, status, title, detail, fix)` है; `id` को स्थिर रखें और `fix` में सटीक स्निपेट या कमांड रखें, केवल उन आवश्यकताओं के लिए जो लॉग नहीं हैं: क्लाइंट के लॉग से जुड़ी जाँच केवल उनका और localSIEM उनसे क्या पढ़ सकता है और क्या नहीं, इसका विवरण देती है, बिना `fix` के। ModSecurity डिटेक्शन की गंभीरताएँ [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) में बदली जाती हैं (`low`, `medium`, `high`, `critical`)।

### privesc मॉड्यूल में नियम कैसे जोड़ें

[mod-privesc/rules/](../mod-privesc/rules/) में Apache वाले नियमों की तरह एक YAML फ़ाइल बनाएँ। कॉलम (`method`, `uri`, `path`, `vhost`, `action`) और इवेंट के फ़ील्ड (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...) से मिलान करें, कभी ऑडिट नियम की कुंजी से नहीं; `ignored: {not: true}` जोड़ें ताकि नज़रअंदाज़ किए गए उपयोगकर्ता इसे कभी ट्रिगर न करें, और `action: none` जब केवल वही गिना जाए जो वास्तव में चला। अगर शर्त को स्थिति या लॉजिक चाहिए (एक ही सत्र का सीक्वेंस, किसी फ़ाइल की जाँच), तो `PrivescModule.mAnalyzeCommand` (हर स्रोत) में या `mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (एक स्रोत) में एक फ़्लैग की गणना करें और नियम से उसका मिलान करें।

### privesc मॉड्यूल में टोही कमांड, टूल या एक्सप्लॉइट कैसे जोड़ें

- टोही: प्रोग्राम को `sReconSimple` में जोड़ें, या `fReconToken` में एक शाखा जोड़ें जो हर प्रकार के सवाल के लिए एक टोकन लौटाए ([mod-privesc/commands.py](../mod-privesc/commands.py))। जो टोकन हर आर्ग्युमेंट के साथ बदलता है, वह गिनती को बढ़ा देता है।
- टूल और एक्सप्लॉइट: [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) या [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) की सूची में एक रेगुलर एक्सप्रेशन जोड़ें (केस-इनसेंसिटिव, कमांड लाइन से मिलाया जाता है); व्यवस्थापक इन्हें सेटिंग्स से भी जोड़ सकता है (`rules.<id>.lists`)।

### privesc मॉड्यूल में स्रोत या ऑडिट रिकॉर्ड का प्रकार कैसे जोड़ें

- संवेदनशील पाथ: इसे [mod-privesc/module.py](../mod-privesc/module.py) के `lSensitivePaths` में उसके समूह के साथ जोड़ें (या एक नया समूह और `sensitive_group` से मेल खाने वाला नियम)। सिस्टम कॉल का प्रकार: उसका नाम `mAuditSyscall` के सेट में और उसकी संख्या `dSyscallTables` की हर तालिका में जोड़ें। कभी ऑडिट नियम की कुंजी पर निर्भर न रहें (अधिक से अधिक उसे `dKeyHints` में जोड़ें) और कभी ऑडिट नियम इंस्टॉल न करें: सर्वर वही रिकॉर्ड करता है जो उसका व्यवस्थापक तय करता है, और डॉक्टर उसका विवरण देता है ([doctor.py](../mod-privesc/doctor.py) का `dAuditKinds`)।
- स्रोत: इसे `fDiscoverSources` से एक नए `kind` के साथ लौटाएँ, `mParse` में पार्स करें और `mBuildEvent` में इसके इवेंट दूसरों जैसे ही कॉलम और फ़ील्ड के साथ बनाएँ, ताकि नियम बिना बदलाव के काम करें।
