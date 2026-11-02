# Manual de utilização do localSIEM-modules

Este MANUAL também está disponível em:\
[de-DE](MANUAL.de-DE.md), [en-GB](MANUAL.en-GB.md), [en-US](MANUAL.md), [es-AR](MANUAL.es-AR.md), [es-ES](MANUAL.es-ES.md), [fr-FR](MANUAL.fr-FR.md), [he-IL](MANUAL.he-IL.md), [hi-IN](MANUAL.hi-IN.md), [it-IT](MANUAL.it-IT.md), [ja-JP](MANUAL.ja-JP.md), [ko-KR](MANUAL.ko-KR.md), [pt-BR](MANUAL.pt-BR.md), pt-PT, [ru-RU](MANUAL.ru-RU.md), [zh-CN](MANUAL.zh-CN.md)

[Instalação](README.pt-PT.md) · [Referência técnica](CODE.pt-PT.md) · [Manual do localSIEM](../../localSIEM/doc/MANUAL.pt-PT.md)

## Índice

1. [O que são os módulos](#what)
2. [Instalar e atualizar os módulos](#installation)
3. [A página Módulos](#modules-page)
4. [A página do módulo do Apache](#apache-page)
5. [Definições do módulo do Apache](#settings)
6. [O que o módulo do Apache envia para o SOC](#soc)
7. [Requisitos do Apache e do ModSecurity: o diagnóstico](#doctor)
8. [Os registos do cliente nunca são alterados](#client-logs)
9. [Regras do módulo do Apache](#rules)
10. [Avisos de saúde do módulo do Apache](#health)
11. [O módulo de escalada de privilégios](#privesc)
12. [Definições do módulo de escalada de privilégios](#privesc-settings)
13. [O que o módulo de escalada de privilégios envia para o SOC: as regras](#privesc-rules)
14. [Requisitos do módulo de escalada de privilégios: o diagnóstico](#privesc-doctor)
15. [Servidores atualizados a partir da versão 1.0.0 do módulo de escalada de privilégios](#privesc-legacy)
16. [Superfície de ataque e avisos de saúde do módulo de escalada de privilégios](#privesc-health)
17. [Linha de comandos](#cli)

<a id="what"></a>
## 1. O que são os módulos

O localSIEM é composto por um **núcleo** e por **módulos**. O núcleo guarda os eventos, pesquisa-os, executa as regras, agrupa os alertas, envia-os para o SOC e vigia a sua própria saúde. Cada módulo acrescenta um serviço do servidor: encontra os respetivos registos, lê-os, transforma-os em eventos, decide o que já está resolvido, traz as suas próprias regras e verifica os requisitos desse serviço.

Os módulos deste projeto são instalados em `/opt/localsiem/modules/<nome>/`. Atualmente há dois: **apache2** («Apache + ModSecurity», secções 4 a 10) e **privesc** («Escalada de privilégios», secções 11 a 16). O localSIEM não tem módulos próprios: a página Módulos só lista os módulos instalados a partir deste repositório.

<a id="installation"></a>
## 2. Instalar e atualizar os módulos

O localSIEM tem de ser instalado primeiro; o respetivo instalador instala apenas o núcleo, nunca um módulo. Os módulos deste projeto são instalados **apenas a partir da interface web do localSIEM**: este projeto não tem instalador próprio. A interface web transfere-os do repositório `https://github.com/PYMEHackers/localSIEM-modules` (ramo `main`). Os módulos precisam do localSIEM 2.2.0 ou mais recente.

**Instalação.** Como administrador, abra Módulos › **Instaláveis** (secção 3), prima **Consultar o repositório**, consulte **Requisitos** (o que o módulo precisa no servidor e os comandos que o instalam, a executar antes de o instalar) e prima depois **Instalar** no módulo. O localSIEM então:

1. transfere o repositório e descompacta-o de forma segura (nada fora da respetiva pasta, limites de tamanho);
2. copia a pasta do módulo (`mod-<nome>/` no repositório) para `/opt/localsiem/modules/<nome>/`, sem `tests/` (e sem caches de Python); um módulo instalado novamente recupera as definições que tinha;
3. reinicia o coletor, que carrega o módulo dentro de alguns segundos;
4. retira o módulo da lista e abre a caixa de diálogo «<módulo> instalado» com o comando a executar como root no servidor (`manage.py setup-modules`) e um botão **Copiar**: esse comando dá ao utilizador `localsiem` acesso de leitura às pastas indicadas em `read_paths` do respetivo `module.json` (`/var/log/apache2` para o módulo apache2, `/var/log/audit` para o módulo privesc), também aos ficheiros das próximas rotações, e reinicia o localSIEM. Esse acesso de leitura é tudo o que um módulo precisa: os módulos não têm opções de configuração e nunca alteram o servidor (secções 8 e 11). Até o comando ser executado, o módulo pode mostrar «Erro»: os respetivos registos ainda não podem ser lidos. A caixa de diálogo fecha-se com «Fechar» ou com «Ver os módulos instalados», que abre Instalados.

**Atualização.** Quando Módulos › **Instalados** abre, a interface web consulta o repositório, e um módulo que tenha lá uma versão mais recente mostra um aviso com **Atualizar** (secção 3). Depois de confirmar, o localSIEM transfere a nova versão e coloca-a no lugar da instalada (passos 1 a 3), mantém as respetivas definições e deixa o módulo ativado ou desativado tal como estava. O comando para o root só volta a ser mostrado se a nova versão ler outros registos (`read_paths`); caso contrário, não há nada a executar. Uma atualização do localSIEM mantém os módulos instalados e o respetivo acesso de leitura.

**Reinstalação.** A interface web não reinstala um módulo nem instala uma versão mais antiga dele: para reinstalar um módulo, prima **Desinstalar** (secção 3) e volte a instalá-lo a partir de **Instaláveis**; as definições mantêm-se.

**Instalar um módulo nunca instala o software que este vigia.** O módulo apache2 não instala o Apache nem o ModSecurity, e o módulo privesc não instala o auditd, um daemon de syslog nem o snoopy. Se, na primeira instalação, faltar ao servidor o que o módulo precisa (o Apache e o ModSecurity para o apache2; para o privesc, uma fonte que o `localsiem` consiga ler, secção 14), o módulo é instalado **desativado**: a caixa de diálogo indica o que falta em vez do comando, e o módulo não pode ser ativado enquanto **Reconfigurar** não os encontrar (secção 4). Uma atualização deixa o módulo ativado ou desativado tal como estava.

<a id="modules-page"></a>
## 3. A página Módulos

Os administradores abrem **Administração › Módulos**, que tem duas secções, cada uma no seu próprio endereço: **Instalados** (`/admin/dashboard/modules/installed/`), que abre por predefinição (`/admin/dashboard/modules/` leva até lá), e **Instaláveis** (`/admin/dashboard/modules/installable/`). Os analistas veem **Módulos** no respetivo painel (`/user/dashboard/modules/`): apenas a lista dos módulos instalados, só de leitura, sem secções.

**Instalados** mostra uma linha por módulo instalado, em toda a largura: o nome, o id, a versão, um indicador de estado, o resumo e, por baixo, os motivos desse estado. A lista atualiza-se sozinha a cada 10 segundos. Sem nenhum módulo instalado, indica «Instale módulos a partir do separador Instaláveis.» (aos analistas: «Não há módulos instalados. São instalados por um administrador em Módulos › Instaláveis.»).

| Estado | Significado |
|---|---|
| **Ativado e a funcionar** | Ativado, carregado pelo coletor e a ler as respetivas fontes. Os avisos do diagnóstico aparecem como notas, mas não alteram o estado. |
| **Ativado, com avisos** | Ativado, mas não foram encontrados registos para ler, uma fonte ainda não existe ou o módulo foi instalado depois de o coletor arrancar (reinicie o serviço `localsiem`). |
| **Erro** | O módulo não é carregado (o erro é mostrado), o respetivo diagnóstico indica um erro ou não é possível ler uma fonte (permissões do utilizador `localsiem`). |
| **Desativado** | Desativado, ou instalado sem os respetivos requisitos (para o apache2: falta o Apache ou o ModSecurity; para o privesc: o `localsiem` não consegue ler nem o registo do auditd nem o syslog), tal como indica o motivo. |
| **A aplicar a alteração…** | Acabou de ser ativado ou desativado: o coletor está a aplicar a alteração. |
| **Desconhecido** | O coletor (serviço `localsiem`) não está em execução, por isso nada está a ser lido. |

Quando o módulo não está desativado, a linha mostra também: **Fontes em leitura** (lidas / encontradas), **Linhas (1 h)**, **Últimos dados**, **Eventos (24 h)**, **Bloqueados (24 h)** e as contagens do **Diagnóstico** («n OK · n avisos · n erros»).

Os administradores têm também, em cada linha:

- **O interruptor** de cada módulo. Desativar um módulo pede confirmação: o localSIEM deixa de ler os respetivos registos e de enviar os respetivos alertas até ser novamente ativado; o que já está guardado mantém-se. Ativá-lo começa a leitura imediatamente. Enquanto faltar um requisito do módulo, o interruptor está bloqueado («Desativado: faltam requisitos»): **Reconfigurar** (secção 4) desbloqueia-o assim que os encontrar.
- **Configurar**, que abre a página do módulo, `/admin/dashboard/modules/installed/<nome>/` (secção 4); o endereço antigo `/admin/dashboard/modules/<nome>/` leva até lá.
- **Desinstalar**, também num módulo que não é carregado (e na página do módulo). Depois de confirmar, o localSIEM elimina `/opt/localsiem/modules/<nome>/` e reinicia o coletor sem ele: deixa de ler os respetivos registos e de enviar os respetivos alertas. Os eventos já guardados continuam a poder ser pesquisados, e as definições mantêm-se, caso o volte a instalar. O acesso de leitura aos respetivos registos que o root deu ao `localsiem` não é retirado.
- **Atualizar**, quando o repositório tem uma versão mais recente do módulo. Sempre que Instalados abre, a interface web consulta o repositório («A consultar o repositório à procura de versões mais recentes…»; o browser reutiliza a resposta durante 10 minutos), e uma linha cujo módulo tenha uma versão mais recente mostra «O repositório tem a versão X (a instalada é a Y).» com o botão **Atualizar**. Depois de confirmar, o localSIEM instala a nova versão (secção 2), mantém as respetivas definições, deixa o módulo ativado ou desativado tal como estava e reinicia o coletor; uma caixa de diálogo mostra o comando para o root apenas se a nova versão ler outros registos. Se a nova versão precisar de um localSIEM mais recente, o aviso indica «O repositório tem a versão X, mas esta precisa do localSIEM Z ou mais recente: atualize o localSIEM para a instalar.» e não tem botão.

**Instaláveis** (só para administradores) tem o cartão «Módulos instaláveis». **Consultar o repositório** transfere o repositório e lista os módulos que ainda não estão instalados neste servidor, cada um com o nome, o id, a versão e o resumo, e um botão ou uma nota:

| Botão ou nota | Significado |
|---|---|
| **Requisitos** | Mostra o que o módulo precisa no servidor e os comandos que o instalam, como root e com sudo (abaixo) |
| **Instalar** | Instala o módulo (secção 2) |
| «Precisa do localSIEM X ou mais recente» | Não pode ser instalado: atualize primeiro o localSIEM |
| «O módulo do repositório não é válido» | Não pode ser instalado |

Os módulos já instalados nunca aparecem aqui: são atualizados a partir de Instalados. Se todos os módulos do repositório estiverem instalados, o cartão indica «Todos os módulos do repositório já estão instalados.». Depois de instalar, a caixa de diálogo «<módulo> instalado» mostra o comando a executar como root para que o `localsiem` possa ler os registos do módulo (secção 2), com um botão **Copiar**; até ser executado, o módulo pode mostrar «Erro»: os respetivos registos ainda não podem ser lidos. Se faltar ao servidor o que o módulo precisa, a caixa de diálogo indica, em vez disso, o que falta, com a sugestão de abrir o módulo em Instalados (**Configurar**) e premir **Reconfigurar** assim que estiver presente.

**Requisitos** abre «<módulo>: requisitos»: o que o módulo precisa no servidor e os comandos que o instalam no sistema deste servidor («Este servidor: …»), declarados pelo módulo (`install_requirements` do respetivo `module.json`), duas vezes, cada uma com **Copiar**: **Como root** e **Com sudo** (os mesmos comandos com `sudo` à frente). Execute-os no servidor antes de instalar o módulo: instalá-lo nunca instala esse software, e o localSIEM nunca os executa. Para o módulo apache2, no Debian: `apt-get -y update`, `apt-get -y install apache2 libapache2-mod-security2 modsecurity-crs`, `a2enmod security2 unique_id`, `cp --update=none /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf` (só cria a configuração do ModSecurity, DetectionOnly, quando não existe nenhuma) e `systemctl restart apache2`; no Alpine, só o Apache (`apk add apache2`, depois `rc-update` e `rc-service` para o iniciar), porque o Alpine não tem pacote do ModSecurity 2: enquanto o ModSecurity não for compilado a partir do código-fonte e carregado, o módulo fica desativado. Para o módulo privesc: `apt-get -y install auditd rsyslog` no Debian, e `apk add audit` com o auditd iniciado no arranque no Alpine; basta uma fonte legível, e num contentor o auditd não pode ser executado.

<a id="apache-page"></a>
## 4. A página do módulo do Apache

`/admin/dashboard/modules/installed/apache2/` (só para administradores; o endereço antigo `/admin/dashboard/modules/apache2/` leva até lá) tem cinco partes:

1. **Cabeçalho**: nome, id, versão, o caminho de instalação (`/opt/localsiem/modules/apache2`), o interruptor, o estado com os respetivos motivos e os números da secção 3. **Voltar aos módulos instalados** regressa a Instalados; **Descobrir novamente e executar o diagnóstico** volta a ler imediatamente a configuração do Apache e atualiza o diagnóstico; **Reconfigurar** volta a procurar o Apache e o ModSecurity (abaixo); **Desinstalar** desinstala o módulo (secção 3) e regressa a Instalados.
2. **Definições**: o formulário da secção 5. **Guardar as definições** verifica cada valor e, se algum estiver errado, indica qual («Valor inválido: …»).
3. **Fontes**: cada registo em leitura, com **Tipo** (`access`, `error`, `audit`), **Caminho**, **Vhost**, **Linhas (1 h)**, **Não analisadas (1 h)**, **Últimos dados** (por exemplo `2026/10/29@13:59:59.723`) e **Estado** (erro se não puder ser lido, aviso se ainda não existir). Por baixo, os registos encontrados mas não lidos, com o motivo: «registo encaminhado por pipe, não suportado», «abrangido por um GlobalLog que escreve todos os vhosts» ou «o formato não tem dados: todas as linhas são o mesmo texto (um nome de LogFormat que não está definido)».
4. **Diagnóstico**: as verificações da secção 7, com a hora em que foram executadas. Cada requisito em falta (ModSecurity, o CRS, `SecRuleEngine`, `mod_unique_id`, o acesso de leitura do `localsiem`) vem acompanhado do excerto ou do comando que o resolve e de um botão **Copiar**. As verificações sobre os registos só os descrevem, e o que o localSIEM consegue ler deles, sem correção: os registos do cliente nunca são alterados (secção 8).
5. **Regras**: as regras da secção 9, cada uma com **Ativa**, **Regra** (nome, id e categoria), **Gravidade**, **Limiar** e **Janela (s)**, e **Guardar as regras**.

**Requisitos e Reconfigurar.** Enquanto faltar o Apache ou o ModSecurity, o módulo está desativado e o cabeçalho indica o que falta, com o comando que o instala. **Reconfigurar** (também quando o módulo está desativado) volta a procurá-los com as definições guardadas; se o Apache estiver num local fora do habitual, defina primeiro **Ficheiro de configuração do Apache** (secção 5). Quando ambos são encontrados, desbloqueia o interruptor —ativar o módulo é decisão sua— e mostra o comando a executar como root para que o `localsiem` possa ler os registos do Apache criados depois de o módulo ter sido instalado. Um módulo ativado que perca o Apache ou o ModSecurity continua ativado: o diagnóstico e os avisos de saúde (secção 10) comunicam-no.

**Cada alteração aplica-se imediatamente, sem reiniciar nada**: a interface web guarda-a e avisa o coletor, que recarrega as respetivas definições, volta a descobrir as fontes e executa o diagnóstico. Se o coletor não responder, a interface web indica-o e a alteração é aplicada quando o coletor arrancar.

<a id="settings"></a>
## 5. Definições do módulo do Apache

| Definição | Predefinição | O que faz |
|---|---|---|
| **Só as fontes abaixo** | desativada | Não descobrir os registos a partir da configuração do Apache: ler apenas as fontes adicionadas manualmente. |
| **Fontes adicionadas manualmente** | nenhuma | Registos a ler além dos descobertos (ou em vez deles, com a opção acima). Até 50. |
| **Ficheiro de configuração do Apache** | vazio | Vazio: encontrado automaticamente (`/etc/apache2/apache2.conf` no Debian, `/etc/apache2/httpd.conf` no Alpine; `/etc/httpd/conf/httpd.conf` também é reconhecido). Um caminho absoluto faz com que seja usado esse ficheiro, se existir. |
| **Intervalo de descoberta (segundos)** | 3600 | Com que frequência a configuração do Apache é lida novamente para encontrar novos vhosts e registos (60 a 86400). |
| **Limiar de bloqueio do ModSecurity** | 0 | 0: lido a partir da configuração do CRS (`tx.inbound_anomaly_score_threshold` em `crs-setup.conf`), 5 se não estiver lá. Serve para distinguir uma correspondência acima do limiar de bloqueio de uma abaixo dele quando as próprias mensagens do ModSecurity não indicam o limiar (0 a 1000). |
| **Dias de aprendizagem para novos ficheiros PHP** | 3 | Durante os primeiros dias após o primeiro arranque do módulo, um ficheiro PHP nunca visto antes não é comunicado como novo pela regra `apache-webshell` (0 a 365). Um ficheiro criado ou modificado no respetivo DocumentRoot no último dia conta sempre como novo. |

Cada **fonte adicionada manualmente** tem estes campos (* obrigatório):

| Campo | Utilização |
|---|---|
| **Tipo** * | `access.log`, `error.log` ou `Registo de auditoria do ModSecurity` |
| **Caminho** * | Caminho absoluto do ficheiro |
| **Vhost** | Vhost das linhas, para registos cujas linhas não o indicam |
| **LogFormat** | Para registos de acesso: um nome (`localsiem_combined`, `combined`, `vhost_combined`, `common`, `combinedio`, ou um definido na configuração do Apache) ou o próprio formato. Vazio: são experimentados os formatos habituais. |
| **Tipo de registo de auditoria** | `Serial (um único ficheiro)` ou `Concorrente (um ficheiro por pedido)` |
| **Pasta de armazenamento da auditoria** | Para o tipo concorrente: a pasta de `SecAuditLogStorageDir` |

Um ficheiro só é lido uma vez, mesmo que seja descoberto e também adicionado manualmente. Uma fonte que apareça enquanto o localSIEM está em execução é lida desde o início se tiver 5 MB ou menos, e a partir do fim caso contrário.

Duas definições de **Administração › Definições** do localSIEM também atuam sobre este módulo: a **janela de correlação** (5 segundos: quanto tempo se esperam os três registos de um pedido) e a **gravidade abaixo do limiar** (`low`). Um pedido que o ModSecurity assinalou também espera pelo respetivo registo de auditoria, que o ModSecurity escreve quando o pedido termina, até 2 minutos: assim, um pedido lento não é dividido em dois eventos.

<a id="soc"></a>
## 6. O que o módulo do Apache envia para o SOC

Para cada pedido, o módulo junta a linha de acesso, as linhas de erro e o registo de auditoria com o mesmo `UNIQUE_ID`. Os registos de acesso que o Apache escreve por predefinição (`combined`, `vhost_combined`, `common`) não têm `UNIQUE_ID`: nesse caso, cada linha de acesso é juntada ao registo de auditoria e às linhas de erro do seu próprio pedido por IP do cliente, método, URI, estado e hora (±2 segundos), mesmo quando o mesmo pedido se repete no mesmo segundo, e o evento é marcado como «correlação fraca». O vhost vem de `%v` ou, se o formato não o tiver, do cabeçalho Host e da porta do registo de auditoria, escolhido da mesma forma que o Apache o escolhe; a hora usa os microssegundos do registo de auditoria. Depois, decide se já foi feito algo a esse respeito («ação tomada»), lendo primeiro o registo de auditoria (`Action: Intercepted (phase N)`) e depois o error.log (`Access denied with code NNN (phase N)`). Um 403 sem qualquer vestígio do ModSecurity não é considerado um bloqueio: é marcado como duvidoso.

| Situação | Vai para o SOC? |
|---|---|
| Bloqueado pelo ModSecurity nas fases 1-2 (a aplicação nunca o recebeu) | **Não.** Fica no localSIEM, disponível para pesquisa (`action:blocked`), e é contado no contexto do próximo alerta desse IP. |
| Bloqueado nas fases 3-4 (a aplicação já o tinha executado) | Sim |
| Correspondências de regras com o motor em `DetectionOnly` | Sim |
| Correspondências de regras abaixo do limiar de bloqueio | Sim |
| Sinais das regras da secção 9 | Sim |

Gravidade dos alertas gerados pelas correspondências do ModSecurity (ficheiro `severity.yaml` do módulo):

| Situação | Gravidade |
|---|---|
| Correspondências não bloqueadas, resposta 3xx, 4xx ou 5xx | média |
| Correspondências não bloqueadas, resposta 2xx | alta |
| Bloqueado nas fases 3-4 | alta |
| Sinais de sucesso: uma regra de saída (950-955) correspondeu e nada foi bloqueado, ou um erro de base de dados seguiu-se ao pedido | crítica |
| Abaixo do limiar de bloqueio (muitas vezes um falso positivo da própria aplicação) | baixa (a gravidade abaixo do limiar de Administração › Definições) |

Cada alerta tem um nome estável (por exemplo «Apache/ModSecurity: SQL injection not blocked (CRS 942)»), uma descrição que termina com a consulta a colar na pesquisa do localSIEM (por exemplo `ip:203.0.113.7 category:sqli`) e detalhes: vhost, IP do cliente, método, URI (mascarado), resposta, user agent e os dados do ModSecurity (motor, ação, fase, pontuação de anomalia, limiar, regras e dados correspondidos). Quando sai, o alerta leva também o contexto do IP: pedidos e pedidos bloqueados da última hora, as regras que o bloquearam e a primeira vez em que foi visto.

As palavras-passe, os cookies, os cabeçalhos `Authorization` e os tokens são mascarados antes de qualquer coisa ser guardada, também dentro dos corpos dos pedidos, e os corpos dos pedidos nunca seguem para o SOC. O corpo da resposta (parte E) e o texto completo das regras executadas (parte K) do registo de auditoria nunca são guardados.

<a id="doctor"></a>
## 7. Requisitos do Apache e do ModSecurity: o diagnóstico

O diagnóstico do módulo apache2 lê a configuração do Apache (sem a alterar) e verifica cada requisito. É executado quando o coletor arranca, após cada alteração das definições, em cada descoberta, com **Descobrir novamente e executar o diagnóstico** e com `manage.py doctor` (secção 17), apenas enquanto o módulo está ativado: enquanto estiver desativado por faltar o Apache ou o ModSecurity, a página do módulo mostra esses requisitos em vez disso (secção 4). Estados: OK, aviso (funciona com limitações), erro (tem de ser corrigido) e informação (só importa em algumas situações).

| Verificação | Correto quando | Caso contrário |
|---|---|---|
| Configuração do Apache | `apache2.conf` ou `httpd.conf` (ou o ficheiro configurado) é encontrado e lido | Erro: adicione as fontes manualmente (secção 5). As partes que não podem ser lidas são indicadas como avisos. |
| ModSecurity | O `mod_security2` (ModSecurity 2) está carregado | Erro. Debian: `apt-get install libapache2-mod-security2 modsecurity-crs && a2enmod security2`. O Alpine não tem pacote: compile o mod_security2 2.9 a partir do código-fonte. O ModSecurity 3 (libmodsecurity) não é suportado. |
| OWASP CRS | Os ficheiros do CRS estão incluídos (o diagnóstico mostra quantos e o limiar de anomalia) | Erro: `apt-get install modsecurity-crs`, ou inclua `crs-setup.conf` e `rules/*.conf` depois do ModSecurity |
| SecRuleEngine | `On` (os pedidos acima do limiar são bloqueados na fase 2 e ficam no localSIEM) ou `DetectionOnly` (nada é bloqueado: cada correspondência vai para o SOC) | Erro se `Off`; aviso se estiver `Off` exceto em alguns vhosts, se faltar (o ModSecurity assume então `Off` por predefinição) ou se alguns vhosts o definirem como `Off` |
| mod_unique_id | Carregado: o ModSecurity funciona e as três fontes de um pedido são juntadas por `UNIQUE_ID` | Erro se o ModSecurity estiver carregado: o ModSecurity 2 não inspeciona nada sem ele (o Alpine não o carrega); caso contrário, aviso (correlação fraca). Debian: `a2enmod unique_id`; Alpine: `LoadModule unique_id_module modules/mod_unique_id.so` |
| Formato do registo de acesso | Os registos de acesso têm IP do cliente, hora, linha do pedido e estado, como os formatos que o Apache escreve por predefinição (OK, «Access logs in the format Apache writes»): cada linha é juntada aos registos do ModSecurity do respetivo pedido por IP do cliente, método, URI, estado e hora. Com milissegundos, vhost e `UNIQUE_ID` no formato (por exemplo `localsiem_combined`, nos servidores que já o escrevem), são juntados por `UNIQUE_ID` (OK, «Access log with milliseconds, vhost, duration and UNIQUE_ID») | Informação, sem correção, se a um registo de acesso faltar algum dos quatro: o localSIEM lê-o tal como está, mas não consegue juntar as respetivas linhas aos registos do ModSecurity (esses pedidos são vistos no registo de auditoria); informação se nenhum registo de acesso for lido (os pedidos são vistos no registo de erros e no registo de auditoria). O formato dos registos é o do cliente (secção 8) |
| mod_remoteip | Carregado com `RemoteIPHeader` | Informação, sem correção: se o site estiver atrás de um proxy ou de um balanceador de carga, os registos contêm o IP do proxy, tal como os alertas e as regras por IP |
| Registo de auditoria | `SecAuditEngine RelevantOnly` (ou `On`) com um `SecAuditLog` | Aviso se estiver desativado: o localSIEM decide apenas a partir do error.log, e a ficha do pedido não tem cabeçalhos nem lista de regras. Quando está ativado, as respetivas notas apenas o descrevem: tipo concorrente (um ficheiro por transação; o ModSecurity costuma criá-los com o modo 600, e o localSIEM lê-os se o `localsiem` conseguir), formato nativo (lido tal como está), parte E registada (nunca vai para o SOC), parte H em falta (a ação tomada não pode ser lida a partir do registo de auditoria; a única nota que torna a verificação um aviso). Sem correção: o registo de auditoria é configurado pelo cliente (secção 8) |
| Mascaramento na origem | Existe uma ação `sanitise` | Informação, sem correção («The audit log on disk is not masked»): o ficheiro escrito pelo ModSecurity pode conter palavras-passe e cookies; o localSIEM mascara-os antes de os guardar, e nunca vão para o SOC |
| Permissões | O `localsiem` consegue ler todas as fontes | Erro. Debian: `usermod -aG adm localsiem`; Alpine: os comandos `setfacl` mostrados. Uma fonte que ainda não existe é apenas informação. |
| Registos por pipe | — | Aviso: `\|/usr/bin/rotatelogs ...` e o syslog não podem ser lidos; escreva também o registo num ficheiro, ou adicione a fonte manualmente |
| Registo de acesso sem dados | — | Aviso: um `CustomLog` utiliza um formato que nenhum `LogFormat` define (ou um `LogFormat` sem nenhuma diretiva `%`), por isso o Apache escreve esse mesmo texto em todas as linhas, sem o IP do cliente, a hora nem o pedido. O localSIEM não lê esse registo e vê os pedidos do respetivo vhost no registo de erros e no registo de auditoria do ModSecurity. O formato dos registos do servidor nunca é alterado. |
| Motor visto como Off | — | Erro: os registos de auditoria indicam o motor como desativado |
| Versão do ModSecurity | — | Informação: a versão lida a partir do registo de auditoria |

Quando a configuração tem um `GlobalLog` cujo formato tem `%v` (escreve todos os vhosts), os outros registos de acesso não são lidos: apenas repetiriam as linhas dele. O diagnóstico nunca propõe alterar o formato dos registos nem as definições do registo de auditoria (secção 8).

<a id="client-logs"></a>
## 8. Os registos do cliente nunca são alterados

O módulo apache2 apenas **lê** os registos do Apache e do ModSecurity: nunca escreve neles, nem os roda, trunca, move ou elimina, e nunca altera o respetivo formato nem a configuração do Apache ou do ModSecurity que os escreve. Se um servidor escrever os registos num formato próprio (por exemplo, um `LogFormat` próprio, ou o IP do cliente que o `mod_remoteip` fornece), o módulo adapta-se a ele: lê cada registo de acesso com o formato que o respetivo `CustomLog` utiliza. O diagnóstico (secção 7) apenas descreve os registos e o que o localSIEM consegue ou não ler deles, sem propor alterá-los; só indica uma correção para o que não é um registo: o ModSecurity, o CRS, `SecRuleEngine`, `mod_unique_id` e o acesso de leitura do utilizador `localsiem`. A única coisa feita como root para este módulo é esse acesso de leitura (`manage.py setup-modules`, secção 2).

As versões 1.2.0 e anteriores do módulo tinham a opção de configuração `--configure-apache`, removida na versão 1.3.0. Os servidores em que foi aplicada mantêm o ficheiro que escreveu, `/etc/apache2/conf-available/localsiem.conf` (Debian) ou `/etc/apache2/conf.d/localsiem.conf` (Alpine), com o formato `localsiem_combined` e o respetivo `GlobalLog` (`localsiem_access.log`), as definições do registo de auditoria e uma `SecAction` que mascara valores sensíveis. Enquanto esse ficheiro existir, o módulo lê esses registos como quaisquer outros. Para o anular, elimine esse ficheiro (Debian: `a2disconf localsiem`) e recarregue o Apache. No Alpine, esse ficheiro também carregava o `mod_unique_id` e o `mod_logio`: carregue o `mod_unique_id` noutro ponto da configuração do Apache antes de o eliminar, porque o ModSecurity 2 não inspeciona nada sem ele (secção 7). O instalador do localSIEM elimina esse ficheiro com `--uninstall` ou `--reinstall` (no Alpine, carregue primeiro o `mod_unique_id` noutro ponto) e deixa os registos (`localsiem_access.log`, `modsec_audit.log`) onde estão.

<a id="rules"></a>
## 9. Regras do módulo do Apache

As regras são avaliadas em cada evento. Um sinal de uma regra vai sempre para o SOC. Na página do módulo, cada regra pode ser desativada, e a respetiva gravidade, limiar (1 a 100000) e janela (1 a 86400 segundos) podem ser alterados; o limiar e a janela só se aplicam às regras de limiar e de sequência. Os respetivos eventos podem ser encontrados com `rule:localsiem:<id>`.

| Regra | Tipo | Gravidade | Quando | Limiar / janela |
|---|---|---|---|---|
| `apache-bruteforce` «força bruta contra uma página de início de sessão» | limiar | média | Pedidos POST não bloqueados de um IP para uma página de início de sessão de um vhost (`/wp-login.php`, `/xmlrpc.php`, `/administrator/index.php`, `/user/login`, `/login`, `/admin/login`, `/login.php`, `/admin.php`, `/signin`, `/auth/login`, `/phpmyadmin/index.php`) | 20 em 300 s |
| `apache-login-after-bruteforce` «início de sessão bem-sucedido após uma força bruta» | sequência | alta | Pelo menos 10 inícios de sessão falhados (POST com resposta 200, 401 ou 403) numa página de início de sessão, seguidos de um com resposta 302 ou 303 (o WordPress responde 200 a um início de sessão falhado e 302 a um bem-sucedido) | 10, em 1800 s |
| `apache-enumeration` «enumeração (rajada de respostas 404)» | limiar | média | Respostas 404 não bloqueadas para um IP a partir de um vhost | 30 em 60 s |
| `apache-sensitive-file` «ficheiro sensível servido» | correspondência | alta | Uma resposta 2xx para um ficheiro que não devia ser público: `.env`, `.git/`, `.svn/`, `.hg/`, `.htaccess`, `.htpasswd`, dumps e cópias de segurança (`.sql`, `.sql.gz`, `.bak`, `.old`, `.orig`, `.swp`, `.save`, `.backup`, `.dump`, nomes terminados em `~`), `phpinfo`, `info.php`, `server-status`, `server-info`, cópias de `wp-config.php` e `config.php`/`config.inc`, `.DS_Store`, chaves SSH privadas, `composer.json`/`composer.lock`, `.aws/`, `backup.zip`/`.tar`/`.tar.gz`/`.tgz`/`.rar` | — |
| `apache-webshell` «possível web shell (POST para um novo ficheiro PHP)» | correspondência | crítica | Um POST com resposta 2xx para um ficheiro PHP criado ou modificado no respetivo DocumentRoot no último dia, ou visto pela primeira vez na última hora (após os dias de aprendizagem) | — |
| `apache-db-error-after-attack` «erro de base de dados após um pedido suspeito» | sequência | crítica | Um pedido que correspondeu a regras do CRS e, a partir do mesmo IP, um erro de base de dados (SQL ou PDO) no error.log | 1, em 30 s |

<a id="health"></a>
## 10. Avisos de saúde do módulo do Apache

Além dos avisos de saúde do próprio localSIEM, o módulo verifica a cada 5 minutos, no máximo, e envia para o SOC:

| Aviso | Gravidade | O que fazer |
|---|---|---|
| O ModSecurity já não está carregado | alta | Estava carregado e já não está: os pedidos não são inspecionados. Se ninguém o fez de propósito, alguém pode ter desativado a proteção. |
| Motor do ModSecurity definido como Off | alta | `SecRuleEngine` passou para `Off`, ou o registo de auditoria indica o motor como desativado. Verifique a configuração do Apache e as respetivas alterações recentes. |
| IP real do cliente em falta (mod_remoteip) | média | Na última hora, pelo menos 90 % de pelo menos 100 pedidos vieram de um único endereço privado ou local: o site está provavelmente atrás de um proxy e o Apache regista o IP do proxy, por isso as regras por IP não funcionam para estes pedidos. Enviado no máximo uma vez por dia. |

O que já foi comunicado é recordado entre reinícios, por isso uma atualização não o volta a enviar. Por causa destes avisos, um módulo ativado nunca é desativado por si só quando o Apache ou o ModSecurity desaparecem.

<a id="privesc"></a>
## 11. O módulo de escalada de privilégios

O módulo **privesc** («Escalada de privilégios») vigia o que as pessoas e os serviços executam no servidor e comunica os passos de uma escalada até root: o reconhecimento, a procura de programas setuid, ferramentas de enumeração como o linpeas, exploits conhecidos, reverse shells, root obtido sem sudo nem su, as backdoors deixadas para trás e as tentativas de cegar a monitorização. Também revê a superfície de ataque do servidor: programas setuid, capacidades e ficheiros sensíveis com permissão de escrita para outros (secção 16).

Só lê o que o servidor já tem: nunca instala nada, nunca carrega regras de auditoria e nunca altera a configuração do auditd, do snoopy nem das shells. Lê até duas fontes:

| Fonte | O que vê | Onde funciona |
|---|---|---|
| **auditd** (`/var/log/audit/audit.log`) | sudo, su, pkexec e inícios de sessão SSH (PAM) e tudo o que as regras de auditoria do servidor registam (abaixo) | Servidores físicos e máquinas virtuais, enquanto o auditd estiver em execução. **Não dentro de um contentor** (LXC, podman, systemd-nspawn, Docker): a auditoria do kernel não tem namespaces, por isso o auditd só funciona no anfitrião. |
| **syslog** (`/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`) | sudo, su, pkexec, doas, inícios de sessão SSH e, se o **snoopy** estiver instalado, cada programa executado | Em todo o lado, incluindo contentores. Lido quando o auditd não está em execução, o respetivo registo não pode ser lido ou o snoopy está instalado (definição **Ler o syslog**). Precisa de um daemon de syslog que escreva um ficheiro: o journal do systemd por si só não é lido. |

O que o auditd mostra depende das regras de auditoria que o servidor carrega, que são uma decisão do respetivo administrador; o módulo usa-as tal como estão, sejam quais forem as respetivas chaves, e classifica cada registo pelo tipo, pela chamada de sistema e pelos ficheiros:

| O módulo vê | Quando as regras de auditoria do servidor registam |
|---|---|
| Cada programa executado (também a partir de scripts, web shells e exploits), programas setuid, root herdado deles, capacidades obtidas | `execve` |
| Alterações de contas, sudoers, PAM, preload, SSH, cron, serviços e `/etc/audit` | Vigilâncias (`-w ... -p wa`) sobre esses ficheiros ou as chamadas de sistema que os alteram |
| Bits setuid ou setgid definidos | `chmod`, `fchmod`, `fchmodat` |
| Módulos do kernel carregados ou removidos | `init_module`, `finit_module`, `delete_module` |
| Processos anexados com ptrace | `ptrace` |
| Ficheiros recusados a uma pessoa | `open`, `openat`, `execve`... que falham com `EACCES` ou `EPERM` |
| Regras de auditoria removidas, auditoria desativada, auditd parado, programas que terminam abruptamente | Sempre (o kernel e o auditd comunicam-nos) |

Num servidor físico ou numa máquina virtual, o auditd é a fonte que um utilizador não consegue evitar; o diagnóstico indica o que as regras de auditoria do servidor registaram até agora (secção 14). Num contentor, o snoopy é a única forma de ver cada programa executado.

Os comandos internos da shell (`pwd`, `cd`, `unset HISTFILE`, `history -c`) nunca executam um programa, por isso nenhuma fonte os vê, exceto dentro de uma linha de comandos como `bash -c '...'`. Um único `whoami` nunca é um alerta: o módulo conta os comandos de reconhecimento **distintos** de cada sessão dentro de uma janela, e só uma rajada deles o é (secção 13).

O que cada evento do módulo contém e como o pesquisar:

| Coluna | Contém | Exemplo de pesquisa |
|---|---|---|
| `vhost` | A pessoa: o utilizador do início de sessão (mantém-se o mesmo através de sudo e su) | `module:privesc vhost:alice` |
| `method` | Tipo de evento: `exec` (programa executado, auditd ou snoopy), `sudo`, `su`, `pkexec`, `doas`, `login`, `pam`, `file` (ficheiro sensível alterado), `chmod` (bit setuid), `kmod`, `ptrace`, `denied` (ficheiro recusado), `audit_config`, `auditd`, `crash`, `syscall` (outra chamada de sistema registada pelas regras de auditoria do servidor) | `module:privesc method:sudo` |
| `uri` | A linha de comandos (palavras-passe mascaradas) | `module:privesc uri:*linpeas*` |
| `path` | O programa executado, ou o ficheiro alterado | `module:privesc path:/tmp/*` |
| `ip` | O endereço SSH da sessão, quando é conhecido | `module:privesc ip:203.0.113.7` |
| `score` | Comandos de reconhecimento distintos da sessão na janela | `module:privesc score:>=8` |
| `action` | `blocked` quando o próprio sistema o impediu: um programa que não pôde ser executado, sudo ou su recusado, um ficheiro recusado | `module:privesc action:blocked` |
| `source` | `audit` ou `syslog` | `module:privesc source:syslog` |

As regras sobre tentativas (falhas repetidas de sudo, muitos ficheiros recusados) contam na mesma os eventos bloqueados; as outras só olham para o que foi realmente executado.

A página do módulo, `/admin/dashboard/modules/installed/privesc/`, tem as mesmas partes que a página do módulo do Apache (secção 4): cabeçalho (com **Descobrir novamente e executar o diagnóstico**, **Reconfigurar** e **Desinstalar**), definições (secção 12), fontes (`audit`, `syslog`; e as não lidas, com o motivo), diagnóstico (secção 14) e regras (secção 13).

<a id="privesc-settings"></a>
## 12. Definições do módulo de escalada de privilégios

| Definição | Predefinição | O que faz |
|---|---|---|
| **Registo de auditoria** | vazio | Vazio: `log_file` de `/etc/audit/auditd.conf`, ou `/var/log/audit/audit.log`. |
| **Ler o syslog** | Automático | Automático: só quando o auditd não está em execução, o respetivo registo não pode ser lido ou o snoopy está instalado. Sempre, ou Nunca. |
| **Ficheiro do syslog** | vazio | Vazio: `/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`, o primeiro que existir. |
| **Utilizadores ignorados** | vazio | Separados por vírgulas. Os respetivos comandos são guardados e podem ser pesquisados, mas nunca geram alertas: contas de automatização (ansible, cópias de segurança). O utilizador `localsiem` é sempre ignorado. |
| **Grupos de administradores** | `sudo,wheel,admin` | Separados por vírgulas. Os seus membros (e o root) têm o limiar de reconhecimento mais alto e podem listar as respetivas permissões de sudo sem alerta. |
| **Janela de reconhecimento (segundos)** | 120 | Janela em que os comandos de reconhecimento distintos de uma sessão são contados (10 a 3600). |
| **Limiar de reconhecimento** | 8 | Comandos de reconhecimento distintos na janela que constituem uma rajada, para utilizadores e contas de serviço (2 a 500). |
| **Limiar de reconhecimento para administradores** | 20 | O mesmo para o root e os administradores, que os executam no âmbito do seu trabalho (2 a 500). |
| **Limiar de enumeração automatizada** | 40 | Comandos de reconhecimento distintos na janela que só um script executa (do tipo linpeas), para todos (5 a 1000). |
| **Dias de aprendizagem das contas de serviço** | 3 | Durante os primeiros dias após o primeiro arranque do módulo, os programas que cada conta de serviço executa (`www-data` a executar `sh -c sendmail`) são aprendidos sem alertas (0 a 365). |
| **Horas entre análises de programas setuid** | 24 | Com que frequência são procurados os programas setuid e setgid e as capacidades de ficheiros (secção 16). 0: nunca (0 a 168). |
| **Pastas analisadas** | `/usr,/bin,/sbin,/lib,/lib64,/opt,/home,/srv,/tmp,/var/tmp,/dev/shm,/var/www,/etc` | Separadas por vírgulas; cada uma é percorrida sem sair do respetivo sistema de ficheiros. As pastas dos contentores e de `/proc` e `/sys` são sempre ignoradas. |
| **Intervalo de descoberta (segundos)** | 300 | Com que frequência são procurados o registo de auditoria, o syslog e o estado do auditd (60 a 86400). O intervalo mais curto dos módulos ativados aplica-se a todos eles. |

O que conta como reconhecimento: `whoami`, `id`, `groups`, `uname`, `hostname`, `w`, `who`, `last`, `ps`, `ss`, `netstat`, `ip`, `ifconfig`, `env`, `pwd`, `history`, `getcap`, `lsmod`, `dmesg`, `mount` e semelhantes; `sudo -l`, `crontab -l`, `systemctl list-*`, as listas de pacotes; `which`, `locate`, `command -v`; `docker ps` e semelhantes; cada `find` diferente; ler `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/*-release`, `/proc/version`, `/root/...`, históricos, chaves SSH e ficheiros `.env`; listar `/root`, `/home`, `/opt`, `/tmp`, as pastas do cron...; `grep -r password`; e `<programa> --version`. Cada comando diferente de uma sessão conta uma vez dentro da janela.

<a id="privesc-rules"></a>
## 13. O que o módulo de escalada de privilégios envia para o SOC: as regras

Cada alerta do módulo vem de uma das respetivas regras (funcionam da mesma forma seja qual for a fonte que viu o comando), exceto os da secção 16. Tal como no Apache, cada regra pode ser desativada e a respetiva gravidade, limiar e janela podem ser alterados na página do módulo; os respetivos eventos podem ser encontrados com `rule:localsiem:<id>`. Nenhuma é disparada para os **Utilizadores ignorados**. As regras marcadas com «auditd» precisam dos registos de auditoria da secção 11.

| Regra | Tipo | Gravidade | Quando | Limiar / janela |
|---|---|---|---|---|
| `privesc-recon-burst` «rajada de reconhecimento» | correspondência | média | A sessão atingiu o limiar de reconhecimento (secção 12) | — |
| `privesc-enumeration` «enumeração automatizada (do tipo linpeas)» | correspondência | alta | A sessão atingiu o limiar de enumeração automatizada, mesmo com um script com outro nome | — |
| `privesc-suid-hunt` «procura de programas setuid ou de capacidades» | correspondência | alta | `find ... -perm -4000` (ou `-u=s`, `/6000`, `-2000`...), `getcap -r`, `find -writable` | — |
| `privesc-sudo-list` «permissões de sudo listadas por um não administrador» | correspondência | média | `sudo -l` por um utilizador ou conta de serviço que não é administrador | — |
| `privesc-known-tool` «ferramenta de enumeração conhecida» | correspondência | alta | linpeas, LinEnum, lse.sh, linux-exploit-suggester, les.sh, pspy, unix-privesc-check, linuxprivchecker, traitor, BeRoot, GTFONow, PEASS, deepce, CDK, sudo_killer, suid3num, mimipenguin, LaZagne, pwncat, searchsploit | — |
| `privesc-exploit` «exploit conhecido» | correspondência | crítica | PwnKit, DirtyPipe, Dirty COW, Baron Samedit (`sudoedit -s '\'`), Looney Tunables (`GLIBC_TUNABLES`), GameOver(lay), nf_tables (CVE-2024-1086), CVE-2023-22809 (`EDITOR=... -- /...`), polkit CVE-2021-3560 (`dbus-send ... CreateUser`), `LD_PRELOAD` com sudo, um script com o nome de um CVE, programas chamados `exploit`, `getroot`, `rootme` | — |
| `privesc-pwnkit` «PwnKit (pkexec executado sem argumentos)» | correspondência | crítica | `pkexec` executado com zero argumentos (auditd) | — |
| `privesc-pwnkit-log` «o pkexec comunica uma tentativa de PwnKit» | correspondência | crítica | O pkexec regista `GCONV_PATH`, «suspicious content» ou «was not found the /etc/shells» (syslog) | — |
| `privesc-suid-escape` «root herdado de um programa setuid» | correspondência | crítica | Um programa que não é setuid é executado com o uid efetivo do root e o uid real de um utilizador: foi abusado um programa setuid (GTFOBins). Os auxiliares de montagem, o D-Bus, o polkit e o X são exceções. | — |
| `privesc-root-without-door` «root sem sudo, su nem pkexec» | correspondência | crítica | Uma sessão de uma pessoa cujo início foi visto executa programas como root sem ter passado por sudo, su, pkexec ou doas (exploits do kernel) (auditd) | — |
| `privesc-root-shell-interpreter` «shell de root iniciada por um interpretador» | correspondência | alta | Uma shell é executada como root, iniciada por python, perl, ruby, awk, gdb... que um utilizador comum estava a executar (o respetivo filho, ou o mesmo processo) (auditd) | — |
| `privesc-file-capabilities` «programa obteve capacidades de root a partir do respetivo ficheiro» | correspondência | alta | Um utilizador executou um programa cujo ficheiro lhe dá `cap_setuid`, `cap_dac_override`, `cap_sys_admin`... (auditd) | — |
| `privesc-tmp-exec` «programa executado a partir de uma pasta com permissão de escrita para todos» | correspondência | alta | Um programa em `/tmp`, `/var/tmp`, `/dev/shm` ou `/run/user/<uid>` | — |
| `privesc-compile-tmp` «programa compilado numa pasta temporária» | correspondência | alta | `gcc`, `cc`, `clang`, `make`... dentro de uma pasta temporária ou sobre ficheiros dela | — |
| `privesc-download-shell` «script transferido executado por uma shell» | correspondência | alta | `curl ... \| sh`, `bash -c "$(curl ...)"`, `bash <(wget ...)`, ou um programa de transferência seguido de uma shell no mesmo pipeline | — |
| `privesc-reverse-shell` «reverse shell» | correspondência | alta | `/dev/tcp/`, `nc -e`, `ncat --exec`, `socat exec:`, `mkfifo ... \| nc`, sockets de python/perl/php/ruby/lua/node, `openssl s_client ... \| sh`, `awk /inet/tcp` | — |
| `privesc-tty-upgrade` «shell promovida a terminal completo» | correspondência | alta | `pty.spawn`, `script ... /dev/null`, `stty raw -echo`, `socat ... pty`, `expect ... spawn sh` | — |
| `privesc-service-recon` «conta de serviço executou comandos de reconhecimento» | correspondência | alta | `www-data`, `mysql` e outras contas de serviço a executar `whoami`, `id`, `uname`... (uma web shell) | — |
| `privesc-service-new-program` «conta de serviço executou um programa que nunca tinha executado» | correspondência | alta | Após os dias de aprendizagem, uma conta de serviço executa uma shell, um interpretador ou uma ferramenta que nunca executou (`sh -c id` onde só executava `sh -c sendmail`) | — |
| `privesc-container-escape` «contentor usado para chegar ao anfitrião como root» | correspondência | alta | Alguém que não é root executa `docker run -v /:/...`, `--privileged`, `--pid=host`, `nsenter -t 1`, `lxc config set ... security.privileged true`, `lxc config device add ... source=/`, `debugfs /dev/...` | — |
| `privesc-auth-failures` «falhas repetidas de sudo ou su» | limiar | média | sudo, su, pkexec ou doas falhados de um utilizador | 3 em 600 s |
| `privesc-sensitive-file` «ficheiro de contas, sudo, PAM ou preload alterado» | correspondência | alta | `/etc/passwd`, `shadow`, `group`, `gshadow`, `sudoers`, `sudoers.d`, `doas.conf`, `doas.d`, `ld.so.preload`, `ld.so.conf`, `ld.so.conf.d`, `pam.d`, `security` alterado por um programa que não é uma ferramenta de pacotes ou de contas (auditd) | — |
| `privesc-persistence-file` «ficheiro de SSH, cron ou serviço alterado» | correspondência | média | `/root/.ssh`, `sshd_config`, `sshd_config.d`, ficheiros do cron, `/etc/systemd/system`, `/etc/init.d`, `rc.local`, `/etc/local.d` alterados (auditd) | — |
| `privesc-monitoring-changed` «configuração do auditd alterada» | correspondência | média | `/etc/audit` alterado por um programa que não é uma ferramenta de pacotes (auditd) | — |
| `privesc-suid-set` «bit setuid ou setgid definido num ficheiro» | correspondência | alta | `chmod u+s`/`g+s` num ficheiro (não numa pasta) fora do gestor de pacotes (auditd) | — |
| `privesc-setcap` «capacidades de ficheiro definidas» | correspondência | alta | `setcap ... cap_...` | — |
| `privesc-kernel-module` «módulo do kernel carregado a partir de uma sessão» | correspondência | alta | Um módulo carregado ou removido a partir da sessão de uma pessoa (auditd) | — |
| `privesc-ptrace` «processo anexado com ptrace» | correspondência | média | `PTRACE_ATTACH` ou `PTRACE_SEIZE` (auditd) | — |
| `privesc-denied-burst` «muitos ficheiros recusados (enumeração)» | limiar | média | Ficheiros recusados (`EACCES`, `EPERM`) a um utilizador (auditd) | 30 em 60 s |
| `privesc-sensitive-denied` «tentativa de ler os hashes das palavras-passe ou os ficheiros do root» | correspondência | média | `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` ou `/root` recusados a um utilizador (auditd) | — |
| `privesc-history-tampering` «histórico da shell apagado ou desativado» | correspondência | média | `ln -s /dev/null ~/.bash_history`, `rm .bash_history`...; `unset HISTFILE`, `HISTFILE=/dev/null`, `HISTSIZE=0`, `history -c`, `set +o history` só dentro de uma linha de comandos (`bash -c`), uma vez que os comandos internos não executam nenhum programa | — |
| `privesc-audit-stop-command` «comando para desativar o auditd» | correspondência | crítica | `auditctl -e 0`, `auditctl -D`, `auditctl -a never`, `systemctl stop/disable/mask auditd`, `service auditd stop`, `pkill auditd`, apagar `/var/log/audit` ou `/etc/audit` | — |
| `privesc-audit-disabled` «auditoria desativada» | correspondência | crítica | O kernel indica `audit_enabled=0` (auditd) | — |
| `privesc-auditd-stopped` «auditd parado por um processo» | correspondência | alta | O auditd foi parado a pedido de um processo que não é o init (um encerramento do servidor não é comunicado) | — |
| `privesc-crash` «programa setuid ou temporário terminou abruptamente» | correspondência | média | Um programa setuid, ou um numa pasta temporária, terminou abruptamente (auditd `ANOM_ABEND`): muitas vezes um exploit falhado | — |

Cada alerta tem um nome estável, uma descrição que termina com a consulta a colar na pesquisa do localSIEM e detalhes: utilizador, tipo de conta (`root`, `admin`, `user`, `service`), utilizador real e efetivo, comando, programa, pasta, terminal, sessão, fonte (`auditd`, `snoopy`, `syslog`), IP do cliente e, quando se aplicam, o programa pai, o interpretador, o ficheiro alterado e o respetivo grupo, os comandos de reconhecimento contados, as capacidades, o modo definido, o pedido de ptrace e o erro de um ficheiro recusado. Quando sai, o alerta leva também o contexto da sessão: se o respetivo início foi visto, se passou por sudo ou su, o respetivo endereço SSH e os seus **últimos 20 comandos**, para que o analista leia o que levou ao alerta sem pesquisar.

O mesmo comando pode ser visto por mais de uma fonte (auditd e snoopy): os alertas são agrupados por módulo, utilizador, IP, categoria e gravidade, por isso continua a resultar num único alerta. As palavras-passe nas linhas de comandos (`mysql -p...`, `sshpass -p`, `curl -u user:pass`, `PASSWORD=...`, URLs com uma palavra-passe) são mascaradas antes de qualquer coisa ser guardada, também no hexadecimal dos registos de auditoria.

<a id="privesc-doctor"></a>
## 14. Requisitos do módulo de escalada de privilégios: o diagnóstico

**Requisitos.** O módulo precisa de uma fonte que o utilizador `localsiem` consiga ler (o ficheiro existe e o `localsiem` consegue abri-lo): o registo do **auditd** (com o auditd em execução, fora de um contentor) ou o ficheiro do **syslog** com sudo, su, pkexec e doas (`/var/log/auth.log`, `/var/log/secure` ou `/var/log/messages`, ou a definição **Ficheiro do syslog**, exceto se **Ler o syslog** for Nunca), onde o **snoopy** também escreve cada programa executado, se estiver instalado. Basta qualquer uma delas. Quando uma fonte existe mas o `localsiem` não a consegue ler, o requisito indica-o, com o comando que dá o acesso de leitura (para o registo de auditoria, o comando da página Módulos, `manage.py setup-modules`; para o syslog, `setfacl -m g:localsiem:r <ficheiro>`). Sem nenhuma delas, indica o que instalar: o auditd (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`), um daemon de syslog (Debian: `apt-get install rsyslog`; Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) ou o snoopy. Até lá, o módulo fica desativado; **Reconfigurar** volta a verificar. Não instala nada por si só. Numa primeira instalação, os registos pertencem normalmente ao root: execute o comando que a interface web mostra e prima depois **Reconfigurar**.

O diagnóstico é executado tal como o do Apache (secção 7). Apenas descreve o que o módulo vê com o que o servidor tem e o que não consegue ver; as respetivas correções são apenas os pacotes a instalar e o acesso de leitura do `localsiem`. Nunca propõe alterar as regras de auditoria, o `auditd.conf` (exceto `log_group`, abaixo), o `snoopy.ini`, as shells nem qualquer outra configuração:

| Verificação | Correto quando | Caso contrário |
|---|---|---|
| auditd | O auditd está em execução | Aviso se não estiver instalado (Debian: `apt-get install auditd`; Alpine: `apk add audit && rc-update add auditd && rc-service auditd start`); aviso, sem correção, se estiver instalado mas parado (executá-lo ou não é decisão do administrador). Informação dentro de um contentor: o auditd não pode ser executado aí. |
| Registo de auditoria | O `localsiem` consegue lê-lo | Erro, com o comando da página Módulos; aviso se o auditd estiver em execução e o respetivo registo não estiver onde o módulo o procura (definição **Registo de auditoria**) |
| Grupo do registo de auditoria | O registo de auditoria não pertence ao grupo `root` | Aviso se pertencer (`log_group = root` em `auditd.conf`): cada registo que o auditd cria ao rodar tem o modo 600, só pode ser lido pelo root e o localSIEM deixa de ler. A correção é a linha `log_group = adm` para `/etc/audit/auditd.conf` (depois reinicie o auditd): os novos registos são criados com o modo 640. |
| Registos das regras de auditoria | Foram lidos programas executados (`EXECVE`) | Aviso se o auditd escrever mas nenhum dos respetivos registos for um programa executado: as regras de auditoria do servidor não registam `execve`, por isso os comandos de scripts, web shells e exploits não são vistos através do auditd. Informação com o que mais as regras registaram até agora (alterações de ficheiros sensíveis, bits setuid, módulos do kernel, ptrace, ficheiros recusados) e o que ainda não |
| syslog | O ficheiro do syslog é lido | Erro se não puder ser lido (`setfacl -m g:localsiem:r <ficheiro>`); aviso se não houver nem um registo de auditoria utilizável nem um ficheiro do syslog (Debian: `apt-get install rsyslog`; Alpine: `apk add rsyslog && rc-update add rsyslog && rc-service rsyslog start`) |
| snoopy | Instalado, e as respetivas linhas são lidas | Aviso sem auditd: os comandos de scripts e web shells não são vistos (Debian: `apt-get install snoopy`; o Alpine não tem pacote: é compilado a partir do código-fonte). Aviso se estiver instalado mas o syslog não for lido. Informação se as respetivas linhas não tiverem uid efetivo (`message_format` de `snoopy.ini`): o root herdado de um programa setuid não é visto através do snoopy |
| O que o módulo vê | — | Informação: auditd (e o que as respetivas regras registam), snoopy (cada programa executado) ou, como aviso, apenas sudo, su, pkexec e doas (syslog sem snoopy: a maioria das regras não pode ser disparada); erro se não conseguir ler nada. Também recorda que os comandos internos da shell nunca são vistos |
| Ficheiros da versão 1.0.0 | — | Informação, sem correção, se forem encontrados os ficheiros que o `--configure-privesc` deixou (secção 15) |
| Programas setuid e capacidades | — | Informação: a última análise (secção 16). Aviso, sem correção, com os programas setuid que dão uma shell de root (GTFOBins) e com os programas cujas capacidades são root na prática |
| Ficheiros sensíveis | Nenhum com permissão de escrita para alguém que não seja o root | Erro, sem correção, para cada um (`/etc/passwd`, `sudoers`, cron, `/etc/profile.d`, as pastas do `PATH` do root, `docker.sock`...) |
| Grupos privilegiados | — | Aviso, sem correção, com os membros de `docker`, `lxd`, `incus-admin`, `disk` e `libvirt`: são root na prática |

<a id="privesc-legacy"></a>
## 15. Servidores atualizados a partir da versão 1.0.0 do módulo de escalada de privilégios

A versão 1.0.0 do módulo tinha a opção de configuração `--configure-privesc` e um hook de bash; a versão 1.1.0 removeu ambos, porque um módulo nunca instala nem altera nada fora de `/opt/localsiem`. Os servidores em que foi aplicada mantêm o que escreveu, e o localSIEM não o utiliza nem o elimina:

- `/etc/audit/rules.d/90-localsiem-privesc.rules`: as respetivas regras de auditoria (chaves `lsiem_*`). Enquanto estiverem carregadas, o módulo lê os respetivos registos como os de qualquer outra regra do servidor.
- `/etc/localsiem-privesc/` (o hook), `/etc/profile.d/localsiem-privesc.sh` e a linha que se segue a «localSIEM privesc: command hook» em `/etc/bash.bashrc` (Debian) ou `/etc/bash/bashrc` (Alpine): enquanto existirem, cada bash interativa continua a escrever os respetivos comandos em `/var/log/localsiem-privesc/`, que ninguém lê.
- `/var/log/localsiem-privesc/`: os ficheiros de comandos de cada utilizador.
- `log_group = adm` em `/etc/audit/auditd.conf`, `/root/.ssh` (criado vazio) e o `message_format` de `/etc/snoopy.ini`: podem ficar (`log_group = adm` mantém legíveis os registos de auditoria rodados, secção 14, e o módulo lê esse formato do snoopy, tal como os formatos predefinidos).

O diagnóstico lista os que consegue ver (verificação «Files of version 1.0.0 of the module»). Para os remover, como root: elimine o ficheiro de regras e volte a carregar as regras (`augenrules --load`); elimine `/etc/profile.d/localsiem-privesc.sh`, `/etc/localsiem-privesc/` e a linha do bashrc; e elimine `/var/log/localsiem-privesc/` se não quiser manter os comandos que contém.

<a id="privesc-health"></a>
## 16. Superfície de ataque e avisos de saúde do módulo de escalada de privilégios

Além das respetivas regras, o módulo observa o próprio servidor e envia para o SOC:

| Aviso | Gravidade | Quando |
|---|---|---|
| Novo programa setuid ou setgid | alta | Uma análise encontra um programa setuid ou setgid que a análise anterior não tinha (a primeira análise é apenas a referência). Um atacante que se tornou root deixa muitas vezes uma shell setuid para trás; uma atualização de pacotes também pode adicionar uma. |
| Novo programa setuid numa pasta com permissão de escrita | crítica | O mesmo, em `/tmp`, `/var/tmp`, `/dev/shm`, `/home`, `/srv` ou `/var/www` |
| Novo programa setuid do GTFOBins | crítica | O mesmo, para um programa que dá uma shell de root quando é setuid (`bash`, `find`, `python`, `vim`, `less`, `cp`...) |
| Novas capacidades | alta | Um programa obteve capacidades que são root na prática (`cap_setuid`, `cap_dac_override`, `cap_sys_admin`...) |
| Ficheiro sensível com permissão de escrita para alguém que não seja o root | crítica | Verificado a cada hora: `/etc/passwd`, `/etc/shadow` (também legível por todos), `sudoers`, cron, `/etc/profile.d`, PAM, serviços, `ld.so.preload`, as pastas do `PATH` do root, `docker.sock`... Comunicado uma vez por ficheiro e problema. |
| auditd parado (saúde do localSIEM) | alta | O auditd estava em execução e já não está (fora de contentores) |

A análise é executada em segundo plano, no máximo a cada **Horas entre análises de programas setuid** (a primeira cinco minutos depois de o coletor arrancar), através das **Pastas analisadas**, como o utilizador `localsiem` (o que não consegue ler é ignorado), e para após 3 milhões de ficheiros ou 15 minutos. O resultado, com os GTFOBins e as capacidades encontrados, é mostrado no diagnóstico. As gravidades destes avisos estão em `severity.yaml` do módulo. O que já foi comunicado é recordado entre reinícios.

<a id="cli"></a>
## 17. Linha de comandos

Como root, `/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py <comando>`:

| Comando | Utilização |
|---|---|
| `modules` | Módulos instalados: id, versão, ativado, desativado ou não carregado, e pasta, com os requisitos em falta, se houver; e os módulos que não puderam ser carregados, com o erro |
| `doctor` | Para cada módulo ativado: cada verificação (`✓`, `!`, `✗`, `·`) com o excerto que a resolve, e as fontes encontradas; para um módulo desativado por faltar um requisito, os respetivos requisitos. `--json` devolve o mesmo em JSON. |
| `read-paths` | Pastas que os módulos leem, às quais o localSIEM dá acesso de leitura como root |
| `setup-modules [--no-restart]` | Como root: o comando que a interface web mostra; acesso de leitura às pastas dos módulos (`read_paths`) e um reinício do localSIEM (`--no-restart`: sem ele). Os módulos não têm opções de configuração |

Execute o diagnóstico como o utilizador `localsiem` para ver as respetivas permissões reais:

```bash
runuser -u localsiem -- /opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor   # Debian
su -s /bin/sh localsiem -c "/opt/localsiem/venv/bin/python /opt/localsiem/webapp/backend/manage.py doctor"   # Alpine
```
