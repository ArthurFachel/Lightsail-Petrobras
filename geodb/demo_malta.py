"""
Bacia de Maltá: carga FICTICIA para demonstracao.

A bacia nao existe. Nenhum documento, artigo ou dado de treino de modelo fala
dela, entao a unica forma de o agente responder area, formacoes, COT ou o poco
daqui e consultando a GeoDB. E o teste mais direto de que a ferramenta foi
usada: pergunte com e sem o MCP ligado e compare.

Regras:
  - Fica fora de seed.py, que so tem fatos das fontes reais. Entra apenas com
    `python seed.py --demo`, que tambem marca a versao da base com SUFIXO_VERSAO.
  - Toda linha cita a referencia "demo_malta", que se declara ficticia. Se o
    agente citar a fonte, a resposta ja diz que o dado e de demonstracao.
  - Nao levar uma base gerada com --demo para producao nem para a UNISINOS.

Os numeros sao propositalmente "quebrados" (4.317 km2, 2.731 m, COT 6,4-11,9 %)
para nao coincidirem com nenhuma bacia real e serem faceis de conferir.
"""

from __future__ import annotations

SUFIXO_VERSAO = "demo-malta"

REF = "demo_malta"

REFERENCIAS = [
    (REF, "Equipe Lightsail (DADO FICTICIO de demonstracao)", 2026,
     "Bacia de Malta: carga sintetica para teste da GeoDB", None),
]

BACIA = dict(
    nome="Bacia de Maltá",
    area_km2=4317.0,
    area_nota="cerca de 4.317 km2 (FICTICIO, demonstracao)",
    orientacao="alongada NE-SW, com depocentro deslocado para sudeste",
    provincia="Provincia Borborema (posicao ficticia)",
    dominio="Dominio Setentrional (posicao ficticia)",
    contexto=("BACIA FICTICIA criada para demonstracao da GeoDB. Rifte intracontinental "
              "eocretaceo com reativacao de zonas de cisalhamento brasilianas."),
    ref=REF,
)

SEQUENCIAS = [
    ("Pre-Rifte", 1, "Jurassico superior",
     "Arenitos fluviais e eolicos da Formacao Serra do Cardo.", REF),
    ("Sin-Rifte", 2, "Berriasiano-Barremiano",
     "Leques aluviais e lagos profundos: Formacoes Vale Seco e Lagoa Funda.", REF),
    ("Pos-Rifte", 3, "Aptiano-Albiano",
     "Carbonatos lacustres rasos da Formacao Pedra Azul.", REF),
]

GRUPOS = [
    ("Tamboril", "Supergrupo Malta", REF),
]

# (nome, ordem, grupo, sequencia, idade, litologia, espessura_m, espessura_nota,
#  ambiente, fossilifera, observacoes, ref)
FORMACOES = [
    ("Serra do Cardo", 1, None, "Pre-Rifte", "Jurassico superior",
     "Arenitos medios a grossos com estratificacao cruzada de grande porte",
     310.0, "ate 310 m", "Fluvial entrelacado com retrabalhamento eolico", 0,
     "Unidade basal; repousa em discordancia sobre o embasamento.", REF),
    ("Vale Seco", 2, "Tamboril", "Sin-Rifte", "Berriasiano-Valanginiano",
     "Conglomerados polimiticos e arenitos conglomeraticos",
     540.0, "ate 540 m junto a falha de borda", "Leques aluviais de borda de falha", 0,
     "Espessamento contra a falha de borda sudeste.", REF),
    ("Lagoa Funda", 3, "Tamboril", "Sin-Rifte", "Hauteriviano-Barremiano",
     "Folhelhos negros laminados com intercalacoes de siltito",
     265.0, "media ~265 m", "Lacustre profundo, anoxico", 1,
     "Principal rocha geradora da bacia (FICTICIO).", REF),
    ("Pedra Azul", 4, None, "Pos-Rifte", "Aptiano-Albiano",
     "Calcarios laminados azulados e margas",
     120.0, "media ~120 m", "Lacustre raso carbonatico", 1,
     "Contem os fosseis mais bem preservados da bacia (FICTICIO).", REF),
]

# (formacao, litotipo, cot_min, cot_max, cot_nota, tipo_querogenio, maturidade,
#  metodo, ambiente_mo, ref)
GEOQUIMICA = [
    ("Lagoa Funda", "folhelho negro laminado", 6.4, 11.9, "COT entre 6,4 e 11,9 % (FICTICIO)",
     "Tipo I", "janela de oleo (Ro ~0,8 %)", "Rock-Eval e COT por combustao",
     "lacustre anoxico com algas", REF),
]

# (formacao, grupo_bio, detalhe, ref)
FOSSEIS = [
    ("Lagoa Funda", "conchostraceos", "niveis monoespecificos (FICTICIO)", REF),
    ("Pedra Azul", "peixes", "Maltichthys azulensis, especie ficticia", REF),
    ("Pedra Azul", "insetos", "efemeropteros articulados (FICTICIO)", REF),
]

# (nome, sub_bacia, prof_embasamento_m, observacoes, ref)
POCOS = [
    ("9-MLT-7-PB", "Sub-bacia de Tamboril", 2731.0,
     "Poco FICTICIO. Atingiu o embasamento a 2.731 m apos atravessar toda a Formacao Lagoa Funda.",
     REF),
]

# (tema, posicao_a, ref_a, posicao_b, ref_b, situacao)
CONTROVERSIAS = [
    ("Idade da Formacao Pedra Azul",
     "Aptiana, por correlacao com ostracodes de bacias vizinhas (FICTICIO).", REF,
     "Albiana, pela posicao acima de discordancia regional (FICTICIO).", REF,
     "Controversia ficticia, existe so para a demonstracao."),
]

CARGA = dict(
    referencias=REFERENCIAS,
    bacia=BACIA,
    sequencias=SEQUENCIAS,
    grupos=GRUPOS,
    formacoes=FORMACOES,
    geoquimica=GEOQUIMICA,
    fosseis=FOSSEIS,
    pocos=POCOS,
    controversias=CONTROVERSIAS,
)
