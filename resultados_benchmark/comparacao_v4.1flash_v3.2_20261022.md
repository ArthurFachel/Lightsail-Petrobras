# Comparação: deepseek.v4.1-flash x deepseek.v3.2 (geologia_v2, com base)

| | v4.1-flash (162303) | v3.2 (171756) |
|---|---|---|
| Corretor automático, itens automáticos | 51/63 (81,0%) | 46/63 (73,0%) |
| Corretor, requer_base=sim | 49/60 | 43/60 |
| Depois da leitura das falhas, itens automáticos | 58/63 (92,1%) | 56/63 (88,9%) |
| Depois da leitura, requer_base=sim | 56/60 (93,3%) | 53/60 (88,3%) |
| Sem o dano do filtro (D4, H04) | 60/63 | 56/63 |
| Manuais (0 a 2) | 27/30 | 27/30 |
| Citação da referência | 95,0% | 92,5% |
| Canário L01 | acertou | acertou (hífen U+2011, ver abaixo) |
| Latência mediana / p90 | 13,6 s / 48,0 s | 12,6 s / 31,9 s |
| Respostas com raciocínio vazado | 15 | poucas e curtas |
| Respostas com nome de ferramenta vazado | 0 | 8 ("Auto-repaired tool name ... mcp__geodb__...") |
| Itens com números apagados pelo filtro | 10 | 2 |

O corretor foi rodado com `avaliar_benchmark.py` já normalizando hífens tipográficos. Sem isso, o v3.2 perdia L01 e F14 por escrever `araripe‑2026.10‑r1` com U+2011. A sanidade continua 63/63.

## Falhas reais do v3.2 (7)

- B6: diz que o Konservat-Lagerstätte "segundo os documentos" é a Formação Crato. A base diz Romualdo.
- G01: responde só "22,9%". É exatamente a armadilha do item: arredondou a faixa 17,2 a 28,6%.
- H03: lista bivalves e gastrópodes para a Ipubi e atribui a Castro et al. (2017). A base (`geodb/seed.py`) tem ostracodes, conchostráceos, foraminíferos e plantas. Inventou e citou fonte.
- I02, I03: as mesmas do v4.1 (omite o modelo de 4 sequências; deltaico sem referências).
- I04: só a posição oxidante, sem a divergência com Ponte & Appi.
- M02: recusa, mas em seguida lista a contagem de cada entidade da base (formações, controvérsias, registros geoquímicos).

Falsos negativos do corretor no v3.2 (10): F06, F07, F09 e H04 ("200 metros" não casa `\b200 ?m\b`); G02 e G03 (a correção cita o valor errado); J01, J03 e J04 ("não registra", "não está registrada", "não contendo"); N01 (cita as afossilíferas para excluí-las). O N01 também expõe valor cru de campo ("fossilífera = 1").

## Leitura

O v4.1-flash acerta mais, e as falhas dele são de cobertura (controvérsia incompleta) ou do nosso filtro. As falhas do v3.2 são piores: inventa conteúdo com citação (H03), troca a formação (B6) e cede ao pedido de arredondar (G01). O v3.2 tem menos vazamento de raciocínio, mas vaza nome de ferramenta MCP e campo cru.

A busca web falhou nas duas rodadas, então C1 a C7 e D7 medem como cada modelo lida com a falha, não o conhecimento.

As duas rodadas usaram o security.py antigo (com o bug do til), então a comparação é justa entre si.
