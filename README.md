# mk-lwip-httpd-fs


![visitors](https://visitor-badge.laobi.icu/badge?page_id=ArvoreDosSaberes.mk-lwip-httpd-fs)
[![Build](https://img.shields.io/github/actions/workflow/status/ArvoreDosSaberes.mk-lwip-httpd-fs/ci.yml?branch=main)](https://github.com/ArvoreDosSaberes.mk-lwip-httpd-fs/actions)
[![Issues](https://img.shields.io/github/issues/ArvoreDosSaberes.mk-lwip-httpd-fs)](https://github.com/ArvoreDosSaberes.mk-lwip-httpd-fs/issues)
[![Stars](https://img.shields.io/github/stars/ArvoreDosSaberes.mk-lwip-httpd-fs)](https://github.com/ArvoreDosSaberes.mk-lwip-httpd-fs/stargazers)
[![Forks](https://img.shields.io/github/forks/ArvoreDosSaberes.mk-lwip-httpd-fs)](https://github.com/ArvoreDosSaberes.mk-lwip-httpd-fs/network/members)
[![Language](https://img.shields.io/badge/Language-C%2FC%2B%2B-brightgreen.svg)]()
[![AI Assisted](https://img.shields.io/badge/AI-Assisted-purple.svg)]()
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-blue.svg)]()
[![License: CC BY 4.0](https://img.shields.io/badge/license-CC%20BY%204.0-blue.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Latest Release](https://img.shields.io/github/v/release/ArvoreDosSaberes.mk-lwip-httpd-fs?label=version)](https://github.com/ArvoreDosSaberes.mk-lwip-httpd-fs/releases/latest)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-success.svg)](#contribuindo)

Ferramenta para converter projetos web estáticos (HTML, CSS, JS, imagens, etc.) em um arquivo `fsdata.c` compatível com o servidor HTTP (`httpd`) do [lwIP](https://savannah.nongnu.org/projects/lwip).

Este repositório contém:

- Ferramenta original em C (`MakeFS/makefsdata.c`).
- Port em Python com funcionalidades equivalentes e opção extra de compressão deflate (`MakeFSdataProjPlusExample/makefsdata/makefsdata.py`).
- Scripts auxiliares para facilitar a execução da versão em Python em Linux e Windows.

Repositório GitHub:  
`git@github.com:ArvoreDosSaberes/mk-lwip-httpd-fs.git`

---

## Estrutura do repositório

Principais pastas/arquivos:

- `MakeFS/`
  - Ferramenta original em C (`makefsdata.c`) e arquivos relacionados.
- `MakeFSdataProjPlusExample/`
  - `fs/` – exemplo de árvore de arquivos web.
  - `makefsdata/makefsdata.py` – implementação em Python.
  - `requirements.txt` – dependências Python (atualmente somente biblioteca padrão).
- `scripts/`
  - `makefsdata.sh` – wrapper Bash para executar a versão Python.
  - `makefsdata.bat` – wrapper Batch (Windows) para executar a versão Python.

---

## Visão geral do fluxo

1. Você organiza seus arquivos web em um diretório (por padrão, `fs/`).
2. A ferramenta (C ou Python) percorre este diretório, gera arrays de bytes em C e estruturas `fsdata_file`.
3. O resultado é um arquivo `fsdata.c` que deve ser incluído/compilado junto ao `httpd` do lwIP.

O formato gerado é compatível com o `httpd` tradicional do lwIP (estrutura `fsdata_file`, `FS_ROOT`, `FS_NUMFILES` etc.).

---

## Ferramenta C original (`MakeFS`)

### Compilação

Exemplo genérico (Linux):

```bash
cd MakeFS
gcc -o makefsdata makefsdata.c
```

ou utilize o build system que você já usa no seu projeto lwIP (Makefile, IDE, etc.).

### Uso básico

No diretório `MakeFS/`, com uma pasta `fs/` ao lado contendo seus arquivos web:

```bash
./makefsdata
```

Por padrão, o utilitário:

- Procura arquivos em `./fs`.
- Processa subdiretórios.
- Gera `fsdata.c` no diretório atual.

Você também pode especificar o diretório alvo:

```bash
./makefsdata caminho/para/seu_fs
```

### Principais opções da ferramenta C

Algumas opções suportadas pelo original (resumo):

- `targetdir` – diretório contendo os arquivos a converter (padrão `fs`).
- `-s` – desliga o processamento de subdiretórios.
- `-e` – exclui o cabeçalho HTTP dos arquivos (cabeçalho gerado em tempo de execução).
- `-11` – usa cabeçalho HTTP/1.1 (padrão é HTTP/1.0).
- `-c` – pré-calcula checksums (suportado apenas na versão C).
- `-f:<arquivo>` – nome do arquivo de saída (padrão `fsdata.c`).
- `-m` – inclui cabeçalho `Last-Modified` baseado no timestamp do arquivo.
- `-svr:<nome>` – identifica o servidor no cabeçalho HTTP.
- `-x:<ext_list>` – lista de extensões (separadas por vírgula) a excluir.
- `-nossi`, `-ssi:<arquivo>` – controle de SSI (Server Side Includes).

Consulte o código `makefsdata.c` para detalhes adicionais.

---

## Ferramenta Python (`makefsdata.py`)

A versão em Python replica o fluxo principal da ferramenta C, com as seguintes características:

- Geração de `fsdata.c` compatível com o `httpd` do lwIP.
- Tratamento de sinais (`SIGINT`, `SIGTERM`) com saída graciosa.
- Opção de compressão deflate opcional (`-defl[:nivel]`).
- Filtro de diretórios ocultos (nomes iniciados em `.`) e `CVS`.
- Manutenção da maior parte da interface de linha de comando do original, com algumas opções aceitas mas ignoradas.

### Pré-requisitos

- Python 3.x (recomendado 3.8 ou superior).
- Não há dependências externas (apenas biblioteca padrão, incluindo `zlib`).

Opcionalmente, você pode criar um ambiente virtual:

```bash
cd MakeFSdataProjPlusExample
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows (PowerShell/CMD)
```

### Execução direta (sem scripts)

No diretório `MakeFSdataProjPlusExample/`:

```bash
python3 makefsdata/makefsdata.py fs
```

Isso:

- Processa a pasta `fs/` (relativa a `MakeFSdataProjPlusExample/`).
- Gera `fsdata.c` no diretório atual.

Você pode apontar para outro diretório:

```bash
python3 makefsdata/makefsdata.py ../meu_fs
```

### Uso com scripts (recomendado)

#### Linux / macOS – `scripts/makefsdata.sh`

A partir da raiz do repositório:

```bash
./scripts/makefsdata.sh fs
```

O script:

- Tenta usar `MakeFSdataProjPlusExample/venv/bin/python`;
- Se não encontrar, tenta `venv-mk-lwip-httpd-fs/bin/python` na raiz;
- Caso não existam ambientes virtuais, usa `python3` (ou `python`).

Todos os parâmetros após o script são repassados ao `makefsdata.py`.

Exemplos:

```bash
# Geração simples, HTTP/1.0, sem compressão
./scripts/makefsdata.sh fs

# Geração com HTTP/1.1, Last-Modified e compressão deflate nível 10
./scripts/makefsdata.sh fs -11 -m -defl:10

# Exclui arquivos .txt e .bak
./scripts/makefsdata.sh fs -x:txt,bak

# Não processar subdiretórios
./scripts/makefsdata.sh fs -s
```

#### Windows – `scripts/makefsdata.bat`

No diretório raiz do repositório (no CMD ou PowerShell):

```bat
scripts\makefsdata.bat fs
```

O script:

- Tenta usar `MakeFSdataProjPlusExample\venv\Scripts\python.exe`;
- Depois tenta `venv-mk-lwip-httpd-fs\Scripts\python.exe`;
- Se não encontrar, usa `python` do sistema (via `where python`).

Exemplos:

```bat
REM Geração simples
scripts\makefsdata.bat fs

REM Geração com HTTP/1.1 e deflate nível 6
scripts\makefsdata.bat fs -11 -defl:6

REM Excluir arquivos .log e .tmp
scripts\makefsdata.bat fs -x:log,tmp
```

---

## Opções suportadas na versão Python

A sintaxe de ajuda segue a do utilitário original:

```text
Usage: htmlgen [targetdir] [-s] [-e] [-11] [-nossi] [-ssi:<filename>]
               [-c] [-f:<filename>] [-m] [-svr:<name>]
               [-x:<ext_list>] [-xc:<ext_list>] [-defl<:compr_level>]
```

Na prática, a implementação Python trata as opções da seguinte forma:

- `targetdir`
  - Diretório (relativo ou absoluto) contendo os arquivos a converter.
  - Padrão: `fs`.

- `-s`
  - Desliga o processamento de subdiretórios.
  - Sem `-s`: percorre recursivamente.

- `-e`
  - Exclui o cabeçalho HTTP embutido em cada arquivo.
  - Útil se o cabeçalho for gerado em tempo de execução no firmware.

- `-11`
  - Usa HTTP/1.1 nas linhas de status.
  - Também ajusta alguns cabeçalhos (por exemplo, `Connection`).

- `-f:<arquivo>`
  - Nome do arquivo de saída.
  - Padrão: `fsdata.c`.

- `-m`
  - Adiciona cabeçalho `Last-Modified` com base no timestamp do arquivo.

- `-svr:<nome>`
  - Define o valor do cabeçalho `Server: ...`.
  - Padrão: `lwIP/1.3.1 (http://savannah.nongnu.org/projects/lwip)`.

- `-x:<ext_list>`
  - Lista de extensões a excluir (sem ponto, separadas por vírgula).
  - Exemplo: `-x:bak,tmp,log`.

- `-xc:<ext_list>`
  - Lista de extensões que não serão comprimidas mesmo com `-defl`.
  - Exemplo: `-xc:png,jpg,gif`.

- `-defl` ou `-defl:<nivel>`
  - Ativa compressão deflate para arquivos não-SSI.
  - `nivel` entre `0` e `10` (internamente mapeado para `zlib` 0..9).
  - Só mantém a versão comprimida se ela for menor que a original.
  - Adiciona `Content-Encoding: deflate` ao cabeçalho HTTP.

- `-nossi`, `-ssi:<arquivo>`, `-c`
  - São aceitos para compatibilidade, mas ignorados na versão Python.
  - Não há cálculo de checksum prévio nem processamento avançado de SSI.

---

## Diferenças entre C e Python

- Compatibilidade de saída: o formato geral de `fsdata.c` é compatível, porém:
  - A formatação (quebras de linha, comentários) pode variar.
  - A versão Python não implementa o cálculo de checksum (`-c`).
  - SSI é detectado apenas por extensão de arquivo (`.shtml`, `.shtm`, `.ssi`).

- Compressão deflate:
  - A versão em Python adiciona a opção `-defl` com estatísticas de compressão.
  - O firmware que usa o `fsdata.c` precisa saber lidar com conteúdo comprimido
    e com o cabeçalho `Content-Encoding: deflate`.

- Tratamento de sinais:
  - A versão Python trata `SIGINT`/`SIGTERM` e tenta encerrar de forma graciosa.

---

## Fluxo sugerido de validação

1. Gere `fsdata.c` com a ferramenta C original:

   ```bash
   cd MakeFS
   ./makefsdata ../MakeFSdataProjPlusExample/fs
   cp fsdata.c ../fsdata_c_original.c
   ```

2. Gere `fsdata.c` com a versão Python (sem `-defl`):

   ```bash
   cd ..
   ./scripts/makefsdata.sh MakeFSdataProjPlusExample/fs
   cp fsdata.c fsdata_python.c
   ```

3. Compare os arquivos:

   ```bash
   diff -u fsdata_c_original.c fsdata_python.c
   ```

   Pequenas diferenças de formatação são esperadas; a estrutura geral deve ser equivalente.

4. Opcionalmente, teste também com `-defl`:

   ```bash
   ./scripts/makefsdata.sh MakeFSdataProjPlusExample/fs -defl:10
   ```

   Verifique no `fsdata.c` resultante os cabeçalhos `Content-Encoding: deflate` e o impacto no tamanho.

---

## Créditos

- Ferramenta original (`makefsdata`)  
  - by Jim Pettinato – circa 2003  
  - extended by Simon Goldschmidt – 2009  

- Versão em Python (`makefsdata.py`)  
  - Criada por Carlos Delfino em 2025  
  - E-mail: `<consultoria@carlosdelfino.eti.br>`  
  - Inspirada diretamente no trabalho acima.

---

## Licença

Consulte o arquivo de licença do projeto ou o cabeçalho dos arquivos fonte para detalhes de uso, redistribuição e créditos.
