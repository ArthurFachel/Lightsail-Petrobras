"""
Testes de varias bacias na mesma base. Rode com:
    cd geodb && ./.venv/bin/python -m pytest -q

Monta uma base com Araripe (real), Malta (demo ficticia) e uma terceira bacia
sintetica que repete de proposito o nome de uma formacao do Araripe, para
provar que as consultas nao misturam bacias.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AQUI))

import consultas as gdb  # noqa: E402
import demo_malta  # noqa: E402
import seed  # noqa: E402

REF = "teste_ficticio"

GEMEA = dict(
    referencias=[(REF, "Teste (FICTICIO)", 2026, "Bacia de teste", None)],
    bacia=dict(nome="Bacia do Teste Gemeo", area_km2=111.0, area_nota=None,
               orientacao="N-S", provincia=None, dominio=None, contexto="FICTICIA", ref=REF),
    sequencias=[("Unica", 1, "Cretaceo", "Sequencia de teste.", REF)],
    grupos=[("Santana", None, REF)],  # mesmo nome de grupo do Araripe
    formacoes=[
        # Mesmo nome de uma formacao do Araripe, dados diferentes.
        ("Crato", 1, "Santana", "Unica", "Cretaceo", "Argilito de teste", 5.0, None,
         "lacustre de teste", 1, "Homonima de teste.", REF),
    ],
    geoquimica=[("Crato", "argilito", 1.0, 2.0, None, "Tipo III", None, None, None, REF)],
    fosseis=[("Crato", "pterossauros", "registro de teste", REF)],
    pocos=[("1-TST-1-XX", None, 50.0, None, REF)],
    controversias=[("Tema de teste", "A", REF, "B", REF, None)],
)


@pytest.fixture(scope="module", autouse=True)
def base(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("geodb_multi") / "geo.db"
    seed.construir(caminho, seed.CARGAS_PADRAO + [demo_malta.CARGA, GEMEA],
                   versao=f"{seed.VERSAO_BASE}+{demo_malta.SUFIXO_VERSAO}").close()
    anterior = gdb.DB_PATH
    gdb.DB_PATH = caminho
    yield caminho
    gdb.DB_PATH = anterior


# ── Bacias ───────────────────────────────────────────────────────────────────

def test_lista_as_tres_bacias():
    nomes = [b["nome"] for b in gdb.listar_bacias()]
    assert nomes == ["Bacia de Maltá", "Bacia do Araripe", "Bacia do Teste Gemeo"]


@pytest.mark.parametrize("entrada", ["Maltá", "malta", "Bacia de Malta", "BACIA DE MALTÁ"])
def test_descreve_malta_por_qualquer_grafia(entrada):
    b = gdb.descrever_bacia(entrada)
    assert b["nome"] == "Bacia de Maltá"
    assert b["area_km2"] == 4317.0
    assert [s["nome"] for s in b["sequencias"]] == ["Pre-Rifte", "Sin-Rifte", "Pos-Rifte"]
    assert [g["nome"] for g in b["grupos"]] == ["Tamboril"]
    assert "FICTICIO" in b["fonte"]


def test_araripe_continua_igual_com_outras_bacias():
    b = gdb.descrever_bacia("Araripe")
    assert b["area_km2"] == 9000.0
    assert len(b["sequencias"]) == 5
    assert len(b["grupos"]) == 3


def test_bacia_inexistente():
    assert gdb.descrever_bacia("Bacia do Parnaiba") is None
    assert gdb.descrever_bacia("") is None


# ── Filtro por bacia ─────────────────────────────────────────────────────────

def test_formacoes_filtradas_por_bacia():
    malta = gdb.listar_formacoes(bacia="Malta")
    assert [f["nome"] for f in malta] == ["Serra do Cardo", "Vale Seco", "Lagoa Funda", "Pedra Azul"]
    assert {f["bacia"] for f in malta} == {"Bacia de Maltá"}
    assert len(gdb.listar_formacoes(bacia="Araripe")) == 10


def test_ordem_sem_buracos_em_cada_bacia():
    for b in gdb.listar_bacias():
        ordens = [f["ordem"] for f in gdb.listar_formacoes(bacia=b["nome"])]
        assert ordens == list(range(1, len(ordens) + 1)), b["nome"]


def test_filtro_de_bacia_inexistente_volta_vazio_e_nao_todas():
    assert gdb.listar_formacoes(bacia="Parnaiba") == []
    assert gdb.buscar_fossil("peixes", bacia="Parnaiba") == []
    assert gdb.listar_pocos(bacia="Parnaiba") == []
    assert gdb.controversias(bacia="Parnaiba") == []
    assert gdb.busca_livre("folhelho", bacia="Parnaiba") == []


def test_grupo_homonimo_nao_mistura():
    nomes = [f["nome"] for f in gdb.listar_formacoes(grupo="Santana", bacia="Araripe")]
    assert nomes == ["Barbalha", "Crato", "Ipubi", "Romualdo"]
    gemea = gdb.listar_formacoes(grupo="Santana", bacia="Teste Gemeo")
    assert [f["nome"] for f in gemea] == ["Crato"]


def test_formacao_sem_id_interno():
    for f in gdb.listar_formacoes():
        assert not any(k.startswith("_") for k in f)
    f = gdb.descrever_formacao("Lagoa Funda")
    assert "_id" not in f


# ── Formacao homonima ────────────────────────────────────────────────────────

def test_formacao_homonima_sem_bacia_pede_desambiguacao():
    r = gdb.descrever_formacao("Crato")
    assert r["ambiguo"] is True
    assert {o["bacia"] for o in r["opcoes"]} == {"Bacia do Araripe", "Bacia do Teste Gemeo"}


def test_formacao_homonima_com_bacia():
    a = gdb.descrever_formacao("Crato", bacia="Araripe")
    t = gdb.descrever_formacao("Crato", bacia="Teste Gemeo")
    assert a["bacia"] == "Bacia do Araripe" and t["bacia"] == "Bacia do Teste Gemeo"
    assert a["litologia"] != t["litologia"]
    assert all(x["bacia"] == "Bacia do Teste Gemeo" for x in t["fosseis"])
    assert all(x["bacia"] == "Bacia do Araripe" for x in a["fosseis"])


def test_geoquimica_homonima_traz_bacia_em_cada_linha():
    linhas = gdb.geoquimica_formacao("Crato")
    assert len(linhas) == 3  # 2 do Araripe + 1 da gemea
    assert {l["bacia"] for l in linhas} == {"Bacia do Araripe", "Bacia do Teste Gemeo"}
    assert len(gdb.geoquimica_formacao("Crato", bacia="Araripe")) == 2
    so_teste = gdb.geoquimica_formacao("Crato", bacia="Teste Gemeo")
    assert [(l["cot_min"], l["cot_max"]) for l in so_teste] == [(1.0, 2.0)]


def test_nome_unico_dispensa_bacia():
    assert gdb.descrever_formacao("Ipubi")["bacia"] == "Bacia do Araripe"
    assert gdb.descrever_formacao("Formação Lagoa Funda")["bacia"] == "Bacia de Maltá"


# ── Canarios da Malta (o que a demo pergunta) ────────────────────────────────

def test_cot_lagoa_funda():
    (g,) = gdb.geoquimica_formacao("Lagoa Funda")
    assert (g["cot_min"], g["cot_max"]) == (6.4, 11.9)
    assert g["bacia"] == "Bacia de Maltá"


def test_poco_malta():
    p = gdb.buscar_poco("9-mlt-7-pb")
    assert p["prof_embasamento_m"] == 2731.0
    assert p["bacia"] == "Bacia de Maltá"


def test_fossil_filtrado_por_bacia():
    todos = {(x["formacao"], x["bacia"]) for x in gdb.buscar_fossil("pterossauros")}
    assert ("Crato", "Bacia do Teste Gemeo") in todos
    assert gdb.buscar_fossil("pterossauros", bacia="Malta") == []
    (peixe,) = gdb.buscar_fossil("peixes", bacia="Malta")
    assert "Maltichthys" in peixe["detalhe"]


def test_controversia_por_bacia():
    (c,) = gdb.controversias(bacia="Malta")
    assert "Pedra Azul" in c["tema"]
    assert all(x["bacia"] == "Bacia do Araripe" for x in gdb.controversias(bacia="Araripe"))


def test_busca_livre_traz_bacia():
    r = gdb.busca_livre("calcarios azulados", bacia="Malta")
    assert [x["nome"] for x in r] == ["Pedra Azul"]
    assert r[0]["bacia"] == "Bacia de Maltá"


def test_versao_marca_a_demo():
    e = gdb.estatisticas()
    assert e["versao_base"].endswith("+demo-malta")
    assert "Bacia de Maltá" in e["cobertura"]
    assert e["bacias"] == ["Bacia de Maltá", "Bacia do Araripe", "Bacia do Teste Gemeo"]
