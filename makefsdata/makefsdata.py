#!/usr/bin/env python3
"""Versão em Python do utilitário makefsdata.

Criado por Carlos Delfino em 2025 <consultoria@carlosdelfino.eti.br>.

Inspirado no trabalho de:
  by Jim Pettinato               - circa 2003
  extended by Simon Goldschmidt  - 2009

Converte um diretório contendo arquivos web (HTML, CSS, JS, imagens, etc.) em
um arquivo `fsdata.c` compatível com o httpd do lwIP.

Esta implementação replica o fluxo principal do `makefsdata.c`, com opção de
compressão deflate (-defl) e sem cálculo de checksums pré-calculados.
"""

from __future__ import annotations

import os
import shutil
import signal
import sys
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


NEWLINE = "\r\n"  # usado apenas dentro de cabeçalhos HTTP
HEX_BYTES_PER_LINE = 16

DEFAULT_SERVER_AGENT = "lwIP/1.3.1 (http://savannah.nongnu.org/projects/lwip)"
DEFAULT_SERVER_HEADER = f"Server: {DEFAULT_SERVER_AGENT}\\r\\n"

CONTENT_TYPE_MAP = {
    "html": "text/html",
    "htm": "text/html",
    "shtml": "text/html",
    "shtm": "text/html",
    "ssi": "text/html",
    "gif": "image/gif",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "bmp": "image/bmp",
    "ico": "image/x-icon",
    "class": "application/octet-stream",
    "cls": "application/octet-stream",
    "js": "application/x-javascript",
    "css": "text/css",
    "swf": "application/x-shockwave-flash",
    "xml": "text/xml",
}
DEFAULT_CONTENT_TYPE = "text/plain"

SSI_EXTENSIONS = [".shtml", ".shtm", ".ssi"]

_stop_requested = False

# Contadores globais para estatísticas de compressão deflate
overall_data_bytes = 0
deflated_bytes_reduced = 0


def _signal_handler(signum: int, _frame) -> None:
    """Manipula SIGINT/SIGTERM solicitando parada graciosa."""

    global _stop_requested
    _stop_requested = True
    sys.stderr.write(f"\nInterrupção solicitada (signal {signum}). Encerrando...\n")
    sys.stderr.flush()


@dataclass
class MakeFsConfig:
    """Configuração de execução da ferramenta makefsdata em Python."""

    target_dir: Path
    process_subdirs: bool = True
    include_http_header: bool = True
    use_http11: bool = False
    target_filename: str = "fsdata.c"
    include_last_modified: bool = False
    server_header: str = DEFAULT_SERVER_HEADER
    exclude_exts: Optional[List[str]] = None
    ncompress_exts: Optional[List[str]] = None
    deflate_non_ssi_files: bool = False
    deflate_level: int = 10


def print_usage() -> None:
    """Mostra ajuda compatível com o makefsdata original (htmlgen)."""

    msg = (
        " Usage: htmlgen [targetdir] [-s] [-e] [-11] [-nossi] [-ssi:<filename>] "
        "[-c] [-f:<filename>] [-m] [-svr:<name>] [-x:<ext_list>] [-xc:<ext_list>] "
        "[-defl<:compr_level>]" + NEWLINE + NEWLINE +
        "   targetdir: relative or absolute path to files to convert" + NEWLINE +
        "   switch -s: toggle processing of subdirectories (default is on)" + NEWLINE +
        "   switch -e: exclude HTTP header from file (header is created at" + NEWLINE +
        "              runtime, default is off)" + NEWLINE +
        "   switch -11: include HTTP 1.1 header (1.0 is default)" + NEWLINE +
        "   switch -nossi: no support for SSI (ignorado nesta versão Python)" + NEWLINE +
        "   switch -ssi: ssi filename (ignorado nesta versão Python)" + NEWLINE +
        "   switch -c: precalculate checksums (ignorado nesta versão Python)" + NEWLINE +
        "   switch -f: target filename (default is \"fsdata.c\")" + NEWLINE +
        "   switch -m: include \"Last-Modified\" header based on file time" + NEWLINE +
        "   switch -svr: server identifier sent in HTTP response header" + NEWLINE +
        "   switch -x: comma separated list of extensions of files to exclude" + NEWLINE +
        "   switch -xc: comma separated list of extensions of files to not" + NEWLINE +
        "              compress (não serão comprimidas mesmo com -defl)" + NEWLINE +
        "   switch -defl: deflate-compress all non-SSI files (optional ':level'" + NEWLINE +
        "                 where level is [0..10], default=10)" + NEWLINE +
        "   if targetdir not specified, htmlgen will attempt to" + NEWLINE +
        "   process files in subdirectory 'fs'" + NEWLINE
    )
    sys.stdout.write(msg)


def parse_ext_list(raw: str) -> List[str]:
    """Converte lista de extensões separadas por vírgula em lista normalizada."""

    parts: List[str] = []
    for item in raw.split(","):
        cleaned = item.strip().lstrip(".").lower()
        if cleaned:
            parts.append(cleaned)
    return parts


def parse_argv(argv: Sequence[str]) -> Tuple[MakeFsConfig, List[str]]:
    """Interpreta os argumentos de linha de comando."""

    path_str = "fs"
    process_subdirs = True
    include_http_header = True
    use_http11 = False
    target_filename = "fsdata.c"
    include_last_modified = False
    server_header = DEFAULT_SERVER_HEADER
    exclude_exts: List[str] = []
    ncompress_exts: List[str] = []
    deflate_non_ssi_files = False
    deflate_level = 10

    i = 0
    while i < len(argv):
        arg = argv[i]
        if not arg:
            i += 1
            continue
        if arg.startswith("-"):
            if arg.startswith("-svr:"):
                name = arg[5:]
                if not name:
                    name = DEFAULT_SERVER_AGENT
                server_header = f"Server: {name}\\r\\n"
            elif arg == "-s":
                process_subdirs = False
            elif arg == "-e":
                include_http_header = False
            elif arg == "-11":
                use_http11 = True
            elif arg == "-m":
                include_last_modified = True
            elif arg.startswith("-f:"):
                value = arg[3:]
                if value:
                    target_filename = value
            elif arg.startswith("-x:"):
                exclude_exts.extend(parse_ext_list(arg[3:]))
            elif arg.startswith("-xc:"):
                ncompress_exts.extend(parse_ext_list(arg[4:]))
            elif arg in ("-nossi", "-c") or arg.startswith("-ssi:"):
                sys.stderr.write(f"Aviso: opção {arg} ignorada nesta implementação Python.\n")
            elif arg == "-defl" or arg.startswith("-defl:"):
                deflate_non_ssi_files = True
                level_str = ""
                if ":" in arg:
                    level_str = arg.split(":", 1)[1]
                if level_str:
                    try:
                        level_val = int(level_str)
                    except ValueError:
                        sys.stderr.write("ERROR: deflate level must be [0..10]\n")
                        sys.exit(1)
                    if 0 <= level_val <= 10:
                        deflate_level = level_val
                    else:
                        sys.stderr.write("ERROR: deflate level must be [0..10]\n")
                        sys.exit(1)
                sys.stdout.write(
                    f"Deflating all non-SSI files with level {deflate_level} "
                    "(but only if size is reduced)\n"
                )
            elif arg in ("-h", "-?", "--help"):
                print_usage()
                sys.exit(0)
            else:
                sys.stderr.write(f"Parâmetro desconhecido: {arg}\n")
                print_usage()
                sys.exit(1)
        elif arg == "/?":
            print_usage()
            sys.exit(0)
        else:
            path_str = arg
        i += 1

    cfg = MakeFsConfig(
        target_dir=Path(path_str),
        process_subdirs=process_subdirs,
        include_http_header=include_http_header,
        use_http11=use_http11,
        target_filename=target_filename,
        include_last_modified=include_last_modified,
        server_header=server_header,
        exclude_exts=exclude_exts or None,
        ncompress_exts=ncompress_exts or None,
        deflate_non_ssi_files=deflate_non_ssi_files,
        deflate_level=deflate_level,
    )
    return cfg, exclude_exts


def check_path(path: Path) -> None:
    """Valida o diretório alvo, semelhante ao check_path em C."""

    if not str(path):
        raise SystemExit("Invalid path: empty")
    if not path.exists() or not path.is_dir():
        raise SystemExit(f"Invalid path: '{path}'. Directory not found.")


def iter_files(root: Path, process_subdirs: bool, exclude_exts: List[str]) -> Iterable[Tuple[str, Path]]:
    """Percorre arquivos a partir de `root`, retornando (qualified_name, caminho)."""

    root = root.resolve()
    exts = {e.lower() for e in exclude_exts}

    if process_subdirs:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            filenames.sort()
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d != "CVS"
            ]
            dir_path = Path(dirpath)
            try:
                rel = dir_path.relative_to(root)
            except ValueError:
                continue
            if str(rel) == ".":
                subdir = ""
            else:
                subdir = "/" + str(rel).replace(os.sep, "/")
            for name in filenames:
                full = dir_path / name
                if not full.is_file():
                    continue
                if name in ("fsdata.tmp", "fshdr.tmp"):
                    continue
                ext = full.suffix.lstrip(".").lower()
                if exts and ext in exts:
                    sys.stderr.write(f"Ignorando {full} pela lista -x.\n")
                    continue
                qualified = f"{subdir}/{name}"
                yield qualified, full
    else:
        filenames = sorted(p for p in root.iterdir() if p.is_file())
        for full in filenames:
            name = full.name
            if name in ("fsdata.tmp", "fshdr.tmp"):
                continue
            ext = full.suffix.lstrip(".").lower()
            if exts and ext in exts:
                sys.stderr.write(f"Ignorando {full} pela lista -x.\n")
                continue
            qualified = f"/{name}"
            yield qualified, full


def make_c_identifier(qualified_name: str, used: List[str]) -> str:
    """Converte o caminho em identificador C único (similar a fix_filename_for_c)."""

    base = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in qualified_name)
    if not base:
        base = "file"
    name = base
    counter = 0
    while name in used:
        counter += 1
        if counter > 999:
            raise RuntimeError("Falha ao gerar nome C único para arquivo.")
        name = f"{base}{counter}"
    used.append(name)
    return name


def is_ssi_file(path: Path) -> bool:
    """Determina se o arquivo deve ser tratado como SSI pela extensão."""

    lower = path.name.lower()
    return any(lower.endswith(ext) for ext in SSI_EXTENSIONS)


def can_be_compressed_by_ext(path: Path, cfg: MakeFsConfig) -> bool:
    """Indica se o arquivo pode ser comprimido, considerando a lista -xc."""

    if not cfg.ncompress_exts:
        return True
    ext = path.suffix.lstrip(".").lower()
    return ext not in {e.lower() for e in cfg.ncompress_exts}


def build_http_header(
    file_path: Path,
    file_size: int,
    cfg: MakeFsConfig,
    is_ssi: bool,
    is_compressed: bool,
) -> str:
    """Constrói cabeçalho HTTP estático, semelhante a file_write_http_header."""

    # Linha de status
    name = file_path.name
    if name.startswith("404"):
        status = "HTTP/1.1 404 File not found" if cfg.use_http11 else "HTTP/1.0 404 File not found"
    elif name.startswith("400"):
        status = "HTTP/1.1 400 Bad Request" if cfg.use_http11 else "HTTP/1.0 400 Bad Request"
    elif name.startswith("501"):
        status = "HTTP/1.1 501 Not Implemented" if cfg.use_http11 else "HTTP/1.0 501 Not Implemented"
    else:
        status = "HTTP/1.1 200 OK" if cfg.use_http11 else "HTTP/1.0 200 OK"

    lines: List[str] = [status + NEWLINE]

    # Server
    lines.append(cfg.server_header)

    # Content-Length (não para SSI)
    if not is_ssi:
        lines.append(f"Content-Length: {file_size}" + NEWLINE)

    # Last-Modified opcional
    if cfg.include_last_modified:
        st = file_path.stat()
        t = time.gmtime(st.st_mtime)
        ts = time.strftime("%a, %d %b %Y %H:%M:%S GMT", t)
        lines.append(f"Last-Modified: {ts}" + NEWLINE)

    # Connection (apenas HTTP/1.1)
    if cfg.use_http11:
        if not is_ssi:
            lines.append("Connection: keep-alive" + NEWLINE)
        else:
            lines.append("Connection: close" + NEWLINE)

    # Content-Encoding (deflate) quando comprimido
    if is_compressed:
        lines.append("Content-Encoding: deflate" + NEWLINE)

    # Content-Type + CRLF final
    ext = file_path.suffix.lstrip(".").lower()
    ctype = CONTENT_TYPE_MAP.get(ext, DEFAULT_CONTENT_TYPE)
    lines.append(f"Content-type: {ctype}" + NEWLINE + NEWLINE)

    return "".join(lines)


def write_hex_bytes(out, data: bytes, start_index: int) -> int:
    """Escreve bytes como 0xNN, com quebras de linha a cada 16 bytes."""

    i = start_index
    for b in data:
        out.write(f"0x{b:02x},")
        i += 1
        if i % HEX_BYTES_PER_LINE == 0:
            out.write("\n")
    return i


def process_file(
    data_file,
    struct_file,
    qualified_name: str,
    full_path: Path,
    cfg: MakeFsConfig,
    last_var_name: str,
    used_names: List[str],
) -> Tuple[str, int]:
    """Gera entradas de dados e struct para um arquivo único."""

    # Nome da variável C
    varname = make_c_identifier(qualified_name, used_names)

    # Dados do arquivo
    file_bytes = full_path.read_bytes()
    file_size = len(file_bytes)
    is_ssi = is_ssi_file(full_path)

    # Compressão deflate opcional (-defl)
    is_compressed = False
    global overall_data_bytes, deflated_bytes_reduced
    if cfg.deflate_non_ssi_files:
        original_size = file_size
        overall_data_bytes += original_size
        can_be_compressed = (
            cfg.include_http_header
            and (not is_ssi)
            and can_be_compressed_by_ext(full_path, cfg)
        )
        if can_be_compressed and original_size > 0:
            try:
                # zlib aceita níveis de 0 a 9; mapeamos 10 para 9.
                zlevel = cfg.deflate_level
                if zlevel < 0:
                    zlevel = 0
                if zlevel > 9:
                    zlevel = 9
                compressed = zlib.compress(file_bytes, level=zlevel)
            except Exception as exc:
                sys.stderr.write(f"Erro ao comprimir {full_path}: {exc}\n")
            else:
                if len(compressed) < original_size:
                    file_bytes = compressed
                    file_size = len(compressed)
                    is_compressed = True
                    deflated_bytes_reduced += original_size - file_size
                    ratio = (file_size * 100.0) / original_size
                    sys.stdout.write(
                        f" - deflate: {original_size} bytes -> {file_size} bytes "
                        f"({ratio:.02f}%)\n"
                    )
                else:
                    diff = len(compressed) - original_size
                    sys.stdout.write(
                        f" - uncompressed: (would be {diff} bytes larger using deflate)\n"
                    )
        else:
            sys.stdout.write(" - cannot be compressed\n")

    # Nome qualificado armazenado no array, incluindo NUL
    name_str = qualified_name
    name_bytes = (name_str + "\0").encode("ascii", errors="ignore")

    data_file.write(f"static const unsigned char data_{varname}[] = {{\n")
    data_file.write(f"/* {name_str} ({len(name_bytes)} chars) */\n")

    # Escreve nome do arquivo
    idx = 0
    idx = write_hex_bytes(data_file, name_bytes, idx)

    # Alinhamento de payload (4 bytes como no C por padrão)
    while idx % 4 != 0:
        data_file.write("0x00,")
        idx += 1
        if idx % HEX_BYTES_PER_LINE == 0:
            data_file.write("\n")

    prefix_len = idx

    # Cabeçalho HTTP opcional
    if cfg.include_http_header:
        header_str = build_http_header(full_path, file_size, cfg, is_ssi, is_compressed)
        header_bytes = header_str.encode("ascii", errors="ignore")
        idx = write_hex_bytes(data_file, header_bytes, idx)
        prefix_len += len(header_bytes)

    # Conteúdo bruto do arquivo
    data_file.write("\n/* raw file data */\n")
    idx = write_hex_bytes(data_file, file_bytes, idx)
    if idx % HEX_BYTES_PER_LINE != 0:
        data_file.write("\n")
    data_file.write("};\n\n")

    # Struct fsdata_file correspondente
    struct_file.write(f"const struct fsdata_file file_{varname}[] = {{ {{\n")
    struct_file.write(f"file_{last_var_name},\n")
    struct_file.write(f"data_{varname},\n")
    struct_file.write(f"data_{varname} + {prefix_len},\n")
    struct_file.write(f"sizeof(data_{varname}) - {prefix_len},\n")

    # Flags HTTP
    flags: List[str] = []
    if cfg.include_http_header:
        flags.append("FS_FILE_FLAGS_HEADER_INCLUDED")
        if not is_ssi:
            flags.append("FS_FILE_FLAGS_HEADER_PERSISTENT")
            if cfg.use_http11:
                flags.append("FS_FILE_FLAGS_HEADER_HTTPVER_1_1")
    if not flags:
        struct_file.write("0,\n")
    else:
        struct_file.write(" | ".join(flags) + ",\n")

    struct_file.write("}};\n\n")

    return varname, 1


def concat_files(file1: Path, file2: Path, target: Path) -> None:
    """Concatena dois arquivos binários em `target` (fsdata.tmp + fshdr.tmp)."""

    with target.open("wb") as fout:
        for src in (file1, file2):
            with src.open("rb") as fin:
                shutil.copyfileobj(fin, fout)


def generate_fs(cfg: MakeFsConfig, exclude_exts: List[str]) -> None:
    """Fluxo principal de geração de fsdata.c."""

    global overall_data_bytes, deflated_bytes_reduced

    # Reinicializa contadores de compressão a cada execução
    overall_data_bytes = 0
    deflated_bytes_reduced = 0

    check_path(cfg.target_dir)

    data_tmp = Path("fsdata.tmp")
    hdr_tmp = Path("fshdr.tmp")

    with data_tmp.open("w", encoding="ascii") as data_file, hdr_tmp.open("w", encoding="ascii") as struct_file:
        # Cabeçalho inicial do fsdata.c (parte de dados)
        data_file.write("#include \"lwip/apps/fs.h\"\n")
        data_file.write("#include \"lwip/def.h\"\n\n\n")
        data_file.write("#define file_NULL (struct fsdata_file *) NULL\n\n\n")
        data_file.write("#ifndef FS_FILE_FLAGS_HEADER_INCLUDED\n")
        data_file.write("#define FS_FILE_FLAGS_HEADER_INCLUDED 1\n")
        data_file.write("#endif\n")
        data_file.write("#ifndef FS_FILE_FLAGS_HEADER_PERSISTENT\n")
        data_file.write("#define FS_FILE_FLAGS_HEADER_PERSISTENT 0\n")
        data_file.write("#endif\n")
        data_file.write("#ifndef FS_FILE_FLAGS_HEADER_HTTPVER_1_1\n")
        data_file.write("#define FS_FILE_FLAGS_HEADER_HTTPVER_1_1 0x04\n")
        data_file.write("#endif\n")
        data_file.write("#ifndef FSDATA_ALIGN_PRE\n#define FSDATA_ALIGN_PRE\n#endif\n")
        data_file.write("#ifndef FSDATA_ALIGN_POST\n#define FSDATA_ALIGN_POST\n#endif\n\n")

        last_var = "NULL"
        num_files = 0
        used_names: List[str] = []

        for qualified, full in iter_files(cfg.target_dir, cfg.process_subdirs, exclude_exts):
            if _stop_requested:
                break
            sys.stdout.write(f"processando {qualified}...\n")
            sys.stdout.flush()
            last_var, inc = process_file(
                data_file=data_file,
                struct_file=struct_file,
                qualified_name=qualified,
                full_path=full,
                cfg=cfg,
                last_var_name=last_var,
                used_names=used_names,
            )
            num_files += inc

        # Definições finais (FS_ROOT, FS_NUMFILES)
        struct_file.write(f"#define FS_ROOT file_{last_var}\n")
        struct_file.write(f"#define FS_NUMFILES {num_files}\n\n")

    # Concatena temporários no arquivo final
    target = Path(cfg.target_filename)
    sys.stdout.write("\nCriando arquivo alvo...\n\n")
    concat_files(data_tmp, hdr_tmp, target)

    # Remove temporários
    try:
        data_tmp.unlink()
    except OSError:
        sys.stderr.write("Aviso: falha ao remover fsdata.tmp\n")
    try:
        hdr_tmp.unlink()
    except OSError:
        sys.stderr.write("Aviso: falha ao remover fshdr.tmp\n")

    sys.stdout.write(f"\nProcessados {num_files} arquivos. Concluído.\n")
    if cfg.deflate_non_ssi_files and overall_data_bytes > 0:
        ratio = (deflated_bytes_reduced * 100.0) / float(overall_data_bytes)
        sys.stdout.write(
            f"(Deflated total byte reduction: {overall_data_bytes} bytes -> "
            f"{deflated_bytes_reduced} bytes ({ratio:.02f}%)\n"
        )


def main(argv: Sequence[str]) -> int:
    """Ponto de entrada da ferramenta makefsdata em Python."""

    signal.signal(signal.SIGINT, _signal_handler)
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
    except AttributeError:
        # SIGTERM pode não existir em algumas plataformas
        pass

    cfg, exclude_exts = parse_argv(argv)

    try:
        generate_fs(cfg, exclude_exts)
    except KeyboardInterrupt:
        sys.stderr.write("\nExecução interrompida pelo usuário.\n")
        return 1

    if _stop_requested:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
