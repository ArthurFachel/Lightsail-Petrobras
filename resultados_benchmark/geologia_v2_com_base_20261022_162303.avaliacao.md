# Avaliação: geologia_v2, com_base, 2026-10-22 16:23

Modelo `deepseek.v4.1-flash`, base `araripe-2026.10-r1` (canário L01 acertou), 78 itens, 0 erros de requisição. Latência: mediana 13,6 s, p90 48 s, máximo 65,7 s.

## Números

| Recorte | Corretor automático | Depois da leitura das falhas |
|---|---|---|
| Itens automáticos | 51/63 (81,0%) | 58/63 (92,1%) |
| requer_base=sim | 49/60 (81,7%) | 56/60 (93,3%) |
| Citação da referência | 38/40 (95,0%) | igual |
| Manuais (0 a 2) | - | 27/30, nenhuma nota 0 |

## As 12 falhas automáticas, uma a uma

Falso negativo do corretor (a resposta está certa):

- F08: "mais de 20 metros"; a regex `\b20 ?m\b` não aceita "metros".
- G02, G03: corrigem a premissa falsa citando o valor errado ("não 150 m", "não perto dos 2.500 m"), e o termo proibido casa com a própria correção.
- I01: "não há consenso" casa com o proibido "ha consenso".
- J03: diz que a base cobre só o Araripe ("a Potiguar não está lá"), mas nenhuma das variantes aceitas cobre essa frase.
- M02: recusa certa; "formações" aparece na oferta de ajuda ("posso responder sobre formações...").
- N01: lista as 7 certas e depois diz que Cariri, Araripina e Exu são afossilíferas.

Falha causada pelo filtro de saída (`security.py`), não pelo modelo:

- D4, H04: o valor certo existia, mas "~113,0" e "~200 m" viraram `[CAMINHO_REMOVIDO]`.

Falha real do agente:

- I02: responde só "5 sequências" e não apresenta o modelo de 4 de Assine (1992).
- I03: menciona a interpretação deltaica, mas sem as referências (Ponte & Appi, Costa et al.).
- L02: "a base cobre a Bacia do Araripe", sem dizer "apenas" nem a versão. Parcial.

## Problemas transversais

1. Filtro apagando números. Em 10 respostas (42 ocorrências), o til de "aproximadamente" (~113,0 Ma, COT ~1%, IH >~600) foi tratado como diretório home. Já está corrigido localmente em `security.py`, com teste novo.
2. Raciocínio vazando na resposta. Pelo menos 14 respostas abrem com "Tenho informações suficientes. Vou compor a resposta...", e D7 abre em inglês. C6 traz o raciocínio inteiro. Isso é stdout do `hermes chat -Q` passado sem limpeza pelo `_clean_stdout`.
3. Busca web falhando. C1, C3, C4 e C5 dizem que a extração de URL não está disponível no backend. Em C3 e C4 o modelo completou de memória e errou: Beurlen chegou em 1950, não nos anos 1930; a lei citada no caso Ubirajara está errada.

Notas manuais e observações por item em `geologia_v2_com_base_20261022_162303.manuais.csv`.
