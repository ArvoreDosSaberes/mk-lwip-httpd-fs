# Tutorial: Uso do `makefsdata.py` (makefs)

Este tutorial explica como usar a ferramenta `makefsdata.py` do subprojeto **makefs** para gerar o arquivo `fsdata.c` compatível com o servidor HTTP do **lwIP**.

---

## 1. Objetivo da ferramenta

A ferramenta `makefsdata.py` converte um diretório com arquivos web estáticos (HTML, CSS, JS, imagens, etc.) em um arquivo C (`fsdata.c`) que contém:

- **Arrays de bytes** com o conteúdo dos arquivos;
- **Cabeçalhos HTTP opcionais** já embutidos (status, content-type, etc.);
- **Estruturas `fsdata_file`** encadeadas, usadas pelo httpd do lwIP.

Este arquivo `fsdata.c` é então compilado junto ao firmware, permitindo servir páginas web diretamente da memória flash do microcontrolador.

---

## 2. Pré-requisitos

- Python 3 instalado (o script começa com `#!/usr/bin/env python3`).
- Caminho do script:

  ```text
  makefs/makefsdata/makefsdata.py
  ```

- Ter um diretório contendo os arquivos web que serão convertidos, por exemplo:

  ```text
  WebReact/dist
  WebReact/build
  WebFiles/fs
  ```

- Ter o projeto configurado com o **lwIP httpd** (incluindo `lwip/apps/fs.h`).

---

## 3. Uso básico

### 3.1. Chamada mínima

Se você executar o script **sem parâmetros**, ele tentará processar o diretório `fs` na pasta atual:

```bash
python3 makefs/makefsdata/makefsdata.py
```

Isso é equivalente a:

```bash
python3 makefs/makefsdata/makefsdata.py fs
```

O resultado será um arquivo `fsdata.c` gerado no diretório atual.

### 3.2. Especificando o diretório de origem

```bash
python3 makefs/makefsdata/makefsdata.py <caminho_dos_arquivos_web>
```

Exemplo:

```bash
python3 makefs/makefsdata/makefsdata.py WebReact/dist
```

- `<caminho_dos_arquivos_web>` pode ser **relativo** ou **absoluto**.
- O diretório **precisa existir**; caso contrário, o script aborta com erro.

---

## 4. Opções de linha de comando

A sintaxe geral é compatível com o utilitário original `htmlgen`/`makefsdata`:

```text
Usage: htmlgen [targetdir] [-s] [-e] [-11] [-nossi] [-ssi:<filename>] \
               [-c] [-f:<filename>] [-m] [-svr:<name>] [-x:<ext_list>] \
               [-xc:<ext_list>] [-defl<:compr_level>]
```

Abaixo, o comportamento **nesta versão em Python**:

### 4.1. `targetdir`

- Diretório com os arquivos a converter.
- Padrão: `fs` caso não seja informado.

### 4.2. `-s`

- **Desativa** o processamento recursivo de subdiretórios.
- Padrão: **subdiretórios são processados**.

Exemplo (apenas arquivos da raiz de `fs`):

```bash
python3 makefs/makefsdata/makefsdata.py fs -s
```

### 4.3. `-e`

- **Exclui** o cabeçalho HTTP estático dos arquivos gerados.
- Padrão: cabeçalho HTTP **incluído**.

Use `-e` se o cabeçalho for montado em tempo de execução pela aplicação.

### 4.4. `-11`

- Gera cabeçalhos HTTP/1.1 em vez de HTTP/1.0.

### 4.5. `-f:<filename>`

- Define o nome do arquivo final.
- Padrão: `fsdata.c`.

Exemplo para gerar um header:

```bash
python3 makefs/makefsdata/makefsdata.py fs -f:fsdata_web.h
```

> Observação: se o alvo terminar em `.h`, as `struct fsdata_file` são geradas como `static const` para evitar múltiplas definições ao incluir o header em vários módulos.

### 4.6. `-m`

- Inclui o cabeçalho HTTP `Last-Modified` baseado na data/hora do arquivo.

### 4.7. `-svr:<name>`

- Personaliza o cabeçalho `Server:`.
- Padrão: `lwIP/1.3.1 (http://savannah.nongnu.org/projects/lwip)`.

Exemplo:

```bash
python3 makefs/makefsdata/makefsdata.py fs -svr:STM32F429-WebServer
```

### 4.8. `-x:<ext_list>` (excluir extensões)

- Lista **separada por vírgulas** de extensões a **excluir** do processamento.
- Exemplo: `-x:map,ts,tsx`.

```bash
python3 makefs/makefsdata/makefsdata.py WebReact/dist -x:map,ts,tsx
```

### 4.9. `-xc:<ext_list>` (não comprimir extensões)

- Lista de extensões que **não devem ser comprimidas**, mesmo com `-defl`.
- Exemplo: `-xc:png,jpg,gif`.

```bash
python3 makefs/makefsdata/makefsdata.py fs -defl -xc:png,jpg,gif
```

### 4.10. `-defl` ou `-defl:<nivel>`

- Ativa compressão **deflate** para todos os arquivos não-SSI, quando o tamanho comprimido for **menor** que o original.
- Nível aceito: `0` a `10` (internamente mapeado para `0` a `9` do zlib).
- Padrão de nível: `10`.

Exemplos:

```bash
# Compressão com nível padrão (10)
python3 makefs/makefsdata/makefsdata.py fs -defl

# Compressão com nível 6
python3 makefs/makefsdata/makefsdata.py fs -defl:6
```

Durante a execução, o script imprime o ganho de compressão por arquivo e o ganho total ao final.

### 4.11. Opções ignoradas nesta versão

As seguintes opções são **aceitas**, mas **ignoradas**, apenas emitindo aviso:

- `-nossi`
- `-c`
- `-ssi:<filename>`

Essas funcionalidades (SSI dedicado, checksums pré-calculados) não foram implementadas na versão Python.

### 4.12. Ajuda

- `-h`, `-?` ou `--help` exibem a mensagem de uso e terminam a execução.

---

## 5. Saída gerada

Durante a execução, são usados arquivos temporários no diretório de trabalho atual:

- `fsdata.tmp`  (dados em C);
- `fshdr.tmp`   (structs `fsdata_file`).

Ao final, esses arquivos são **concatenados** no arquivo alvo (`fsdata.c` ou o nome definido em `-f:`) e os temporários são removidos.

A saída contém:

- `#include "lwip/apps/fs.h"`
- `#include "lwip/def.h"`
- Definições de alinhamento `FSDATA_ALIGN_PRE/POST`;
- Arrays `static const unsigned char data_<nome>[]` com:
  - nome qualificado do arquivo (como `/index.html`), finalizado em `\0`;
  - cabeçalho HTTP opcional;
  - dados brutos do arquivo.
- Estruturas `file_<nome>` do tipo `struct fsdata_file`;
- Definições finais:
  - `#define FS_ROOT file_<ultimo>`
  - `#define FS_NUMFILES <quantidade>`.

---

## 6. Integração com o projeto STM32/lwIP

1. **Escolha o diretório base** com os arquivos web finais (por exemplo, o resultado de um build React/Vite).
2. **Gere o `fsdata.c`** em um diretório que faça parte do build do firmware (por exemplo, `Sources/` ou um subdiretório dedicado):

   ```bash
   cd /home/carlosdelfino/STM32CubeIDE/workspace_2.0.0/STM32-F429zi-http
   python3 makefs/makefsdata/makefsdata.py WebReact/dist -defl -x:map
   mv fsdata.c Sources/fsdata.c   # se desejado
   ```

3. **Garanta que o arquivo esteja incluído** no CMake/STM32CubeIDE (já deve compilar como parte do projeto).
4. No `lwipopts.h`, ajuste os parâmetros relacionados a buffers TCP (`TCP_SND_BUF`, `TCP_WND`) conforme o resumo impresso ao final da execução do script. O script sugere valores mínimos baseados:

   - No **maior arquivo HTTP**;
   - No **total de bytes HTTP**;
   - Em uma heurística de pelo menos **2x o maior arquivo** e não menos que **16 KiB**.

Sempre revise manualmente esses valores considerando a RAM disponível e o número de conexões simultâneas.

---

## 7. Interrupção graciosa (Ctrl+C)

O script trata sinais `SIGINT` e `SIGTERM`:

- Ao pressionar **Ctrl+C**, ele solicita parada graciosa;
- Emite mensagem de interrupção no `stderr`;
- Retorna código de saída `1` em caso de interrupção.

Isso permite integrar o script em pipelines de build (CMake, `package.json`, etc.) de forma segura, detectando falhas ou cancelamentos.

---

## 8. Exemplos práticos

### 8.1. Geração simples para diretório `fs`

```bash
python3 makefs/makefsdata/makefsdata.py fs
```

### 8.2. Geração a partir de build React com compressão e exclusão de `.map`

```bash
python3 makefs/makefsdata/makefsdata.py WebReact/dist -defl -x:map
```

### 8.3. Geração de header para inclusão em módulo específico

```bash
python3 makefs/makefsdata/makefsdata.py WebReact/dist -f:fsdata_web.h -defl:6
```

Neste caso, as `struct fsdata_file` serão `static const`, adequadas para inclusão em um único módulo C que faça o link com o httpd do lwIP.

---

## 9. Boas práticas

- Sempre rodar o script **após o build** do front-end, para garantir que os arquivos estejam atualizados.
- Evitar comprimir arquivos já comprimidos por natureza (PNG, JPG, GIF, etc.) utilizando `-xc`.
- Acompanhar as mensagens do script para avaliar:
  - Ganho de compressão real;
  - Sugestões de ajuste em `lwipopts.h`.
- Versionar o script e o processo de geração (por exemplo, via scripts em `package.json` ou CMake) para facilitar reprodutibilidade.
