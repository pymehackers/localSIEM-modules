# Referência técnica do localSIEM-modules

Este CODE também está disponível em:\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), [pt-BR](CODE.pt-BR.md), pt-PT, [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## Índice

1. [Arquitetura e decisões de design](#architecture)
2. [Mapa de módulos](#modules)
3. [Símbolos principais](#symbols)
4. [Fluxos de chamadas principais](#flows)
5. [Pontos de entrada](#routes)
6. [Análise de impacto](#impact)
7. [Pontos de extensão](#extensions)

[Instalação](README.pt-PT.md) · [Manual de utilização](MANUAL.pt-PT.md) · [Referência técnica do localSIEM](../../localSIEM/doc/CODE.pt-PT.md)

<a id="architecture"></a>
## 1. Arquitetura e decisões de design

Este projeto contém os módulos instaláveis do localSIEM (projeto irmão `../localSIEM`). Não tem serviço nem instalador próprios: os módulos são instalados apenas a partir da interface web do localSIEM, em Módulos › Instaláveis (são atualizados e desinstalados em Módulos › Instalados), que transfere este repositório (ramo `main`) e copia a pasta de cada módulo, `mod-<nome>/`, para `/opt/localsiem/modules/<nome>/`; o instalador do localSIEM instala apenas o núcleo, nunca um módulo, e o localSIEM não tem módulos próprios. Os processos do localSIEM (coletor, interface web, `manage.py`) carregam-no. O prefixo `mod-` pertence apenas ao nome da pasta neste repositório: o próprio módulo (o `id` do respetivo `module.json`, as opções, as definições e a pasta instalada) mantém o nome sem ele. Atualmente há dois módulos: `apache2` (pasta `mod-apache2/`) e `privesc` (pasta `mod-privesc/`).

### Porque é que os módulos vivem fora do núcleo

O núcleo do localSIEM ([backend/core/](../../localSIEM/backend/core/)) é genérico: o armazenamento, a pesquisa, o motor de regras, o agrupamento, a fila do SOC, o sinal de vida e a saúde não sabem nada sobre o Apache. O que um serviço significa (onde estão os respetivos registos, como são delimitados e analisados, como os registos se juntam num evento, o que conta como já resolvido, as respetivas regras e os requisitos) vive num módulo. Manter os módulos no seu próprio projeto significa que:

- um módulo tem versão (`version`), declara a versão mínima do localSIEM de que precisa (`core`) e é atualizado, adicionado ou desativado sem uma nova versão do localSIEM;
- o núcleo não importa nenhum módulo pelo nome e não tem módulos próprios: o registo de módulos ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) apenas percorre `/opt/localsiem/modules/` (`LOCALSIEM_MODULES_PATH` nas cópias de desenvolvimento), onde a interface web instala os módulos deste repositório;
- um módulo que não consegue ser carregado nunca impede os outros: o respetivo erro é indicado na interface web (estado «Erro») e por `manage.py modules`;
- um módulo nunca modifica o núcleo: `backend/core/module.py` e `backend/core/registry.py` são todo o contrato.

### O contrato: module.json, locales e uma subclasse de Module

**`module.json`** (verificado por `fReadManifest`):

| Chave | Predefinição | Significado | apache2 | privesc |
|---|---|---|---|---|
| `id` | obrigatório | Nome da pasta do módulo sem o prefixo `mod-` (o nome da pasta instalada), `[a-z][a-z0-9_]{1,31}`; também o `vName` da classe | `apache2` | `privesc` |
| `version` | `"0"` | Versão do módulo, mostrada na interface web e por `manage.py modules` | `1.3.2` | `1.1.2` |
| `core` | `"0"` | Versão mínima do localSIEM de que precisa; uma versão superior à `cVersion` do localSIEM instalado significa que o módulo não é carregado | `2.2.0` | `2.2.0` |
| `entry` | obrigatório | `"ficheiro:Classe"`: `ficheiro` sem `.py` (`[a-z][a-z0-9_]{0,63}`), `Classe` uma subclasse de `Module` | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | Se é executado até o administrador decidir (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | Pastas absolutas que o localSIEM, como root, permite que o utilizador `localsiem` leia (o comando que a interface web mostra depois de instalar, depois de **Reconfigurar** e depois de uma atualização que as altere) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | Comandos que instalam no servidor, como root, o software de que o módulo precisa, para cada sistema (`debian`, `alpine`): um comando por linha, sem operadores de shell, porque a interface web também os mostra com `sudo` à frente (`fCheckInstallRequirements` do núcleo). Mostrados em Módulos › Instaláveis › Requisitos, nunca executados | Debian: Apache, ModSecurity 2, o CRS, `a2enmod`, a configuração recomendada do ModSecurity se não existir nenhuma, reinício; Alpine: Apache | Debian: auditd e rsyslog; Alpine: auditd |
| `setup_option` | — | Não é utilizada por nenhum módulo: o núcleo ignora-a (o registo de módulos descarta-a), porque um módulo nunca altera o servidor; os ficheiros `module.json` de versões mais antigas ainda podem tê-la | não definida | não definida (`--configure-privesc` foi removida na 1.1.0) |
| `settings` | `[]` | Descrição de cada definição: a interface web constrói o respetivo formulário a partir dela | 6 definições | 13 definições |

Cada definição tem uma `key` (`[a-z][a-z0-9_]{1,31}`), um `type`, normalmente um `default`, e os atributos do respetivo tipo. `fValidateSettings` / `fCleanValue` / `fCleanRecords` verificam o que o administrador guarda:

| Tipo | Atributos | Controlo na interface web | Valores aceites |
|---|---|---|---|
| `boolean` | — | caixa de verificação | `true` / `false` |
| `integer` | `min`, `max` | campo numérico | um inteiro entre `min`..`max` |
| `string` | `max_length` (500) | campo de texto | texto sem caracteres de controlo, sem espaços nas extremidades, até `max_length` |
| `path` | — | campo de texto monoespaçado | vazio ou absoluto (começa por `/`), até 1024 caracteres |
| `choice` | `choices` (obrigatório), `required` | lista (com «—» quando não é obrigatório) | um de `choices`, ou vazio |
| `records` | `fields` (obrigatório: definições dos outros tipos), `max_items` (50) | um bloco por registo com Adicionar e Remover | uma lista de até `max_items` registos; cada campo é verificado, os campos `required` não podem estar vazios e os campos vazios são descartados |

**`locales/<idioma>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), lido por `fReadTexts` e mostrado pela interface web (`modules.js fModuleText`, que recorre ao en-US e depois à chave):

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

Um ficheiro de locale em falta ou danificado só perde o respetivo idioma.

**A subclasse de `Module`** ([backend/core/module.py](../../localSIEM/backend/core/module.py)). O registo de módulos cria-a como `Classe(pSettings, pMasker, pStorage, pManifest)`. Os respetivos hooks:

| Hook | Chamado por | Predefinição | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | coletor, uma vez, com o armazenamento pronto | nada | guarda `apache.first_start` (início dos dias de aprendizagem) | guarda `privesc.first_start`; carrega `privesc.sessions`, `privesc.surface` e `privesc.health` |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | coletor, interface web | de `modules.<id>` sobre as predefinições de `module.json` | herdado | herdado; `mReload` também esvazia a cache de `mSettings` |
| `mDiscoveryInterval()` | coletor (o mais curto dos módulos ativados, pelo menos 60 s) | `discovery_interval_seconds` ou 3600 | herdado | herdado (predefinição 300) |
| `mDiscover()` | coletor (arranque, intervalo, recarregamento, pedido de diagnóstico), `manage.py doctor` | `[]` | fontes `{key, path, kind, format, vhost, audit_type, storage_dir}` a partir da configuração do Apache e das fontes manuais | `fDiscoverSources`: o registo de auditoria e o syslog |
| `mCreateFramer(pSource)` | coletor, por fonte | `LineFramer` | `AuditFramer` para o registo de auditoria serial nativo | herdado (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | coletor, por unidade | obrigatório | registo de `access`, `error` ou `audit` | registo de `audit` ou `syslog` |
| `mCreateCorrelator()` | coletor, no arranque | obrigatório | `Correlator` (janela e correlação fraca a partir das definições do núcleo) | `Correlator`: registos de auditoria por número de série (EOE ou 2 s); linhas do syslog imediatamente |
| `mBuildEvent(pTransaction)` | coletor, por transação vencida | obrigatório | evento com `action` e `detections` | evento com os indicadores a que as regras correspondem; sem deteções próprias |
| `mRulesPath()` / `mRuleFunctions()` | coletor, ao carregar as regras | `None` / `{}` | `rules/` da respetiva pasta / `{"apache2.new_php": mIsNewPhp}` | `rules/` da respetiva pasta / `{}` herdado |
| `mDetectionFromSignal(pEvent, pSignal)` | coletor, por sinal de regra (opcional: procurado com `hasattr`) | deteção genérica | deteção com os detalhes do pedido e `{rule: {id, count}}` | deteção com utilizador, comando, programa, sessão, pai, ficheiro... |
| `mEnrich(pDetection)` | coletor, com o grupo, antes de construir o alerta | `{}` | contexto do IP na última hora | contexto da sessão: início visto, porta de entrada, endereço SSH, últimos 20 comandos |
| `mDoctor()` | coletor (estado `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd e o que as respetivas regras registaram, syslog, snoopy, o que o módulo vê, ficheiros da versão 1.0.0, superfície de ataque) |
| `mHealth(pNow)` | coletor, a cada 60 s, só módulos ativados | `[]` | ModSecurity descarregado ou Off, IP real do cliente em falta (no máximo a cada 300 s) | guarda as sessões; resultados da análise; a cada 300 s: auditd parado, ficheiros sensíveis com permissão de escrita (a cada hora), inicia a análise de programas setuid |
| `mSkipped()` | estado do coletor, `manage.py doctor` | `[]` | registos por pipe, registos abrangidos pelo `GlobalLog`, registos de acesso sem dados (`format_without_data`) | syslog não lido (auditd em execução, `syslog_mode` nunca), registo de auditoria em falta |
| `mSetLowDisk(pLowDisk)` | coletor, nível do disco | nada | deixa de guardar cabeçalhos e corpos da auditoria | herdado |
| `mDisplayRecord(pRecord)` | interface web, ficha do pedido | `{}` | cabeçalhos e corpo do registo de auditoria guardado (`fAuditDisplay`) | herdado |
| `mRequirements()` | núcleo, localSIEM 2.2.0 ou mais recente: primeira instalação, arranque e recarregamento do coletor, **Reconfigurar** na interface web, `manage.py modules` e `doctor` | `[]` (sem requisitos) | `apache_config` e `modsecurity` (`fRequirementChecks`) | `command_source`: qualquer fonte que o `localsiem` consiga ler, o registo de auditoria (auditd em execução, fora de um contentor) ou o syslog (com o snoopy, se instalado); `audit_log` / `syslog` quando uma fonte existe mas não pode ser lida |

O núcleo já não tem `mSetupSnippet` nem `mApplySetup`: os módulos não têm opções de configuração e nunca alteram o servidor.

Os registos são dicts com `time`, `received`, `module` (o id: o coletor escolhe o correlacionador por ele), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` e `raw` (mascarado), mais, opcionalmente, `search` (o texto indexado para a pesquisa de texto completo). Os eventos têm as colunas da tabela de eventos (`lEventColumns` em `storage_sqlite.py`) mais `record_ids`, `rule_hits` e `detections`. Uma deteção tem `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` e `uid`.

### Requisitos: um módulo nunca instala o que vigia

Instalar um módulo nunca instala o software que este vigia: o módulo apache2 não instala o Apache nem o ModSecurity, e o módulo privesc não instala o auditd, um daemon de syslog nem o snoopy (o respetivo requisito, `command_source`, é qualquer fonte que o utilizador `localsiem` consiga ler: o registo de auditoria com o auditd em execução fora de um contentor, ou o syslog; `fRequirementChecks` de `mod-privesc/doctor.py`). O próprio módulo define o que precisa antes de poder ser ativado, em `mRequirements()` (localSIEM 2.2.0 ou mais recente): uma lista de verificações no formato do diagnóstico, cumpridas quando nenhuma tem o estado `error`. O módulo apache2 devolve `apache_config` (é encontrada uma configuração do Apache: `apache2.conf`, `httpd.conf` ou o ficheiro da definição `config_file`) e `modsecurity` (o `mod_security2` está carregado; o ModSecurity 3 não conta), que `fRequirementChecks` obtém das primeiras verificações do diagnóstico; sem o Apache, ambas são erros. O que instala esse software é declarado em `install_requirements` de `module.json`: a interface web mostra-o antes de instalar o módulo (Módulos › Instaláveis › Requisitos), para o sistema do servidor, e nunca o executa. O núcleo:

- instala o módulo desativado (`modules.<id>.enabled = false`) quando falta um requisito na primeira instalação e o administrador nunca decidiu; uma atualização nunca altera `enabled`;
- não permite ativá-lo enquanto faltar um requisito: o interruptor fica bloqueado e a interface web mostra os requisitos com o respetivo `fix`;
- nunca desativa por si só um módulo ativado que perca um requisito: o respetivo diagnóstico e os avisos de saúde (`mHealth`: «ModSecurity is no longer loaded») comunicam-no, e desativá-lo silenciá-los-ia;
- volta a verificar os requisitos quando o coletor arranca ou recarrega, e com **Reconfigurar** na página do módulo (também quando está desativado): se estiverem cumpridos, desbloqueia o interruptor, o administrador ativa o módulo e a interface web mostra o comando a executar como root que permite ao `localsiem` ler os registos criados após a instalação (`read_paths`).

### Carregado como namespace package

Não existe nenhum `__init__.py` (namespace packages implícitos do Python 3.13). `fRegisterPackage` cria o pacote `localsiem_modules` com a pasta dos módulos como `__path__`, e `fLoadClass` importa `localsiem_modules.<id>.<ficheiro>`, verifica que a classe é um `Module` e que o respetivo `vName` é igual ao `id`. Consequências para o código de um módulo:

- os seus próprios ficheiros são importados de forma **relativa** (`from .parsers import AccessParser`);
- o núcleo é importado como **`backend.core...`** (`from backend.core.module import Module`): os processos do localSIEM colocam a pasta do localSIEM no `sys.path`;
- só estão disponíveis a biblioteca padrão e as dependências do localSIEM (o respetivo ambiente virtual `/opt/localsiem/venv/`, por exemplo o PyYAML): o localSIEM não instala nada para um módulo.

### Formulário de definições construído a partir do manifesto

Um módulo não tem HTML próprio. A interface web lê `settings` de `module.json` e os textos de `locales/`, constrói o formulário (`modules.js fBuildSettings`, `fRecordsEditor`), valida o que é guardado com `fValidateSettings` e guarda apenas os valores que o administrador guardou em `settings.json` sob `modules.<id>`; `enabled` também vive aí. O módulo lê `mModuleSettings()`: as predefinições de `module.json` com os valores guardados por cima. Por isso, adicionar uma definição não requer nenhuma alteração na interface web nem no núcleo.

Definições do núcleo que o módulo apache2 também lê de `self.dSettings`: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) e `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()` também passa chaves guardadas sob `modules.apache2` que `module.json` não declara: `mDiscover` lê `document_roots` (`{vhost: pasta}`, sobre os DocumentRoots descobertos) dessa forma; só pode ser definido editando `settings.json`.

### O princípio da «ação tomada»

Só vai para o SOC o que ainda ninguém resolveu. No módulo apache2, a ação tomada é lida a partir da fonte mais fiável: o registo de auditoria (`Action: Intercepted (phase N)` no formato nativo, `audit_data.action.intercepted/phase` em JSON) e depois o error.log (`Access denied with code NNN (phase N)`). Um 403 sem qualquer vestígio do ModSecurity não é um bloqueio (`fields.doubtful_block`).

| Situação | `action` | Deteção (para o SOC) |
|---|---|---|
| Intercetado nas fases 1-2 (a aplicação nunca o recebeu) | `blocked` | nenhuma: `mAssess` devolve `None`; contado no contexto de alertas posteriores |
| Intercetado nas fases 3-4 | `none` | sim, `blocked_late` (alta), ou `success_indicator` com um erro de base de dados |
| Correspondências com o motor em `DetectionOnly` | `none` | sim |
| Correspondências abaixo do limiar de anomalia | `none` | sim, `below_threshold` (baixa) |
| Sinais das regras YAML | `none` | sim |

As gravidades vêm de `severity.yaml` (`fLoadSeverityTable`; um ficheiro em falta ou um valor inválido mantém a predefinição incorporada): `crs_not_blocked_2xx` alta, `crs_not_blocked_other` média, `blocked_late` alta, `success_indicator` crítica (regra de saída 950-955 não bloqueada, ou um erro de base de dados no mesmo pedido), `below_threshold` baixa (a definição do núcleo `below_threshold_severity` tem precedência). «Acima do limiar» significa que correspondeu uma regra 949xxx ou que a pontuação indicada pelo ModSecurity atingiu o limiar; uma pontuação calculada a partir das gravidades das regras é apenas uma estimativa e não decide. O limiar é o das mensagens, senão `anomaly_threshold`, senão o de `crs-setup.conf`, senão 5.

### Como funciona o módulo apache2

1. **Descoberta** (`discovery.py`): `ApacheConfig` lê a configuração diretamente (`Include`, `IncludeOptional`, `Define`, `${VARS}` do `envvars` do Debian, `<VirtualHost>`, `<IfModule>` em relação aos módulos carregados), como o utilizador `localsiem` e sem `apache2ctl`. `fDiscoverSources` transforma `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` e `SecAuditLog` em fontes com a chave estável `apache:<tipo>:<caminho real>`. Um `GlobalLog` cujo formato tem `%v` abrange todos os vhosts (os outros registos de acesso são ignorados); os registos por pipe e o syslog são ignorados, tal como os registos de acesso cujo formato não tem nenhuma diretiva `%` (o Apache escreve tal como está um nome que nenhum `LogFormat` define: `format_without_data`, a menos que outro `CustomLog` com dados escreva no mesmo ficheiro; o diagnóstico indica-o, sem correção, uma vez que o formato dos registos nunca é alterado); as fontes manuais vêm primeiro e um ficheiro é lido uma única vez.
2. **Delimitação e análise** (`parsers.py`, `logformat.py`, `modsec.py`): as linhas de acesso são analisadas com uma expressão regular gerada a partir do respetivo `LogFormat` (o último formato que funcionou é experimentado primeiro); as linhas de erro são classificadas (`modsecurity`, `database`, `php`, `crash`, `apache`); os registos de auditoria são lidos como JSON (uma linha, cortada antes de `matched_rules`), serial nativo (`AuditFramer` junta `--id-A--` a `--id-Z--`) ou concorrente (a linha de índice aponta para um ficheiro sob `SecAuditLogStorageDir`). Tudo é mascarado; o que não encaixa é guardado como `unparsed`.
3. **Correlação** (`correlate.py`): os registos com o mesmo `UNIQUE_ID` formam uma transação, que espera a janela de correlação e a marca de água das fontes que estão a recuperar o atraso; uma linha de acesso sem `UNIQUE_ID` (os formatos que o Apache escreve por predefinição) é emparelhada por `mPair`, quando ela ou os registos do respetivo pedido vencem, com os registos do ModSecurity que não têm linha de acesso: o mesmo IP do cliente, hora dentro de ±2 s (a linha tem segundos inteiros) e o mesmo método, URI, estado e caminho quando ambos os lados os conhecem; ganha o candidato que coincide em mais deles, depois o mais próximo, depois o mais antigo, e o evento é marcado como fraco. As linhas do error.log sem `UNIQUE_ID` juntam-se imediatamente à transação mais próxima do respetivo IP. Uma transação com um `UNIQUE_ID` e uma linha do ModSecurity do error.log, enquanto chegam registos de auditoria (`vAuditSeen`), também espera pelo seu próprio registo de auditoria (`mWaitsForAudit`), no máximo `cAuditWaitSeconds` (120 s) desde o primeiro registo: o ModSecurity escreve as linhas das respetivas regras enquanto o pedido decorre e o registo de auditoria quando termina, por isso, caso contrário, um pedido lento tornar-se-ia dois eventos; quando o registo de auditoria chega, a linha de acesso tem mais `cAfterAuditSeconds` (2 s).
4. **Evento** (`ApacheModule.mBuildEvent`): campos escolhidos do acesso, depois da auditoria, depois do erro; o vhost a partir de `%v` ou, sem ele, do cabeçalho Host e da porta local do registo de auditoria (`mVhostName`); com uma linha de acesso de segundos inteiros, a hora do registo de auditoria; `fSummarize` dá regras, categorias, pontuação, limiar e interceção; a ação tomada e `mAssess` decidem a deteção.
5. **Regras, enriquecimento, diagnóstico e saúde**: as regras YAML de `rules/` são executadas em cada evento (motor do núcleo); `mEnrich` acrescenta o contexto do IP; `fRunDoctor` verifica os requisitos e descreve os registos, sem alterar nada; `mHealth` vigia o ModSecurity e o IP real do cliente. O módulo não tem opção de configuração: como root, o localSIEM apenas dá ao `localsiem` acesso de leitura a `/var/log/apache2`.

### Decisões de design que convém conhecer

- **Sem instalador próprio**: os módulos são instalados (Módulos › Instaláveis), atualizados (**Atualizar**, em Módulos › Instalados) e desinstalados (**Desinstalar**) apenas a partir da interface web do localSIEM, que transfere este repositório e os instala com `backend/core/catalog.py` (descompactação segura, uma instalação de cada vez, troca atómica da pasta). O que precisa de root (acesso de leitura aos `read_paths`) é feito pelo localSIEM: depois de instalar (e depois de uma atualização que altere os `read_paths`), a interface web mostra o comando a executar como root.
- **Os registos do cliente apenas são lidos**: um módulo nunca escreve nos registos dos serviços que vigia, nem os roda, trunca, move ou elimina, e nunca altera o respetivo formato; o módulo apache2 também nunca altera a configuração do Apache nem do ModSecurity (não tem `setup_option`). Se um servidor escrever os registos num formato próprio (um `LogFormat` próprio, o IP do cliente do `mod_remoteip`), o módulo adapta-se: `AccessFormat` constrói o analisador de cada registo de acesso a partir do respetivo `LogFormat`, e `fCanPair` / `Correlator.mPair` juntam as linhas sem `UNIQUE_ID`. O diagnóstico apenas descreve os registos e o que o localSIEM consegue ou não ler deles: as verificações `log_format`, `log_format_without_data`, `remoteip`, `audit_log` e `sanitise` não têm `fix`; só o que não é um registo (o ModSecurity, o CRS, `SecRuleEngine`, `mod_unique_id`, as permissões de leitura do `localsiem`) vem acompanhado de um. O `--configure-apache` foi removido na versão 1.3.0; `localsiem_combined` mantém-se em `dKnownFormats` para os servidores que já o escrevem, e o instalador do localSIEM elimina o `localsiem.conf` que as versões mais antigas escreveram (`--uninstall`, `--reinstall`).
- A **parte K** (`matched_rules`) e a **parte E** (corpo da resposta) do registo de auditoria nunca são guardadas. Os cabeçalhos e o corpo ficam apenas no registo em bruto mascarado; a ficha do pedido reconstrói-os (`fAuditDisplay`). O índice de texto completo recebe um texto reduzido (`search`: linha do pedido, host, user agent e o id, a mensagem e os dados de cada regra).
- **O texto em bruto é reconstruído a partir das partes mascaradas**: o registo de auditoria original pode conter palavras-passe e cookies.
- **A interface web e as ferramentas criam o módulo sem armazenamento** (`pStorage` é `None` em `WebContext.mModule` e em `manage.py`): o construtor e os hooks que chamam não podem usar o armazenamento.
- **Estado na base de dados de eventos**: `apache.first_start` (dias de aprendizagem), `apache.health` (o que já foi comunicado, para que um reinício não o repita) e `apache2.doctor` (escrito pelo coletor). Os dois primeiros, tal como as chaves das fontes `apache:<tipo>:<caminho real>`, mantêm o nome que o módulo tinha antes de se chamar apache2: um servidor que tinha o módulo `apache` mantém os dias de aprendizagem, a memória de saúde e as posições de leitura (com uma nova chave de fonte, cada registo com menos de 5 MiB seria lido novamente desde o início). As horas da memória de saúde estão no formato nativo do projeto (`2026-10-29@13-59-59.723`, UTC); um estado guardado por uma versão mais antiga, com segundos epoch, é convertido ao ser carregado.
- **Segurança dos caminhos**: `mIsNewPhp` recusa `..` e fica dentro do DocumentRoot; `fReadConcurrentEntry` fica dentro de `SecAuditLogStorageDir` e lê no máximo 8 MiB; o correlacionador mantém no máximo 50 000 transações pendentes.

### Como funciona o módulo privesc

A pergunta não é «alguém executou `whoami`?» (os administradores fazem-no todos os dias), mas sim «esta sessão está a percorrer o caminho de uma escalada, e chegou lá?». O módulo transforma duas fontes em eventos com um único significado (`vhost` a pessoa, `method` o tipo, `uri` o comando, `path` o programa ou o ficheiro, `ip` o endereço SSH, `score` o reconhecimento distinto da sessão), calcula indicadores sobre eles e deixa que as regras YAML decidam o que vai para o SOC.

1. **Descoberta** (`discovery.py`): `fDiscoverSources` devolve o registo de auditoria (`fAuditLogPath`: definição, `log_file` de `auditd.conf`, `/var/log/audit/audit.log`; também quando o auditd está em execução e o `localsiem` ainda não o consegue ler, para que o núcleo o comunique) e o syslog (`fSyslogPath`) quando `syslog_mode` o indica (`auto`: auditd não em execução, o respetivo registo não legível, ou snoopy instalado). Também reúne o que o diagnóstico precisa: contentor (`fContainer`, legível sem root: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), binário e pid do auditd, snoopy, se cada registo pode ser lido (`fReadState`: `readable`, `unreadable` ou `missing`) e os ficheiros que a versão 1.0.0 deixou (`fLegacyLeftovers`). `Accounts` volta a ler `/etc/passwd`, `/etc/group` e `UID_MIN` quando mudam, e classifica um uid como `root`, `admin` (membro de `admin_groups`), `user` ou `service`.
2. **Análise** (`parsers.py`): `fParseAuditLine` lê `type=... msg=audit(<time>:<serial>): k=v ...`, a parte de espaço de utilizador `msg='...'`, a parte enriquecida após `\x1d`, junta os argumentos de `EXECVE` (também os divididos em partes `aN[i]`), descodifica os valores hexadecimais (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) e **reconstrói o texto em bruto a partir dos valores descodificados e mascarados** (o hexadecimal de uma palavra-passe mantê-la-ia); `search` recebe o comando descodificado. `fParseSyslogLine` lê carimbos de data/hora ISO e clássicos (com ou sem o `facility.priority` do busybox) e `fParseSyslogMessage` entende o snoopy (os respetivos formatos predefinidos da 2.4 e da 2.5, incluindo `uid:alice(1000)/root(0)`, e o que a versão 1.0.0 definia), sudo, su (util-linux e busybox), pkexec, doas, `pam_unix` e sshd. `fMaskCommand` mascara as palavras-passe nas linhas de comandos antes do mascarador do núcleo.
3. **Correlação** (`correlate.py`): os registos de auditoria com o mesmo número de série formam uma transação, que vence no `EOE`, imediatamente para os tipos de espaço de utilizador de um único registo (`USER_*`, `CRED_*`, `DAEMON_*`...), ou após 2 s sem registos; no máximo 50 000 pendentes. As linhas do syslog vencem imediatamente.
4. **Evento** (`PrivescModule.mBuildEvent`): `mAuditEvent` separa por tipo: `EXECVE` → `mAuditExec` (bit setuid do programa a partir do registo `PATH` ou de `stat`, `suid_escape` quando o euid é 0, o uid real não é e o programa não é setuid, capacidades obtidas de `BPRM_FCAPS`, `root_without_door`, `parent_interpreter` quando uma shell é executada como root iniciada por um interpretador de um utilizador que não é o root, o pai a partir da memória dos processos); `USER_*`/`LOGIN` → `mAuditUser` (sessão iniciada, endereço SSH, portas de entrada: `USER_START`/`USER_CMD` de sudo, su, pkexec, doas, run0, systemd; falhas); `CONFIG_CHANGE` (`audit_disabled`, `audit_rule_removed` para qualquer regra removida), `DAEMON_*` (`auditd_stopped_manually` quando o remetente não é o pid 1), `ANOM_ABEND` (`crash_suspicious`); qualquer outro `SYSCALL` → `mAuditSyscall`, que o classifica pela respetiva chamada de sistema (`fSyscallName`: o nome do formato enriquecido, ou o número na tabela da respetiva arquitetura), pelos argumentos e pelos registos `PATH`, nunca pela chave da regra: `denied` (open, exec ou truncate falhados com `EACCES`/`EPERM` para uma pessoa), `kmod`, `ptrace` (`ptrace_attach` para `PTRACE_ATTACH`/`PTRACE_SEIZE`), `chmod` (modo com o bit setuid ou setgid, não numa pasta, com `writer_allowed`) e `file` (uma alteração de um caminho de `lSensitivePaths`, com `sensitive_group` e `writer_allowed`; a chave, através de `dKeyHints`, só quando não é possível resolver nenhum caminho). `mSyslogEvent` trata o snoopy como `exec` (`suid_escape` a partir de `stat`; sem `filename`, o programa a partir da primeira palavra do comando) e sudo, su, pkexec, doas, login e pam. Cada comando passa por `mAnalyzeCommand`: token de reconhecimento (`fReconToken`) e tokens distintos da sessão na janela (`recon_burst`, `recon_massive`, `score`), transferências executadas por uma shell (`cDownloadOnelinerRegex`, ou um programa de transferência seguido de uma shell com o mesmo pai), `compile_in_tmp`, os últimos comandos da sessão e, para as contas de serviço, o programa (`fProgramKey`) face ao respetivo histórico (`mPathFirstSeen` do núcleo, após `learning_days`: `new_program`). `ignored` marca os utilizadores ignorados.
5. **Regras, enriquecimento, diagnóstico e saúde**: as 35 regras YAML de `rules/` decidem cada deteção (`mDetectionFromSignal`); `mEnrich` acrescenta o contexto da sessão; `fRunDoctor` descreve o auditd e o que as respetivas regras registaram, o syslog, o snoopy, o que o módulo vê e o que não vê, os ficheiros da versão 1.0.0 e a superfície de ataque; `mHealth` comunica o auditd parado, os ficheiros sensíveis com permissão de escrita e o resultado da análise de programas setuid (`SurfaceScanner`, uma thread). O módulo não tem opção de configuração e não altera nada no servidor.

### Decisões de design do módulo privesc

- **Duas fontes, um significado.** O auditd não pode ser evitado por um utilizador, mas não funciona dentro de contentores (a auditoria do kernel não tem namespaces); o snoopy vê cada programa em contentores, mas precisa do syslog; o syslog por si só dá apenas sudo, su, pkexec e doas. Nenhuma fonte vê os comandos internos da shell. As regras correspondem a colunas e indicadores, nunca à fonte, por isso uma fonte pode ser adicionada sem lhes mexer. O mesmo comando visto duas vezes resulta num único alerta: o núcleo agrupa as deteções por módulo, utilizador, IP, categoria e gravidade.
- **Rajadas, não comandos.** O reconhecimento é um token por tipo de pergunta (`whoami`, `read:/etc/passwd`, `find:-perm:`...), e só o número de tokens distintos de uma sessão numa janela gera um alerta, com um limiar mais alto para os administradores e um terceiro para os scripts. Os limiares são definições, não limiares de regras: a regra só corresponde a `recon_burst` / `recon_massive`.
- **O sucesso é o que mais importa.** `suid_escape` (um programa que não é setuid a ser executado com euid 0 e um uid real que não é 0) e `root_without_door` (root numa sessão cujo início foi visto e que nunca passou por sudo, su, pkexec ou doas) são os dois sinais críticos de que uma escalada resultou, quase sem falsos positivos. Uma sessão cujo início não foi visto (sessões abertas antes do módulo, sessões esquecidas após um dia de inatividade) nunca é assinalada.
- **As sessões sobrevivem aos reinícios.** `SessionTracker` guarda o início, o endereço SSH e a porta de entrada de cada sessão no estado `privesc.sessions` (guardado no máximo a cada minuto); os tokens de reconhecimento e os últimos comandos ficam em memória. As sessões inativas durante um dia são descartadas.
- **Só o que o servidor já tem.** O módulo nunca instala nada nem altera nada fora de `/opt/localsiem`: não carrega regras de auditoria, não mexe no `auditd.conf` nem no `snoopy.ini` e não instala nenhum hook. A versão 1.0.0 fazia-o (`--configure-privesc`: regras de auditoria com as chaves `lsiem_*`, `log_group = adm`, um hook de bash, o formato do snoopy); a versão 1.1.0 removeu-o. Por isso, os registos de auditoria são classificados pelo tipo, pela chamada de sistema e pelos caminhos, de modo que quaisquer regras de auditoria funcionam (as do servidor, as regras de exemplo do STIG ou as regras `lsiem_*` que a 1.0.0 deixou); a chave é mantida em `fields.key` para as pesquisas e é apenas uma pista (`dKeyHints`). Os números das chamadas de sistema são lidos por arquitetura (`dSyscallTables`: x86_64, i386 e a tabela genérica de aarch64, riscv64 e loongarch64) quando o registo não tem nomes enriquecidos. O diagnóstico descreve o que as regras do servidor registam e o que não registam; o respetivo `fix` é apenas um pacote a instalar ou o acesso de leitura do `localsiem`.
- **Legível significa legível.** O requisito é cumprido por uma fonte que existe e que o `localsiem` consegue abrir (`fReadState`), não por um programa estar instalado: numa primeira instalação, os registos pertencem normalmente ao root, por isso o módulo fica desativado até ao comando para o root (`manage.py setup-modules`) e a **Reconfigurar**.
- **Os gestores de pacotes não são atacantes.** As alterações de ficheiros sensíveis e de bits setuid feitas pelas ferramentas de contas e de pacotes (`sAllowedWriters`), ou por programas cujos antecessores conhecidos são gestores de pacotes, definem `writer_allowed`, e as regras ignoram-nas.
- **A análise nunca bloqueia o coletor.** `SurfaceScanner` percorre os `scan_paths` numa thread própria, sem sair do sistema de ficheiros de cada um, ignorando `/proc`, `/sys` e as pastas dos contentores, até 3 milhões de ficheiros ou 15 minutos; `mHealth` recolhe o resultado quando está pronto. A primeira análise é a referência; as seguintes comunicam o que é novo.
- **A interface web e as ferramentas criam o módulo sem armazenamento**: `mDiscover`, `mDoctor` e `mRequirements` nunca o utilizam, e `mAnalyzeCommand` só chama `mPathFirstSeen` quando existe.
- **Estado na base de dados de eventos**: `privesc.first_start` (dias de aprendizagem), `privesc.sessions`, `privesc.surface` (a referência da análise e o diagnóstico), `privesc.health` (o que já foi comunicado, se o auditd estava em execução) e `privesc.doctor` (escrito pelo coletor). Os programas vistos das contas de serviço são linhas de `seen_paths` com o vhost `privesc:<conta>`. As horas de `privesc.health` (a memória de saúde) e de `privesc.sessions` (`last` de cada sessão) estão no formato nativo do projeto (`2026-10-29@13-59-59.723`, UTC); um estado guardado por uma versão mais antiga, com segundos epoch, é convertido ao ser carregado.

<a id="modules"></a>
## 2. Mapa de módulos

| Módulo | Caminho | Responsabilidade | Depende de | Usado por |
|---|---|---|---|---|
| Manifesto | [mod-apache2/module.json](../mod-apache2/module.json) | id, versão, núcleo mínimo, entrada, caminhos de leitura, definições (sem opção de configuração) | — | registo de módulos, interface web, `manage.py` |
| Módulo do Apache | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: hooks, ação tomada, gravidade, deteções, função de regra, enriquecimento, saúde | correlate, discovery, doctor, modsec, parsers; núcleo `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | coletor, interface web, `manage.py` |
| Descoberta | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (analisador da configuração), fontes e registos ignorados, DocumentRoots | logformat (`dKnownFormats`) | module, doctor |
| Diagnóstico | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | Verificações de requisitos; descreve os registos (formato, registo de auditoria, mascaramento) sem propor alterá-los | discovery | module |
| Formatos de acesso | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` para expressão regular, horas para UTC, linha do pedido | núcleo `timeutil` | parsers, discovery |
| Analisadores | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, nativo, concorrente), `AuditFramer`, `fAuditDisplay` | logformat, modsec; núcleo `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | Mensagens, categorias, intervalos do CRS, pontuações, interceção | — | parsers, module |
| Correlação | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, emparelhamento sem ele (`mPair`), janela, marca de água | núcleo `timeutil` | module (coletor) |
| Tabela de gravidades | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | Gravidades das deteções do ModSecurity | — | module (`fLoadSeverityTable`) |
| Regras | [mod-apache2/rules/](../mod-apache2/rules/) | Seis regras YAML | motor de regras do núcleo, `mIsNewPhp` | coletor (`RulesEngine`), interface web (`fRules`) |
| Textos | [mod-apache2/locales/](../mod-apache2/locales/) | Nome, resumo, etiquetas e ajuda das definições, opções | — | interface web |
| privesc: manifesto | [mod-privesc/module.json](../mod-privesc/module.json) | id, versão, núcleo mínimo, entrada, caminhos de leitura, 13 definições (sem opção de configuração) | — | registo de módulos, interface web, `manage.py` |
| privesc: módulo | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: hooks, eventos das duas fontes, classificação dos registos de auditoria (caminhos sensíveis, chamadas de sistema por arquitetura), indicadores, deteções das regras, enriquecimento, saúde, resultados da análise | commands, correlate, discovery, doctor, parsers, surface; núcleo `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | coletor, interface web, `manage.py` |
| privesc: descoberta | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | Fontes, contentor, auditd, snoopy, syslog, se cada registo pode ser lido, ficheiros deixados pela versão 1.0.0, `Accounts` (utilizadores, grupos, tipo de conta) | — | module, doctor |
| privesc: analisadores | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | Registos de auditoria (hexadecimal, `msg='...'`, enriquecidos), linhas do syslog (snoopy nos formatos habituais, sudo, su, pkexec, doas, pam, sshd), mascaramento das linhas de comandos | núcleo `masking`, `timeutil` | module |
| privesc: correlação | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | Registos de auditoria por número de série (EOE, registos de espaço de utilizador, 2 s); linhas do syslog imediatamente | — | module (coletor) |
| privesc: comandos | [mod-privesc/commands.py](../mod-privesc/commands.py) | Tokens de reconhecimento, programa de uma conta de serviço, shells, interpretadores, programas de transferência, portas de entrada, compiladores; `SessionTracker` | núcleo `timeutil` | module |
| privesc: superfície de ataque | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, capacidades), GTFOBins, ficheiros sensíveis com permissão de escrita, grupos privilegiados | — | module, doctor |
| privesc: diagnóstico | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | Descreve o auditd, o respetivo registo e o que as respetivas regras registaram, o syslog, o snoopy, o que o módulo vê, os ficheiros da versão 1.0.0 e a superfície (correções: apenas pacotes e acesso de leitura); requisito `command_source` (qualquer fonte legível) | discovery, surface; núcleo `timeutil` | module |
| privesc: regras | [mod-privesc/rules/](../mod-privesc/rules/) | 35 regras YAML | motor de regras do núcleo | coletor (`RulesEngine`), interface web (`fRules`) |
| privesc: tabela de gravidades | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | Gravidades das deteções construídas pelo módulo (análise, ficheiros sensíveis) | — | module (`fLoadSeverityTable`) |
| privesc: textos | [mod-privesc/locales/](../mod-privesc/locales/) | Nome, resumo, etiquetas e ajuda das definições, opções | — | interface web |
| Núcleo: interface | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | registry | módulos |
| Núcleo: registo de módulos | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | Encontrar, verificar e carregar módulos; predefinições e validação das definições | `config` | coletor, interface web, `manage.py`, `backend/core/catalog.py` |
| Núcleo: interface web | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | Páginas de Módulos (Instalados, Instaláveis, a página de um módulo) e API | registry, catalog, rules | browsers |
| Núcleo: catálogo | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | Transferência e descompactação segura do repositório, lista com a ação de cada módulo (`install`, `update`, `incompatible`, `invalid`...) e `newer`, instalação ou atualização atómica (`previous`, `access_changed`), desinstalação, comando para o root: Módulos › Instaláveis e **Atualizar** / **Desinstalar** de Módulos › Instalados, a única forma de instalar módulos | registry | interface web |

<a id="symbols"></a>
## 3. Símbolos principais

| Símbolo | Ficheiro:linha | O que faz |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | O módulo apache2 (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | `severity.yaml` sobre as predefinições incorporadas |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | Analisa a configuração; fontes, registos ignorados, DocumentRoots |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | Limiar de anomalia: definição, CRS ou 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | Unidade para registo, por tipo de fonte |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | Transação para evento: campos, ação tomada, pontuações, deteção |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Cabeçalho Host ou hostname do ModSecurity para o vhost que o Apache escolheu (o que `%v` regista) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | Gravidade, nome da regra, descrição e detalhes do que vai para o SOC |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | Sinal de uma regra YAML para deteção |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | Função de regra `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | Contexto do IP (última hora) para o alerta |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity descarregado ou Off; IP real do cliente em falta |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | Cabeçalhos e corpo para a ficha do pedido |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache e ModSecurity 2: o que o módulo precisa antes de poder ser ativado |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Analisador da configuração do Apache |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | Diretivas lidas (registos, vhosts, módulos, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Vhost de um pedido a partir do cabeçalho Host e do endereço e porta locais, tal como o Apache o escolhe |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | Chave estável da fonte; fontes a ler e fontes ignoradas |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | Verificações de requisitos `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | Se um formato de acesso pode ser juntado sem `UNIQUE_ID` (IP do cliente, hora, linha do pedido, estado) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | As verificações `apache_config` e `modsecurity` do diagnóstico ou, sem o Apache, ambas como erros, com o comando que os instala |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` para expressão regular; nomes conhecidos |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | Linha do access.log para registo |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | Linha do error.log: ModSecurity, base de dados, PHP, crash |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | Registos nativos ao longo de várias linhas; posição de commit segura |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | Registo de auditoria JSON ou nativo; mascaramento, texto em bruto e texto indexado |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | Ficha de um registo guardado; ficheiro de uma entrada concorrente |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | Uma mensagem do ModSecurity; regras, categorias, pontuação, limiar, interceção |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | O módulo privesc (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | Transação para evento, por fonte; `ignored`; campos vazios descartados (`fCleanFields` mantém o 0) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | Reconhecimento da sessão, transferência executada por uma shell, compilação em `/tmp`, comandos recentes, novo programa de uma conta de serviço |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | Transação de auditoria por tipo; programas executados (`suid_escape`, `root_without_door`, `parent_interpreter`, capacidades); inícios de sessão, portas de entrada e falhas |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | Qualquer outra chamada de sistema pelo nome, pelos argumentos e pelos caminhos: `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) ou `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | Nome de uma chamada de sistema (nome enriquecido, ou número por arquitetura); grupo de um caminho sensível (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, inícios de sessão |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | Quem escreve um ficheiro sensível, ou um antecessor conhecido, é uma ferramenta de contas ou de pacotes |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | Sinal de uma regra para deteção; contexto da sessão para o alerta |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | Sessões guardadas, auditd parado, ficheiros sensíveis, análise iniciada; novos programas setuid e capacidades |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | Fontes, fontes ignoradas e informação para o diagnóstico; se um registo pode ser lido; ficheiros deixados pela versão 1.0.0 |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | Tipo de contentor (sem root); pid de um auditd em execução |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | Nomes de uids, grupos, `UID_MIN`, tipo de conta (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | Registos das duas fontes |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | Palavras-passe das linhas de comandos, depois o mascarador do núcleo |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | Registos de auditoria por número de série; os outros imediatamente |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | Token de reconhecimento de um comando; programa de uma conta de serviço; palavras de um comando escrito |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | Sessões (início, IP, porta de entrada, reconhecimento, últimos comandos), processos, transferências; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | Análise de setuid, setgid e capacidades numa thread; ficheiros sensíveis com permissão de escrita para outros |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | Verificações do diagnóstico (descrições; correções apenas para pacotes e acesso de leitura); requisito `command_source`: qualquer fonte legível |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | Interface de um módulo; uma linha por unidade |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | Verifica `module.json`, lê os textos |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | Os módulos instalados (`/opt/localsiem/modules/*`); instâncias e erros |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | Namespace package `localsiem_modules`; importação e verificações da entrada |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | Predefinições sob os valores guardados; validação do que é guardado |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`; `POST /api/admin/module-catalog/{name}` (instalar ou atualizar; uma primeira instalação sem os respetivos requisitos fica desativada: `fFirstInstallation`); `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | Instala ou atualiza um módulo ao lado da cópia instalada e troca-os com uma mudança de nome (`previous`, `access_changed`); os módulos do repositório com `installed`, `newer` e a respetiva ação |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | Desinstala um módulo (mudança de nome e eliminação); o comando para o root (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | Secção Instaláveis (só os módulos não instalados, **Instalar** e a respetiva caixa de diálogo); aviso de uma versão mais recente numa linha de Instalados; **Atualizar** (confirmação, o mesmo `POST`, uma caixa de diálogo só com `access_changed` ou quando o coletor não respondeu) |

<a id="flows"></a>
## 4. Fluxos de chamadas principais

**Arranque do coletor → registo de módulos → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = pasta, entry, definições, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, subclasse de `Module`, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, sobreposições `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`; um `FileTailer` e `mCreateFramer` por fonte) → registos pendentes de volta ao correlacionador → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → estado `apache2.doctor`).

**Uma linha lida → deteções**

1. `Collector.mReadSources` → `FileTailer.mPoll` → framer `mFeed` (`LineFramer`, ou `AuditFramer`, cujo `mSafeCommit` mantém a posição antes de um registo inacabado) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, ou `fReadConcurrentEntry` + `fParseAuditRecord` e `mObserveAudit`) → registos e posições guardados numa única transação → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, ação tomada, `mAssess`, `mPathFirstSeen` para `.php` 2xx) → `RulesEngine.mEvaluate` (regras YAML; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → `mDetect` para cada deteção e `mDetectionFromSignal` para cada sinal → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → fila do SOC.

**O administrador guarda as definições → recarregamento do coletor**

`modules.js fBuildSettings` (submissão) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` ou `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → socket do coletor `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). O interruptor envia `{enabled}` da mesma forma (ao ativá-lo: 422 `requirements_missing` enquanto faltar um requisito do módulo) e a tabela de regras envia `{rules}` (`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` ou `first_threshold`, `window`). Se o socket não responder, o coletor deteta mesmo assim o novo `settings.json` no ciclo seguinte.

**Instalar um módulo a partir da interface web** (a única forma de instalar módulos)

`modules.js fCatalogPanel` (Módulos › Instaláveis) → **Consultar o repositório** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: cada pasta `mod-<nome>/` do repositório, com `installed`, `newer` e `action`) → só são listados os itens com `installed` nulo → **Requisitos** (`fShowRequirements` → `fRequirementsBody`: os `install_requirements` do módulo para o sistema do servidor, `system` da resposta, como root e com `sudo`, e as notas `install_requirements.*` dos respetivos locales; nada é executado) → **Instalar** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` nulo, `access_changed` verdadeiro) → `WebContext.mReloadModules` → `fFirstInstallation` (um requisito em falta e `modules.<nome>.enabled` nunca guardado: `enabled = false`) → `restart` do coletor → `fCreateModules` carrega o módulo → a caixa de diálogo «<módulo> instalado» mostra o comando para o root (`fRootCommand`: `manage.py setup-modules`, acesso de leitura aos `read_paths`) ou, se faltar um requisito, as verificações não cumpridas.

**Atualizar um módulo a partir da interface web**

Abre-se Módulos › Instalados → `fCheckRepository` → `fFetchCatalog(false)` de `modules.js` (a última resposta de `GET /api/admin/module-catalog`, reutilizada durante 600 s; instalar, atualizar ou desinstalar um módulo esquece-a) → itens com `newer` e `action` `update` ou `incompatible` → `fUpdateNotice` na linha (só enquanto a versão instalada for a comparada) → **Atualizar** → `fUpdate` → confirmação → `POST /api/admin/module-catalog/{name}` (o mesmo `fInstallFromCatalog` → `fInstall`: a nova cópia substitui a instalada, `previous` é a versão antiga, `access_changed` indica se `read_paths` mudou; sem `fFirstInstallation`, por isso `enabled` e as definições mantêm-se) → `restart` do coletor → uma caixa de diálogo só se `access_changed` (o comando para o root) ou se o coletor não respondeu.

**Desinstalar um módulo a partir da interface web**

**Desinstalar** (linha de Módulos › Instalados ou página do módulo) → `fUninstallButton` → confirmação → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → mudança de nome de `/opt/localsiem/modules/<nome>/` para uma pasta temporária, onde é eliminada) → `WebContext.mReloadModules` → `restart` do coletor. `modules.<nome>` e as sobreposições das respetivas regras mantêm-se em `settings.json`, e o acesso de leitura dado pelo root mantém-se.

**Primeira instalação sem o Apache ou o ModSecurity → Reconfigurar** (localSIEM 2.2.0 ou mais recente)

Instalar na interface web → `fInstall` (primeira instalação) → o módulo criado a partir da cópia instalada (armazenamento `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (com o Apache: `fRunDoctor` → `apache_config`, `modsecurity`; sem ele, ambos como erros) → um erro e `modules.apache2.enabled` nunca guardado → `modules.apache2.enabled = false` («Desativado», interruptor bloqueado, requisitos na página). Mais tarde, com o Apache e o ModSecurity instalados: **Reconfigurar** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → cumpridos → interruptor desbloqueado e o comando para o root (acesso de leitura aos `read_paths`; o apache2 não tem `setup_option`) → o administrador ativa o módulo → recarregamento do coletor → `mDiscover` → `mPublishDoctor`.

**Ficha do pedido e diagnóstico a partir da interface web**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **Descobrir novamente e executar o diagnóstico** → `POST /api/admin/modules/apache2/doctor` → coletor `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**Saúde**

`Collector.mCycle` (a cada 60 s) → `mCheckHealth` → `ApacheModule.mHealth` (no máximo a cada 300 s; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc: um comando executado → deteções**

1. O auditd escreve `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE` com um número de série → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (hexadecimal descodificado, `fMaskCommand`, texto em bruto reconstruído) → `Correlator.mAdd` (chave `audit:<time>:<serial>`, vence no `EOE`).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `root_without_door` a partir de `SessionTracker.mGet`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`; `fCompileInTemporary`; `mCommand`; conta de serviço: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (regras de `mod-privesc/rules/`) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (sessão: últimos 20 comandos) → `fBuildAlert` → fila do SOC.

Com o snoopy, o mesmo comando chega também como uma linha do syslog: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (sessão `snoopy:<uid>:<sid>`).

**privesc: sessões e portas de entrada**

`LOGIN` (auid e ses atribuídos) ou `USER_LOGIN`/`USER_START` do sshd ou do login → `mAuditUser` → `SessionTracker.mStart` (utilizador, endereço SSH). `USER_START`/`USER_CMD` com resultado de sucesso de sudo, su, pkexec, doas, run0 ou systemd → `SessionTracker.mDoor`. Um `EXECVE` posterior dessa sessão com uid e euid 0 → `root_without_door` só se o início tiver sido visto e não tiver havido porta de entrada. `mHealth` guarda `SessionTracker.mExport` em `privesc.sessions` no máximo a cada minuto; `mStart` carrega-o (`mImport`).

**privesc: uma chamada de sistema registada pelas regras de auditoria do servidor**

O auditd escreve `SYSCALL` (com `arch`, `syscall`, `a0`-`a3`, `success`, `exit` e a chave da regra que o registou, seja ela qual for), `CWD`, `PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → open/exec/truncate falhado com `EACCES`/`EPERM` e um uid de início de sessão → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; `chmod`/`fchmod`/`fchmodat`/`fchmodat2` com `S_ISUID`/`S_ISGID` no modo, não numa pasta → `chmod` (`mWriterAllowed`); uma alteração (uma chamada de `sChangeSyscalls`, um open com flags de escrita, um `PATH` com `CREATE`/`DELETE`) de um caminho de `lSensitivePaths` → `file` com `sensitive_group` (`dKeyHints` só sem um caminho resolúvel) e `mWriterAllowed`; qualquer outra coisa → `syscall`. `mBuildEvent` recorda a hora de cada tipo (`dRuntime["audit_kinds"]`) para o diagnóstico.

**privesc: análise da superfície de ataque**

`mHealth` (a cada 300 s, cinco minutos após o arranque, a cada `surface_scan_hours`) → `SurfaceScanner.mStart` (thread: `os.walk` de `scan_paths`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → `mHealth` seguinte → `mSurfaceResult` (`SurfaceScanner.mTake`, face a `privesc.surface`: novo setuid/setgid → `new_setuid*`, novas capacidades → `new_capabilities`) → `mModuleDetection` → `mDetect`; o resultado é guardado em `privesc.surface` e mostrado por `fSurfaceChecks`. A cada hora, `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc: requisitos e Reconfigurar**

`fInstall` (primeira instalação) ou **Reconfigurar** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`; `fSyslogPath` → `fReadState` exceto se `syslog_mode` for `never`; `fSnoopyInstalled`) → uma fonte legível: `command_source` ok (as não legíveis como avisos); uma fonte que existe mas não pode ser lida: erro `audit_log` ou `syslog` com o acesso de leitura (`manage.py setup-modules` ou `setfacl`); nada: erro `command_source` com o pacote a instalar. O módulo fica desativado enquanto houver um erro.

<a id="routes"></a>
## 5. Pontos de entrada

| Ponto de entrada | Handler | Ficheiro |
|---|---|---|
| `"entry": "module:ApacheModule"` de `module.json` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (núcleo) | [mod-apache2/rules/](../mod-apache2/rules/) |
| Função de regra `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Interface web: Módulos › Instaláveis, a única forma de instalar módulos (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`; vista `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Interface web: **Atualizar** numa linha de Módulos › Instalados (o mesmo `GET`, reutilizado durante 10 minutos pelo browser, e o mesmo `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Interface web: **Desinstalar** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `read_paths` de `module.json` | `manage.py read-paths`: as pastas que o localSIEM permite que o `localsiem` leia, como root (o comando de `fRootCommand`) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | `read_paths` de cada manifesto | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (302 para `installed/`), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`; vista `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (o antigo `/admin/dashboard/modules/apache2/` responde com 301 para ele) | `fAdminModule` (o 301: `fAdminModulesSection`); vista `LocalsiemViews.module` | os mesmos ficheiros |
| `GET /api/modules` | `fModules` (estado para todos os que iniciaram sessão) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (definições, valores, fontes, diagnóstico, regras) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**Reconfigurar**, localSIEM 2.2.0 ou mais recente) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `"entry": "module:PrivescModule"` de `mod-privesc/module.json` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (núcleo) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| Registos de auditoria das regras do servidor (qualquer chave) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. Análise de impacto

| Componente | O que é afetado se mudar |
|---|---|
| `module.json` `id` | Tem de ser igual ao nome da pasta sem `mod-` (o nome da pasta instalada) e ao `vName`. É a chave das definições (`modules.<id>`), do estado (`<id>.doctor`) e o `module` de cada evento: mudar-lhe o nome perde as definições guardadas e divide o histórico. |
| `module.json` `core` | Subi-lo acima do localSIEM instalado impede que o módulo seja carregado (estado «Erro»); no repositório, Instaláveis mostra «Precisa do localSIEM X ou mais recente» e Instalados mostra a versão mais recente sem **Atualizar**. |
| `module.json` `entry` | Tem de apontar para uma subclasse de `Module`; um valor errado é um erro de carregamento. |
| `module.json` `default_enabled` | Ativado/desativado nos servidores em que o administrador nunca decidiu (se faltarem os requisitos na primeira instalação, desativado). |
| `module.json` `read_paths` | O acesso de leitura que o localSIEM dá como root (`manage.py read-paths`): uma pasta em falta significa erros de permissões no diagnóstico e no estado. Uma alteração numa nova versão faz com que a interface web volte a mostrar o comando para o root depois de **Atualizar** (`access_changed`). |
| `module.json` `install_requirements` | A caixa de diálogo Requisitos de Instaláveis (`fRequirementsBody` de `modules.js`). Um valor errado (um sistema que não seja `debian` nem `alpine`, uma lista vazia ou com mais de 20 comandos, um comando com um operador de shell ou uma quebra de linha) torna o módulo inválido (`fCheckInstallRequirements` do núcleo): não é instalado nem carregado. |
| `module.json` `setup_option` | Nada: o núcleo ignora-a (nenhum módulo a tem desde o apache2 1.3.0 e o privesc 1.1.0). |
| Pastas `mod-<nome>/` com um `module.json` na raiz do repositório | O que o catálogo da interface web lista, como o módulo `<nome>`: Instaláveis mostra os que ainda não estão instalados (um que precise de um núcleo mais recente como «Precisa do localSIEM X ou mais recente», um inválido como «O módulo do repositório não é válido»), e uma `version` superior à instalada faz com que Instalados ofereça **Atualizar**. |
| `module.json` `settings` | O formulário, a validação e as predefinições. Uma nova predefinição aplica-se aos servidores que nunca guardaram essa chave. Os valores guardados não são migrados: uma chave com outro nome perde o valor e um valor antigo com um tipo novo chega ao módulo tal como foi guardado. |
| `locales/*.json` | Apenas os textos da interface web; um texto em falta recorre ao en-US e depois à chave. |
| `parsers.py` (dict do registo) | A correlação (`correlation`, `fields.client_ip`, `fields.path`), a ficha do pedido, o índice de texto completo (`search`, `raw`), a saúde das linhas não analisadas e a privacidade. |
| `logformat.py` `dKnownFormats` | A análise de cada registo de acesso; `localsiem_combined` mantém-se para os servidores que já o escrevem (as versões 1.2.0 e anteriores do módulo adicionavam-no): não altere a respetiva definição. |
| `correlate.py` | Um evento por pedido; o núcleo chama `mAdd`, `mDue(pNow, pForce, pWatermark)` e `mPendingCount`, e volta a fornecer os registos ainda pendentes após um reinício. Sem `UNIQUE_ID`, emparelha os registos pelos campos `client_ip`, `method`, `uri`, `status` e `path`: um analisador que os escreva de outra forma quebra o emparelhamento. A espera pelo registo de auditoria (`mWaitsForAudit`) precisa do campo `modsecurity` das linhas do error.log e dos registos da fonte `audit`. |
| `modsec.py` (categorias, etiquetas, intervalos) | Os nomes das regras dos alertas (as estatísticas do SOC agrupam-se por eles: mantenha-os estáveis), as chaves de agrupamento, as pesquisas `category:`. |
| `ApacheModule.mBuildEvent` (dict do evento) | As colunas da tabela de eventos, os campos lidos pelas regras YAML (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), as pesquisas e a exportação CSV. |
| `ApacheModule.mAssess` | O que chega ao SOC e a respetiva gravidade; os limites de `GenericAlert` do núcleo (regra 300, descrição 10 000 caracteres). |
| `severity.yaml` | A gravidade de cada deteção do ModSecurity; a gravidade faz parte da chave de agrupamento, por isso uma alteração inicia novos grupos. |
| `rules/*.yaml` | O `id` é a chave das sobreposições (`rules.<id>`) e das pesquisas (`rule:localsiem:<id>`): mantenha-o estável. Os campos têm de existir nos eventos; `{function: ...}` precisa de `mRuleFunctions`. |
| `discovery.py` | Que registos são lidos; `fSourceKey` é a chave das posições guardadas (uma nova chave torna o ficheiro uma nova fonte, sem a respetiva posição guardada); os DocumentRoots da regra de web shell; o diagnóstico. |
| `doctor.py` | O diagnóstico da interface web e de `manage.py` e as indicações mostradas ao cliente. Só as verificações sobre o que não é um registo (ModSecurity, o CRS, `SecRuleEngine`, `mod_unique_id`, permissões) podem ter um `fix`; as verificações sobre os registos apenas os descrevem. |
| `mRequirements` / `fRequirementChecks` | Se o módulo pode ser ativado, o estado «Desativado» após uma primeira instalação sem o Apache ou o ModSecurity, os requisitos que a interface web mostra e **Reconfigurar**. São executados na interface web e em `manage.py` sem armazenamento e analisam a configuração do Apache em cada chamada: mantenha-os longe do armazenamento e de qualquer coisa lenta, e mantenha estáveis os ids `apache_config` e `modsecurity`. |
| privesc: colunas e campos dos eventos (`mBuildEvent`, `mAnalyzeCommand`) | As regras YAML correspondem-lhes pelo nome (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...): um campo com outro nome desativa silenciosamente as regras que o utilizam. `vhost` é o utilizador: a chave de agrupamento dos alertas e as pesquisas `vhost:` dependem dele. |
| privesc: `fReconToken` | O que conta como reconhecimento e como se distinguem os comandos distintos: alterar um token altera a rapidez com que uma sessão atinge os limiares. |
| privesc: `SessionTracker` e as portas de entrada (`sDoors`) | `root_without_door`: uma porta de entrada em falta na lista torna críticas sessões de root legítimas; uma a mais esconde exploits do kernel. `mExport`/`mImport` é o formato de `privesc.sessions`. |
| privesc: `parsers.py` | Os campos dos registos (`args`, `command`, `kind`, `uid`/`euid` do snoopy), o mascaramento das palavras-passe e o texto em bruto dos registos de auditoria; os formatos do snoopy que lê (o módulo nunca altera o `snoopy.ini`). |
| privesc: classificação dos registos de auditoria (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | O que se torna `file`, `chmod`, `kmod`, `ptrace` e `denied`, e portanto as regras sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst e sensitive-denied; um número de syscall errado classifica mal os registos dessa arquitetura. |
| privesc: `surface.py` | O custo da análise (thread, limites) e o que o diagnóstico e `mSurfaceResult` comunicam; `privesc.surface` é a respetiva referência. |
| privesc: `mRequirements` / `fRequirementChecks` | Se o módulo pode ser ativado (qualquer fonte legível), o estado «Desativado» após uma primeira instalação cujos registos o `localsiem` ainda não consegue ler, e **Reconfigurar**; chamados sem armazenamento pela interface web e por `manage.py`: mantenha-os rápidos e sem root. Mantenha os ids `command_source`, `audit_log` e `syslog`. |
| Interface do núcleo (`backend/core/module.py`, `registry.py` do localSIEM) | Todos os módulos: uma assinatura de hook alterada, uma nova chave obrigatória do manifesto ou um novo contrato de registos e eventos quebra-os; suba o `core` no respetivo `module.json` quando precisarem do novo localSIEM. |

<a id="extensions"></a>
## 7. Pontos de extensão

### Como escrever um novo módulo

1. **Pasta**: crie `mod-<nome>/` na raiz deste projeto; `<nome>`, o nome do módulo, corresponde a `[a-z][a-z0-9_]{1,31}`. O prefixo `mod-` é só para a pasta: o `module.json`, a classe, as opções e os textos utilizam `<nome>`. Sem `__init__.py`.
2. **`module.json`**, por exemplo:

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

3. **Textos**: `locales/<idioma>.json` para cada um dos 15 idiomas do localSIEM com `name`, `summary` e a etiqueta e a ajuda de cada definição. As notas sobre os requisitos vão em `install_requirements` (`note`, para todos os sistemas, e `debian` e `alpine`), mostradas na caixa de diálogo Requisitos.
4. **Código**: `module.py` com uma subclasse de `Module` cujo `vName` é o id. Tem de implementar `mParse`, `mCreateCorrelator` e `mBuildEvent`, e normalmente `mDiscover`; os outros hooks são opcionais (secção 1). Importe os seus próprios ficheiros de forma relativa e o núcleo como `backend.core...`. Os dois módulos deste repositório são exemplos completos ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)); um esboço mínimo:

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # Cada registo é um evento próprio, sem esperar.

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

5. **Ação tomada**: decida o que significa «já resolvido» para o serviço (por exemplo, um IP já banido) e defina `action` como `blocked` nesse caso; adicione uma deteção apenas aos eventos sem ação tomada.
6. **Regras**: ficheiros YAML em `mod-<nome>/rules/`, devolvidos por `mRulesPath`, e as funções que chamam em `mRuleFunctions`.
7. **Requisitos**: se o módulo precisar de software no servidor (tal como o apache2 precisa do Apache e do ModSecurity 2), devolva uma verificação por requisito a partir de `mRequirements()` (o formato de `fCheck`: `status` `ok` ou `error`, e em `fix` o comando que o instala) e nunca instale esse software a partir do módulo: sem os respetivos requisitos, o módulo é instalado desativado. É executado sem armazenamento, também na interface web e em `manage.py`. Declare também, em `install_requirements` de `module.json`, os comandos que instalam esse software no Debian e no Alpine (um comando por linha, sem operadores de shell): a interface web mostra-os em Módulos › Instaláveis › Requisitos, tal como estão e com `sudo` à frente, antes de o módulo ser instalado.
8. **Instalação**: publique-o neste repositório (ramo `main`); aparece em Módulos › Instaláveis da interface web do localSIEM enquanto não estiver instalado, e **Instalar** copia a pasta `mod-<nome>/` para `/opt/localsiem/modules/<nome>/` e reinicia o coletor. O acesso de leitura aos respetivos `read_paths` precisa de root: a interface web mostra o comando (`manage.py setup-modules`). Um módulo não tem opção de configuração: nunca instala nada nem altera nada fora de `/opt/localsiem`, e nunca escreve nos registos do cliente, nem os roda ou elimina, nem altera o respetivo formato; se um servidor escrever os registos à sua maneira, o módulo adapta-se a ele, e o que falta ao servidor é um requisito. Para publicar uma nova versão, suba a `version`: Módulos › Instalados mostra o aviso e **Atualizar**, que mantém as definições e o estado ativado/desativado do módulo e só volta a mostrar o comando para o root se `read_paths` tiver mudado.
9. **Documentação**: atualize o README, este CODE e o MANUAL nos 15 idiomas.

### Como adicionar uma regra ao módulo apache2

Crie um ficheiro YAML em [mod-apache2/rules/](../mod-apache2/rules/) (cada chave e operador está descrito no início de [backend/core/rules.py](../../localSIEM/backend/core/rules.py)): `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` ou `sequence`), as condições (`when`, ou `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` e `search`. Os campos são procurados primeiro nas colunas do evento e depois em `fields`. A regra aparece na tabela de regras da página do módulo e é carregada pelo coletor assim que a nova versão do módulo for instalada: suba a `version` em `module.json`, publique-a e prima **Atualizar** em Módulos › Instalados.

### Como adicionar uma definição ao módulo apache2

Adicione-a a `settings` de [mod-apache2/module.json](../mod-apache2/module.json) com o respetivo tipo e predefinição, adicione a respetiva `label` e `help` aos quatro ficheiros de [mod-apache2/locales/](../mod-apache2/locales/) e leia-a com `self.mModuleSettings().get("<key>")`. O formulário, a validação e o recarregamento vêm do núcleo.

### Como adicionar uma verificação ao diagnóstico ou alterar uma gravidade

Uma verificação é um `fCheck(id, status, title, detail, fix)` em `fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)); mantenha o `id` estável e coloque em `fix` o excerto ou o comando exato, apenas para requisitos que não sejam registos: uma verificação sobre os registos do cliente apenas os descreve, e o que o localSIEM consegue ou não ler deles, sem `fix`. As gravidades das deteções do ModSecurity são alteradas em [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) (`low`, `medium`, `high`, `critical`).

### Como adicionar uma regra ao módulo privesc

Crie um ficheiro YAML em [mod-privesc/rules/](../mod-privesc/rules/), como os do Apache. Faça corresponder as colunas (`method`, `uri`, `path`, `vhost`, `action`) e os campos dos eventos (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...), nunca a chave de uma regra de auditoria; adicione `ignored: {not: true}` para que os utilizadores ignorados nunca a disparem, e `action: none` quando só conta o que foi realmente executado. Se a condição precisar de estado ou de lógica (uma sequência da mesma sessão, uma verificação de um ficheiro), calcule um indicador em `PrivescModule.mAnalyzeCommand` (todas as fontes) ou em `mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (uma fonte) e faça a regra corresponder a ele.

### Como adicionar um comando de reconhecimento, uma ferramenta ou um exploit ao módulo privesc

- Reconhecimento: adicione o programa a `sReconSimple`, ou um ramo a `fReconToken` que devolva um token por tipo de pergunta ([mod-privesc/commands.py](../mod-privesc/commands.py)). Um token que muda com cada argumento inflaciona as contagens.
- Ferramentas e exploits: adicione uma expressão regular à lista de [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) ou de [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) (sem distinção entre maiúsculas e minúsculas, comparada com a linha de comandos); o administrador também as pode adicionar a partir das definições (`rules.<id>.lists`).

### Como adicionar uma fonte ou um tipo de registo de auditoria ao módulo privesc

- Um caminho sensível: adicione-o a `lSensitivePaths` de [mod-privesc/module.py](../mod-privesc/module.py) com o respetivo grupo (ou um novo grupo e uma regra que corresponda a `sensitive_group`). Um tipo de chamada de sistema: adicione o respetivo nome aos conjuntos de `mAuditSyscall` e o respetivo número a cada tabela de `dSyscallTables`. Nunca dependa da chave de uma regra de auditoria (no máximo, adicione-a a `dKeyHints`) e nunca instale regras de auditoria: o servidor regista o que o respetivo administrador decide, e o diagnóstico descreve-o (`dAuditKinds` de [doctor.py](../mod-privesc/doctor.py)).
- Uma fonte: devolva-a a partir de `fDiscoverSources` com um novo `kind`, analise-a em `mParse` e construa os respetivos eventos em `mBuildEvent` com as mesmas colunas e campos que as outras, para que as regras funcionem sem alterações.
