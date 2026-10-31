"""Formato texto ``KeyValues`` da Valve (``libraryfolders.vdf``) — leitor e gravador puros.

Chaves e valores entre aspas, blocos entre chaves, comentários ``//``. Não é texto localizado.
"""

from __future__ import annotations

from typing import Union

VdfValue = Union[str, "VdfDict"]
VdfDict = dict[str, VdfValue]

_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


class VdfError(ValueError):
    pass


def _tokens(text: str) -> list[str | None]:
    """Strings, ``{`` e ``}`` (estes como ``None`` + marcador)."""
    out: list[str | None] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == "/" and text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif c in "{}":
            out.append(None)
            out.append(c)
            i += 1
        elif c == '"':
            i += 1
            buf = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    buf.append(_ESCAPES.get(text[i + 1], text[i + 1]))
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            if i >= n:
                raise VdfError("texto entre aspas sem fechar")
            out.append("".join(buf))
            i += 1
        else:
            start = i
            while i < n and not text[i].isspace() and text[i] not in '{}"':
                i += 1
            out.append(text[start:i])
    return out


def loads(text: str) -> VdfDict:
    toks = _tokens(text.lstrip("\ufeff"))
    pos = 0

    def block(top: bool) -> VdfDict:
        nonlocal pos
        out: VdfDict = {}
        while pos < len(toks):
            tok = toks[pos]
            if tok is None:
                brace = toks[pos + 1]
                pos += 2
                if brace == "}" and not top:
                    return out
                raise VdfError("chave '{' ou '}' fora do lugar")
            key = tok
            pos += 1
            if pos >= len(toks):
                raise VdfError(f"chave sem valor: {key}")
            nxt = toks[pos]
            if nxt is None and toks[pos + 1] == "{":
                pos += 2
                out[key] = block(top=False)
            elif nxt is None:
                raise VdfError(f"valor inválido para {key}")
            else:
                out[key] = nxt
                pos += 1
        if not top:
            raise VdfError("bloco sem '}'")
        return out

    return block(top=True)


def _quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def dumps(data: VdfDict, indent: int = 0) -> str:
    pad = "\t" * indent
    out = []
    for key, value in data.items():
        if isinstance(value, dict):
            out.append(f"{pad}{_quote(key)}\n{pad}{{\n{dumps(value, indent + 1)}{pad}}}\n")
        else:
            out.append(f"{pad}{_quote(key)}\t\t{_quote(value)}\n")
    return "".join(out)
