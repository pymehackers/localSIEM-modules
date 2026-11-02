# localSIEM-modules

यह README इन भाषाओं में भी उपलब्ध है:\
[de-DE](README.de-DE.md), [en-GB](README.en-GB.md), [en-US](../README.md), [es-AR](README.es-AR.md), [es-ES](README.es-ES.md), [fr-FR](README.fr-FR.md), [he-IL](README.he-IL.md), hi-IN, [it-IT](README.it-IT.md), [ja-JP](README.ja-JP.md), [ko-KR](README.ko-KR.md), [pt-BR](README.pt-BR.md), [pt-PT](README.pt-PT.md), [ru-RU](README.ru-RU.md), [zh-CN](README.zh-CN.md)

## यह क्या है

[localSIEM](https://github.com/PYMEHackers/localSIEM) के मॉड्यूल; localSIEM वह हल्का SIEM है जो उसी सर्वर पर चलता है जिसकी वह सुरक्षा करता है। हर मॉड्यूल उसे सर्वर की एक सेवा सिखाता है: उसके लॉग कहाँ हैं, उन्हें कैसे पढ़ना है और कौन से नियम लागू होते हैं। अभी दो मॉड्यूल हैं:

- **apache2** (Apache + ModSecurity): हर अनुरोध के access लॉग, error लॉग और ModSecurity के ऑडिट लॉग को जोड़ता है, ब्रूट फ़ोर्स, एन्यूमरेशन, संवेदनशील फ़ाइलों, वेब शेल और डेटाबेस त्रुटियों के नियमों के साथ।
- **privesc** (प्रिविलेज एस्केलेशन): सर्वर पर जो चलाया जाता है उस पर नज़र रखता है (auditd, sudo, su, pkexec, doas, snoopy) और root तक पहुँचने के चरणों की चेतावनी देता है।

कोई मॉड्यूल सर्वर पर कभी कुछ इंस्टॉल नहीं करता: वह उसी के साथ काम करता है जो सर्वर में पहले से है।

## स्क्रीनशॉट

![localSIEM में apache2 मॉड्यूल](https://raw.githubusercontent.com/PYMEHackers/localSIEM-modules/main/doc/screenshot.png)

## इंस्टॉलेशन

मॉड्यूल localSIEM के वेब इंटरफ़ेस से इंस्टॉल किए जाते हैं। पहले localSIEM को `root` के रूप में इंस्टॉल करें:

**Debian 13**:

```bash
curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-debian.sh | bash -s -- --install --allow-from 203.0.113.10
```

**Alpine Linux 3.24**:

```bash
apk add bash curl && curl -fsSL -H 'Accept: application/vnd.github.raw+json' https://api.github.com/repos/PYMEHackers/localSIEM/contents/deploy/install-update-reinstall-alpine.sh | bash -s -- --install --allow-from 203.0.113.10
```

`--allow-from`: वे IP जिन्हें वेब (`https://<server>:10443`) खोलने की अनुमति है।

फिर वेब इंटरफ़ेस में **मॉड्यूल › इंस्टॉल योग्य** खोलें, **रिपॉज़िटरी जाँचें** दबाएँ, **आवश्यकताएँ** देखें और मॉड्यूल पर **इंस्टॉल करें** दबाएँ।

## दस्तावेज़ पढ़ें

आगे देखें:

- [doc/MANUAL.hi-IN.md](MANUAL.hi-IN.md), हर मॉड्यूल को इंस्टॉल, सेट और इस्तेमाल करना सीखने के लिए।
- [doc/CODE.hi-IN.md](CODE.hi-IN.md), यह समझने के लिए कि वे कैसे बने हैं और नया मॉड्यूल कैसे लिखें (डेवलपरों और AI मॉडलों के लिए)।
