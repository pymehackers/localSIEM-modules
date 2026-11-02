# Manual do usuário do localSIEM-modules

Este MANUAL também está disponível em:\
[de-DE](MANUAL.de-DE.md), [en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md), [fr-FR](MANUAL.fr-FR.md), [he-IL](MANUAL.he-IL.md), [hi-IN](MANUAL.hi-IN.md), [it-IT](MANUAL.it-IT.md), [ja-JP](MANUAL.ja-JP.md), [ko-KR](MANUAL.ko-KR.md), pt-BR, [pt-PT](MANUAL.pt-PT.md), [ru-RU](MANUAL.ru-RU.md), [zh-CN](MANUAL.zh-CN.md)

[Instalação](README.pt-BR.md) · [Referência técnica](CODE.pt-BR.md) · [Manual do localSIEM](../../localSIEM/doc/MANUAL.pt-BR.md)

## Sumário

1. [O que são os módulos](#what)
2. [Instalar e atualizar os módulos](#installation)
3. [A página Módulos](#modules-page)
4. [A página do módulo Apache](#apache-page)
5. [Configurações do módulo Apache](#settings)
6. [O que o módulo Apache envia ao SOC](#soc)
7. [Requisitos do Apache e do ModSecurity: o diagnóstico](#doctor)
8. [Os logs do cliente nunca são tocados](#client-logs)
9. [Regras do módulo Apache](#rules)
10. [Avisos de saúde do módulo Apache](#health)
11. [O módulo de escalonamento de privilégios](#privesc)
12. [Configurações do módulo de escalonamento de privilégios](#privesc-settings)
13. [O que o módulo de escalonamento de privilégios envia ao SOC: as regras dele](#privesc-rules)
14. [Requisitos do módulo de escalonamento de privilégios: o diagnóstico](#privesc-doctor)
15. [Servidores atualizados a partir da versão 1.0.0 do módulo de escalonamento de privilégios](#privesc-legacy)
16. [Superfície de ataque e avisos de saúde do módulo de escalonamento de privilégios](#privesc-health)
17. [Linha de comando](#cli)

<a id="what"></a>
## 1. O que são os módulos

O localSIEM é formado por um **núcleo** e por **módulos**. O núcleo armazena os eventos, pesquisa neles, executa as regras, agrupa os alertas, envia-os ao SOC e vigia a própria saúde. Cada módulo acrescenta um serviço do servidor: encontra os logs dele, lê esses logs, transforma-os em eventos, decide o que já está resolvido, traz as próprias regras e verifica os requisitos desse serviço.

Os módulos deste projeto são instalados em `/opt/localsiem/modules/<name>/`. Hoje há dois: **apache2** («Apache + ModSecurity», seções 4 a 10) e **privesc** («Escalonamento de privilégios», seções 11 a 16). O localSIEM não tem módulos próprios: a página Módulos só lista os módulos instalados a partir deste repositório.

<a id="installation"></a>
## 2. Instalar e atualizar os módulos

Primeiro é preciso instalar o localSIEM; o instalador dele instala só o núcleo, nunca um módulo. Os módulos deste projeto são instalados **somente pela interface web do localSIEM**: este projeto não tem instalador próprio. A interface web os baixa do repositório `https://github.com/PYMEHackers/localSIEM-modules` (branch `main`). Os módulos precisam do localSIEM 2.2.0 ou mais recente.

**Instalar.** Como administrador, abra Módulos › **Instaláveis** (seção 3), clique em **Consultar o repositório**, veja **Requisitos** (o que o módulo precisa no servidor e os comandos que o instalam, para executar antes de instalá-lo) e depois clique em **Instalar** no módulo. Então o localSIEM:

1. baixa o repositório e o descompacta com segurança (nada fora da pasta dele, limites de tamanho);
2. copia a pasta do módulo (`mod-<name>/` no repositório) para `/opt/localsiem/modules/<name>/`, sem `tests/` (e sem caches do Python); um módulo instalado novamente recupera as configurações que tinha;
3. reinicia o coletor, que carrega o módulo em poucos segundos;
4. tira o módulo da lista e abre a caixa de diálogo «<módulo> instalado» com o comando a executar como root no servidor (`manage.py setup-modules`) e um botão **Copiar**: ele dá ao usuário `localsiem` acesso de leitura às pastas listadas em `read_paths` do `module.json` do módulo (`/var/log/apache2` para o módulo apache2, `/var/log/audit` para o módulo privesc), inclusive aos arquivos das próximas rotações, e reinicia o localSIEM. Esse acesso de leitura é tudo de que um módulo precisa: os módulos não têm opções de configuração e nunca alteram o servidor (seções 8 e 11). Até que ele seja executado, o módulo pode mostrar «Erro»: os logs dele ainda não podem ser lidos. A caixa de diálogo é fechada com «Fechar» ou com «Ver os módulos instalados», que abre Instalados.

**Atualizar.** Quando Módulos › **Instalados** é aberto, a interface web consulta o repositório, e um módulo que tem lá uma versão mais nova mostra um aviso com **Atualizar** (seção 3). Depois que você confirma, o localSIEM baixa a nova versão e a coloca no lugar da instalada (passos 1 a 3), mantém as configurações dele e deixa o módulo ativado ou desativado como estava. O comando para o root só é mostrado novamente se a nova versão lê outros logs (`read_paths`); caso contrário, não há nada a executar. Uma atualização do localSIEM mantém os módulos instalados e o acesso de leitura deles.

**Reinstalar.** A interface web não reinstala um módulo nem instala uma versão mais antiga dele: para reinstalar um módulo, clique em **Desinstalar** (seção 3) e instale-o novamente a partir de **Instaláveis**; as configurações dele são mantidas.

**Instalar um módulo nunca instala o software que ele monitora.** O módulo apache2 não instala o Apache nem o ModSecurity, e o módulo privesc não instala o auditd, um daemon de syslog nem o snoopy. Se, na primeira instalação, faltar ao servidor o que o módulo precisa (Apache e ModSecurity para o apache2; para o privesc, uma fonte que o `localsiem` possa ler, seção 14), o módulo é instalado **desativado**: a caixa de diálogo lista o que falta em vez do comando, e o módulo não pode ser ativado até que **Reconfigurar** encontre o que falta (seção 4). Uma atualização mantém o módulo ativado ou desativado como estava.

<a id="modules-page"></a>
## 3. A página Módulos

Os administradores abrem **Administração › Módulos**, que tem duas seções, cada uma no seu próprio endereço: **Instalados** (`/admin/dashboard/modules/installed/`), que abre por padrão (`/admin/dashboard/modules/` leva até lá), e **Instaláveis** (`/admin/dashboard/modules/installable/`). Os analistas veem **Módulos** no painel deles (`/user/dashboard/modules/`): só a lista dos módulos instalados, somente leitura, sem seções.

**Instalados** mostra uma linha por módulo instalado, em toda a largura: o nome, o id, a versão, um indicador de estado, o resumo e, abaixo dele, os motivos desse estado. A lista se atualiza sozinha a cada 10 segundos. Sem nenhum módulo instalado, ela diz «Instale módulos pela aba Instaláveis.» (aos analistas: «Nenhum módulo instalado. Um administrador os instala em Módulos › Instaláveis.»).

| Estado | Significado |
|---|---|
| **Ativado e funcionando** | Ativado, carregado pelo coletor e lendo as fontes dele. Os avisos do diagnóstico são listados como notas, mas não mudam o estado. |
| **Ativado, com avisos** | Ativado, mas não foram encontrados logs para ler, uma fonte ainda não existe ou o módulo foi instalado depois que o coletor iniciou (reinicie o serviço `localsiem`). |
| **Erro** | O módulo não carrega (o erro é mostrado), o diagnóstico dele relata um erro ou uma fonte não pode ser lida (permissões do usuário `localsiem`). |
| **Desativado** | Desativado, ou instalado sem os requisitos dele (para o apache2: falta o Apache ou o ModSecurity; para o privesc: o `localsiem` não consegue ler nem o log do auditd nem o syslog), como diz o motivo. |
| **Aplicando a alteração…** | Acabou de ser ativado ou desativado: o coletor está aplicando a alteração. |
| **Desconhecido** | O coletor (serviço `localsiem`) não está em execução, então nada está sendo lido. |

Quando o módulo não está desativado, a linha também mostra: **Fontes em leitura** (lidas / encontradas), **Linhas (1 h)**, **Últimos dados**, **Eventos (24 h)**, **Bloqueados (24 h)** e as contagens do **Diagnóstico** («n OK · n avisos · n erros»).

Os administradores também têm, em cada linha:

- **O interruptor** de cada módulo. Desativar um módulo pede confirmação: o localSIEM para de ler os logs dele e de enviar os alertas dele até que ele seja ativado novamente; o que já está armazenado é mantido. Ativá-lo começa a leitura imediatamente. Enquanto faltar um requisito do módulo, o interruptor fica bloqueado («Desativado: faltam requisitos»): **Reconfigurar** (seção 4) o desbloqueia assim que encontra o que falta.
- **Configurar**, que abre a página do módulo, `/admin/dashboard/modules/installed/<name>/` (seção 4); o endereço antigo `/admin/dashboard/modules/<name>/` leva até ela.
- **Desinstalar**, também em um módulo que não carrega (e na página do módulo). Depois que você confirma, o localSIEM exclui `/opt/localsiem/modules/<name>/` e reinicia o coletor sem ele: para de ler os logs dele e de enviar os alertas dele. Os eventos já armazenados ainda podem ser pesquisados, e as configurações dele são mantidas, caso você o instale novamente. O acesso de leitura que o root deu ao `localsiem` sobre os logs dele não é retirado.
- **Atualizar**, quando o repositório tem uma versão mais nova do módulo. Cada vez que Instalados é aberto, a interface web consulta o repositório («Consultando o repositório em busca de versões mais novas…»; o navegador reutiliza a resposta por 10 minutos), e uma linha cujo módulo tem uma versão mais nova mostra «O repositório tem a versão X (a instalada é a Y).» com o botão **Atualizar**. Depois que você confirma, o localSIEM instala a nova versão (seção 2), mantém as configurações dele, deixa o módulo ativado ou desativado como estava e reinicia o coletor; uma caixa de diálogo mostra o comando para o root só se a nova versão lê outros logs. Se a nova versão precisa de um localSIEM mais recente, o aviso diz «O repositório tem a versão X, mas ela precisa do localSIEM Z ou mais recente: atualize o localSIEM para instalá-la.» e não tem botão.

**Instaláveis** (só administradores) tem o cartão «Módulos instaláveis». **Consultar o repositório** baixa o repositório e lista os módulos que ainda não estão instalados neste servidor, cada um com o nome, o id, a versão e o resumo dele e um botão ou uma nota:

| Botão ou nota | Significado |
|---|---|
| **Requisitos** | Mostra o que o módulo precisa no servidor e os comandos que o instalam, como root e com sudo (abaixo) |
| **Instalar** | Instala o módulo (seção 2) |
| «Precisa do localSIEM X ou mais recente» | Não pode ser instalado: atualize o localSIEM primeiro |
| «O módulo do repositório não é válido» | Não pode ser instalado |

Os módulos já instalados nunca aparecem aqui: eles são atualizados a partir de Instalados. Se todos os módulos do repositório estiverem instalados, o cartão diz «Todos os módulos do repositório já estão instalados.». Depois da instalação, a caixa de diálogo «<módulo> instalado» mostra o comando a executar como root para que o `localsiem` possa ler os logs do módulo (seção 2), com um botão **Copiar**; até que ele seja executado, o módulo pode mostrar «Erro»: os logs dele ainda não podem ser lidos. Se faltar ao servidor o que o módulo precisa, a caixa de diálogo lista em vez disso o que falta, com a dica de abrir o módulo em Instalados (**Configurar**) e clicar em **Reconfigurar** assim que estiver presente.

**Requisitos** abre «<módulo>: requisitos»: o que o módulo precisa no servidor e os comandos que o instalam no sistema deste servidor («Este servidor: …»), declarados pelo módulo (`install_requirements` do `module.json` dele), duas vezes, cada uma com **Copiar**: **Como root** e **Com sudo** (os mesmos comandos com `sudo` na frente). Execute-os no servidor antes de instalar o módulo: instalá-lo nunca instala esse software, e o localSIEM nunca os executa. Para o módulo apache2, no Debian: `apt-get -y update`, `apt-get -y install apache2 libapache2-mod-security2 modsecurity-crs`, `a2enmod security2 unique_id`, `cp --update=none /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf` (ele só cria a configuração do ModSecurity, DetectionOnly, quando não existe nenhuma) e `systemctl restart apache2`; no Alpine, só o Apache (`apk add apache2`, depois `rc-update` e `rc-service` para iniciá-lo), porque o Alpine não tem pacote do ModSecurity 2: até que o ModSecurity seja compilado a partir do código-fonte e carregado, o módulo fica desativado. Para o módulo privesc: `apt-get -y install auditd rsyslog` no Debian, e `apk add audit` com o auditd iniciado no boot no Alpine; basta uma fonte legível, e em um contêiner o auditd não funciona.

<a id="apache-page"></a>
## 4. A página do módulo Apache

`/admin/dashboard/modules/installed/apache2/` (só administradores; o antigo `/admin/dashboard/modules/apache2/` leva até ela) tem cinco partes:

1. **Cabeçalho**: nome, id, versão, o caminho de instalação (`/opt/localsiem/modules/apache2`), o interruptor, o estado com os motivos dele e os números da seção 3. **Voltar aos módulos instalados** volta para Instalados; **Descobrir novamente e executar o diagnóstico** lê novamente a configuração do Apache na hora e atualiza o diagnóstico; **Reconfigurar** procura novamente o Apache e o ModSecurity (abaixo); **Desinstalar** desinstala o módulo (seção 3) e volta para Instalados.
2. **Configurações**: o formulário da seção 5. **Salvar as configurações** verifica cada valor e, se algum estiver errado, diz qual («Valor inválido: …»).
3. **Fontes**: cada log em leitura, com **Tipo** (`access`, `error`, `audit`), **Caminho**, **Vhost**, **Linhas (1 h)**, **Não analisadas (1 h)**, **Últimos dados** (por exemplo `2026/10/29@13:59:59.723`) e **Estado** (erro se não puder ser lido, aviso se ainda não existir). Abaixo, os logs encontrados mas não lidos, com o motivo: «log por pipe, não suportado», «coberto por um GlobalLog que grava todos os vhosts» ou «o formato dele não tem dados: cada linha é o mesmo texto (um apelido de LogFormat que não está definido)».
4. **Diagnóstico**: as verificações da seção 7, com a hora em que foram executadas. Cada requisito ausente (ModSecurity, o CRS, `SecRuleEngine`, `mod_unique_id`, o acesso de leitura do `localsiem`) vem com o trecho de configuração ou o comando que o resolve e um botão **Copiar**. As verificações sobre os logs apenas os descrevem e dizem o que o localSIEM consegue ler deles, sem correção: os logs do cliente nunca são alterados (seção 8).
5. **Regras**: as regras da seção 9, cada uma com **Ativa**, **Regra** (nome, id e categoria), **Severidade**, **Limite** e **Janela (s)**, e **Salvar as regras**.

**Requisitos e Reconfigurar.** Enquanto faltar o Apache ou o ModSecurity, o módulo fica desativado e o cabeçalho lista o que falta, com o comando que o instala. **Reconfigurar** (também quando o módulo está desativado) procura-os novamente com as configurações salvas; se o Apache estiver em um local fora do padrão, defina primeiro **Arquivo de configuração do Apache** (seção 5). Quando os dois são encontrados, ele desbloqueia o interruptor —ativar o módulo é decisão sua— e mostra o comando a executar como root para que o `localsiem` possa ler os logs do Apache criados depois que o módulo foi instalado. Um módulo que está ativado e perde o Apache ou o ModSecurity continua ativado: o diagnóstico e os avisos de saúde (seção 10) relatam isso.

**Cada alteração é aplicada na hora, sem reiniciar nada**: a interface web a salva e avisa o coletor, que recarrega as configurações dele, descobre novamente as fontes e executa o diagnóstico. Se o coletor não responder, a interface web avisa, e a alteração é aplicada quando o coletor iniciar.

<a id="settings"></a>
## 5. Configurações do módulo Apache

| Configuração | Padrão | O que faz |
|---|---|---|
| **Só as fontes abaixo** | desativado | Não descobrir os logs a partir da configuração do Apache: ler só as fontes adicionadas manualmente. |
| **Fontes adicionadas manualmente** | nenhuma | Logs a ler além dos descobertos (ou em vez deles, com a opção acima). Até 50. |
| **Arquivo de configuração do Apache** | vazio | Vazio: encontrado automaticamente (`/etc/apache2/apache2.conf` no Debian, `/etc/apache2/httpd.conf` no Alpine; `/etc/httpd/conf/httpd.conf` também é reconhecido). Um caminho absoluto usa esse arquivo em vez disso, se ele existir. |
| **Intervalo de descoberta (segundos)** | 3600 | Com que frequência a configuração do Apache é lida novamente para encontrar novos vhosts e logs (60 a 86400). |
| **Limite de bloqueio do ModSecurity** | 0 | 0: lido da configuração do CRS (`tx.inbound_anomaly_score_threshold` em `crs-setup.conf`), 5 se não estiver lá. Usado para distinguir uma correspondência acima do limite de bloqueio de uma abaixo dele quando as próprias mensagens do ModSecurity não informam o limite (0 a 1000). |
| **Dias de aprendizado para novos arquivos PHP** | 3 | Durante os primeiros dias depois que o módulo iniciou pela primeira vez, um arquivo PHP nunca visto antes não é relatado como novo pela regra `apache-webshell` (0 a 365). Um arquivo criado ou modificado no DocumentRoot dele no último dia sempre conta como novo. |

Cada **fonte adicionada manualmente** tem estes campos (* obrigatório):

| Campo | Uso |
|---|---|
| **Tipo** * | `access.log`, `error.log` ou `Log de auditoria do ModSecurity` |
| **Caminho** * | Caminho absoluto do arquivo |
| **Vhost** | Vhost das linhas, para logs cujas linhas não o informam |
| **LogFormat** | Para logs de acesso: um apelido (`localsiem_combined`, `combined`, `vhost_combined`, `common`, `combinedio` ou um definido na configuração do Apache) ou o próprio formato. Vazio: os formatos habituais são testados. |
| **Tipo de log de auditoria** | `Serial (um único arquivo)` ou `Concorrente (um arquivo por requisição)` |
| **Pasta de armazenamento da auditoria** | Para o tipo concorrente: a pasta de `SecAuditLogStorageDir` |

Um arquivo é lido só uma vez, mesmo que seja descoberto e também adicionado manualmente. Uma fonte que aparece enquanto o localSIEM está em execução é lida desde o início se tiver 5 MB ou menos, e a partir do fim caso contrário.

Duas configurações de **Administração › Configurações** do localSIEM também atuam sobre este módulo: a **janela de correlação** (5 segundos: quanto tempo se esperam os três registros de uma requisição) e a **severidade abaixo do limite** (`low`). Uma requisição que o ModSecurity sinalizou também espera o registro de auditoria dela, que o ModSecurity grava quando a requisição termina, por até 2 minutos: assim uma requisição lenta não é dividida em dois eventos.

<a id="soc"></a>
## 6. O que o módulo Apache envia ao SOC

Para cada requisição, o módulo junta a linha de acesso, as linhas de erro e o registro de auditoria com o mesmo `UNIQUE_ID`. Os logs de acesso que o Apache grava por padrão (`combined`, `vhost_combined`, `common`) não têm `UNIQUE_ID`: nesse caso, cada linha de acesso é unida ao registro de auditoria e às linhas de erro da própria requisição por IP do cliente, método, URI, status e hora (±2 segundos), mesmo quando a mesma requisição se repete no mesmo segundo, e o evento é marcado como «correlação fraca». O vhost vem de `%v` ou, se o formato não o tiver, do cabeçalho Host e da porta do registro de auditoria, escolhido da mesma forma que o Apache o escolhe; a hora usa os microssegundos do registro de auditoria. Depois, o módulo decide se algo já foi feito a respeito («ação tomada»), lendo primeiro o log de auditoria (`Action: Intercepted (phase N)`) e depois o error.log (`Access denied with code NNN (phase N)`). Um 403 sem nenhum rastro do ModSecurity não é considerado um bloqueio: é marcado como duvidoso.

| Situação | Vai para o SOC? |
|---|---|
| Bloqueado pelo ModSecurity nas fases 1-2 (a aplicação nunca o recebeu) | **Não.** Fica no localSIEM, disponível para pesquisa (`action:blocked`), e é contado no contexto do próximo alerta desse IP. |
| Bloqueado nas fases 3-4 (a aplicação já o havia executado) | Sim |
| Correspondências de regras com o motor em `DetectionOnly` | Sim |
| Correspondências de regras abaixo do limite de bloqueio | Sim |
| Sinais das regras da seção 9 | Sim |

Severidade dos alertas gerados por correspondências do ModSecurity (arquivo `severity.yaml` do módulo):

| Situação | Severidade |
|---|---|
| Correspondências não bloqueadas, resposta 3xx, 4xx ou 5xx | média |
| Correspondências não bloqueadas, resposta 2xx | alta |
| Bloqueado nas fases 3-4 | alta |
| Sinais de sucesso: uma regra de saída (950-955) correspondeu e nada foi bloqueado, ou um erro de banco de dados seguiu a requisição | crítica |
| Abaixo do limite de bloqueio (muitas vezes um falso positivo da própria aplicação) | baixa (a severidade abaixo do limite de Administração › Configurações) |

Cada alerta tem um nome estável (por exemplo «Apache/ModSecurity: SQL injection not blocked (CRS 942)»), uma descrição que termina com a consulta a colar na pesquisa do localSIEM (por exemplo `ip:203.0.113.7 category:sqli`) e detalhes: vhost, IP do cliente, método, URI (mascarada), resposta, user agent e os dados do ModSecurity (motor, ação, fase, pontuação de anomalia, limite, regras e dados correspondidos). Quando sai, o alerta também leva o contexto do IP: requisições e requisições bloqueadas da última hora, as regras que o bloquearam e a primeira vez em que foi visto.

Senhas, cookies, cabeçalhos `Authorization` e tokens são mascarados antes de qualquer coisa ser armazenada, também dentro dos corpos das requisições, e os corpos das requisições nunca viajam para o SOC. O corpo da resposta (parte E) e o texto completo das regras executadas (parte K) do log de auditoria nunca são guardados.

<a id="doctor"></a>
## 7. Requisitos do Apache e do ModSecurity: o diagnóstico

O diagnóstico do módulo apache2 lê a configuração do Apache (sem alterá-la) e verifica cada requisito. Ele é executado quando o coletor inicia, depois de cada alteração das configurações, em cada descoberta, com **Descobrir novamente e executar o diagnóstico** e com `manage.py doctor` (seção 17), só enquanto o módulo está ativado: enquanto ele está desativado porque falta o Apache ou o ModSecurity, a página do módulo mostra esses requisitos em vez disso (seção 4). Status: OK, aviso (funciona com limitações), erro (precisa ser corrigido) e info (só importa em algumas situações).

| Verificação | Correto quando | Caso contrário |
|---|---|---|
| Configuração do Apache | `apache2.conf` ou `httpd.conf` (ou o arquivo configurado) é encontrado e lido | Erro: adicione as fontes manualmente (seção 5). As partes que não podem ser lidas são listadas como avisos. |
| ModSecurity | `mod_security2` (ModSecurity 2) está carregado | Erro. Debian: `apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`. O Alpine não tem pacote: compile o mod_security2 2.9 a partir do código-fonte. O ModSecurity 3 (libmodsecurity) não é suportado. |
| OWASP CRS | Os arquivos do CRS estão incluídos (o diagnóstico mostra quantos e o limite de anomalia) | Erro: `apt-get install modsecurity-crs`, ou inclua `crs-setup.conf` e `rules/*.conf` depois do ModSecurity |
| SecRuleEngine | `On` (as requisições acima do limite são bloqueadas na fase 2 e ficam no localSIEM) ou `DetectionOnly` (nada é bloqueado: cada correspondência vai para o SOC) | Erro se for `Off`; aviso se for `Off` exceto em alguns vhosts, se estiver ausente (nesse caso o ModSecurity assume `Off` por padrão) ou se alguns vhosts o definem como `Off` |
| mod_unique_id | Carregado: o ModSecurity funciona e as três fontes de uma requisição são unidas por `UNIQUE_ID` | Erro se o ModSecurity estiver carregado: o ModSecurity 2 não inspeciona nada sem ele (o Alpine não o carrega); caso contrário, aviso (correlação fraca). Debian: `a2enmod unique_id`; Alpine: `LoadModule unique_id_module modules/mod_unique_id.so` |
| Formato do log de acesso | Os logs de acesso têm IP do cliente, hora, linha da requisição e status, como têm os formatos que o Apache grava por padrão (OK, «Access logs in the format Apache writes»): cada linha é unida aos registros do ModSecurity da própria requisição por IP do cliente, método, URI, status e hora. Com milissegundos, vhost e `UNIQUE_ID` no formato (por exemplo `localsiem_combined`, nos servidores que já o gravam), elas são unidas por `UNIQUE_ID` (OK, «Access log with milliseconds, vhost, duration and UNIQUE_ID») | Info, sem correção, se a um log de acesso faltar qualquer um dos quatro: o localSIEM o lê como está, mas não consegue unir as linhas dele aos registros do ModSecurity (essas requisições são vistas no log de auditoria); info se nenhum log de acesso for lido (as requisições são vistas no log de erros e no log de auditoria). O formato dos logs é do cliente (seção 8) |
| mod_remoteip | Carregado com `RemoteIPHeader` | Info, sem correção: se o site estiver atrás de um proxy ou de um balanceador de carga, os logs contêm o IP do proxy, assim como os alertas e as regras por IP |
| Log de auditoria | `SecAuditEngine RelevantOnly` (ou `On`) com um `SecAuditLog` | Aviso se estiver desativado: o localSIEM decide só a partir do error.log, e o cartão da requisição não tem cabeçalhos nem lista de regras. Quando está ativado, as notas dele apenas o descrevem: tipo concorrente (um arquivo por transação; o ModSecurity costuma criá-los com modo 600, e o localSIEM os lê se o `localsiem` puder), formato nativo (lido como está), parte E registrada (nunca vai para o SOC), parte H ausente (a ação tomada não pode ser lida do log de auditoria; a única nota que transforma a verificação em aviso). Sem correção: o log de auditoria é configurado pelo cliente (seção 8) |
| Mascaramento na origem | Existe uma ação `sanitise` | Info, sem correção («The audit log on disk is not masked»): o arquivo gravado pelo ModSecurity pode conter senhas e cookies; o localSIEM os mascara antes de armazená-los, e eles nunca vão para o SOC |
| Permissões | O `localsiem` consegue ler todas as fontes | Erro. Debian: `usermod -aG adm localsiem`; Alpine: os comandos `setfacl` mostrados. Uma fonte que ainda não existe é só info. |
| Logs por pipe | — | Aviso: `\|/usr/bin/rotatelogs ...` e o syslog não podem ser lidos; grave o log também em um arquivo, ou adicione a fonte manualmente |
| Log de acesso sem dados | — | Aviso: um `CustomLog` usa um formato que nenhum `LogFormat` define (ou um `LogFormat` sem nenhuma diretiva `%`), então o Apache grava esse mesmo texto em cada linha, sem o IP do cliente, a hora ou a requisição. O localSIEM não lê esse log e vê as requisições do vhost dele no log de erros dele e no log de auditoria do ModSecurity. O formato dos logs do servidor nunca é alterado. |
| Motor visto como Off | — | Erro: os registros de auditoria informam o motor como desativado |
| Versão do ModSecurity | — | Info: a versão lida do log de auditoria |

Quando a configuração tem um `GlobalLog` cujo formato tem `%v` (ele grava todos os vhosts), os outros logs de acesso não são lidos: eles só repetiriam as linhas dele. O diagnóstico nunca propõe alterar o formato dos logs nem as configurações do log de auditoria (seção 8).

<a id="client-logs"></a>
## 8. Os logs do cliente nunca são tocados

O módulo apache2 apenas **lê** os logs do Apache e do ModSecurity: nunca grava neles, nem os rotaciona, trunca, move ou exclui, e nunca altera o formato deles nem a configuração do Apache ou do ModSecurity que os grava. Se um servidor grava os logs em um formato próprio (por exemplo, um `LogFormat` próprio, ou o IP do cliente que o `mod_remoteip` fornece), o módulo se adapta a ele: lê cada log de acesso com o formato que o `CustomLog` dele usa. O diagnóstico (seção 7) apenas descreve os logs e o que o localSIEM consegue ou não ler deles, sem propor alterá-los; ele só dá uma correção para o que não é um log: o ModSecurity, o CRS, `SecRuleEngine`, `mod_unique_id` e o acesso de leitura do usuário `localsiem`. A única coisa feita como root para este módulo é esse acesso de leitura (`manage.py setup-modules`, seção 2).

As versões 1.2.0 e anteriores do módulo tinham a opção de configuração `--configure-apache`, removida na versão 1.3.0. Os servidores em que ela foi aplicada mantêm o arquivo que ela gravou, `/etc/apache2/conf-available/localsiem.conf` (Debian) ou `/etc/apache2/conf.d/localsiem.conf` (Alpine), com o formato `localsiem_combined` e o `GlobalLog` dele (`localsiem_access.log`), configurações do log de auditoria e um `SecAction` que mascara valores sensíveis. Enquanto esse arquivo estiver lá, o módulo lê esses logs como quaisquer outros. Para desfazer isso, exclua esse arquivo (Debian: `a2disconf localsiem`) e recarregue o Apache. No Alpine, esse arquivo também carregava o `mod_unique_id` e o `mod_logio`: carregue o `mod_unique_id` em outro lugar da configuração do Apache antes de excluí-lo, porque o ModSecurity 2 não inspeciona nada sem ele (seção 7). O instalador do localSIEM exclui esse arquivo com `--uninstall` ou `--reinstall` (no Alpine, carregue antes o `mod_unique_id` em outro lugar), e deixa os logs (`localsiem_access.log`, `modsec_audit.log`) onde estão.

<a id="rules"></a>
## 9. Regras do módulo Apache

As regras são avaliadas em cada evento. Um sinal de uma regra sempre vai para o SOC. Na página do módulo, cada regra pode ser desativada, e a severidade, o limite (1 a 100000) e a janela (1 a 86400 segundos) dela podem ser alterados; o limite e a janela só se aplicam às regras de limite e de sequência. Os eventos dela podem ser encontrados com `rule:localsiem:<id>`.

| Regra | Tipo | Severidade | Quando | Limite / janela |
|---|---|---|---|---|
| `apache-bruteforce` «força bruta contra uma página de login» | limite | média | Requisições POST não bloqueadas de um IP para uma página de login de um vhost (`/wp-login.php`, `/xmlrpc.php`, `/administrator/index.php`, `/user/login`, `/login`, `/admin/login`, `/login.php`, `/admin.php`, `/signin`, `/auth/login`, `/phpmyadmin/index.php`) | 20 em 300 s |
| `apache-login-after-bruteforce` «login bem-sucedido depois de uma força bruta» | sequência | alta | Pelo menos 10 logins com falha (POST respondido com 200, 401 ou 403) a uma página de login, e depois um respondido com 302 ou 303 (o WordPress responde 200 a um login com falha e 302 a um correto) | 10, em até 1800 s |
| `apache-enumeration` «enumeração (rajada de respostas 404)» | limite | média | Respostas 404 não bloqueadas a um IP a partir de um vhost | 30 em 60 s |
| `apache-sensitive-file` «arquivo sensível servido» | correspondência | alta | Uma resposta 2xx para um arquivo que não deveria ser público: `.env`, `.git/`, `.svn/`, `.hg/`, `.htaccess`, `.htpasswd`, dumps e backups (`.sql`, `.sql.gz`, `.bak`, `.old`, `.orig`, `.swp`, `.save`, `.backup`, `.dump`, nomes terminados em `~`), `phpinfo`, `info.php`, `server-status`, `server-info`, cópias de `wp-config.php` e `config.php`/`config.inc`, `.DS_Store`, chaves SSH privadas, `composer.json`/`composer.lock`, `.aws/`, `backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «possível web shell (POST para um novo arquivo PHP)» | correspondência | crítica | Um POST respondido com 2xx para um arquivo PHP criado ou modificado no DocumentRoot dele no último dia, ou visto pela primeira vez na última hora (depois dos dias de aprendizado) | — |
| `apache-db-error-after-attack` «erro de banco de dados depois de uma requisição suspeita» | sequência | crítica | Uma requisição que correspondeu a regras do CRS e, a partir do mesmo IP, um erro de banco de dados (SQL ou PDO) no error.log | 1, em até 30 s |

<a id="health"></a>
## 10. Avisos de saúde do módulo Apache

Além dos avisos de saúde do próprio localSIEM, o módulo verifica a cada 5 minutos, no máximo, e envia ao SOC:

| Aviso | Severidade | O que fazer |
|---|---|---|
| O ModSecurity não está mais carregado | alta | Estava carregado e não está mais: as requisições não são inspecionadas. Se ninguém fez isso de propósito, alguém pode ter desativado a proteção. |
| Motor do ModSecurity passado para Off | alta | `SecRuleEngine` mudou para `Off`, ou o log de auditoria informa o motor como desativado. Verifique a configuração do Apache e as alterações recentes dela. |
| Falta o IP real do cliente (mod_remoteip) | média | Na última hora, pelo menos 90 % de pelo menos 100 requisições vieram de um único endereço privado ou local: o site provavelmente está atrás de um proxy e o Apache registra o IP do proxy, então as regras por IP não funcionam para essas requisições. Enviado no máximo uma vez por dia. |

O que já foi relatado é lembrado entre reinicializações, então uma atualização não o envia novamente. Por causa desses avisos, um módulo que está ativado nunca é desativado por conta própria quando o Apache ou o ModSecurity desaparece.

<a id="privesc"></a>
## 11. O módulo de escalonamento de privilégios

O módulo **privesc** («Escalonamento de privilégios») monitora o que pessoas e serviços executam no servidor e relata as etapas de um escalonamento até root: reconhecimento, a busca por programas setuid, ferramentas de enumeração como o linpeas, exploits conhecidos, reverse shells, root obtido sem sudo nem su, os backdoors deixados para trás e as tentativas de cegar o monitoramento. Ele também revisa a superfície de ataque do servidor: programas setuid, capabilities e arquivos sensíveis graváveis por outros (seção 16).

Ele só lê o que o servidor já tem: nunca instala nada, nunca carrega regras de auditoria e nunca altera a configuração do auditd, do snoopy ou dos shells. Ele lê até duas fontes:

| Fonte | O que vê | Onde funciona |
|---|---|---|
| **auditd** (`/var/log/audit/audit.log`) | sudo, su, pkexec e logins SSH (PAM) e tudo o que as regras de auditoria do servidor registram (abaixo) | Servidores físicos e máquinas virtuais, enquanto o auditd está em execução. **Não dentro de um contêiner** (LXC, podman, systemd-nspawn, Docker): a auditoria do kernel não tem namespaces, então o auditd só funciona no host. |
| **syslog** (`/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`) | sudo, su, pkexec, doas, logins SSH e, se o **snoopy** estiver instalado, cada programa executado | Em todo lugar, contêineres incluídos. Lido quando o auditd não está em execução, quando o log dele não pode ser lido ou quando o snoopy está instalado (configuração **Ler o syslog**). Ele precisa de um daemon de syslog que grave um arquivo: o journal do systemd sozinho não é lido. |

O que o auditd mostra depende das regras de auditoria que o servidor carrega, que são decisão do administrador dele; o módulo as usa como estão, sejam quais forem as chaves delas, e classifica cada registro pelo tipo, pela chamada de sistema e pelos arquivos dele:

| O módulo vê | Quando as regras de auditoria do servidor registram |
|---|---|
| Cada programa executado (também a partir de scripts, web shells e exploits), programas setuid, root herdado deles, capabilities obtidas | `execve` |
| Alterações de contas, sudoers, PAM, preload, SSH, cron, serviços e `/etc/audit` | Monitoramentos (`-w ... -p wa`) sobre esses arquivos ou as chamadas de sistema que os alteram |
| Bits setuid ou setgid definidos | `chmod`, `fchmod`, `fchmodat` |
| Módulos do kernel carregados ou removidos | `init_module`, `finit_module`, `delete_module` |
| Processos anexados com ptrace | `ptrace` |
| Arquivos negados a uma pessoa | `open`, `openat`, `execve`... que falham com `EACCES` ou `EPERM` |
| Regras de auditoria removidas, auditoria desativada, auditd parado, programas que travam | Sempre (o kernel e o auditd os informam) |

Em um servidor físico ou em uma máquina virtual, o auditd é a fonte que um usuário não consegue evitar; o diagnóstico diz o que as regras de auditoria do servidor registraram até agora (seção 14). Em um contêiner, o snoopy é a única forma de ver cada programa executado.

Os comandos internos do shell (`pwd`, `cd`, `unset HISTFILE`, `history -c`) nunca executam um programa, então nenhuma fonte os vê, exceto dentro de uma linha de comando como `bash -c '...'`. Um único `whoami` nunca é um alerta: o módulo conta os comandos de reconhecimento **distintos** de cada sessão dentro de uma janela, e só uma rajada deles é (seção 13).

O que cada evento do módulo contém, e como pesquisá-lo:

| Coluna | Contém | Exemplo de pesquisa |
|---|---|---|
| `vhost` | A pessoa: o usuário do login (ele continua o mesmo através de sudo e su) | `module:privesc vhost:alice` |
| `method` | Tipo de evento: `exec` (programa executado, auditd ou snoopy), `sudo`, `su`, `pkexec`, `doas`, `login`, `pam`, `file` (arquivo sensível alterado), `chmod` (bit setuid), `kmod`, `ptrace`, `denied` (arquivo negado), `audit_config`, `auditd`, `crash`, `syscall` (outra chamada de sistema registrada pelas regras de auditoria do servidor) | `module:privesc method:sudo` |
| `uri` | A linha de comando (senhas mascaradas) | `module:privesc uri:*linpeas*` |
| `path` | O programa executado, ou o arquivo alterado | `module:privesc path:/tmp/*` |
| `ip` | O endereço SSH da sessão, quando é conhecido | `module:privesc ip:203.0.113.7` |
| `score` | Comandos de reconhecimento distintos da sessão na janela | `module:privesc score:>=8` |
| `action` | `blocked` quando o próprio sistema o impediu: um programa que não pôde ser executado, sudo ou su recusado, um arquivo negado | `module:privesc action:blocked` |
| `source` | `audit` ou `syslog` | `module:privesc source:syslog` |

As regras sobre tentativas (falhas repetidas de sudo, muitos arquivos negados) contam os eventos bloqueados mesmo assim; as outras só olham o que realmente foi executado.

A página do módulo, `/admin/dashboard/modules/installed/privesc/`, tem as mesmas partes que a página do módulo Apache (seção 4): cabeçalho (com **Descobrir novamente e executar o diagnóstico**, **Reconfigurar** e **Desinstalar**), configurações (seção 12), fontes (`audit`, `syslog`; e as não lidas, com o motivo), diagnóstico (seção 14) e regras (seção 13).

<a id="privesc-settings"></a>
## 12. Configurações do módulo de escalonamento de privilégios

| Configuração | Padrão | O que faz |
|---|---|---|
| **Log de auditoria** | vazio | Vazio: `log_file` de `/etc/audit/auditd.conf`, ou `/var/log/audit/audit.log`. |
| **Ler o syslog** | Automático | Automático: só quando o auditd não está em execução, o log dele não pode ser lido ou o snoopy está instalado. Sempre, ou Nunca. |
| **Arquivo do syslog** | vazio | Vazio: `/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`, o primeiro que existir. |
| **Usuários ignorados** | vazio | Separados por vírgula. Os comandos deles são armazenados e podem ser pesquisados, mas nunca geram alerta: contas de automação (ansible, backups). O usuário `localsiem` é sempre ignorado. |
| **Grupos de administradores** | `sudo,wheel,admin` | Separados por vírgula. Os membros deles (e o root) recebem o limite de reconhecimento mais alto e podem listar os seus direitos de sudo sem alerta. |
| **Janela de reconhecimento (segundos)** | 120 | Janela em que os comandos de reconhecimento distintos de uma sessão são contados (10 a 3600). |
| **Limite de reconhecimento** | 8 | Comandos de reconhecimento distintos na janela que formam uma rajada, para usuários e contas de serviço (2 a 500). |
| **Limite de reconhecimento para administradores** | 20 | O mesmo para o root e os administradores, que os executam como parte do trabalho (2 a 500). |
| **Limite de enumeração automatizada** | 40 | Comandos de reconhecimento distintos na janela que só um script executa (ao estilo do linpeas), para todos (5 a 1000). |
| **Dias de aprendizado das contas de serviço** | 3 | Durante os primeiros dias depois que o módulo iniciou pela primeira vez, os programas que cada conta de serviço executa (`www-data` executando `sh -c sendmail`) são aprendidos sem alertas (0 a 365). |
| **Horas entre varreduras de programas setuid** | 24 | Com que frequência os programas setuid e setgid e as capabilities de arquivo são procurados (seção 16). 0: nunca (0 a 168). |
| **Pastas varridas** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | Separadas por vírgula; cada uma é percorrida sem sair do seu sistema de arquivos. As pastas dos contêineres e de `/proc` e `/sys` são sempre ignoradas. |
| **Intervalo de descoberta (segundos)** | 300 | Com que frequência o log de auditoria, o syslog e o estado do auditd são procurados (60 a 86400). O intervalo mais curto dos módulos ativados se aplica a todos eles. |

O que conta como reconhecimento: `whoami`, `id`, `groups`, `uname`, `hostname`, `w`, `who`, `last`, `ps`, `ss`, `netstat`, `ip`, `ifconfig`, `env`, `pwd`, `history`, `getcap`, `lsmod`, `dmesg`, `mount` e similares; `sudo -l`, `crontab -l`, `systemctl list-*`, as listas de pacotes; `which`, `locate`, `command -v`; `docker ps` e similares; cada `find` diferente; ler `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/*-release`, `/proc/version`, `/root/...`, históricos, chaves SSH e arquivos `.env`; listar `/root`, `/home`, `/opt`, `/tmp`, as pastas do cron...; `grep -r password`; e `<program> --version`. Cada comando diferente de uma sessão conta uma vez dentro da janela.

<a id="privesc-rules"></a>
## 13. O que o módulo de escalonamento de privilégios envia ao SOC: as regras dele

Cada alerta do módulo vem de uma das regras dele (elas funcionam da mesma forma seja qual for a fonte que viu o comando), exceto os da seção 16. Assim como no Apache, cada regra pode ser desativada e a severidade, o limite e a janela dela podem ser alterados na página do módulo; os eventos dela podem ser encontrados com `rule:localsiem:<id>`. Nenhuma dispara para os **Usuários ignorados**. As regras marcadas com «auditd» precisam dos registros de auditoria da seção 11.

| Regra | Tipo | Severidade | Quando | Limite / janela |
|---|---|---|---|---|
| `privesc-recon-burst` «rajada de reconhecimento» | correspondência | média | A sessão atingiu o limite de reconhecimento (seção 12) | — |
| `privesc-enumeration` «enumeração automatizada (ao estilo do linpeas)» | correspondência | alta | A sessão atingiu o limite de enumeração automatizada, mesmo com um script renomeado | — |
| `privesc-suid-hunt` «busca por programas setuid ou capabilities» | correspondência | alta | `find ... -perm -4000` (ou `-u=s`, `/6000`, `-2000`...), `getcap -r`, `find -writable` | — |
| `privesc-sudo-list` «direitos de sudo listados por quem não é administrador» | correspondência | média | `sudo -l` por um usuário ou conta de serviço que não é administrador | — |
| `privesc-known-tool` «ferramenta de enumeração conhecida» | correspondência | alta | linpeas, LinEnum, lse.sh, linux-exploit-suggester, les.sh, pspy, unix-privesc-check, linuxprivchecker, traitor, BeRoot, GTFONow, PEASS, deepce, CDK, sudo_killer, suid3num, mimipenguin, LaZagne, pwncat, searchsploit | — |
| `privesc-exploit` «exploit conhecido» | correspondência | crítica | PwnKit, DirtyPipe, Dirty COW, Baron Samedit (`sudoedit -s '\'`), Looney Tunables (`GLIBC_TUNABLES`), GameOver(lay), nf_tables (CVE-2024-1086), CVE-2023-22809 (`EDITOR=... -- /...`), polkit CVE-2021-3560 (`dbus-send ... CreateUser`), `LD_PRELOAD` com sudo, um script com o nome de uma CVE, programas chamados `exploit`, `getroot`, `rootme` | — |
| `privesc-pwnkit` «PwnKit (pkexec executado sem argumentos)» | correspondência | crítica | `pkexec` executado com zero argumentos (auditd) | — |
| `privesc-pwnkit-log` «pkexec relata uma tentativa de PwnKit» | correspondência | crítica | O pkexec registra `GCONV_PATH`, «suspicious content» ou «was not found the /etc/shells» (syslog) | — |
| `privesc-suid-escape` «root herdado de um programa setuid» | correspondência | crítica | Um programa que não é setuid é executado com o uid efetivo do root e o uid real de um usuário: um programa setuid foi abusado (GTFOBins). Os auxiliares de montagem, o D-Bus, o polkit e o X são exceções. | — |
| `privesc-root-without-door` «root sem sudo, su nem pkexec» | correspondência | crítica | Uma sessão de uma pessoa cujo início foi visto executa programas como root sem ter passado por sudo, su, pkexec ou doas (exploits de kernel) (auditd) | — |
| `privesc-root-shell-interpreter` «shell de root iniciado por um interpretador» | correspondência | alta | Um shell é executado como root, iniciado por python, perl, ruby, awk, gdb... que um usuário comum estava executando (filho dele, ou o mesmo processo) (auditd) | — |
| `privesc-file-capabilities` «programa obteve capabilities de root do seu arquivo» | correspondência | alta | Um usuário executou um programa cujo arquivo lhe dá `cap_setuid`, `cap_dac_override`, `cap_sys_admin`... (auditd) | — |
| `privesc-tmp-exec` «programa executado a partir de uma pasta gravável por todos» | correspondência | alta | Um programa em `/tmp`, `/var/tmp`, `/dev/shm` ou `/run/user/<uid>` | — |
| `privesc-compile-tmp` «programa compilado em uma pasta temporária» | correspondência | alta | `gcc`, `cc`, `clang`, `make`... em uma pasta temporária ou sobre arquivos dela | — |
| `privesc-download-shell` «script baixado executado por um shell» | correspondência | alta | `curl ... \| sh`, `bash -c "$(curl ...)"`, `bash <(wget ...)`, ou um downloader seguido de um shell no mesmo pipeline | — |
| `privesc-reverse-shell` «reverse shell» | correspondência | alta | `/dev/tcp/`, `nc -e`, `ncat --exec`, `socat exec:`, `mkfifo ... \| nc`, sockets de python/perl/php/ruby/lua/node, `openssl s_client ... \| sh`, `awk /inet/tcp` | — |
| `privesc-tty-upgrade` «shell promovido a um terminal completo» | correspondência | alta | `pty.spawn`, `script ... /dev/null`, `stty raw -echo`, `socat ... pty`, `expect ... spawn sh` | — |
| `privesc-service-recon` «conta de serviço executou comandos de reconhecimento» | correspondência | alta | `www-data`, `mysql` e outras contas de serviço executando `whoami`, `id`, `uname`... (uma web shell) | — |
| `privesc-service-new-program` «conta de serviço executou um programa que nunca havia executado» | correspondência | alta | Depois dos dias de aprendizado, uma conta de serviço executa um shell, interpretador ou ferramenta que nunca executou (`sh -c id` onde só executava `sh -c sendmail`) | — |
| `privesc-container-escape` «contêiner usado para chegar ao host como root» | correspondência | alta | Alguém que não é root executa `docker run -v /:/...`, `--privileged`, `--pid=host`, `nsenter -t 1`, `lxc config set ... security.privileged true`, `lxc config device add ... source=/`, `debugfs /dev/...` | — |
| `privesc-auth-failures` «falhas repetidas de sudo ou su» | limite | média | sudo, su, pkexec ou doas com falha de um usuário | 3 em 600 s |
| `privesc-sensitive-file` «arquivo de contas, sudo, PAM ou preload alterado» | correspondência | alta | `/etc/passwd`, `shadow`, `group`, `gshadow`, `sudoers`, `sudoers.d`, `doas.conf`, `doas.d`, `ld.so.preload`, `ld.so.conf`, `ld.so.conf.d`, `pam.d`, `security` alterados por um programa que não é uma ferramenta de pacotes ou de contas (auditd) | — |
| `privesc-persistence-file` «arquivo de SSH, cron ou serviço alterado» | correspondência | média | `/root/.ssh`, `sshd_config`, `sshd_config.d`, arquivos do cron, `/etc/systemd/system`, `/etc/init.d`, `rc.local`, `/etc/local.d` alterados (auditd) | — |
| `privesc-monitoring-changed` «configuração do auditd alterada» | correspondência | média | `/etc/audit` alterado por um programa que não é uma ferramenta de pacotes (auditd) | — |
| `privesc-suid-set` «bit setuid ou setgid definido em um arquivo» | correspondência | alta | `chmod u+s`/`g+s` em um arquivo (não uma pasta) fora do gerenciador de pacotes (auditd) | — |
| `privesc-setcap` «capabilities de arquivo definidas» | correspondência | alta | `setcap ... cap_...` | — |
| `privesc-kernel-module` «módulo do kernel carregado a partir de uma sessão» | correspondência | alta | Um módulo carregado ou removido a partir da sessão de uma pessoa (auditd) | — |
| `privesc-ptrace` «processo anexado com ptrace» | correspondência | média | `PTRACE_ATTACH` ou `PTRACE_SEIZE` (auditd) | — |
| `privesc-denied-burst` «muitos arquivos negados (enumeração)» | limite | média | Arquivos negados (`EACCES`, `EPERM`) a um usuário (auditd) | 30 em 60 s |
| `privesc-sensitive-denied` «tentativa de ler os hashes das senhas ou arquivos do root» | correspondência | média | `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` ou `/root` negados a um usuário (auditd) | — |
| `privesc-history-tampering` «histórico do shell apagado ou desativado» | correspondência | média | `ln -s /dev/null ~/.bash_history`, `rm .bash_history`...; `unset HISTFILE`, `HISTFILE=/dev/null`, `HISTSIZE=0`, `history -c`, `set +o history` só dentro de uma linha de comando (`bash -c`), já que os comandos internos não executam nenhum programa | — |
| `privesc-audit-stop-command` «comando para desativar o auditd» | correspondência | crítica | `auditctl -e 0`, `auditctl -D`, `auditctl -a never`, `systemctl stop/disable/mask auditd`, `service auditd stop`, `pkill auditd`, apagar `/var/log/audit` ou `/etc/audit` | — |
| `privesc-audit-disabled` «auditoria desativada» | correspondência | crítica | O kernel informa `audit_enabled=0` (auditd) | — |
| `privesc-auditd-stopped` «auditd parado por um processo» | correspondência | alta | auditd parado a pedido de um processo que não é o init (um desligamento do servidor não é relatado) | — |
| `privesc-crash` «programa setuid ou temporário travou» | correspondência | média | Um programa setuid, ou um em uma pasta temporária, travou (auditd `ANOM_ABEND`): muitas vezes um exploit que falhou | — |

Cada alerta tem um nome estável, uma descrição que termina com a consulta a colar na pesquisa do localSIEM, e detalhes: usuário, tipo de conta (`root`, `admin`, `user`, `service`), usuário real e efetivo, comando, programa, pasta, terminal, sessão, fonte (`auditd`, `snoopy`, `syslog`), IP do cliente e, quando se aplicam, o programa pai, o interpretador, o arquivo alterado e o grupo dele, os comandos de reconhecimento contados, as capabilities, o modo definido, a requisição de ptrace e o erro de um arquivo negado. Quando sai, o alerta também leva o contexto da sessão: se o início dela foi visto, se passou por sudo ou su, o endereço SSH dela e os **últimos 20 comandos**, para que o analista leia o que levou ao alerta sem pesquisar.

O mesmo comando pode ser visto por mais de uma fonte (auditd e snoopy): os alertas são agrupados por módulo, usuário, IP, categoria e severidade, então ainda formam um único alerta. As senhas nas linhas de comando (`mysql -p...`, `sshpass -p`, `curl -u user:pass`, `PASSWORD=...`, URLs com senha) são mascaradas antes de qualquer coisa ser armazenada, também no hexadecimal dos registros de auditoria.

<a id="privesc-doctor"></a>
## 14. Requisitos do módulo de escalonamento de privilégios: o diagnóstico

**Requisitos.** O módulo precisa de uma fonte que o usuário `localsiem` possa ler (o arquivo existe e o `localsiem` consegue abri-lo): o log do **auditd** (auditd em execução, fora de um contêiner) ou o arquivo do **syslog** com sudo, su, pkexec e doas (`/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`, ou a configuração **Arquivo do syslog**, a menos que **Ler o syslog** seja Nunca), onde o **snoopy** também grava cada programa executado, se estiver instalado. Basta qualquer uma delas. Quando uma fonte existe, mas o `localsiem` não consegue lê-la, o requisito informa isso, com o comando que dá acesso de leitura (para o log de auditoria, o comando da página Módulos, `manage.py setup-modules`; para o syslog, `setfacl -m g:localsiem:r <file>`). Sem nenhuma delas, ele diz o que instalar: o auditd (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`), um daemon de syslog (Debian: `apt-get install rsyslog`; Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) ou o snoopy. Até lá, o módulo fica desativado; **Reconfigurar** verifica novamente. Ele não instala nada por conta própria. Em uma primeira instalação, os logs costumam pertencer ao root: execute o comando que a interface web mostra e depois clique em **Reconfigurar**.

O diagnóstico funciona como o do Apache (seção 7). Ele apenas descreve o que o módulo vê com o que o servidor tem e o que não consegue ver; as correções dele são só os pacotes a instalar e o acesso de leitura do `localsiem`. Ele nunca propõe alterar as regras de auditoria, o `auditd.conf` (exceto `log_group`, abaixo), o `snoopy.ini`, os shells nem nenhuma outra configuração:

| Verificação | Correto quando | Caso contrário |
|---|---|---|
| auditd | O auditd está em execução | Aviso se não estiver instalado (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`); aviso, sem correção, se estiver instalado mas parado (se ele é executado ou não é decisão do administrador). Info dentro de um contêiner: o auditd não funciona lá. |
| Log de auditoria | O `localsiem` consegue lê-lo | Erro, com o comando da página Módulos; aviso se o auditd está em execução e o log dele não está onde o módulo o procura (configuração **Log de auditoria**) |
| Grupo do log de auditoria | O log de auditoria não pertence ao grupo `root` | Aviso se pertencer (`log_group = root` em `auditd.conf`): cada log que o auditd cria ao rotacionar tem modo 600, só pode ser lido pelo root e o localSIEM para de ler. A correção é a linha `log_group = adm` para `/etc/audit/auditd.conf` (depois reinicie o auditd): os novos logs são criados com modo 640. |
| Registros das regras de auditoria | Foram lidos programas executados (`EXECVE`) | Aviso se o auditd grava, mas nenhum dos registros dele é de um programa executado: as regras de auditoria do servidor não registram `execve`, então os comandos de scripts, web shells e exploits não são vistos por meio do auditd. Info com o que mais as regras registraram até agora (alterações de arquivos sensíveis, bits setuid, módulos do kernel, ptrace, arquivos negados) e o que ainda não |
| syslog | O arquivo do syslog é lido | Erro se não puder ser lido (`setfacl -m g:localsiem:r <file>`); aviso se não houver nem um log de auditoria utilizável nem um arquivo do syslog (Debian: `apt-get install rsyslog`; Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) |
| snoopy | Instalado, e as linhas dele são lidas | Aviso sem auditd: os comandos de scripts e de web shells não são vistos (Debian: `apt-get install snoopy`; o Alpine não tem pacote: ele é compilado a partir do código-fonte). Aviso se estiver instalado, mas o syslog não for lido. Info se as linhas dele não tiverem uid efetivo (`message_format` de `snoopy.ini`): o root herdado de um programa setuid não é visto por meio do snoopy |
| O que o módulo vê | — | Info: auditd (e o que as regras dele registram), snoopy (cada programa executado) ou, como aviso, só sudo, su, pkexec e doas (syslog sem snoopy: a maioria das regras não pode disparar); erro se não conseguir ler nada. Também lembra que os comandos internos do shell nunca são vistos |
| Arquivos da versão 1.0.0 | — | Info, sem correção, se forem encontrados os arquivos que o `--configure-privesc` deixou (seção 15) |
| Programas setuid e capabilities | — | Info: a última varredura (seção 16). Aviso, sem correção, com os programas setuid que dão um shell de root (GTFOBins) e com os programas cujas capabilities são, na prática, root |
| Arquivos sensíveis | Nenhum gravável por alguém que não seja o root | Erro, sem correção, para cada um (`/etc/passwd`, `sudoers`, cron, `/etc/profile.d`, as pastas do `PATH` do root, `docker.sock`...) |
| Grupos privilegiados | — | Aviso, sem correção, com os membros de `docker`, `lxd`, `incus-admin`, `disk` e `libvirt`: eles são, na prática, root |

<a id="privesc-legacy"></a>
## 15. Servidores atualizados a partir da versão 1.0.0 do módulo de escalonamento de privilégios

A versão 1.0.0 do módulo tinha a opção de configuração `--configure-privesc` e um hook de bash; a versão 1.1.0 removeu os dois, porque um módulo nunca instala nem altera nada fora de `/opt/localsiem`. Os servidores em que ela foi aplicada mantêm o que ela gravou, e o localSIEM não o usa nem o exclui:

- `/etc/audit/rules.d/90-localsiem-privesc.rules`: as regras de auditoria dela (chaves `lsiem_*`). Enquanto estiverem carregadas, o módulo lê os registros delas como os de qualquer outra regra do servidor.
- `/etc/localsiem-privesc/` (o hook), `/etc/profile.d/localsiem-privesc.sh` e a linha que segue «localSIEM privesc: command hook» em `/etc/bash.bashrc` (Debian) ou `/etc/bash/bashrc` (Alpine): enquanto estiverem lá, cada bash interativo continua gravando os comandos dele em `/var/log/localsiem-privesc/`, que ninguém lê.
- `/var/log/localsiem-privesc/`: os arquivos de comandos de cada usuário.
- `log_group = adm` em `/etc/audit/auditd.conf`, `/root/.ssh` (criado vazio) e o `message_format` de `/etc/snoopy.ini`: eles podem ficar (`log_group = adm` mantém legíveis os logs de auditoria rotacionados, seção 14, e o módulo lê esse formato do snoopy assim como os formatos padrão dele).

O diagnóstico lista os que consegue ver (verificação «Files of version 1.0.0 of the module»). Para removê-los, como root: exclua o arquivo de regras e carregue as regras novamente (`augenrules --load`); exclua `/etc/profile.d/localsiem-privesc.sh`, `/etc/localsiem-privesc/` e a linha do bashrc; e exclua `/var/log/localsiem-privesc/` se não quiser manter os comandos que ela contém.

<a id="privesc-health"></a>
## 16. Superfície de ataque e avisos de saúde do módulo de escalonamento de privilégios

Além das regras dele, o módulo olha o próprio servidor e envia ao SOC:

| Aviso | Severidade | Quando |
|---|---|---|
| Novo programa setuid ou setgid | alta | Uma varredura encontra um programa setuid ou setgid que a varredura anterior não tinha (a primeira varredura é só a referência). Um atacante que se tornou root costuma deixar para trás um shell setuid; uma atualização de pacote também pode adicionar um. |
| Novo programa setuid em uma pasta gravável | crítica | O mesmo, em `/tmp`, `/var/tmp`, `/dev/shm`, `/home`, `/srv` ou `/var/www` |
| Novo programa setuid do GTFOBins | crítica | O mesmo, para um programa que dá um shell de root quando é setuid (`bash`, `find`, `python`, `vim`, `less`, `cp`...) |
| Novas capabilities | alta | Um programa obteve capabilities que são, na prática, root (`cap_setuid`, `cap_dac_override`, `cap_sys_admin`...) |
| Arquivo sensível gravável por alguém que não seja o root | crítica | Verificado a cada hora: `/etc/passwd`, `/etc/shadow` (também legível por todos), `sudoers`, cron, `/etc/profile.d`, PAM, serviços, `ld.so.preload`, as pastas do `PATH` do root, `docker.sock`... Relatado uma vez por arquivo e problema. |
| auditd parado (saúde do localSIEM) | alta | O auditd estava em execução e não está mais (fora de contêineres) |

A varredura é executada em segundo plano, no máximo a cada **Horas entre varreduras de programas setuid** (a primeira cinco minutos depois que o coletor inicia), pelas **Pastas varridas**, como o usuário `localsiem` (o que ele não consegue ler é ignorado), e para depois de 3 milhões de arquivos ou 15 minutos. O resultado dela, com os GTFOBins e as capabilities encontrados, é mostrado no diagnóstico. As severidades desses avisos estão em `severity.yaml` do módulo. O que já foi relatado é lembrado entre reinicializações.

<a id="cli"></a>
## 17. Linha de comando

Como root, `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <command>`:

| Comando | Uso |
|---|---|
| `modules` | Módulos instalados: id, versão, ativado, desativado ou não carregado, e pasta, com os requisitos que faltam, se houver; e os módulos que não puderam ser carregados, com o erro |
| `doctor` | Para cada módulo ativado: cada verificação (`✓`, `!`, `✗`, `·`) com o trecho que a corrige, e as fontes encontradas; para um módulo desativado porque falta um requisito, os requisitos dele. `--json` fornece o mesmo em JSON. |
| `read-paths` | Pastas que os módulos leem, às quais o localSIEM dá acesso de leitura como root |
| `setup-modules [--no-restart]` | Como root: o comando que a interface web mostra; acesso de leitura às pastas dos módulos (`read_paths`) e uma reinicialização do localSIEM (`--no-restart`: sem ela). Os módulos não têm opções de configuração |

Execute o diagnóstico como o usuário `localsiem` para ver as permissões reais dele:

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
