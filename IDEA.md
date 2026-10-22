# IDEA: Hermes-Geo (Gonzaguinha)

O README diz como instalar e usar. Este arquivo diz para que o projeto existe,
qual é o nosso pedaço do sistema e como saber se ele está pronto.

## O cenário

Uma pessoa está num laboratório com um óculos de realidade virtual. Ela está
dentro da bacia X, olhando para a estrutura Y (uma formação, um afloramento, um
poço, um fóssil) e quer saber mais sobre ela. Pergunta e recebe a resposta ali
mesmo, sem tirar o óculos.

## O nosso papel

Não construímos o ambiente de VR. Construímos o que responde: uma API que um
sistema desses consegue acoplar e que também funciona sozinha (curl, notebook,
Telegram), do jeito que testamos até agora.

Dois requisitos, com o mesmo peso:

1. Acoplável. O sistema de VR chama a API, diz onde o usuário está e o que ele
   está olhando, e recebe uma resposta que cabe na cena.
2. Autônoma. Sem o VR, a API continua sendo um agente de Geociências completo,
   com autenticação, sessão, trace e benchmark.

Mudança que serve a um e quebra o outro está errada.

## Por que uma base estruturada

Quem está olhando para a Formação Ipubi quer o número certo: faixa de COT,
espessura, idade, fósseis registrados. Um LLM sozinho, ou com busca em PDF,
arredonda (17,2-28,6% vira "cerca de 20%"), inventa quando o dado não existe e
apresenta uma posição da literatura como consenso. E raramente diz de onde
tirou o número.

Por isso separamos fato de explicação:

- fato pontual vai para a GeoDB, SQLite somente leitura em que cada valor
  carrega a referência bibliográfica e as divergências da literatura ficam
  registradas como tal;
- interpretação (contexto tectônico, histórico estratigráfico, debate sobre
  ambiente deposicional) fica nos artigos de `fontes_de_conhecimento/`;
- o agente consulta a base antes de responder qualquer número, usa o valor
  exato, cita a fonte e mostra as duas posições quando há controvérsia.

Isso casa com o VR. A estrutura que o usuário olha corresponde a uma entrada
da base: a cena sabe o que é, a base sabe o que dizer sobre ela.

## Duas vias de acesso

A GeoDB já fala REST (`/v1/bacias`, `/v1/formacoes/{nome}`,
`/v1/formacoes/{nome}/geoquimica`, `/v1/formacoes/{nome}/fosseis`,
`/v1/pocos/{nome}`, `/v1/controversias`) além de MCP. Isso dá ao cliente de VR
dois caminhos:

- Ficha da estrutura, direto na GeoDB. O usuário aponta para a Formação
  Barbalha, a cena chama `/v1/formacoes/barbalha` e mostra a ficha. Sem LLM,
  determinístico, sempre a mesma resposta.
- Pergunta livre, via `/chat`. "Por que essa camada é tão escura?", "Isso aqui
  tem petróleo?". Aí entra o agente, com a base e os documentos.

A ficha cobre a interação mais comum sem esperar o modelo. O chat fica para o
que precisa de raciocínio.

## Decisões de desenho que já valem

- Base como serviço. A GeoDB roda numa porta; quem hospeda é dono do dado.
  Quando for para a UNISINOS, muda uma URL do lado do agente e nada mais.
- Sem SQL vindo de fora. O agente escolhe uma função nomeada e passa
  parâmetros.
- Sigilo da infraestrutura. A resposta cita "Castro et al., 2017", nunca
  caminho, tabela, porta ou endpoint. É instrução no `SOUL.md` e também filtro
  de saída em `security.py`.
- Rastreabilidade. Cada `/chat` gera um trace com as tool calls cronometradas,
  então dá para auditar se o agente consultou a base.
- Deploy reproduzível. Um instalador idempotente leva uma Ubuntu limpa ao
  estado final: API, modelo no Bedrock, GeoDB, skills, Telegram com
  transcrição de áudio.

## O que falta para acoplar no VR

Lacunas que conferi no código e nos resultados que existem:

1. Contexto da cena. O `/chat` só aceita `query`, `session_id` e
   `new_session`. Não há campo para dizer em que bacia o usuário está nem para
   qual estrutura ele olha; o cliente teria que escrever isso dentro da
   pergunta. Proposta: campo opcional
   `contexto: {"bacia": "araripe", "estrutura": {"tipo": "formacao", "id": "ipubi"}}`,
   que a API converte em instrução para o agente. Sem ele, o uso autônomo não
   muda.
2. Latência. Nas duas rodadas de 21/08 (20 perguntas cada, tempo medido no
   cliente), a mediana foi 20,4 s e 12,2 s, e o p90 55,2 s e 41,5 s. Para quem
   está de óculos esperando, é muito. A via da ficha resolve parte; o resto
   pede streaming ou uma primeira resposta curta.
3. Concorrência. O `/chat` é `async def`, mas chama `subprocess.run`, que
   bloqueia o servidor até o `hermes chat` terminar. Duas pessoas perguntando
   ao mesmo tempo esperam em fila. Um laboratório com mais de um óculos esbarra
   nisso logo. Também cada turno sobe um `hermes chat` novo e reenvia o
   histórico inteiro no prompt.
4. Formato da resposta. Hoje é texto livre em markdown, com a referência no
   meio da frase. Num painel de VR, ou lido em voz alta, isso atrapalha.
   Proposta: manter `response` e acrescentar `resposta_curta` (uma ou duas
   frases), `referencias` (lista separada) e os ids das entidades da base
   citadas, para a cena destacar o que foi mencionado.
5. Voz. A transcrição existe só no gateway do Telegram. Se o VR mandar áudio,
   falta um endpoint que receba áudio, e talvez síntese de voz na volta.
6. Rede. A GeoDB escuta só em `127.0.0.1` por padrão, e nem a API nem a GeoDB
   configuram CORS. Para um cliente nativo (Unity, Unreal) o CORS não importa;
   para WebXR no navegador, importa.
7. Contrato estável. O cliente vai depender do formato da API. Precisa de
   versão (`/v1/chat`) e de um exemplo de integração documentado.

## Como saber se funciona

Sozinha:

- Benchmark v2 em A/B, com e sem GeoDB, mesmo modelo, mesma janela de tempo.
  Quatro números: acerto em `requer_base=sim`, acerto em Fato Pontual, taxa de
  citação, itens que regrediram. O canário `L01` (versão `araripe-2026.10-r1`,
  string que não existe em documento nem no modelo) diz se o agente consultou
  a base.
- Benchmark de segurança: 20 casos, 0 a 2 pontos, com as notas 0 contadas à
  parte.

Acoplada:

- Um cliente mínimo que simula a cena (manda bacia, estrutura e pergunta) e
  mede latência p50/p90 e taxa de erro com 1 e com N usuários simultâneos.
- O benchmark rodado com `contexto` preenchido, para mostrar que dizer onde o
  usuário está melhora a resposta, ou pelo menos não piora.

Estado atual: o A/B do v2 ainda não foi rodado. Os resultados em
`resultados_benchmark/` são de 21/08, anteriores à GeoDB, sem correção
registrada. Os testes de acoplamento ainda não existem.

## O que o projeto não é

- Não é o sistema de VR. Cena, modelos 3D e interação ficam com quem constrói
  o ambiente.
- Não é um sistema de interpretação geológica. Organiza e cita o que a
  literatura diz.
- Não é um banco geológico completo. Hoje cobre só a Bacia do Araripe: 5
  sequências, 3 grupos, 10 formações, 4 registros de geoquímica, 37 de
  fósseis, 1 poço, 4 controvérsias.
- Não é um chatbot genérico. Fora de Geociências, recusa.

## Riscos

- O agente consultar a base depende de ele decidir chamar a ferramenta. Se o
  canário falhar com frequência, instrução no `SOUL.md` não basta; o
  `contexto` da cena pode servir para forçar a consulta.
- O modelo hospedado (DeepSeek V3.2 no Bedrock) muda entre versões. O A/B
  precisa ser refeito a cada troca.
- Cobertura. Se o VR tiver bacias que a base não tem, o agente cai para
  documentos e memória, que é justamente o que o projeto quer evitar.

## Perguntas em aberto

- Quem constrói o VR, e em que engine (Unity, Unreal, WebXR)? Define como eles
  chamam HTTP e se streaming é viável do lado deles.
- Como a cena identifica uma estrutura? Se usar os mesmos nomes da GeoDB, o
  acoplamento é direto. Se não, alguém mantém um mapeamento.
- A interação é por voz, texto ou os dois? A resposta é lida ou falada?
- A API roda na rede do laboratório ou na nuvem (Lightsail)?
- Quantos óculos ao mesmo tempo?
- Quais bacias o VR vai ter?

## Próximos passos

1. Rodar o A/B do benchmark v2 e registrar os quatro números com modelo, data
   e versão da base.
2. Destravar o `/chat` (subprocess sem bloquear o servidor) e medir com
   usuários simultâneos.
3. Adicionar `contexto` opcional ao `/chat` e campos estruturados na resposta,
   sem quebrar o formato atual.
4. Escrever um cliente de exemplo que simula a cena, servindo de teste e de
   documentação para quem for integrar.
5. Fechar as perguntas em aberto com a equipe do VR.

## Quem

MALTA-Lab / PUCRS, com Petrobras e UNISINOS. Arthur Fachel e Otávio Parraga.
