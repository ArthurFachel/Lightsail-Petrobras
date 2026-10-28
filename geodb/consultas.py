"""
Camada de consulta da GeoDB.

Abre o SQLite em modo somente-leitura (URI mode=ro) e expoe funcoes nomeadas.
Nao ha execucao de SQL arbitrario vindo de fora: o agente escolhe uma funcao e
passa parametros, que entram sempre por placeholder.

A base guarda varias bacias. As consultas aceitam um filtro opcional `bacia`, e
todo retorno de formacao, fossil, poco ou controversia traz o campo "bacia" para
que o agente nunca misture dados de bacias diferentes.

Todo retorno de fato traz o campo "fonte" com a referencia bibliografica. Nenhum
retorno contem caminho de arquivo, nome de tabela interna ou detalhe de deploy.
"""

from __future__ import annotations

import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

DB_PATH = Path(os.environ.get("GEODB_PATH", Path(__file__).resolve().parent / "geo.db"))

_CAMPOS_REF = """
    r.autores || CASE WHEN r.ano IS NOT NULL THEN ' (' || r.ano || ')' ELSE '' END
"""


class BaseIndisponivel(RuntimeError):
    """A base nao existe ou nao pode ser aberta."""


def conectar() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise BaseIndisponivel("base de dados nao encontrada")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _linhas(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with conectar() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _uma(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    linhas = _linhas(sql, params)
    return linhas[0] if linhas else None


def _sem_id(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove chaves internas (prefixo _) antes de devolver ao consumidor."""
    return [{k: v for k, v in l.items() if not k.startswith("_")} for l in linhas]


def normalizar(texto: str) -> str:
    """Remove acentos, caixa e o prefixo 'formacao'/'fm' para casar nomes."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower().strip()
    t = re.sub(r"^(formacao|formacao\s+geologica|fm\.?|grupo)\s+", "", t)
    return re.sub(r"\s+", " ", t)


def normalizar_bacia(texto: str) -> str:
    """Como normalizar(), tirando tambem o prefixo 'bacia do/da/de'."""
    t = normalizar(texto)
    return re.sub(r"^bacia(\s+(do|da|de|dos|das))?\s+", "", t).strip()


# ── Bacias ───────────────────────────────────────────────────────────────────

class _Filtro:
    """Resultado de resolver o parametro `bacia`.

    ativo=False: sem filtro. ativo=True e id=None: a bacia pedida nao existe,
    entao a consulta volta vazia em vez de cair para todas as bacias.
    """

    def __init__(self, ativo: bool, id: int | None = None):
        self.ativo = ativo
        self.id = id

    @property
    def vazio(self) -> bool:
        return self.ativo and self.id is None


def _resolver_bacia(nome: str | None) -> dict[str, Any] | None:
    alvo = normalizar_bacia(nome or "")
    if not alvo:
        return None
    todas = _linhas("SELECT id, nome FROM bacias ORDER BY nome")
    exatas = [b for b in todas if normalizar_bacia(b["nome"]) == alvo]
    if exatas:
        return exatas[0]
    parciais = [b for b in todas if alvo in normalizar_bacia(b["nome"])]
    return parciais[0] if len(parciais) == 1 else None


def _filtro(bacia: str | None) -> _Filtro:
    if not (bacia and bacia.strip()):
        return _Filtro(False)
    b = _resolver_bacia(bacia)
    return _Filtro(True, b["id"] if b else None)


def listar_bacias() -> list[dict[str, Any]]:
    return _linhas(
        """SELECT b.nome, b.area_km2, b.orientacao,
                  (SELECT COUNT(*) FROM formacoes f WHERE f.bacia_id = b.id) AS n_formacoes
           FROM bacias b ORDER BY b.nome"""
    )


def descrever_bacia(nome: str) -> dict[str, Any] | None:
    alvo = _resolver_bacia(nome)
    if not alvo:
        return None
    bacia = _uma(
        f"""SELECT b.nome, b.area_km2, b.area_nota, b.orientacao, b.provincia,
                   b.dominio, b.contexto, {_CAMPOS_REF} AS fonte
            FROM bacias b LEFT JOIN referencias r ON r.id = b.ref_id
            WHERE b.id = ?""",
        (alvo["id"],),
    )
    if bacia is None:
        return None
    bacia["sequencias"] = _linhas(
        f"""SELECT s.nome, s.ordem, s.idade, s.descricao, {_CAMPOS_REF} AS fonte
            FROM sequencias s LEFT JOIN referencias r ON r.id = s.ref_id
            WHERE s.bacia_id = ? ORDER BY s.ordem""",
        (alvo["id"],),
    )
    bacia["grupos"] = _linhas(
        "SELECT nome, supergrupo FROM grupos WHERE bacia_id = ? ORDER BY id",
        (alvo["id"],),
    )
    return bacia


# ── Formacoes ────────────────────────────────────────────────────────────────

_SQL_FORMACAO = f"""
    SELECT f.id AS _id, b.nome AS bacia, f.nome, f.ordem, f.idade, f.litologia,
           f.espessura_m, f.espessura_nota, f.ambiente, f.fossilifera, f.observacoes,
           g.nome AS grupo, g.supergrupo, s.nome AS sequencia,
           {_CAMPOS_REF} AS fonte
    FROM formacoes f
    JOIN bacias b           ON b.id = f.bacia_id
    LEFT JOIN grupos g      ON g.id = f.grupo_id
    LEFT JOIN sequencias s  ON s.id = f.sequencia_id
    LEFT JOIN referencias r ON r.id = f.ref_id
"""


def _formacoes(filtro: _Filtro) -> list[dict[str, Any]]:
    if filtro.vazio:
        return []
    if filtro.ativo:
        return _linhas(_SQL_FORMACAO + " WHERE f.bacia_id = ? ORDER BY b.nome, f.ordem", (filtro.id,))
    return _linhas(_SQL_FORMACAO + " ORDER BY b.nome, f.ordem")


def listar_formacoes(
    grupo: str | None = None, sequencia: str | None = None, bacia: str | None = None
) -> list[dict[str, Any]]:
    linhas = _formacoes(_filtro(bacia))
    if grupo:
        alvo = normalizar(grupo)
        linhas = [l for l in linhas if l["grupo"] and normalizar(l["grupo"]) == alvo]
    if sequencia:
        alvo = normalizar(sequencia)
        linhas = [l for l in linhas if l["sequencia"] and normalizar(l["sequencia"]) == alvo]
    return _sem_id(linhas)


def _achar_formacoes(nome: str, bacia: str | None = None) -> list[dict[str, Any]]:
    """Formacoes que casam com o nome, no maximo uma por bacia.

    Mais de um item significa que o nome existe em bacias diferentes e a
    pergunta nao disse qual.
    """
    alvo = normalizar(nome)
    if not alvo:
        return []
    candidatos = _formacoes(_filtro(bacia))
    achadas = [l for l in candidatos if normalizar(l["nome"]) == alvo]
    if not achadas:
        achadas = [l for l in candidatos
                   if alvo in normalizar(l["nome"]) or normalizar(l["nome"]) in alvo]
    por_bacia: dict[str, dict[str, Any]] = {}
    for l in achadas:
        por_bacia.setdefault(l["bacia"], l)
    return list(por_bacia.values())


def _ambiguo(achadas: list[dict[str, Any]], nome: str) -> dict[str, Any]:
    return {
        "ambiguo": True,
        "mensagem": (f"Ha formacoes chamadas '{nome}' em mais de uma bacia. "
                     "Repita a consulta informando a bacia."),
        "opcoes": [{"nome": l["nome"], "bacia": l["bacia"]} for l in achadas],
    }


def descrever_formacao(nome: str, bacia: str | None = None) -> dict[str, Any] | None:
    achadas = _achar_formacoes(nome, bacia)
    if not achadas:
        return None
    if len(achadas) > 1:
        return _ambiguo(achadas, nome)
    f = achadas[0]
    f["geoquimica"] = _geoquimica_ids([f["_id"]])
    f["fosseis"] = _fosseis_ids([f["_id"]])
    return _sem_id([f])[0]


def _placeholders(n: int) -> str:
    return ",".join("?" * n)


def _geoquimica_ids(ids: list[int]) -> list[dict[str, Any]]:
    if not ids:
        return []
    return _linhas(
        f"""SELECT f.nome AS formacao, b.nome AS bacia, q.litotipo, q.cot_min, q.cot_max,
                   q.cot_nota, q.tipo_querogenio, q.maturidade, q.metodo, q.ambiente_mo,
                   {_CAMPOS_REF} AS fonte
            FROM geoquimica q
            JOIN formacoes f        ON f.id = q.formacao_id
            JOIN bacias b           ON b.id = f.bacia_id
            LEFT JOIN referencias r ON r.id = q.ref_id
            WHERE f.id IN ({_placeholders(len(ids))})
            ORDER BY b.nome, q.id""",
        tuple(ids),
    )


def _fosseis_ids(ids: list[int]) -> list[dict[str, Any]]:
    if not ids:
        return []
    return _linhas(
        f"""SELECT f.nome AS formacao, b.nome AS bacia, x.grupo_bio, x.detalhe,
                   {_CAMPOS_REF} AS fonte
            FROM fosseis x
            JOIN formacoes f        ON f.id = x.formacao_id
            JOIN bacias b           ON b.id = f.bacia_id
            LEFT JOIN referencias r ON r.id = x.ref_id
            WHERE f.id IN ({_placeholders(len(ids))})
            ORDER BY b.nome, x.grupo_bio""",
        tuple(ids),
    )


def geoquimica_formacao(nome: str, bacia: str | None = None) -> list[dict[str, Any]]:
    """Se o nome existir em varias bacias, devolve todas; cada linha diz a bacia."""
    return _geoquimica_ids([f["_id"] for f in _achar_formacoes(nome, bacia)])


def fosseis_formacao(nome: str, bacia: str | None = None) -> list[dict[str, Any]]:
    return _fosseis_ids([f["_id"] for f in _achar_formacoes(nome, bacia)])


def buscar_fossil(grupo_bio: str, bacia: str | None = None) -> list[dict[str, Any]]:
    """Em quais formacoes ocorre determinado grupo fossil."""
    filtro = _filtro(bacia)
    if filtro.vazio:
        return []
    sql = f"""SELECT f.nome AS formacao, b.nome AS bacia, x.grupo_bio, x.detalhe,
                     {_CAMPOS_REF} AS fonte
              FROM fosseis x
              JOIN formacoes f        ON f.id = x.formacao_id
              JOIN bacias b           ON b.id = f.bacia_id
              LEFT JOIN referencias r ON r.id = x.ref_id
              WHERE x.grupo_bio LIKE ?"""
    params: tuple = (f"%{grupo_bio.strip().lower()}%",)
    if filtro.ativo:
        sql += " AND f.bacia_id = ?"
        params += (filtro.id,)
    return _linhas(sql + " ORDER BY b.nome, f.ordem", params)


# ── Pocos, controversias, busca ──────────────────────────────────────────────

def buscar_poco(nome: str) -> dict[str, Any] | None:
    return _uma(
        f"""SELECT p.nome, b.nome AS bacia, p.sub_bacia, p.prof_embasamento_m, p.observacoes,
                   {_CAMPOS_REF} AS fonte
            FROM pocos p
            JOIN bacias b           ON b.id = p.bacia_id
            LEFT JOIN referencias r ON r.id = p.ref_id
            WHERE UPPER(p.nome) = UPPER(?)""",
        (nome.strip(),),
    )


def listar_pocos(bacia: str | None = None) -> list[dict[str, Any]]:
    filtro = _filtro(bacia)
    if filtro.vazio:
        return []
    sql = """SELECT p.nome, b.nome AS bacia, p.sub_bacia, p.prof_embasamento_m
             FROM pocos p JOIN bacias b ON b.id = p.bacia_id"""
    if filtro.ativo:
        return _linhas(sql + " WHERE p.bacia_id = ? ORDER BY p.nome", (filtro.id,))
    return _linhas(sql + " ORDER BY b.nome, p.nome")


def controversias(tema: str | None = None, bacia: str | None = None) -> list[dict[str, Any]]:
    filtro = _filtro(bacia)
    if filtro.vazio:
        return []
    sql = """SELECT c.tema, b.nome AS bacia, c.posicao_a, c.posicao_b, c.situacao,
                    ra.autores || ' (' || ra.ano || ')' AS fonte_a,
                    rb.autores || ' (' || rb.ano || ')' AS fonte_b
             FROM controversias c
             LEFT JOIN bacias b       ON b.id = c.bacia_id
             LEFT JOIN referencias ra ON ra.id = c.ref_a_id
             LEFT JOIN referencias rb ON rb.id = c.ref_b_id"""
    params: tuple = ()
    if filtro.ativo:
        # Controversia sem bacia e tema geral: vale para qualquer filtro.
        sql += " WHERE c.bacia_id = ? OR c.bacia_id IS NULL"
        params = (filtro.id,)
    linhas = _linhas(sql + " ORDER BY c.id", params)
    if tema:
        termos = [t for t in normalizar(tema).split() if len(t) > 3]
        if termos:
            linhas = [
                l for l in linhas
                if any(t in normalizar(l["tema"] + " " + l["posicao_a"] + " " + l["posicao_b"])
                       for t in termos)
            ]
    return linhas


def busca_livre(termo: str, limite: int = 10, bacia: str | None = None) -> list[dict[str, Any]]:
    """Busca textual (FTS5) sobre nome, litologia, ambiente e observacoes das formacoes."""
    termo = (termo or "").strip()
    if not termo:
        return []
    filtro = _filtro(bacia)
    if filtro.vazio:
        return []
    # Converte a consulta do usuario em prefix-match seguro para o FTS5.
    tokens = [t for t in re.findall(r"\w+", termo, flags=re.UNICODE) if len(t) > 2]
    if not tokens:
        return []
    consulta = " OR ".join(f'"{t}"*' for t in tokens)
    sql = f"""SELECT f.nome, b.nome AS bacia, f.idade, f.litologia, f.ambiente, g.nome AS grupo,
                     {_CAMPOS_REF} AS fonte
              FROM formacoes_fts fts
              JOIN formacoes f        ON f.id = fts.rowid
              JOIN bacias b           ON b.id = f.bacia_id
              LEFT JOIN grupos g      ON g.id = f.grupo_id
              LEFT JOIN referencias r ON r.id = f.ref_id
              WHERE formacoes_fts MATCH ?"""
    params: tuple = (consulta,)
    if filtro.ativo:
        sql += " AND f.bacia_id = ?"
        params += (filtro.id,)
    try:
        return _linhas(sql + " ORDER BY rank LIMIT ?", params + (limite,))
    except sqlite3.OperationalError:
        return []


def estatisticas() -> dict[str, Any]:
    """Identidade e tamanho da carga. Usada para verificar que a base foi consultada."""
    with conectar() as conn:
        tabelas = ["bacias", "sequencias", "grupos", "formacoes",
                   "geoquimica", "fosseis", "pocos", "controversias", "referencias"]
        registros = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tabelas}
        bacias = [r["nome"] for r in conn.execute("SELECT nome FROM bacias ORDER BY nome")]
        try:
            meta = {r["chave"]: r["valor"] for r in conn.execute("SELECT chave, valor FROM metadados")}
        except sqlite3.OperationalError:
            meta = {}
    return {**meta, "bacias": bacias, "registros": registros}
