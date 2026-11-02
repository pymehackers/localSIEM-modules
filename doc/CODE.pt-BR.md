# Referência técnica do localSIEM-modules

Este CODE também está disponível em:\
[de-DE](CODE.de-DE.md), [en-GB](CODE.en-GB.md), [en-US](CODE.md), [es-AR](CODE.es-AR.md), [es-ES](CODE.es-ES.md), [fr-FR](CODE.fr-FR.md), [he-IL](CODE.he-IL.md), [hi-IN](CODE.hi-IN.md), [it-IT](CODE.it-IT.md), [ja-JP](CODE.ja-JP.md), [ko-KR](CODE.ko-KR.md), pt-BR, [pt-PT](CODE.pt-PT.md), [ru-RU](CODE.ru-RU.md), [zh-CN](CODE.zh-CN.md)

## Índice

1. [Arquitetura e decisões de design](#architecture)
2. [Mapa de módulos](#modules)
3. [Símbolos principais](#symbols)
4. [Fluxos principais (call paths)](#flows)
5. [Pontos de entrada](#routes)
6. [Análise de impacto](#impact)
7. [Pontos de extensão](#extensions)

[Instalação](README.pt-BR.md) · [Manual do usuário](MANUAL.pt-BR.md) · [Referência técnica do localSIEM](../../localSIEM/doc/CODE.pt-BR.md)

<a id="architecture"></a>
## 1. Arquitetura e decisões de design

Este projeto contém os módulos instaláveis do localSIEM (projeto irmão `../localSIEM`). Ele não tem serviço nem instalador próprios: os módulos são instalados somente pela interface web do localSIEM, em Módulos › Instaláveis (são atualizados e desinstalados em Módulos › Instalados), que baixa este repositório (branch `main`) e copia a pasta de cada módulo, `mod-<name>/`, para `/opt/localsiem/modules/<name>/`; o instalador do localSIEM instala só o núcleo, nunca um módulo, e o localSIEM não tem módulos próprios. Os processos do localSIEM (coletor, interface web, `manage.py`) o carregam. O prefixo `mod-` pertence só ao nome da pasta neste repositório: o próprio módulo (o `id` do `module.json` dele, as opções, as configurações e a pasta instalada dele) mantém o nome sem o prefixo. Hoje há dois módulos: `apache2` (pasta `mod-apache2/`) e `privesc` (pasta `mod-privesc/`).

### Por que os módulos ficam fora do núcleo

O núcleo do localSIEM ([backend/core/](../../localSIEM/backend/core/)) é genérico: o armazenamento, a pesquisa, o motor de regras, o agrupamento, a fila do SOC, o heartbeat e a saúde não sabem nada sobre o Apache. O que um serviço significa (onde estão os logs dele, como são delimitados e analisados, como os registros se tornam um único evento, o que conta como já resolvido, as regras e os requisitos dele) fica em um módulo. Manter os módulos em um projeto próprio significa que:

- um módulo tem versão (`version`), declara o localSIEM mínimo de que precisa (`core`) e é atualizado, adicionado ou desativado sem uma nova versão do localSIEM;
- o núcleo não importa nenhum módulo pelo nome e não tem módulos próprios: o registro ([backend/core/registry.py](../../localSIEM/backend/core/registry.py)) só varre `/opt/localsiem/modules/` (`LOCALSIEM_MODULES_PATH` nas cópias de desenvolvimento), onde a interface web instala os módulos deste repositório;
- um módulo que não consegue carregar nunca impede os outros: o erro dele é listado na interface web (estado «Erro») e por `manage.py modules`;
- um módulo nunca modifica o núcleo: `backend/core/module.py` e `backend/core/registry.py` são o contrato inteiro.

### O contrato: module.json, locales e uma subclasse de Module

**`module.json`** (verificado por `fReadManifest`):

| Chave | Padrão | Significado | apache2 | privesc |
|---|---|---|---|---|
| `id` | obrigatório | Nome da pasta do módulo sem o prefixo `mod-` (o nome da pasta instalada), `[a-z][a-z0-9_]{1,31}`; também o `vName` da classe | `apache2` | `privesc` |
| `version` | `"0"` | Versão do módulo, mostrada na interface web e por `manage.py modules` | `1.3.2` | `1.1.2` |
| `core` | `"0"` | Versão mínima do localSIEM de que precisa; uma maior que o `cVersion` do localSIEM instalado significa que o módulo não é carregado | `2.2.0` | `2.2.0` |
| `entry` | obrigatório | `"file:Class"`: `file` sem `.py` (`[a-z][a-z0-9_]{0,63}`), `Class` uma subclasse de `Module` | `module:ApacheModule` | `module:PrivescModule` |
| `default_enabled` | `true` | Se ele funciona até que o administrador decida (`modules.<id>.enabled`) | `true` | `true` |
| `read_paths` | `[]` | Pastas absolutas que o localSIEM, como root, permite ao usuário `localsiem` ler (o comando que a interface web mostra depois de instalar, depois de **Reconfigurar** e depois de uma atualização que as altera) | `["/var/log/apache2"]` | `["/var/log/audit"]` |
| `install_requirements` | `{}` | Comandos que instalam no servidor, como root, o software de que o módulo precisa, para cada sistema (`debian`, `alpine`): um comando por linha, sem operadores de shell, porque a interface web também os mostra com `sudo` na frente (`fCheckInstallRequirements` do núcleo). Mostrados em Módulos › Instaláveis › Requisitos, nunca executados | Debian: Apache, ModSecurity 2, o CRS, `a2enmod`, a configuração recomendada do ModSecurity se não houver nenhuma, reinicialização; Alpine: Apache | Debian: auditd e rsyslog; Alpine: auditd |
| `setup_option` | — | Não é usado por nenhum módulo: o núcleo o ignora (o registro o descarta), porque um módulo nunca altera o servidor; os arquivos `module.json` de versões antigas ainda podem tê-lo | não definido | não definido (`--configure-privesc` foi removido na 1.1.0) |
| `settings` | `[]` | Descrição de cada configuração: a interface web monta o formulário dela a partir disso | 6 configurações | 13 configurações |

Cada configuração tem uma `key` (`[a-z][a-z0-9_]{1,31}`), um `type`, normalmente um `default`, e os atributos do tipo dela. `fValidateSettings` / `fCleanValue` / `fCleanRecords` verificam o que o administrador salva:

| Tipo | Atributos | Controle da interface web | Valores aceitos |
|---|---|---|---|
| `boolean` | — | caixa de seleção | `true` / `false` |
| `integer` | `min`, `max` | campo numérico | um inteiro dentro de `min`..`max` |
| `string` | `max_length` (500) | campo de texto | texto sem caracteres de controle, sem espaços nas pontas, até `max_length` |
| `path` | — | campo de texto monoespaçado | vazio ou absoluto (começa com `/`), até 1024 caracteres |
| `choice` | `choices` (obrigatório), `required` | lista (com «—» quando não é obrigatório) | um de `choices`, ou vazio |
| `records` | `fields` (obrigatório: configurações dos outros tipos), `max_items` (50) | um bloco por registro com Adicionar e Remover | uma lista de até `max_items` registros; cada campo é verificado, os campos `required` não podem ficar vazios e os campos vazios são descartados |

**`locales/<language>.json`** (de-DE, en-GB, en-US, es-AR, es-ES, fr-FR, he-IL, hi-IN, it-IT, ja-JP, ko-KR, pt-BR, pt-PT, ru-RU, zh-CN), lido por `fReadTexts` e mostrado pela interface web (`modules.js fModuleText`, que recorre ao en-US e depois à chave):

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

Um arquivo de locale ausente ou corrompido só perde o idioma dele.

**A subclasse de `Module`** ([backend/core/module.py](../../localSIEM/backend/core/module.py)). O registro a cria como `Class(pSettings, pMasker, pStorage, pManifest)`. Os hooks dela:

| Hook | Chamado por | Padrão | `ApacheModule` | `PrivescModule` |
|---|---|---|---|---|
| `mStart()` | coletor, uma vez, com o armazenamento pronto | nada | salva `apache.first_start` (início dos dias de aprendizado) | salva `privesc.first_start`; carrega `privesc.sessions`, `privesc.surface` e `privesc.health` |
| `mEnabled()`, `mModuleSettings()`, `mReload()` | coletor, interface web | de `modules.<id>` sobre os padrões do `module.json` | herdado | herdado; `mReload` também esvazia o cache de `mSettings` |
| `mDiscoveryInterval()` | coletor (o mais curto dos módulos ativados, pelo menos 60 s) | `discovery_interval_seconds` ou 3600 | herdado | herdado (padrão 300) |
| `mDiscover()` | coletor (início, intervalo, recarga, pedido de diagnóstico), `manage.py doctor` | `[]` | fontes `{key, path, kind, format, vhost, audit_type, storage_dir}` a partir da configuração do Apache e das fontes manuais | `fDiscoverSources`: o log de auditoria e o syslog |
| `mCreateFramer(pSource)` | coletor, por fonte | `LineFramer` | `AuditFramer` para o log de auditoria serial nativo | herdado (`LineFramer`) |
| `mParse(pSource, pUnit, pReceived)` | coletor, por unidade | obrigatório | registro de `access`, `error` ou `audit` | registro de `audit` ou `syslog` |
| `mCreateCorrelator()` | coletor, no início | obrigatório | `Correlator` (janela e correlação fraca a partir das configurações do núcleo) | `Correlator`: registros de auditoria por serial (EOE ou 2 s); linhas do syslog na hora |
| `mBuildEvent(pTransaction)` | coletor, por transação vencida | obrigatório | evento com `action` e `detections` | evento com os indicadores aos quais as regras correspondem; sem detecções próprias |
| `mRulesPath()` / `mRuleFunctions()` | coletor, ao carregar as regras | `None` / `{}` | `rules/` da pasta dele / `{"apache2.new_php": mIsNewPhp}` | `rules/` da pasta dele / `{}` herdado |
| `mDetectionFromSignal(pEvent, pSignal)` | coletor, por sinal de regra (opcional: procurado com `hasattr`) | detecção genérica | detecção com detalhes da requisição e `{rule: {id, count}}` | detecção com usuário, comando, programa, sessão, processo pai, arquivo... |
| `mEnrich(pDetection)` | coletor, com o grupo, antes de montar o alerta | `{}` | contexto do IP na última hora | contexto da sessão: início visto, porta, endereço SSH, últimos 20 comandos |
| `mDoctor()` | coletor (estado `<id>.doctor`), `manage.py doctor` | `[]` | `fRunDoctor` | `fRunDoctor` (auditd e o que as regras dele registraram, syslog, snoopy, o que o módulo vê, arquivos da versão 1.0.0, superfície de ataque) |
| `mHealth(pNow)` | coletor, a cada 60 s, só módulos ativados | `[]` | ModSecurity descarregado ou Off, falta o IP real do cliente (no máximo a cada 300 s) | salva as sessões; resultados da varredura; a cada 300 s: auditd parado, arquivos sensíveis graváveis (a cada hora), inicia a varredura de programas setuid |
| `mSkipped()` | estado do coletor, `manage.py doctor` | `[]` | logs por pipe, logs cobertos pelo `GlobalLog`, logs de acesso sem dados (`format_without_data`) | syslog não lido (auditd em execução, `syslog_mode` never), log de auditoria ausente |
| `mSetLowDisk(pLowDisk)` | coletor, nível do disco | nada | para de armazenar cabeçalhos e corpos de auditoria | herdado |
| `mDisplayRecord(pRecord)` | interface web, cartão da requisição | `{}` | cabeçalhos e corpo do registro de auditoria armazenado (`fAuditDisplay`) | herdado |
| `mRequirements()` | núcleo, localSIEM 2.2.0 ou mais recente: primeira instalação, início e recarga do coletor, **Reconfigurar** na interface web, `manage.py modules` e `doctor` | `[]` (sem requisitos) | `apache_config` e `modsecurity` (`fRequirementChecks`) | `command_source`: qualquer fonte que o `localsiem` possa ler, o log de auditoria (auditd em execução, fora de um contêiner) ou o syslog (com snoopy, se instalado); `audit_log` / `syslog` quando uma fonte existe mas não pode ser lida |

O núcleo não tem mais `mSetupSnippet` nem `mApplySetup`: os módulos não têm opções de configuração e nunca alteram o servidor.

Os registros são dicts com `time`, `received`, `module` (o id: o coletor escolhe o correlacionador por ele), `source`, `source_key`, `correlation`, `parse_status` (`ok`, `partial`, `unparsed`), `fields` e `raw` (mascarado), mais, opcionalmente, `search` (o texto indexado para a pesquisa de texto completo). Os eventos têm as colunas da tabela de eventos (`lEventColumns` em `storage_sqlite.py`) mais `record_ids`, `rule_hits` e `detections`. Uma detecção tem `module`, `vhost`, `ip`, `category`, `severity`, `rule`, `type`, `description`, `search`, `details`, `time` e `uid`.

### Requisitos: um módulo nunca instala o que monitora

Instalar um módulo nunca instala o software que ele monitora: o módulo apache2 não instala o Apache nem o ModSecurity, e o módulo privesc não instala o auditd, um daemon de syslog nem o snoopy (o requisito dele, `command_source`, é qualquer fonte que o usuário `localsiem` possa ler: o log de auditoria com o auditd em execução fora de um contêiner, ou o syslog; `fRequirementChecks` de `mod-privesc/doctor.py`). O próprio módulo define o que precisa antes de poder ser ativado, em `mRequirements()` (localSIEM 2.2.0 ou mais recente): uma lista de verificações no formato do diagnóstico, atendida quando nenhuma tem o status `error`. O módulo apache2 retorna `apache_config` (uma configuração do Apache é encontrada: `apache2.conf`, `httpd.conf` ou o arquivo da configuração `config_file`) e `modsecurity` (o `mod_security2` está carregado; o ModSecurity 3 não conta), que `fRequirementChecks` obtém das primeiras verificações do diagnóstico; sem o Apache, as duas são erros. O que instala esse software é declarado em `install_requirements` do `module.json`: a interface web o mostra antes de instalar o módulo (Módulos › Instaláveis › Requisitos), para o sistema do servidor, e nunca o executa. O núcleo:

- instala o módulo desativado (`modules.<id>.enabled = false`) quando falta um requisito na primeira instalação dele e o administrador nunca decidiu; uma atualização nunca altera `enabled`;
- não permite ativá-lo enquanto faltar um requisito: o interruptor fica bloqueado e a interface web mostra os requisitos com o `fix` deles;
- nunca desativa por conta própria um módulo que está ativado e perde um requisito: o diagnóstico e os avisos de saúde dele (`mHealth`: «ModSecurity is no longer loaded») relatam isso, e desativá-lo os silenciaria;
- verifica os requisitos novamente quando o coletor inicia ou recarrega, e com **Reconfigurar** na página do módulo (também quando ele está desativado): se forem atendidos, desbloqueia o interruptor, o administrador ativa o módulo, e a interface web mostra o comando a executar como root que permite ao `localsiem` ler os logs criados depois da instalação (`read_paths`).

### Carregado como namespace package

Não há nenhum `__init__.py` em lugar nenhum (namespace packages implícitos do Python 3.13). `fRegisterPackage` cria o pacote `localsiem_modules` com a pasta dos módulos como `__path__`, e `fLoadClass` importa `localsiem_modules.<id>.<file>`, verifica que a classe é um `Module` e que o `vName` dela é igual ao `id`. Consequências para o código de um módulo:

- os próprios arquivos dele são importados de forma **relativa** (`from .parsers import AccessParser`);
- o núcleo é importado como **`backend.core...`** (`from backend.core.module import Module`): os processos do localSIEM colocam a pasta do localSIEM no `sys.path`;
- só estão disponíveis a biblioteca padrão e as dependências do localSIEM (o ambiente virtual dele, `/opt/localsiem/venv/`, por exemplo PyYAML): o localSIEM não instala nada para um módulo.

### Formulário de configurações montado a partir do manifesto

Um módulo não tem HTML próprio. A interface web lê `settings` do `module.json` e os textos de `locales/`, monta o formulário (`modules.js fBuildSettings`, `fRecordsEditor`), valida o que é salvo com `fValidateSettings` e armazena só os valores que o administrador salvou em `settings.json`, sob `modules.<id>`; `enabled` também fica ali. O módulo lê `mModuleSettings()`: os padrões do `module.json` com os valores salvos por cima. Por isso, adicionar uma configuração não exige nenhuma alteração na interface web nem no núcleo.

Configurações do núcleo que o módulo apache2 também lê de `self.dSettings`: `host`, `correlation_window_seconds` (5), `weak_correlation_seconds` (2), `below_threshold_severity` (`low`) e `health.single_ip_percent` / `health.single_ip_minimum_requests` (90 / 100). `mModuleSettings()` também repassa chaves salvas sob `modules.apache2` que o `module.json` não declara: `mDiscover` lê `document_roots` (`{vhost: folder}`, sobre os DocumentRoots descobertos) dessa forma; só pode ser definido editando o `settings.json`.

### O princípio da «ação tomada»

Só vai para o SOC o que ninguém resolveu ainda. No módulo apache2, a ação tomada é lida da fonte mais confiável: o log de auditoria (`Action: Intercepted (phase N)` no formato nativo, `audit_data.action.intercepted/phase` em JSON) e depois o error.log (`Access denied with code NNN (phase N)`). Um 403 sem nenhum rastro do ModSecurity não é um bloqueio (`fields.doubtful_block`).

| Situação | `action` | Detecção (para o SOC) |
|---|---|---|
| Interceptada nas fases 1-2 (a aplicação nunca a recebeu) | `blocked` | nenhuma: `mAssess` retorna `None`; contada no contexto de alertas posteriores |
| Interceptada nas fases 3-4 | `none` | sim, `blocked_late` (alta), ou `success_indicator` com um erro de banco de dados |
| Correspondências com o motor em `DetectionOnly` | `none` | sim |
| Correspondências abaixo do limite de anomalia | `none` | sim, `below_threshold` (baixa) |
| Sinais das regras YAML | `none` | sim |

As severidades vêm de `severity.yaml` (`fLoadSeverityTable`; um arquivo ausente ou um valor inválido mantém o padrão embutido): `crs_not_blocked_2xx` high, `crs_not_blocked_other` medium, `blocked_late` high, `success_indicator` critical (regra de saída 950-955 não bloqueada, ou um erro de banco de dados na mesma requisição), `below_threshold` low (a configuração do núcleo `below_threshold_severity` tem precedência). «Acima do limite» significa que uma regra 949xxx correspondeu ou que a pontuação informada pelo ModSecurity atingiu o limite; uma pontuação calculada a partir das severidades das regras é só uma estimativa e não decide. O limite é o das mensagens; se não houver, `anomaly_threshold`; se não houver, o de `crs-setup.conf`; se não houver, 5.

### Como funciona o módulo apache2

1. **Descoberta** (`discovery.py`): `ApacheConfig` lê a configuração diretamente (`Include`, `IncludeOptional`, `Define`, `${VARS}` do `envvars` do Debian, `<VirtualHost>`, `<IfModule>` comparado com os módulos carregados), como o usuário `localsiem` e sem `apache2ctl`. `fDiscoverSources` transforma `CustomLog`/`GlobalLog`/`TransferLog`, `ErrorLog` e `SecAuditLog` em fontes com a chave estável `apache:<kind>:<real path>`. Um `GlobalLog` cujo formato tem `%v` cobre todos os vhosts (os outros logs de acesso são ignorados); os logs por pipe e o syslog são ignorados, assim como os logs de acesso cujo formato não tem nenhuma diretiva `%` (o Apache grava literalmente um apelido que nenhum `LogFormat` define: `format_without_data`, a menos que outro `CustomLog` com dados grave no mesmo arquivo; o diagnóstico informa isso, sem correção, já que o formato dos logs nunca é alterado); as fontes manuais vêm primeiro e um arquivo é lido uma só vez.
2. **Delimitação e análise** (`parsers.py`, `logformat.py`, `modsec.py`): as linhas de acesso são analisadas com uma expressão regular gerada a partir do `LogFormat` delas (o último formato que funcionou é testado primeiro); as linhas de erro são classificadas (`modsecurity`, `database`, `php`, `crash`, `apache`); os registros de auditoria são lidos como JSON (uma linha, cortada antes de `matched_rules`), serial nativo (`AuditFramer` junta de `--id-A--` até `--id-Z--`) ou concorrente (a linha de índice aponta para um arquivo sob `SecAuditLogStorageDir`). Tudo é mascarado; o que não se encaixa é mantido como `unparsed`.
3. **Correlação** (`correlate.py`): os registros com o mesmo `UNIQUE_ID` formam uma transação, que espera a janela de correlação e a marca d'água das fontes que estão se atualizando; uma linha de acesso sem `UNIQUE_ID` (os formatos que o Apache grava por padrão) é emparelhada por `mPair`, quando ela ou os registros da requisição dela vencem, com os registros do ModSecurity que não têm linha de acesso: mesmo IP do cliente, hora dentro de ±2 s (a linha tem segundos inteiros) e os mesmos método, URI, status e caminho quando os dois lados os conhecem; vence o candidato que concorda em mais deles, depois o mais próximo, depois o mais antigo, e o evento é marcado como fraco. As linhas do error.log sem `UNIQUE_ID` se juntam na hora à transação mais próxima do IP delas. Uma transação com um `UNIQUE_ID` e uma linha do ModSecurity no error.log, enquanto chegam registros de auditoria (`vAuditSeen`), também espera o próprio registro de auditoria (`mWaitsForAudit`), no máximo `cAuditWaitSeconds` (120 s) desde o primeiro registro dela: o ModSecurity grava as linhas das regras dele enquanto a requisição é executada e o registro de auditoria quando ela termina, então, caso contrário, uma requisição lenta viraria dois eventos; quando o registro de auditoria chega, a linha de acesso tem mais `cAfterAuditSeconds` (2 s).
4. **Evento** (`ApacheModule.mBuildEvent`): campos obtidos do acesso, depois da auditoria, depois do erro; o vhost a partir de `%v` ou, sem ele, do cabeçalho Host e da porta local do registro de auditoria (`mVhostName`); com uma linha de acesso de segundos inteiros, a hora do registro de auditoria; `fSummarize` fornece regras, categorias, pontuação, limite e interceptação; a ação tomada e `mAssess` decidem a detecção.
5. **Regras, enriquecimento, diagnóstico e saúde**: as regras YAML de `rules/` são executadas em cada evento (motor do núcleo); `mEnrich` adiciona o contexto do IP; `fRunDoctor` verifica os requisitos e descreve os logs, sem alterar nada; `mHealth` monitora o ModSecurity e o IP real do cliente. O módulo não tem opção de configuração: como root, o localSIEM só dá ao `localsiem` acesso de leitura a `/var/log/apache2`.

### Decisões de design que vale a pena conhecer

- **Sem instalador próprio**: os módulos são instalados (Módulos › Instaláveis), atualizados (**Atualizar**, em Módulos › Instalados) e desinstalados (**Desinstalar**) somente pela interface web do localSIEM, que baixa este repositório e os instala com `backend/core/catalog.py` (descompactação segura, uma instalação por vez, troca atômica da pasta). O que precisa de root (acesso de leitura aos `read_paths`) é feito pelo localSIEM: depois de instalar (e depois de uma atualização que altera `read_paths`), a interface web mostra o comando a executar como root.
- **Os logs do cliente são apenas lidos**: um módulo nunca grava nos logs dos serviços que monitora, nem os rotaciona, trunca, move ou exclui, e nunca altera o formato deles; o módulo apache2 também nunca altera a configuração do Apache ou do ModSecurity (ele não tem `setup_option`). Se um servidor grava os logs em um formato próprio (um `LogFormat` próprio, o IP do cliente do `mod_remoteip`), o módulo se adapta: `AccessFormat` monta o analisador de cada log de acesso a partir do `LogFormat` dele, e `fCanPair` / `Correlator.mPair` unem as linhas sem `UNIQUE_ID`. O diagnóstico apenas descreve os logs e o que o localSIEM consegue ou não ler deles: as verificações `log_format`, `log_format_without_data`, `remoteip`, `audit_log` e `sanitise` não têm `fix`; só o que não é um log (ModSecurity, o CRS, `SecRuleEngine`, `mod_unique_id`, as permissões de leitura do `localsiem`) vem com um. `--configure-apache` foi removido na versão 1.3.0; `localsiem_combined` continua em `dKnownFormats` para os servidores que já o gravam, e o instalador do localSIEM exclui o `localsiem.conf` que as versões antigas gravaram (`--uninstall`, `--reinstall`).
- A **parte K** (`matched_rules`) e a **parte E** (corpo da resposta) do log de auditoria nunca são armazenadas. Os cabeçalhos e o corpo ficam só no registro bruto mascarado; o cartão da requisição os reconstrói (`fAuditDisplay`). O índice de texto completo recebe um texto reduzido (`search`: linha da requisição, host, user agent e o id, a mensagem e os dados de cada regra).
- **O texto bruto é reconstruído a partir das partes mascaradas**: o registro de auditoria original pode conter senhas e cookies.
- **A interface web e as ferramentas criam o módulo sem armazenamento** (`pStorage` é `None` em `WebContext.mModule` e em `manage.py`): o construtor e os hooks que elas chamam não devem usar o armazenamento.
- **Estado no banco de dados de eventos**: `apache.first_start` (dias de aprendizado), `apache.health` (o que já foi relatado, para que uma reinicialização não o repita) e `apache2.doctor` (gravado pelo coletor). Os dois primeiros, assim como as chaves de fonte `apache:<kind>:<real path>`, mantêm o nome que o módulo tinha antes de se chamar apache2: um servidor que tinha o módulo `apache` mantém os dias de aprendizado, a memória de saúde e as posições de leitura dele (com uma nova chave de fonte, cada log com menos de 5 MiB seria lido novamente desde o início). As horas da memória de saúde estão no formato nativo do projeto (`2026-10-29@13-59-59.723`, UTC); um estado salvo por uma versão antiga, com segundos epoch, é convertido ao ser carregado.
- **Segurança dos caminhos**: `mIsNewPhp` recusa `..` e fica dentro do DocumentRoot; `fReadConcurrentEntry` fica dentro de `SecAuditLogStorageDir` e lê no máximo 8 MiB; o correlacionador mantém no máximo 50 000 transações pendentes.

### Como funciona o módulo privesc

A pergunta não é «alguém executou `whoami`?» (os administradores fazem isso todos os dias), mas «esta sessão está percorrendo o caminho de um escalonamento, e chegou lá?». O módulo transforma duas fontes em eventos com um único significado (`vhost` a pessoa, `method` o tipo, `uri` o comando, `path` o programa ou arquivo, `ip` o endereço SSH, `score` o reconhecimento distinto da sessão), calcula indicadores sobre eles e deixa que as regras YAML decidam o que vai para o SOC.

1. **Descoberta** (`discovery.py`): `fDiscoverSources` retorna o log de auditoria (`fAuditLogPath`: configuração, `log_file` do `auditd.conf`, `/var/log/audit/audit.log`; também quando o auditd está em execução e o `localsiem` ainda não consegue lê-lo, para que o núcleo o relate) e o syslog (`fSyslogPath`) quando `syslog_mode` assim indica (`auto`: auditd fora de execução, log dele ilegível ou snoopy instalado). Ele também reúne o que o diagnóstico precisa: contêiner (`fContainer`, legível sem root: `/run/systemd/container`, `/run/.containerenv`, `/.dockerenv`, `/proc/self/cgroup`, `systemd-detect-virt`), binário e pid do auditd, snoopy, se cada log pode ser lido (`fReadState`: `readable`, `unreadable` ou `missing`) e os arquivos que a versão 1.0.0 deixou (`fLegacyLeftovers`). `Accounts` lê novamente `/etc/passwd`, `/etc/group` e `UID_MIN` quando eles mudam, e classifica um uid como `root`, `admin` (membro de `admin_groups`), `user` ou `service`.
2. **Análise** (`parsers.py`): `fParseAuditLine` lê `type=... msg=audit(<time>:<serial>): k=v ...`, a parte de espaço de usuário `msg='...'`, a parte enriquecida depois de `\x1d`, junta os argumentos de `EXECVE` (também os divididos em pedaços `aN[i]`), decodifica os valores hexadecimais (`proctitle`, `cmd`, `cwd`, `name`, `exe`, `aN`...) e **reconstrói o texto bruto a partir dos valores decodificados e mascarados** (o hexadecimal de uma senha a manteria); `search` recebe o comando decodificado. `fParseSyslogLine` lê timestamps ISO e clássicos (com ou sem o `facility.priority` do busybox) e `fParseSyslogMessage` entende o snoopy (os formatos padrão dele da 2.4 e da 2.5, `uid:alice(1000)/root(0)` incluído, e o que a versão 1.0.0 definia), sudo, su (util-linux e busybox), pkexec, doas, `pam_unix` e sshd. `fMaskCommand` mascara senhas nas linhas de comando antes do mascarador do núcleo.
3. **Correlação** (`correlate.py`): os registros de auditoria com o mesmo serial formam uma transação, que vence em `EOE`, na hora para os tipos de espaço de usuário de um único registro (`USER_*`, `CRED_*`, `DAEMON_*`...), ou depois de 2 s sem registros; no máximo 50 000 pendentes. As linhas do syslog vencem na hora.
4. **Evento** (`PrivescModule.mBuildEvent`): `mAuditEvent` separa por tipo: `EXECVE` → `mAuditExec` (bit setuid do programa a partir do registro `PATH` ou de `stat`, `suid_escape` quando o euid é 0, o uid real não é e o programa não é setuid, capabilities obtidas de `BPRM_FCAPS`, `root_without_door`, `parent_interpreter` quando um shell é executado como root iniciado por um interpretador de um usuário que não é o root, o processo pai a partir da memória de processos); `USER_*`/`LOGIN` → `mAuditUser` (sessão iniciada, endereço SSH, portas: `USER_START`/`USER_CMD` de sudo, su, pkexec, doas, run0, systemd; falhas); `CONFIG_CHANGE` (`audit_disabled`, `audit_rule_removed` para qualquer regra removida), `DAEMON_*` (`auditd_stopped_manually` quando o remetente não é o pid 1), `ANOM_ABEND` (`crash_suspicious`); qualquer outro `SYSCALL` → `mAuditSyscall`, que o classifica pela chamada de sistema (`fSyscallName`: o nome do formato enriquecido, ou o número na tabela da arquitetura dele), pelos argumentos e pelos registros `PATH` dele, nunca pela chave da regra: `denied` (open, exec ou truncate que falhou com `EACCES`/`EPERM` para uma pessoa), `kmod`, `ptrace` (`ptrace_attach` para `PTRACE_ATTACH`/`PTRACE_SEIZE`), `chmod` (modo com o bit setuid ou setgid, não em uma pasta, com `writer_allowed`) e `file` (uma alteração de um caminho de `lSensitivePaths`, com `sensitive_group` e `writer_allowed`; a chave, por meio de `dKeyHints`, só quando nenhum caminho pode ser resolvido). `mSyslogEvent` trata o snoopy como `exec` (`suid_escape` a partir de `stat`; sem `filename`, o programa a partir da primeira palavra do comando) e sudo, su, pkexec, doas, login e pam. Cada comando passa por `mAnalyzeCommand`: token de reconhecimento (`fReconToken`) e tokens distintos da sessão na janela (`recon_burst`, `recon_massive`, `score`), downloads executados por um shell (`cDownloadOnelinerRegex`, ou um downloader seguido de um shell com o mesmo processo pai), `compile_in_tmp`, os últimos comandos da sessão e, para contas de serviço, o programa (`fProgramKey`) comparado com o histórico dele (`mPathFirstSeen` do núcleo, depois de `learning_days`: `new_program`). `ignored` marca os usuários ignorados.
5. **Regras, enriquecimento, diagnóstico e saúde**: as 35 regras YAML de `rules/` decidem cada detecção (`mDetectionFromSignal`); `mEnrich` adiciona o contexto da sessão; `fRunDoctor` descreve o auditd e o que as regras dele registraram, o syslog, o snoopy, o que o módulo vê e o que não vê, os arquivos da versão 1.0.0 e a superfície de ataque; `mHealth` relata o auditd parado, os arquivos sensíveis graváveis e o resultado da varredura de programas setuid (`SurfaceScanner`, uma thread). O módulo não tem opção de configuração e não altera nada no servidor.

### Decisões de design do módulo privesc

- **Duas fontes, um único significado.** O auditd não pode ser evitado por um usuário, mas não funciona dentro de contêineres (a auditoria do kernel não tem namespaces); o snoopy vê cada programa nos contêineres, mas precisa do syslog; o syslog sozinho só fornece sudo, su, pkexec e doas. Nenhuma fonte vê os comandos internos do shell. As regras comparam colunas e indicadores, nunca a fonte, então uma fonte pode ser adicionada sem mexer nelas. O mesmo comando visto duas vezes gera um único alerta: o núcleo agrupa as detecções por módulo, usuário, IP, categoria e severidade.
- **Rajadas, não comandos.** O reconhecimento é um token por tipo de pergunta (`whoami`, `read:/etc/passwd`, `find:-perm:`...), e só o número de tokens distintos de uma sessão em uma janela gera um alerta, com um limite mais alto para administradores e um terceiro para scripts. Os limites são configurações, não limites de regras: a regra só compara `recon_burst` / `recon_massive`.
- **O sucesso é o que mais importa.** `suid_escape` (um programa que não é setuid executado com euid 0 e um uid real que não é 0) e `root_without_door` (root em uma sessão cujo início foi visto e que nunca passou por sudo, su, pkexec ou doas) são os dois sinais críticos de que um escalonamento funcionou, quase sem falsos positivos. Uma sessão cujo início não foi visto (sessões abertas antes do módulo, sessões esquecidas depois de um dia de inatividade) nunca é sinalizada.
- **As sessões sobrevivem às reinicializações.** `SessionTracker` mantém o início, o endereço SSH e a porta de cada sessão no estado `privesc.sessions` (salvo no máximo a cada minuto); os tokens de reconhecimento e os últimos comandos ficam na memória. As sessões ociosas por um dia são descartadas.
- **Só o que o servidor já tem.** O módulo nunca instala nada nem altera nada fora de `/opt/localsiem`: não carrega regras de auditoria, não mexe no `auditd.conf` nem no `snoopy.ini` e não instala nenhum hook. A versão 1.0.0 fazia isso (`--configure-privesc`: regras de auditoria com as chaves `lsiem_*`, `log_group = adm`, um hook de bash, o formato do snoopy); a versão 1.1.0 o removeu. Por isso, os registros de auditoria são classificados pelo tipo, pela chamada de sistema e pelos caminhos deles, de modo que quaisquer regras de auditoria funcionam (as do servidor, as regras de exemplo do STIG ou as regras `lsiem_*` que a 1.0.0 deixou); a chave é mantida em `fields.key` para as pesquisas e é só uma pista (`dKeyHints`). Os números das chamadas de sistema são lidos por arquitetura (`dSyscallTables`: x86_64, i386 e a tabela genérica de aarch64, riscv64 e loongarch64) quando o log não tem nomes enriquecidos. O diagnóstico descreve o que as regras do servidor registram e o que não registram; o `fix` dele é só um pacote a instalar ou o acesso de leitura do `localsiem`.
- **Legível significa legível.** O requisito é atendido por uma fonte que existe e que o `localsiem` consegue abrir (`fReadState`), não por um programa estar instalado: em uma primeira instalação, os logs costumam pertencer ao root, então o módulo fica desativado até o comando para o root (`manage.py setup-modules`) e **Reconfigurar**.
- **Os gerenciadores de pacotes não são atacantes.** As alterações de arquivos sensíveis e de bits setuid feitas pelas ferramentas de contas e de pacotes (`sAllowedWriters`), ou por programas cujos ancestrais conhecidos são gerenciadores de pacotes, definem `writer_allowed`, e as regras as ignoram.
- **A varredura nunca bloqueia o coletor.** `SurfaceScanner` percorre os `scan_paths` em uma thread própria, sem sair do sistema de arquivos de cada um, ignorando `/proc`, `/sys` e as pastas dos contêineres, até 3 milhões de arquivos ou 15 minutos; `mHealth` obtém o resultado quando ele está pronto. A primeira varredura é a referência; as seguintes relatam o que é novo.
- **A interface web e as ferramentas criam o módulo sem armazenamento**: `mDiscover`, `mDoctor` e `mRequirements` nunca o usam, e `mAnalyzeCommand` só chama `mPathFirstSeen` quando ele existe.
- **Estado no banco de dados de eventos**: `privesc.first_start` (dias de aprendizado), `privesc.sessions`, `privesc.surface` (a referência da varredura e o diagnóstico), `privesc.health` (o que já foi relatado, se o auditd estava em execução) e `privesc.doctor` (gravado pelo coletor). Os programas vistos das contas de serviço são linhas de `seen_paths` com o vhost `privesc:<account>`. As horas de `privesc.health` (a memória de saúde) e de `privesc.sessions` (`last` de cada sessão) estão no formato nativo do projeto (`2026-10-29@13-59-59.723`, UTC); um estado salvo por uma versão antiga, com segundos epoch, é convertido ao ser carregado.

<a id="modules"></a>
## 2. Mapa de módulos

| Módulo | Caminho | Responsabilidade | Depende de | Usado por |
|---|---|---|---|---|
| Manifesto | [mod-apache2/module.json](../mod-apache2/module.json) | id, versão, núcleo mínimo, entrada, caminhos de leitura, configurações (sem opção de configuração) | — | registro, interface web, `manage.py` |
| Módulo Apache | [mod-apache2/module.py](../mod-apache2/module.py) | `ApacheModule`: hooks, ação tomada, severidade, detecções, função de regra, enriquecimento, saúde | correlate, discovery, doctor, modsec, parsers; núcleo `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | coletor, interface web, `manage.py` |
| Descoberta | [mod-apache2/discovery.py](../mod-apache2/discovery.py) | `ApacheConfig` (analisador da configuração), fontes e logs ignorados, DocumentRoots | logformat (`dKnownFormats`) | module, doctor |
| Diagnóstico | [mod-apache2/doctor.py](../mod-apache2/doctor.py) | Verificações de requisitos; descreve os logs (formato, log de auditoria, mascaramento) sem propor alterá-los | discovery | module |
| Formatos de acesso | [mod-apache2/logformat.py](../mod-apache2/logformat.py) | `LogFormat` para expressão regular, horas para UTC, linha da requisição | núcleo `timeutil` | parsers, discovery |
| Analisadores | [mod-apache2/parsers.py](../mod-apache2/parsers.py) | access, error, audit (JSON, nativo, concorrente), `AuditFramer`, `fAuditDisplay` | logformat, modsec; núcleo `masking`, `timeutil` | module |
| ModSecurity | [mod-apache2/modsec.py](../mod-apache2/modsec.py) | Mensagens, categorias, faixas do CRS, pontuações, interceptação | — | parsers, module |
| Correlação | [mod-apache2/correlate.py](../mod-apache2/correlate.py) | `UNIQUE_ID`, emparelhamento sem ele (`mPair`), janela, marca d'água | núcleo `timeutil` | module (coletor) |
| Tabela de severidades | [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) | Severidades das detecções do ModSecurity | — | module (`fLoadSeverityTable`) |
| Regras | [mod-apache2/rules/](../mod-apache2/rules/) | Seis regras YAML | motor de regras do núcleo, `mIsNewPhp` | coletor (`RulesEngine`), interface web (`fRules`) |
| Textos | [mod-apache2/locales/](../mod-apache2/locales/) | Nome, resumo, rótulos e ajuda das configurações, opções | — | interface web |
| privesc: manifesto | [mod-privesc/module.json](../mod-privesc/module.json) | id, versão, núcleo mínimo, entrada, caminhos de leitura, 13 configurações (sem opção de configuração) | — | registro, interface web, `manage.py` |
| privesc: módulo | [mod-privesc/module.py](../mod-privesc/module.py) | `PrivescModule`: hooks, eventos das duas fontes, classificação dos registros de auditoria (caminhos sensíveis, chamadas de sistema por arquitetura), indicadores, detecções das regras, enriquecimento, saúde, resultados da varredura | commands, correlate, discovery, doctor, parsers, surface; núcleo `masking`, `module`, `query`, `timeutil`, `health`; PyYAML | coletor, interface web, `manage.py` |
| privesc: descoberta | [mod-privesc/discovery.py](../mod-privesc/discovery.py) | Fontes, contêiner, auditd, snoopy, syslog, se cada log pode ser lido, arquivos deixados pela versão 1.0.0, `Accounts` (usuários, grupos, tipo de conta) | — | module, doctor |
| privesc: analisadores | [mod-privesc/parsers.py](../mod-privesc/parsers.py) | Registros de auditoria (hexadecimal, `msg='...'`, enriquecidos), linhas do syslog (snoopy nos formatos habituais dele, sudo, su, pkexec, doas, pam, sshd), mascaramento das linhas de comando | núcleo `masking`, `timeutil` | module |
| privesc: correlação | [mod-privesc/correlate.py](../mod-privesc/correlate.py) | Registros de auditoria por serial (EOE, registros de espaço de usuário, 2 s); linhas do syslog na hora | — | module (coletor) |
| privesc: comandos | [mod-privesc/commands.py](../mod-privesc/commands.py) | Tokens de reconhecimento, programa de uma conta de serviço, shells, interpretadores, downloaders, portas, compiladores; `SessionTracker` | núcleo `timeutil` | module |
| privesc: superfície de ataque | [mod-privesc/surface.py](../mod-privesc/surface.py) | `SurfaceScanner` (setuid, setgid, capabilities), GTFOBins, arquivos sensíveis graváveis, grupos privilegiados | — | module, doctor |
| privesc: diagnóstico | [mod-privesc/doctor.py](../mod-privesc/doctor.py) | Descreve o auditd, o log dele e o que as regras dele registraram, o syslog, o snoopy, o que o módulo vê, os arquivos da versão 1.0.0 e a superfície (correções: só pacotes e acesso de leitura); requisito `command_source` (qualquer fonte legível) | discovery, surface; núcleo `timeutil` | module |
| privesc: regras | [mod-privesc/rules/](../mod-privesc/rules/) | 35 regras YAML | motor de regras do núcleo | coletor (`RulesEngine`), interface web (`fRules`) |
| privesc: tabela de severidades | [mod-privesc/severity.yaml](../mod-privesc/severity.yaml) | Severidades das detecções montadas pelo módulo (varredura, arquivos sensíveis) | — | module (`fLoadSeverityTable`) |
| privesc: textos | [mod-privesc/locales/](../mod-privesc/locales/) | Nome, resumo, rótulos e ajuda das configurações, opções | — | interface web |
| Núcleo: interface | [backend/core/module.py](../../localSIEM/backend/core/module.py) | `Module`, `LineFramer` | registry | módulos |
| Núcleo: registro | [backend/core/registry.py](../../localSIEM/backend/core/registry.py) | Encontrar, verificar e carregar módulos; padrões e validação das configurações | `config` | coletor, interface web, `manage.py`, `backend/core/catalog.py` |
| Núcleo: interface web | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) | Páginas Módulos (Instalados, Instaláveis, a página de um módulo) e API | registry, catalog, rules | navegadores |
| Núcleo: catálogo | [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) | Download e descompactação segura do repositório, lista com a ação de cada módulo (`install`, `update`, `incompatible`, `invalid`...) e `newer`, instalação ou atualização atômica (`previous`, `access_changed`), desinstalação, comando para o root: Módulos › Instaláveis e **Atualizar** / **Desinstalar** de Módulos › Instalados, a única forma de instalar módulos | registry | interface web |

<a id="symbols"></a>
## 3. Símbolos principais

| Símbolo | Arquivo:linha | O que faz |
|---|---|---|
| `ApacheModule` | [mod-apache2/module.py:68](../mod-apache2/module.py#L68) | O módulo apache2 (`vName = "apache2"`) |
| `fLoadSeverityTable` | [mod-apache2/module.py:54](../mod-apache2/module.py#L54) | `severity.yaml` sobre os padrões embutidos |
| `ApacheModule.mDiscover` | [mod-apache2/module.py:95](../mod-apache2/module.py#L95) | Analisa a configuração, fontes, logs ignorados, DocumentRoots |
| `ApacheModule.mThreshold` | [mod-apache2/module.py:105](../mod-apache2/module.py#L105) | Limite de anomalia: configuração, CRS ou 5 |
| `ApacheModule.mParse` | [mod-apache2/module.py:136](../mod-apache2/module.py#L136) | Unidade para registro, por tipo de fonte |
| `ApacheModule.mBuildEvent` | [mod-apache2/module.py:176](../mod-apache2/module.py#L176) | Transação para evento: campos, ação tomada, pontuações, detecção |
| `ApacheModule.mVhostName` | [mod-apache2/module.py:311](../mod-apache2/module.py#L311) | Cabeçalho Host ou hostname do ModSecurity para o vhost que o Apache escolheu (o que `%v` registra) |
| `ApacheModule.mAssess` | [mod-apache2/module.py:323](../mod-apache2/module.py#L323) | Severidade, nome da regra, descrição e detalhes do que vai para o SOC |
| `ApacheModule.mDetectionFromSignal` | [mod-apache2/module.py:385](../mod-apache2/module.py#L385) | Sinal de uma regra YAML para detecção |
| `ApacheModule.mIsNewPhp` | [mod-apache2/module.py:414](../mod-apache2/module.py#L414) | Função de regra `apache2.new_php` |
| `ApacheModule.mEnrich` | [mod-apache2/module.py:442](../mod-apache2/module.py#L442) | Contexto do IP (última hora) para o alerta |
| `ApacheModule.mHealth` | [mod-apache2/module.py:461](../mod-apache2/module.py#L461) | ModSecurity descarregado ou Off; falta o IP real do cliente |
| `ApacheModule.mDisplayRecord` | [mod-apache2/module.py:538](../mod-apache2/module.py#L538) | Cabeçalhos e corpo para o cartão da requisição |
| `ApacheModule.mRequirements` | [mod-apache2/module.py:545](../mod-apache2/module.py#L545) | Apache e ModSecurity 2: o que o módulo precisa antes de poder ser ativado |
| `ApacheConfig` | [mod-apache2/discovery.py:105](../mod-apache2/discovery.py#L105) | Analisador da configuração do Apache |
| `ApacheConfig.mDirective` | [mod-apache2/discovery.py:228](../mod-apache2/discovery.py#L228) | Diretivas lidas (logs, vhosts, módulos, ModSecurity) |
| `ApacheConfig.mVhostName` | [mod-apache2/discovery.py:358](../mod-apache2/discovery.py#L358) | Vhost de uma requisição a partir do cabeçalho Host e do endereço e porta locais dela, como o Apache o escolhe |
| `fSourceKey` / `fDiscoverSources` | [mod-apache2/discovery.py:403](../mod-apache2/discovery.py#L403) / [:408](../mod-apache2/discovery.py#L408) | Chave estável da fonte; fontes a ler e fontes ignoradas |
| `fRunDoctor` | [mod-apache2/doctor.py:46](../mod-apache2/doctor.py#L46) | Verificações de requisitos `{id, status, title, detail, fix}` |
| `fCanPair` | [mod-apache2/doctor.py:26](../mod-apache2/doctor.py#L26) | Se um formato de acesso pode ser unido sem `UNIQUE_ID` (IP do cliente, hora, linha da requisição, status) |
| `fRequirementChecks` | [mod-apache2/doctor.py:174](../mod-apache2/doctor.py#L174) | As verificações `apache_config` e `modsecurity` do diagnóstico ou, sem o Apache, as duas como erros, com o comando que os instala |
| `AccessFormat` / `dKnownFormats` | [mod-apache2/logformat.py:60](../mod-apache2/logformat.py#L60) / [:15](../mod-apache2/logformat.py#L15) | `LogFormat` para expressão regular; apelidos conhecidos |
| `AccessParser` | [mod-apache2/parsers.py:59](../mod-apache2/parsers.py#L59) | Linha do access.log para registro |
| `fParseErrorLine` | [mod-apache2/parsers.py:147](../mod-apache2/parsers.py#L147) | Linha do error.log: ModSecurity, banco de dados, PHP, travamento |
| `AuditFramer` | [mod-apache2/parsers.py:233](../mod-apache2/parsers.py#L233) | Registros nativos em várias linhas; posição de commit segura |
| `fParseAuditRecord` / `fFinishAudit` | [mod-apache2/parsers.py:277](../mod-apache2/parsers.py#L277) / [:426](../mod-apache2/parsers.py#L426) | Registro de auditoria JSON ou nativo; mascaramento, texto bruto e indexado |
| `fAuditDisplay` / `fReadConcurrentEntry` | [mod-apache2/parsers.py:495](../mod-apache2/parsers.py#L495) / [:577](../mod-apache2/parsers.py#L577) | Cartão de um registro armazenado; arquivo de uma entrada concorrente |
| `fParseMessage` / `fSummarize` | [mod-apache2/modsec.py:52](../mod-apache2/modsec.py#L52) / [:152](../mod-apache2/modsec.py#L152) | Uma mensagem do ModSecurity; regras, categorias, pontuação, limite, interceptação |
| `Correlator` | [mod-apache2/correlate.py:57](../mod-apache2/correlate.py#L57) | `mAdd` ([:148](../mod-apache2/correlate.py#L148)), `mPair` ([:207](../mod-apache2/correlate.py#L207)), `mDue` ([:248](../mod-apache2/correlate.py#L248)), `mWaitsForAudit` ([:271](../mod-apache2/correlate.py#L271)), `mPendingCount` |
| `PrivescModule` | [mod-privesc/module.py:226](../mod-privesc/module.py#L226) | O módulo privesc (`vName = "privesc"`) |
| `PrivescModule.mBuildEvent` | [mod-privesc/module.py:341](../mod-privesc/module.py#L341) | Transação para evento, por fonte; `ignored`; campos vazios descartados (`fCleanFields` mantém o 0) |
| `PrivescModule.mAnalyzeCommand` | [mod-privesc/module.py:366](../mod-privesc/module.py#L366) | Reconhecimento da sessão, download executado por um shell, compilação em `/tmp`, comandos recentes, novo programa de uma conta de serviço |
| `PrivescModule.mAuditEvent` / `mAuditExec` / `mAuditUser` | [mod-privesc/module.py:427](../mod-privesc/module.py#L427) / [:587](../mod-privesc/module.py#L587) / [:661](../mod-privesc/module.py#L661) | Transação de auditoria por tipo; programas executados (`suid_escape`, `root_without_door`, `parent_interpreter`, capabilities); logins, portas e falhas |
| `PrivescModule.mAuditSyscall` | [mod-privesc/module.py:509](../mod-privesc/module.py#L509) | Qualquer outra chamada de sistema pelo nome, pelos argumentos e pelos caminhos dela: `denied`, `kmod`, `ptrace`, `chmod`, `file` (`sensitive_group`) ou `syscall` |
| `fSyscallName` / `fSensitiveGroup` | [mod-privesc/module.py:184](../mod-privesc/module.py#L184) / [:210](../mod-privesc/module.py#L210) | Nome de uma chamada de sistema (nome enriquecido, ou número por arquitetura); grupo de um caminho sensível (`lSensitivePaths`) |
| `PrivescModule.mSyslogEvent` | [mod-privesc/module.py:702](../mod-privesc/module.py#L702) | snoopy, sudo, su, pkexec, doas, logins |
| `PrivescModule.mWriterAllowed` | [mod-privesc/module.py:412](../mod-privesc/module.py#L412) | Quem grava um arquivo sensível, ou um ancestral conhecido dele, é uma ferramenta de contas ou de pacotes |
| `PrivescModule.mDetectionFromSignal` / `mEnrich` | [mod-privesc/module.py:781](../mod-privesc/module.py#L781) / [:818](../mod-privesc/module.py#L818) | Sinal de uma regra para detecção; contexto da sessão para o alerta |
| `PrivescModule.mHealth` / `mSurfaceResult` | [mod-privesc/module.py:851](../mod-privesc/module.py#L851) / [:903](../mod-privesc/module.py#L903) | Sessões salvas, auditd parado, arquivos sensíveis, varredura iniciada; novos programas setuid e capabilities |
| `fDiscoverSources` / `fReadState` / `fLegacyLeftovers` | [mod-privesc/discovery.py:291](../mod-privesc/discovery.py#L291) / [:160](../mod-privesc/discovery.py#L160) / [:175](../mod-privesc/discovery.py#L175) | Fontes, fontes ignoradas e informações para o diagnóstico; se um log pode ser lido; arquivos deixados pela versão 1.0.0 |
| `fContainer` / `fAuditdPid` | [mod-privesc/discovery.py:54](../mod-privesc/discovery.py#L54) / [:96](../mod-privesc/discovery.py#L96) | Tipo de contêiner (sem root); pid de um auditd em execução |
| `Accounts` | [mod-privesc/discovery.py:190](../mod-privesc/discovery.py#L190) | Nomes de uids, grupos, `UID_MIN`, tipo de conta (`mAccountType`) |
| `fParseAuditLine` / `fParseSyslogLine` | [mod-privesc/parsers.py:83](../mod-privesc/parsers.py#L83) / [:316](../mod-privesc/parsers.py#L316) | Registros das duas fontes |
| `fMaskCommand` | [mod-privesc/parsers.py:45](../mod-privesc/parsers.py#L45) | Senhas das linhas de comando, depois o mascarador do núcleo |
| `Correlator` (privesc) | [mod-privesc/correlate.py:20](../mod-privesc/correlate.py#L20) | Registros de auditoria por serial; os outros na hora |
| `fReconToken` / `fProgramKey` / `fCommandArgs` | [mod-privesc/commands.py:115](../mod-privesc/commands.py#L115) / [:180](../mod-privesc/commands.py#L180) / [:91](../mod-privesc/commands.py#L91) | Token de reconhecimento de um comando; programa de uma conta de serviço; palavras de um comando digitado |
| `SessionTracker` | [mod-privesc/commands.py:202](../mod-privesc/commands.py#L202) | Sessões (início, IP, porta, reconhecimento, últimos comandos), processos, downloads; `mExport`/`mImport` |
| `SurfaceScanner` / `fCheckSensitiveFiles` | [mod-privesc/surface.py:167](../mod-privesc/surface.py#L167) / [:133](../mod-privesc/surface.py#L133) | Varredura de setuid, setgid e capabilities em uma thread; arquivos sensíveis graváveis por outros |
| `fRunDoctor` / `fRequirementChecks` (privesc) | [mod-privesc/doctor.py:275](../mod-privesc/doctor.py#L275) / [:282](../mod-privesc/doctor.py#L282) | Verificações do diagnóstico (descrições; correções só para pacotes e acesso de leitura); requisito `command_source`: qualquer fonte legível |
| `Module` / `LineFramer` | [backend/core/module.py:59](../../localSIEM/backend/core/module.py#L59) / [:48](../../localSIEM/backend/core/module.py#L48) | Interface de um módulo; uma linha por unidade |
| `fReadManifest` | [backend/core/registry.py:133](../../localSIEM/backend/core/registry.py#L133) | Verifica o `module.json`, lê os textos |
| `fListManifests` / `fCreateModules` | [backend/core/registry.py:165](../../localSIEM/backend/core/registry.py#L165) / [:229](../../localSIEM/backend/core/registry.py#L229) | Os módulos instalados (`/opt/localsiem/modules/*`); instâncias e erros |
| `fRegisterPackage` / `fLoadClass` | [backend/core/registry.py:185](../../localSIEM/backend/core/registry.py#L185) / [:197](../../localSIEM/backend/core/registry.py#L197) | Namespace package `localsiem_modules`; importação e verificações da entrada |
| `fModuleSettings` / `fValidateSettings` | [backend/core/registry.py:250](../../localSIEM/backend/core/registry.py#L250) / [:317](../../localSIEM/backend/core/registry.py#L317) | Padrões sob os valores salvos; validação do que é salvo |
| `fSaveModule` | [backend/web/api_modules.py:290](../../localSIEM/backend/web/api_modules.py#L290) | `POST /api/admin/modules/{name}` |
| `fGetCatalog` / `fInstallFromCatalog` / `fUninstallModule` | [backend/web/api_modules.py:384](../../localSIEM/backend/web/api_modules.py#L384) / [:395](../../localSIEM/backend/web/api_modules.py#L395) / [:422](../../localSIEM/backend/web/api_modules.py#L422) | `GET /api/admin/module-catalog`; `POST /api/admin/module-catalog/{name}` (instalar ou atualizar; uma primeira instalação sem os requisitos dela fica desativada: `fFirstInstallation`); `DELETE /api/admin/modules/{name}` |
| `fInstall` / `fCatalog` | [backend/core/catalog.py:235](../../localSIEM/backend/core/catalog.py#L235) / [:171](../../localSIEM/backend/core/catalog.py#L171) | Instala ou atualiza um módulo ao lado da cópia instalada e as troca com um rename (`previous`, `access_changed`); os módulos do repositório com `installed`, `newer` e a ação deles |
| `fRemove` / `fRootCommand` | [backend/core/catalog.py:302](../../localSIEM/backend/core/catalog.py#L302) / [:372](../../localSIEM/backend/core/catalog.py#L372) | Desinstala um módulo (rename e exclusão); o comando para o root (`manage.py setup-modules`) |
| `fCatalogPanel` / `fUpdateNotice` / `fUpdate` | [frontend/assets/modules.js:218](../../localSIEM/frontend/assets/modules.js#L218) / [:417](../../localSIEM/frontend/assets/modules.js#L417) / [:452](../../localSIEM/frontend/assets/modules.js#L452) | Seção Instaláveis (só os módulos não instalados, **Instalar** e a caixa de diálogo dele); aviso de uma versão mais nova em uma linha de Instalados; **Atualizar** (confirmação, o mesmo `POST`, uma caixa de diálogo só com `access_changed` ou quando o coletor não respondeu) |

<a id="flows"></a>
## 4. Fluxos principais (call paths)

**Início do coletor → registro → ApacheModule**

`Collector.mSetup` → `fCreateModules` → `fListManifests` (`/opt/localsiem/modules/*`) → `fReadManifest` (id = pasta, entrada, configurações, `core` ≤ `cVersion`, `fReadTexts`) → `fCreateModule` → `fLoadClass` (`fRegisterPackage`, `import localsiem_modules.apache2.module`, subclasse de `Module`, `vName == id`) → `ApacheModule(dSettings, vMasker, vStorage, dManifest)` → `mStart` → `mCreateCorrelator` → `Collector.mLoadRules` (`mRulesPath`, `mRuleFunctions`, sobrescritas `rules.<id>` → `RulesEngine.mLoad`) → `Collector.mDiscover` (`mEnabled` → `mDiscover` → `ApacheConfig.mParse` → `fDiscoverSources`; um `FileTailer` e `mCreateFramer` por fonte) → registros pendentes de volta ao correlacionador → `mPublishDoctor` (`mDoctor` → `fRunDoctor` → estado `apache2.doctor`).

**Uma linha lida → detecções**

1. `Collector.mReadSources` → `FileTailer.mPoll` → framer `mFeed` (`LineFramer`, ou `AuditFramer`, cujo `mSafeCommit` mantém a posição antes de um registro inacabado) → `ApacheModule.mParse` (`AccessParser.mParse`, `fParseErrorLine`, ou `fReadConcurrentEntry` + `fParseAuditRecord` e `mObserveAudit`) → registros e posições armazenados em uma única transação → `Correlator.mAdd`.
2. `Collector.mProcessDue` → `Correlator.mDue(pWatermark=...)` → `ApacheModule.mBuildEvent` (`fSummarize`, ação tomada, `mAssess`, `mPathFirstSeen` para `.php` com 2xx) → `RulesEngine.mEvaluate` (regras YAML; `{function: apache2.new_php}` → `mIsNewPhp`) → `mSaveEvents` → `mDetect` para cada detecção e `mDetectionFromSignal` para cada sinal → `Grouper.mAdd`.
3. `Collector.mProcessGroups` → `ApacheModule.mEnrich` (`mGetIpContext`) → `fBuildAlert` → fila do SOC.

**O administrador salva as configurações → recarga do coletor**

`modules.js fBuildSettings` (envio) → `POST /api/admin/modules/apache2` `{settings}` → `fSaveModule` → `fValidateSettings` (422 `invalid_setting:<key>` ou `<key>.<field>`) → `fSaveSettings` (`settings.json`, `modules.apache2`) → `WebContext.mApplySettings` → socket do coletor `{"command": "reload"}` → `Collector.mHandleIpc` → `Collector.mCycle` → `mReloadSettings` (`ApacheModule.mReload`, `mLoadRules`, `mDiscover`, `mPublishDoctor`, `mPublishState`). O interruptor envia `{enabled}` da mesma forma (ao ativá-lo: 422 `requirements_missing` enquanto faltar um requisito do módulo) e a tabela de regras envia `{rules}` (`fCleanRules` → `rules.<id>`: `enabled`, `severity`, `threshold` ou `first_threshold`, `window`). Se o socket não responder, o coletor ainda percebe o novo `settings.json` no ciclo seguinte.

**Instalar um módulo pela interface web** (a única forma de instalar módulos)

`modules.js fCatalogPanel` (Módulos › Instaláveis) → **Consultar o repositório** → `GET /api/admin/module-catalog` (`fGetCatalog` → `fFetchCatalog` → `fDownload` → `fCatalog`: cada pasta `mod-<name>/` do repositório, com `installed`, `newer` e `action`) → só os itens com `installed` nulo são listados → **Requisitos** (`fShowRequirements` → `fRequirementsBody`: os `install_requirements` do módulo para o sistema do servidor, `system` da resposta, como root e com `sudo`, e as notas `install_requirements.*` dos locales dele; nada é executado) → **Instalar** → `POST /api/admin/module-catalog/{name}` (`fInstallFromCatalog` → `fFetchAndInstall` → `InstallLock` → `fDownload` → `fInstall`: `mod-apache2/` → `/opt/localsiem/modules/apache2/`, `previous` nulo, `access_changed` true) → `WebContext.mReloadModules` → `fFirstInstallation` (falta um requisito e `modules.<name>.enabled` nunca foi salvo: `enabled = false`) → `restart` do coletor → `fCreateModules` carrega o módulo → a caixa de diálogo «<módulo> instalado» mostra o comando para o root (`fRootCommand`: `manage.py setup-modules`, acesso de leitura aos `read_paths`) ou, se faltar um requisito, as verificações não atendidas.

**Atualizar um módulo pela interface web**

Módulos › Instalados é aberto → `fCheckRepository` → `fFetchCatalog(false)` de `modules.js` (a última resposta de `GET /api/admin/module-catalog`, reutilizada por 600 s; instalar, atualizar ou desinstalar um módulo a descarta) → itens com `newer` e `action` `update` ou `incompatible` → `fUpdateNotice` na linha (só enquanto a versão instalada for a comparada) → **Atualizar** → `fUpdate` → confirmação → `POST /api/admin/module-catalog/{name}` (o mesmo `fInstallFromCatalog` → `fInstall`: a nova cópia substitui a instalada, `previous` é a versão antiga, `access_changed` indica se `read_paths` mudou; sem `fFirstInstallation`, então `enabled` e as configurações são mantidos) → `restart` do coletor → uma caixa de diálogo só se `access_changed` (o comando para o root) ou se o coletor não respondeu.

**Desinstalar um módulo pela interface web**

**Desinstalar** (linha de Módulos › Instalados ou página do módulo) → `fUninstallButton` → confirmação → `DELETE /api/admin/modules/{name}` (`fUninstallModule` → `fRemove` → `InstallLock` → rename de `/opt/localsiem/modules/<name>/` para uma pasta temporária, onde é excluída) → `WebContext.mReloadModules` → `restart` do coletor. `modules.<name>` e as sobrescritas das regras dele continuam em `settings.json`, e o acesso de leitura dado pelo root continua.

**Primeira instalação sem Apache ou ModSecurity → Reconfigurar** (localSIEM 2.2.0 ou mais recente)

Instalar na interface web → `fInstall` (primeira instalação) → o módulo criado a partir da cópia instalada (armazenamento `None`) → `ApacheModule.mRequirements` → `ApacheConfig.mParse` → `fRequirementChecks` (com o Apache: `fRunDoctor` → `apache_config`, `modsecurity`; sem ele, os dois como erros) → um erro e `modules.apache2.enabled` nunca salvo → `modules.apache2.enabled = false` («Desativado», interruptor bloqueado, requisitos na página). Depois, com o Apache e o ModSecurity instalados: **Reconfigurar** → `POST /api/admin/modules/apache2/reconfigure` → `mRequirements` → atendidos → interruptor desbloqueado e o comando para o root (acesso de leitura aos `read_paths`; o apache2 não tem `setup_option`) → o administrador ativa o módulo → recarga do coletor → `mDiscover` → `mPublishDoctor`.

**Cartão da requisição e diagnóstico a partir da interface web**

`GET /api/events/{id}` → `fEvent` → `WebContext.mModule("apache2")` → `mDisplayRecord` → `fAuditDisplay`. **Descobrir novamente e executar o diagnóstico** → `POST /api/admin/modules/apache2/doctor` → coletor `{"command": "doctor"}` → `mDiscover` + `mPublishDoctor`.

**Saúde**

`Collector.mCycle` (a cada 60 s) → `mCheckHealth` → `ApacheModule.mHealth` (no máximo a cada 300 s; `ApacheConfig.mParse`, `mCountRecentEvents`) → `fHealthDetection` → `mDetect`.

**privesc: um comando executado → detecções**

1. O auditd grava `SYSCALL`, `EXECVE`, `CWD`, `PATH`, `PROCTITLE`, `EOE` com um mesmo serial → `FileTailer.mPoll` → `LineFramer` → `PrivescModule.mParse` → `fParseAuditLine` (hexadecimal decodificado, `fMaskCommand`, texto bruto reconstruído) → `Correlator.mAdd` (chave `audit:<time>:<serial>`, vence em `EOE`).
2. `Correlator.mDue` → `PrivescModule.mBuildEvent` → `mAuditEvent` → `mAuditExec` (`suid_escape`, `BPRM_FCAPS`, `root_without_door` a partir de `SessionTracker.mGet`, `mRememberProcess`) → `mAnalyzeCommand` (`fReconToken` → `SessionTracker.mRecon` → `recon_burst`/`recon_massive`; `cDownloadOnelinerRegex`, `mDownload`/`mRecentDownload`; `fCompileInTemporary`; `mCommand`; conta de serviço: `fProgramKey` → `mPathFirstSeen` → `new_program`) → `fCleanFields`.
3. `RulesEngine.mEvaluate` (regras de `mod-privesc/rules/`) → `PrivescModule.mDetectionFromSignal` → `Grouper.mAdd` → `Collector.mProcessGroups` → `PrivescModule.mEnrich` (sessão: últimos 20 comandos) → `fBuildAlert` → fila do SOC.

Com o snoopy, o mesmo comando também chega como uma linha do syslog: `fParseSyslogLine` → `fParseSyslogMessage` → `mSyslogEvent` → `mAnalyzeCommand` (sessão `snoopy:<uid>:<sid>`).

**privesc: sessões e portas**

`LOGIN` (auid e ses atribuídos) ou `USER_LOGIN`/`USER_START` do sshd ou do login → `mAuditUser` → `SessionTracker.mStart` (usuário, endereço SSH). `USER_START`/`USER_CMD` com resultado success de sudo, su, pkexec, doas, run0 ou systemd → `SessionTracker.mDoor`. Um `EXECVE` posterior dessa sessão com uid e euid 0 → `root_without_door` só se o início foi visto e não houve porta. `mHealth` salva `SessionTracker.mExport` em `privesc.sessions` no máximo a cada minuto; `mStart` o carrega (`mImport`).

**privesc: uma chamada de sistema registrada pelas regras de auditoria do servidor**

O auditd grava `SYSCALL` (com `arch`, `syscall`, `a0`-`a3`, `success`, `exit` e a chave da regra que a registrou, seja ela qual for), `CWD`, `PATH`... → `fParseAuditLine` → `Correlator` → `mAuditEvent` → `mAuditSyscall`: `fSyscallName` → open/exec/truncate com falha por `EACCES`/`EPERM` e um uid de login → `denied`; `init_module`/`finit_module`/`delete_module` → `kmod`; `ptrace` → `ptrace`; `chmod`/`fchmod`/`fchmodat`/`fchmodat2` com `S_ISUID`/`S_ISGID` no modo, não em uma pasta → `chmod` (`mWriterAllowed`); uma alteração (uma chamada de `sChangeSyscalls`, um open com flags de escrita, um `PATH` com `CREATE`/`DELETE`) de um caminho de `lSensitivePaths` → `file` com `sensitive_group` (`dKeyHints` só sem um caminho resolvível) e `mWriterAllowed`; qualquer outra coisa → `syscall`. `mBuildEvent` lembra a hora de cada tipo (`dRuntime["audit_kinds"]`) para o diagnóstico.

**privesc: varredura da superfície de ataque**

`mHealth` (a cada 300 s, cinco minutos depois do início, a cada `surface_scan_hours`) → `SurfaceScanner.mStart` (thread: `os.walk` de `scan_paths`, `os.lstat`, `os.getxattr("security.capability")` → `fCapabilities`) → próximo `mHealth` → `mSurfaceResult` (`SurfaceScanner.mTake`, comparado com `privesc.surface`: novo setuid/setgid → `new_setuid*`, novas capabilities → `new_capabilities`) → `mModuleDetection` → `mDetect`; o resultado é salvo em `privesc.surface` e mostrado por `fSurfaceChecks`. A cada hora, `fCheckSensitiveFiles` → `sensitive_file_writable`.

**privesc: requisitos e Reconfigurar**

`fInstall` (primeira instalação) ou **Reconfigurar** → `PrivescModule.mRequirements` → `fRequirementChecks(mModuleSettings())` (`fContainer`, `fAuditdPid`, `fAuditLogPath` → `fReadState`; `fSyslogPath` → `fReadState`, a menos que `syslog_mode` seja `never`; `fSnoopyInstalled`) → uma fonte legível: `command_source` ok (as ilegíveis como avisos); uma fonte que existe mas não pode ser lida: erro de `audit_log` ou `syslog` com o acesso de leitura (`manage.py setup-modules` ou `setfacl`); nada: erro de `command_source` com o pacote a instalar. O módulo fica desativado enquanto houver um erro.

<a id="routes"></a>
## 5. Pontos de entrada

| Ponto de entrada | Handler | Arquivo |
|---|---|---|
| `"entry": "module:ApacheModule"` do `module.json` | `ApacheModule` | [mod-apache2/module.py](../mod-apache2/module.py) |
| `mod-apache2/rules/*.yaml` | `RulesEngine` (núcleo) | [mod-apache2/rules/](../mod-apache2/rules/) |
| Função de regra `apache2.new_php` | `ApacheModule.mIsNewPhp` | [mod-apache2/module.py](../mod-apache2/module.py) |
| Interface web: Módulos › Instaláveis, a única forma de instalar módulos (`GET /api/admin/module-catalog`, `POST /api/admin/module-catalog/{name}`) | `fGetCatalog`, `fInstallFromCatalog`; visão `fCatalogPanel` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| Interface web: **Atualizar** em uma linha de Módulos › Instalados (o mesmo `GET`, reutilizado por 10 minutos pelo navegador, e o mesmo `POST`) | `fCheckRepository`, `fUpdateNotice`, `fUpdate` → `fInstallFromCatalog` | [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js), [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| Interface web: **Desinstalar** (`DELETE /api/admin/modules/{name}`) | `fUninstallModule` → `fRemove` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `read_paths` do `module.json` | `manage.py read-paths`: as pastas que o localSIEM permite ao `localsiem` ler, como root (o comando de `fRootCommand`) | [backend/manage.py](../../localSIEM/backend/manage.py), [backend/core/catalog.py](../../localSIEM/backend/core/catalog.py) |
| `manage.py modules` | `fMain` (`fModules`) | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py doctor [--json]` | `mDiscover`, `mSkipped`, `mDoctor` | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `manage.py read-paths` | `read_paths` de cada manifesto | [backend/manage.py](../../localSIEM/backend/manage.py) |
| `/user/dashboard/modules/`; `/admin/dashboard/modules/` (302 para `installed/`), `/admin/dashboard/modules/installed/`, `/admin/dashboard/modules/installable/` | `fUserTab` / `fAdminTab` / `fAdminModulesSection`; visão `LocalsiemViews.modules` | [backend/web/app.py](../../localSIEM/backend/web/app.py), [frontend/assets/modules.js](../../localSIEM/frontend/assets/modules.js) |
| `/admin/dashboard/modules/installed/apache2/` (o antigo `/admin/dashboard/modules/apache2/` responde com 301 para ele) | `fAdminModule` (o 301: `fAdminModulesSection`); visão `LocalsiemViews.module` | mesmos arquivos |
| `GET /api/modules` | `fModules` (estado para todos os que entraram) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `GET /api/admin/modules/apache2` | `fModule` (configurações, valores, fontes, diagnóstico, regras) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2` | `fSaveModule` (`enabled`, `settings`, `rules`) | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/doctor` | `fRunDoctor` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py) |
| `POST /api/admin/modules/apache2/reconfigure` (**Reconfigurar**, localSIEM 2.2.0 ou mais recente) | `mRequirements` → `fRequirementChecks` | [mod-apache2/module.py](../mod-apache2/module.py), [mod-apache2/doctor.py](../mod-apache2/doctor.py) |
| `GET /api/events/{id}` | `fEvent` → `mDisplayRecord` | [backend/web/api_search.py](../../localSIEM/backend/web/api_search.py) |
| `"entry": "module:PrivescModule"` de `mod-privesc/module.json` | `PrivescModule` | [mod-privesc/module.py](../mod-privesc/module.py) |
| `mod-privesc/rules/*.yaml` | `RulesEngine` (núcleo) | [mod-privesc/rules/](../mod-privesc/rules/) |
| `/admin/dashboard/modules/installed/privesc/`, `GET`/`POST /api/admin/modules/privesc`, `.../privesc/doctor`, `.../privesc/reconfigure` | `fAdminModule`, `fModule`, `fSaveModule`, `fRunDoctor`, `mRequirements` → `fRequirementChecks` | [backend/web/api_modules.py](../../localSIEM/backend/web/api_modules.py), [mod-privesc/doctor.py](../mod-privesc/doctor.py) |
| Registros de auditoria das regras do servidor (qualquer chave) | `mAuditEvent` → `mAuditExec`, `mAuditUser`, `mAuditSyscall` | [mod-privesc/module.py](../mod-privesc/module.py) |

<a id="impact"></a>
## 6. Análise de impacto

| Componente | O que é afetado se ele mudar |
|---|---|
| `module.json` `id` | Deve ser igual ao nome da pasta sem `mod-` (o nome da pasta instalada) e ao `vName`. É a chave das configurações (`modules.<id>`), do estado (`<id>.doctor`) e o `module` de cada evento: renomeá-lo perde as configurações salvas e divide o histórico. |
| `module.json` `core` | Elevá-lo acima do localSIEM instalado impede que o módulo seja carregado (estado «Erro»); no repositório, Instaláveis mostra «Precisa do localSIEM X ou mais recente» e Instalados mostra a versão mais nova sem **Atualizar**. |
| `module.json` `entry` | Deve apontar para uma subclasse de `Module`; um valor errado é um erro de carregamento. |
| `module.json` `default_enabled` | Ativado/desativado dos servidores em que o administrador nunca decidiu (se faltarem os requisitos dele na primeira instalação, desativado). |
| `module.json` `read_paths` | O acesso de leitura que o localSIEM dá como root (`manage.py read-paths`): uma pasta ausente significa erros de permissão no diagnóstico e no estado. Uma alteração em uma nova versão faz a interface web mostrar novamente o comando para o root depois de **Atualizar** (`access_changed`). |
| `module.json` `install_requirements` | A caixa de diálogo Requisitos de Instaláveis (`fRequirementsBody` de `modules.js`). Um valor errado (um sistema diferente de `debian` e `alpine`, uma lista vazia ou mais de 20 comandos, um comando com um operador de shell ou uma quebra de linha) torna o módulo inválido (`fCheckInstallRequirements` do núcleo): ele não é instalado nem carregado. |
| `module.json` `setup_option` | Nada: o núcleo o ignora (nenhum módulo o tem desde o apache2 1.3.0 e o privesc 1.1.0). |
| Pastas `mod-<name>/` com um `module.json` na raiz do repositório | O que o catálogo da interface web lista, como o módulo `<name>`: Instaláveis mostra os que ainda não estão instalados (um que precisa de um núcleo mais novo como «Precisa do localSIEM X ou mais recente», um inválido como «O módulo do repositório não é válido»), e uma `version` maior que a instalada faz Instalados oferecer **Atualizar**. |
| `module.json` `settings` | O formulário, a validação e os padrões. Um novo padrão se aplica aos servidores que nunca salvaram essa chave. Os valores salvos não são migrados: uma chave renomeada perde o valor dela e um valor antigo com um novo tipo chega ao módulo como foi salvo. |
| `locales/*.json` | Só os textos da interface web; um texto ausente recorre ao en-US e depois à chave. |
| `parsers.py` (dict do registro) | A correlação (`correlation`, `fields.client_ip`, `fields.path`), o cartão da requisição, o índice de texto completo (`search`, `raw`), a saúde das linhas não analisadas e a privacidade. |
| `logformat.py` `dKnownFormats` | A análise de cada log de acesso; `localsiem_combined` continua para os servidores que já o gravam (as versões 1.2.0 e anteriores do módulo o adicionavam): não altere a definição dele. |
| `correlate.py` | Um evento por requisição; o núcleo chama `mAdd`, `mDue(pNow, pForce, pWatermark)` e `mPendingCount`, e devolve os registros ainda pendentes depois de uma reinicialização. Sem `UNIQUE_ID`, ele emparelha os registros pelos campos `client_ip`, `method`, `uri`, `status` e `path`: um analisador que os grave de outra forma quebra o emparelhamento. A espera pelo registro de auditoria (`mWaitsForAudit`) precisa do campo `modsecurity` das linhas do error.log e dos registros da fonte `audit`. |
| `modsec.py` (categorias, rótulos, faixas) | Os nomes das regras dos alertas (as estatísticas do SOC agrupam por eles: mantenha-os estáveis), as chaves de agrupamento, as pesquisas `category:`. |
| `ApacheModule.mBuildEvent` (dict do evento) | As colunas da tabela de eventos, os campos lidos pelas regras YAML (`action`, `status`, `method`, `path`, `crs_matched`, `db_error`...), as pesquisas e a exportação CSV. |
| `ApacheModule.mAssess` | O que chega ao SOC e a severidade dele; os limites de `GenericAlert` do núcleo (regra 300, descrição 10 000 caracteres). |
| `severity.yaml` | A severidade de cada detecção do ModSecurity; a severidade faz parte da chave de agrupamento, então uma alteração inicia novos grupos. |
| `rules/*.yaml` | O `id` é a chave das sobrescritas (`rules.<id>`) e das pesquisas (`rule:localsiem:<id>`): mantenha-o estável. Os campos devem existir nos eventos; `{function: ...}` precisa de `mRuleFunctions`. |
| `discovery.py` | Quais logs são lidos; `fSourceKey` é a chave das posições salvas (uma nova chave transforma o arquivo em uma nova fonte, sem a posição salva dele); os DocumentRoots da regra de web shell; o diagnóstico. |
| `doctor.py` | O diagnóstico da interface web e de `manage.py` e as dicas mostradas ao cliente. Só as verificações sobre o que não é um log (ModSecurity, o CRS, `SecRuleEngine`, `mod_unique_id`, permissões) podem ter um `fix`; as verificações sobre os logs apenas os descrevem. |
| `mRequirements` / `fRequirementChecks` | Se o módulo pode ser ativado, o estado «Desativado» depois de uma primeira instalação sem Apache ou ModSecurity, os requisitos que a interface web mostra e **Reconfigurar**. São executados na interface web e em `manage.py` sem armazenamento e analisam a configuração do Apache a cada chamada: mantenha-os longe do armazenamento e de qualquer coisa lenta, e mantenha estáveis os ids `apache_config` e `modsecurity`. |
| privesc: colunas e campos dos eventos (`mBuildEvent`, `mAnalyzeCommand`) | As regras YAML os comparam pelo nome (`recon_burst`, `suid_escape`, `root_without_door`, `sensitive_group`, `writer_allowed`, `ptrace_attach`, `parent_interpreter`, `account_type`, `real_uid`, `argc_zero`...): um campo renomeado desativa silenciosamente as regras que o usam. `vhost` é o usuário: a chave de agrupamento dos alertas e as pesquisas `vhost:` dependem dele. |
| privesc: `fReconToken` | O que conta como reconhecimento e como os comandos distintos são diferenciados: alterar um token altera a rapidez com que uma sessão atinge os limites. |
| privesc: `SessionTracker` e as portas (`sDoors`) | `root_without_door`: uma porta ausente da lista torna críticas sessões de root legítimas; uma a mais esconde exploits de kernel. `mExport`/`mImport` é o formato de `privesc.sessions`. |
| privesc: `parsers.py` | Os campos dos registros (`args`, `command`, `kind`, `uid`/`euid` do snoopy), o mascaramento das senhas e o texto bruto dos registros de auditoria; os formatos do snoopy que ele lê (o módulo nunca altera o `snoopy.ini`). |
| privesc: classificação dos registros de auditoria (`lSensitivePaths`, `dSyscallTables`, `sChangeSyscalls`, `dOpenFlagArgument`, `dChmodModeArgument`, `sDeniedSyscalls`, `dKeyHints`) | O que se torna `file`, `chmod`, `kmod`, `ptrace` e `denied` e, portanto, as regras sensitive-file, persistence-file, monitoring-changed, suid-set, kernel-module, ptrace, denied-burst e sensitive-denied; um número de syscall errado classifica mal os registros dessa arquitetura. |
| privesc: `surface.py` | O custo da varredura (thread, limites) e o que o diagnóstico e `mSurfaceResult` relatam; `privesc.surface` é a referência dela. |
| privesc: `mRequirements` / `fRequirementChecks` | Se o módulo pode ser ativado (qualquer fonte legível), o estado «Desativado» depois de uma primeira instalação cujos logs o `localsiem` ainda não consegue ler, e **Reconfigurar**; chamados sem armazenamento pela interface web e por `manage.py`: mantenha-os rápidos e sem root. Mantenha os ids `command_source`, `audit_log` e `syslog`. |
| Interface do núcleo (`backend/core/module.py`, `registry.py` do localSIEM) | Todos os módulos: uma assinatura de hook alterada, uma nova chave obrigatória do manifesto ou um novo contrato de registros e eventos os quebra; eleve `core` no `module.json` deles quando precisarem do novo localSIEM. |

<a id="extensions"></a>
## 7. Pontos de extensão

### Como escrever um novo módulo

1. **Pasta**: crie `mod-<name>/` na raiz deste projeto; `<name>`, o nome do módulo, corresponde a `[a-z][a-z0-9_]{1,31}`. O prefixo `mod-` é só para a pasta: o `module.json`, a classe, as opções e os textos usam `<name>`. Sem `__init__.py`.
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

3. **Textos**: `locales/<language>.json` para cada um dos 15 idiomas do localSIEM com `name`, `summary` e o rótulo e a ajuda de cada configuração. As notas sobre os requisitos vão em `install_requirements` (`note`, para todos os sistemas, e `debian` e `alpine`), mostradas na caixa de diálogo Requisitos.
4. **Código**: `module.py` com uma subclasse de `Module` cujo `vName` é o id. Ele deve implementar `mParse`, `mCreateCorrelator` e `mBuildEvent`, e normalmente `mDiscover`; os outros hooks são opcionais (seção 1). Importe os próprios arquivos de forma relativa e o núcleo como `backend.core...`. Os dois módulos deste repositório são exemplos completos ([mod-apache2/module.py](../mod-apache2/module.py), [mod-privesc/module.py](../mod-privesc/module.py)); um esboço mínimo:

   ```python
   from backend.core.module import Module


   class OneEventCorrelator:
     # Cada registro é um evento próprio, sem espera.

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

5. **Ação tomada**: decida o que «já resolvido» significa para o serviço (por exemplo, um IP já banido) e defina `action` como `blocked` nesse caso; adicione uma detecção só aos eventos sem ação tomada.
6. **Regras**: arquivos YAML em `mod-<name>/rules/`, retornados por `mRulesPath`, e as funções que eles chamam em `mRuleFunctions`.
7. **Requisitos**: se o módulo precisa de software no servidor (como o apache2 precisa do Apache e do ModSecurity 2), retorne uma verificação por requisito a partir de `mRequirements()` (o formato de `fCheck`: `status` `ok` ou `error`, e em `fix` o comando que o instala) e nunca instale esse software a partir do módulo: sem os requisitos dele, o módulo é instalado desativado. Ele é executado sem armazenamento, também na interface web e em `manage.py`. Declare também, em `install_requirements` do `module.json`, os comandos que instalam esse software no Debian e no Alpine (um comando por linha, sem operadores de shell): a interface web os mostra em Módulos › Instaláveis › Requisitos, como estão e com `sudo` na frente, antes que o módulo seja instalado.
8. **Instalar**: publique-o neste repositório (branch `main`); ele aparece em Módulos › Instaláveis da interface web do localSIEM enquanto não estiver instalado, e **Instalar** copia a pasta `mod-<name>/` para `/opt/localsiem/modules/<name>/` e reinicia o coletor. O acesso de leitura aos `read_paths` dele precisa de root: a interface web mostra o comando (`manage.py setup-modules`). Um módulo não tem opção de configuração: nunca instala nada nem altera nada fora de `/opt/localsiem`, e nunca grava nos logs do cliente, nem os rotaciona ou exclui, nem altera o formato deles; se um servidor grava os logs à sua maneira, o módulo se adapta a ele, e o que falta ao servidor é um requisito. Para publicar uma nova versão, aumente `version`: Módulos › Instalados mostra o aviso e **Atualizar**, que mantém as configurações e o estado ativado/desativado do módulo e só mostra novamente o comando para o root se `read_paths` mudou.
9. **Documentação**: atualize o README, este CODE e o MANUAL nos 15 idiomas.

### Como adicionar uma regra ao módulo apache2

Crie um arquivo YAML em [mod-apache2/rules/](../mod-apache2/rules/) (cada chave e operador está descrito no início de [backend/core/rules.py](../../localSIEM/backend/core/rules.py)): `id`, `name`, `category`, `type`, `severity`, `kind` (`match`, `threshold` ou `sequence`), as condições (`when`, ou `first`/`first_threshold`/`then`), `by`, `window`, `threshold`, `lists`, `description` e `search`. Os campos são procurados primeiro nas colunas do evento e depois em `fields`. Ela aparece na tabela de regras da página do módulo e é carregada pelo coletor assim que a nova versão do módulo é instalada: aumente `version` no `module.json`, publique-o e clique em **Atualizar** em Módulos › Instalados.

### Como adicionar uma configuração ao módulo apache2

Adicione-a a `settings` de [mod-apache2/module.json](../mod-apache2/module.json) com o tipo e o padrão dela, adicione o `label` e o `help` dela aos quatro arquivos de [mod-apache2/locales/](../mod-apache2/locales/) e leia-a com `self.mModuleSettings().get("<key>")`. O formulário, a validação e a recarga vêm do núcleo.

### Como adicionar uma verificação ao diagnóstico ou alterar uma severidade

Uma verificação é um `fCheck(id, status, title, detail, fix)` em `fRunDoctor` ([mod-apache2/doctor.py](../mod-apache2/doctor.py)); mantenha o `id` estável e coloque em `fix` o trecho ou comando exato, só para requisitos que não são logs: uma verificação sobre os logs do cliente apenas os descreve e diz o que o localSIEM consegue ou não ler deles, sem `fix`. As severidades das detecções do ModSecurity são alteradas em [mod-apache2/severity.yaml](../mod-apache2/severity.yaml) (`low`, `medium`, `high`, `critical`).

### Como adicionar uma regra ao módulo privesc

Crie um arquivo YAML em [mod-privesc/rules/](../mod-privesc/rules/), como os do Apache. Compare as colunas (`method`, `uri`, `path`, `vhost`, `action`) e os campos dos eventos (`sensitive_group`, `account_type`, `real_uid`, `recon`, `service_account`, `file`...), nunca a chave de uma regra de auditoria; adicione `ignored: {not: true}` para que os usuários ignorados nunca a disparem, e `action: none` quando só contar o que realmente foi executado. Se a condição precisar de estado ou de lógica (uma sequência da mesma sessão, uma verificação de um arquivo), calcule um indicador em `PrivescModule.mAnalyzeCommand` (todas as fontes) ou em `mAuditExec`/`mAuditSyscall`/`mSyslogEvent` (uma fonte) e compare-o a partir da regra.

### Como adicionar um comando de reconhecimento, uma ferramenta ou um exploit ao módulo privesc

- Reconhecimento: adicione o programa a `sReconSimple`, ou um ramo a `fReconToken` que retorne um token por tipo de pergunta ([mod-privesc/commands.py](../mod-privesc/commands.py)). Um token que muda a cada argumento infla as contagens.
- Ferramentas e exploits: adicione uma expressão regular à lista de [rules/known-tool.yaml](../mod-privesc/rules/known-tool.yaml) ou de [rules/exploit.yaml](../mod-privesc/rules/exploit.yaml) (sem diferenciar maiúsculas de minúsculas, comparada com a linha de comando); o administrador também pode adicioná-las a partir das configurações (`rules.<id>.lists`).

### Como adicionar uma fonte ou um tipo de registro de auditoria ao módulo privesc

- Um caminho sensível: adicione-o a `lSensitivePaths` de [mod-privesc/module.py](../mod-privesc/module.py) com o grupo dele (ou um novo grupo e uma regra que compare `sensitive_group`). Um tipo de chamada de sistema: adicione o nome dela aos conjuntos de `mAuditSyscall` e o número dela a cada tabela de `dSyscallTables`. Nunca dependa da chave de uma regra de auditoria (no máximo, adicione-a a `dKeyHints`) e nunca instale regras de auditoria: o servidor registra o que o administrador dele decide, e o diagnóstico o descreve (`dAuditKinds` de [doctor.py](../mod-privesc/doctor.py)).
- Uma fonte: retorne-a a partir de `fDiscoverSources` com um novo `kind`, analise-a em `mParse` e monte os eventos dela em `mBuildEvent` com as mesmas colunas e campos que as outras, para que as regras funcionem sem alterações.
