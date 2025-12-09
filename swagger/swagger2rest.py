#!/usr/bin/env python3
"""Gera descrições de endpoints REST a partir de um arquivo Swagger/OpenAPI em JSON.

Uso básico:
    python swagger2rest.py <swagger_dir> -o <dest_header> -v <version>

- <swagger_dir>: pasta que contém o arquivo Swagger/OpenAPI em JSON.
                 O script procura, nesta ordem:
                   * swagger.json
                   * openapi.json
                   * único arquivo .json encontrado (se houver apenas um)
- -o / --output: caminho completo do header C a ser gerado (ex.: Sources/rest_endpoints.h)
- -v / --version: versão da API (inteiro). Usado para compor o prefixo /api/v<versao>.

Comportamento adicional:
- Gera, no mesmo diretório do header, um arquivo .c com a mesma base de nome
  (ex.: rest_endpoints.c) contendo o array restEndpoints[] e restEndpointCount.
- Se ainda não existirem, gera também stubs de dispatcher REST:
    rest_dispatcher.h e rest_dispatcher.c

O script trata SIGINT/SIGTERM para encerramento gracioso.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

_stop_requested = False


def _signal_handler(signum, _frame) -> None:
    """Sinaliza encerramento gracioso do script."""

    global _stop_requested
    _stop_requested = True
    sys.stderr.write(f"\nInterrupção solicitada (signal {signum}). Encerrando...\n")
    sys.stderr.flush()


@dataclass
class Endpoint:
    """Representa um endpoint REST extraído do Swagger/OpenAPI."""

    path: str
    method: str
    handler_name: str


HTTP_METHODS = [
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "options",
    "head",
    "trace",
    "connect",
]


def find_swagger_file(swagger_dir: Path) -> Path:
    """Localiza o arquivo JSON de Swagger/OpenAPI dentro da pasta indicada."""

    if not swagger_dir.exists() or not swagger_dir.is_dir():
        raise SystemExit(f"Diretório de swagger inválido: {swagger_dir}")

    candidates = [
        swagger_dir / "swagger.json",
        swagger_dir / "openapi.json",
    ]
    for c in candidates:
        if c.is_file():
            return c

    json_files = sorted(swagger_dir.glob("*.json"))
    json_files = [p for p in json_files if p.is_file()]

    if len(json_files) == 1:
        return json_files[0]

    if not json_files:
        raise SystemExit(f"Nenhum arquivo JSON encontrado em {swagger_dir}")

    raise SystemExit(
        "Mais de um arquivo JSON encontrado em {dir}. "
        "Renomeie o desejado para swagger.json ou openapi.json.".format(dir=swagger_dir)
    )


def normalize_path(path: str) -> str:
    """Normaliza um path Swagger para iniciar com '/' e remover barras duplicadas."""

    if not path.startswith("/"):
        path = "/" + path
    # Remove barras duplas internas
    while "//" in path:
        path = path.replace("//", "/")
    return path


def build_handler_name(method: str, path: str) -> str:
    """Gera o nome de função C para o handler a partir de método + path."""

    # remove prefixo inicial
    if path.startswith("/"):
        path = path[1:]

    # remove chaves de parâmetros {id}
    clean = []
    for ch in path:
        if ch in "{}":
            continue
        if ch.isalnum():
            clean.append(ch)
        else:
            clean.append("_")
    base = "".join(clean).strip("_") or "root"

    return f"restHandle_{method.upper()}_{base}"


def extract_endpoints(swagger: Dict, api_prefix: str) -> List[Endpoint]:
    """Extrai a lista de endpoints a partir da estrutura do Swagger/OpenAPI."""

    paths = swagger.get("paths")
    if not isinstance(paths, dict):
        raise SystemExit("Swagger/OpenAPI JSON inválido: objeto 'paths' não encontrado.")

    endpoints: List[Endpoint] = []

    for raw_path, item in paths.items():
        if _stop_requested:
            break
        if not isinstance(item, dict):
            continue

        # Garante path normalizado
        raw_path = normalize_path(str(raw_path))

        # Aplica prefixo /api/vX se ainda não estiver presente
        full_path = raw_path
        if not full_path.startswith(api_prefix):
            # Evita duplicar barra
            if raw_path.startswith("/"):
                full_path = api_prefix + raw_path
            else:
                full_path = api_prefix + "/" + raw_path

        for method, op in item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            if not isinstance(op, dict):
                continue

            handler_name = build_handler_name(method, full_path)
            endpoints.append(Endpoint(path=full_path, method=method.lower(), handler_name=handler_name))

    return endpoints


def method_enum_name(method: str) -> str:
    """Converte método HTTP textual em identificador de enum C."""

    return f"HTTP_METHOD_{method.upper()}"


def generate_header_content(header_path: Path, endpoints: Iterable[Endpoint]) -> str:
    """Gera o conteúdo do arquivo header com typedefs e tabela de endpoints.

    Toda a definição de `restEndpoints` e `restEndpointCount` é gerada aqui
    como `static const`, evitando a necessidade de um .c separado e
    prevenindo múltiplas definições ao incluir o header em mais de um módulo.
    """

    guard = header_path.name.replace(".", "_").upper()

    # Coleta métodos distintos
    methods = []
    for ep in endpoints:
        m = method_enum_name(ep.method)
        if m not in methods:
            methods.append(m)

    # Garante que todos os métodos padrão existam
    all_methods = [
        "HTTP_METHOD_GET",
        "HTTP_METHOD_POST",
        "HTTP_METHOD_PUT",
        "HTTP_METHOD_DELETE",
        "HTTP_METHOD_PATCH",
        "HTTP_METHOD_OPTIONS",
        "HTTP_METHOD_HEAD",
        "HTTP_METHOD_TRACE",
        "HTTP_METHOD_CONNECT",
    ]
    for m in all_methods:
        if m not in methods:
            methods.append(m)

    lines: List[str] = []
    lines.append("/**\n")
    lines.append(" * Arquivo gerado automaticamente por swagger2rest.py.\n")
    lines.append(" * NÃO EDITE MANUALMENTE: alterações serão sobrescritas.\n")
    lines.append(" */\n\n")
    lines.append(f"#ifndef {guard}\n")
    lines.append(f"#define {guard}\n\n")
    lines.append("#ifdef __cplusplus\nextern \"C\" {\n#endif\n\n")

    lines.append("typedef enum {\n")
    for m in methods:
        lines.append(f"    {m},\n")
    lines.append("} httpMethod_t;\n\n")

    lines.append("typedef struct restRequestContext {\n")
    lines.append("    const char   *uri;\n")
    lines.append("    const char   *queryString;\n")
    lines.append("    const char   *body;\n")
    lines.append("    unsigned int  bodyLength;\n")
    lines.append("    httpMethod_t  method;\n")
    lines.append("} restRequestContext_t;\n\n")

    lines.append("typedef int (*restHandlerFn)(const restRequestContext_t *ctx);\n\n")

    lines.append("typedef struct restEndpoint {\n")
    lines.append("    const char   *pathPattern;\n")
    lines.append("    httpMethod_t  method;\n")
    lines.append("    restHandlerFn handler;\n")
    lines.append("} restEndpoint_t;\n\n")

    # Protótipos das funções handler (o firmware deve implementá-las)
    handler_names: List[str] = []
    for ep in endpoints:
        if ep.handler_name not in handler_names:
            handler_names.append(ep.handler_name)
    for name in handler_names:
        lines.append(f"int {name}(const restRequestContext_t *ctx);\n")
    if handler_names:
        lines.append("\n")

    # Definição da tabela de endpoints e contagem, como static const
    lines.append("static const restEndpoint_t restEndpoints[] = {\n")
    for ep in endpoints:
        lines.append(
            f"    {{ \"{ep.path}\", {method_enum_name(ep.method)}, {ep.handler_name} }},\n"
        )
    lines.append("};\n\n")
    lines.append(
        "static const unsigned int restEndpointCount = sizeof(restEndpoints) / sizeof(restEndpoints[0]);\n\n"
    )

    lines.append("#ifdef __cplusplus\n}\n#endif\n\n")
    lines.append(f"#endif /* {guard} */\n")

    return "".join(lines)


def ensure_dispatcher_files(header_path: Path) -> None:
    """Cria arquivos rest_dispatcher.[ch] básicos, se ainda não existirem."""

    base_dir = header_path.parent
    hdr = base_dir / "rest_dispatcher.h"
    src = base_dir / "rest_dispatcher.c"

    if not hdr.exists():
        hdr_guard = "REST_DISPATCHER_H"
        hdr_content = """/**\n * Dispatcher REST gerado inicialmente por swagger2rest.py.\n * Pode ser editado manualmente para implementar lógica de roteamento.\n */\n\n#ifndef {guard}\n#define {guard}\n\n#ifdef __cplusplus\nextern \"C\" {{\n#endif\n\n#include \"lwip/apps/fs.h\"\n#include \"{endpoints_header}\"\n\nint restDispatch(const char *uri, const char *method, const char *body, unsigned int bodyLength, struct fs_file *fileOut);\n\n#ifdef __cplusplus\n}}\n#endif\n\n#endif /* {guard} */\n""".format(
            guard=hdr_guard,
            endpoints_header=header_path.name,
        )
        hdr.write_text(hdr_content, encoding="utf-8")

    if not src.exists():
        src_content = """/**\n * Implementação básica do dispatcher REST.\n * Este arquivo foi criado automaticamente por swagger2rest.py\n * e pode ser editado para integrar com a aplicação.\n */\n\n#include \"string.h\"\n#include \"lwip/apps/fs.h\"\n#include \"rest_dispatcher.h\"\n\nint restDispatch(const char *uri, const char *method, const char *body, unsigned int bodyLength, struct fs_file *fileOut)\n{{\n    (void)uri;\n    (void)method;\n    (void)body;\n    (void)bodyLength;\n    (void)fileOut;\n\n    /* TODO: implementar integração com restEndpoints[] e gerar resposta HTTP. */\n    return 0;\n}}\n"""
        src.write_text(src_content, encoding="utf-8")


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Interpreta parâmetros de linha de comando."""

    parser = argparse.ArgumentParser(description="Gera endpoints REST a partir de Swagger/OpenAPI JSON.")
    parser.add_argument("swagger_dir", help="Diretório que contém o arquivo swagger.json / openapi.json")
    parser.add_argument("-o", "--output", required=True, help="Caminho completo do arquivo header a ser gerado")
    parser.add_argument("-v", "--version", required=True, type=int, help="Versão da API para compor o prefixo /api/vX")

    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    signal.signal(signal.SIGINT, _signal_handler)
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
    except AttributeError:
        pass

    args = parse_args(argv)

    swagger_dir = Path(args.swagger_dir).resolve()
    header_path = Path(args.output).resolve()
    api_version = int(args.version)

    api_prefix = f"/api/v{api_version}"

    swagger_file = find_swagger_file(swagger_dir)
    sys.stdout.write(f"Usando Swagger/OpenAPI: {swagger_file}\n")

    try:
        data = json.loads(swagger_file.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.stderr.write(f"Erro ao ler/parsear JSON: {exc}\n")
        return 1

    endpoints = extract_endpoints(data, api_prefix)

    if not endpoints:
        sys.stderr.write("Aviso: nenhum endpoint REST encontrado em 'paths'.\n")

    header_path.parent.mkdir(parents=True, exist_ok=True)

    header_content = generate_header_content(header_path, endpoints)

    header_path.write_text(header_content, encoding="utf-8")

    ensure_dispatcher_files(header_path)

    sys.stdout.write(f"Header gerado: {header_path}\n")

    if _stop_requested:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
