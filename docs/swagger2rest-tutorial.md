# Tutorial: Ferramenta de Conversão Swagger → Endpoints REST (`swagger2rest.py`)

Este tutorial explica como usar o script `swagger2rest.py` do subprojeto **makefs** para
converter um arquivo **Swagger/OpenAPI (JSON)** em um header C (`rest_endpoints.h`)
que descreve os endpoints REST do servidor HTTP baseado em LwIP.

O fluxo é:

1. Criar/editar o arquivo Swagger em JSON.
2. Executar o script `swagger2rest.py` apontando para a pasta do Swagger.
3. Incluir o header gerado no firmware (`Sources/rest_endpoints.h`).
4. Implementar os handlers REST em C.
5. Ajustar (se necessário) o dispatcher REST e recompilar o firmware.

---

## 1. Localização dos Arquivos

- **Script Python**:
  - `makefs/swagger/swagger2rest.py`
- **Swagger de exemplo** (no projeto):
  - `RESTfull/swagger.json`
- **Header gerado** (por padrão que estamos usando):
  - `Sources/rest_endpoints.h`
- **Dispatcher REST**:
  - `Sources/rest_dispatcher.h`
  - `Sources/rest_dispatcher.c`
- **Handlers REST (implementação de negócio)**:
  - `Sources/rest_handlers.c`

> Observação: os caminhos exatos podem ser alterados desde que o comando
> de geração aponte para o destino correto via opção `-o`.

---

## 2. Pré-requisitos

1. **Python 3** instalado no ambiente onde o projeto é compilado.
2. O arquivo Swagger/OpenAPI deve estar em **formato JSON UTF‑8**.
3. O subprojeto `makefs` já está configurado com um `requirements.txt`
   que usa apenas bibliotecas da **biblioteca padrão** do Python.

Não é necessário instalar dependências extras, pois o script usa
apenas:

- `json`, `argparse`, `signal`, `sys`, `pathlib`, `dataclasses`, `typing`.

---

## 3. Estrutura Esperada do Swagger

O script espera um **Swagger/OpenAPI 3.x em JSON**, com a chave `paths`
preenchida. Exemplo simplificado (arquivo `RESTfull/swagger.json`):

```json
{
  "openapi": "3.0.3",
  "info": {
    "title": "STM32 HTTP API",
    "version": "1.0.0"
  },
  "paths": {
    "/temperature": {
      "get": {
        "summary": "Retorna a temperatura",
        "responses": {
          "200": {
            "description": "Temperatura retornada com sucesso"
          }
        }
      }
    }
  }
}
```

### Regras principais:

- Os métodos suportados são: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`,
  `OPTIONS`, `HEAD`, `TRACE`, `CONNECT`.
- O script lê a estrutura `paths` e, para cada combinação
  **(path, method)**, cria um endpoint REST.
- O prefixo `/api/vX` é adicionado automaticamente, conforme a versão
  informada na linha de comando (`-v`).

---

## 4. Execução do Script `swagger2rest.py`

### 4.1. Sintaxe Geral

No diretório raiz do projeto:

```bash
python makefs/swagger/swagger2rest.py <swagger_dir> -o <dest_header> -v <version>
```

Onde:

- `<swagger_dir>`: diretório onde está o arquivo Swagger JSON.
  - O script procura nesta ordem:
    1. `swagger.json`
    2. `openapi.json`
    3. Se só existir **um** arquivo `*.json` na pasta, ele será usado.
- `-o <dest_header>`: caminho completo do header C gerado.
  - Ex.: `Sources/rest_endpoints.h`.
- `-v <version>`: número inteiro da versão para compor o prefixo REST.
  - Ex.: `1` → prefixo `/api/v1`.

### 4.2. Exemplo Prático (usando o projeto atual)

No repositório atual, há um arquivo `RESTfull/swagger.json`. Para gerar
os endpoints da API versão 1 utilizando esse Swagger:

```bash
cd <raiz-do-projeto>
python makefs/swagger/swagger2rest.py RESTfull/ -o Sources/rest_endpoints.h -v 1
```

Saída esperada (similar a):

```text
Usando Swagger/OpenAPI: /.../RESTfull/swagger.json
Header gerado: /.../Sources/rest_endpoints.h
```

Após isso, o arquivo `Sources/rest_endpoints.h` será atualizado com:

- `typedefs` de tipos HTTP e contexto de requisição.
- Protótipos de handlers `restHandle_*`.
- Tabela `static const restEndpoint_t restEndpoints[]` com todos
  os endpoints.
- `static const unsigned int restEndpointCount` com a quantidade de
  entradas na tabela.

O script também garante a existência de:

- `Sources/rest_dispatcher.h`
- `Sources/rest_dispatcher.c`

(caso ainda não existam).

---

## 5. Conteúdo Gerado em `rest_endpoints.h`

O header gerado contém, em linhas gerais:

- Enumeração de métodos HTTP:

```c
typedef enum {
    HTTP_METHOD_GET,
    HTTP_METHOD_POST,
    HTTP_METHOD_PUT,
    HTTP_METHOD_DELETE,
    HTTP_METHOD_PATCH,
    HTTP_METHOD_OPTIONS,
    HTTP_METHOD_HEAD,
    HTTP_METHOD_TRACE,
    HTTP_METHOD_CONNECT,
} httpMethod_t;
```

- Contexto da requisição:

```c
typedef struct restRequestContext {
    const char   *uri;
    const char   *queryString;
    const char   *body;
    unsigned int  bodyLength;
    httpMethod_t  method;
} restRequestContext_t;
```

- Tipo de handler e de endpoint:

```c
typedef int (*restHandlerFn)(const restRequestContext_t *ctx);

typedef struct restEndpoint {
    const char   *pathPattern;
    httpMethod_t  method;
    restHandlerFn handler;
} restEndpoint_t;
```

- Protótipos gerados a partir do Swagger (exemplo):

```c
int restHandle_GET_api_v1_temperature(const restRequestContext_t *ctx);
int restHandle_GET_api_v1_fan(const restRequestContext_t *ctx);
int restHandle_POST_api_v1_fan(const restRequestContext_t *ctx);
int restHandle_GET_api_v1_time(const restRequestContext_t *ctx);
```

- Tabela de endpoints e contagem:

```c
static const restEndpoint_t restEndpoints[] = {
    { "/api/v1/temperature", HTTP_METHOD_GET,  restHandle_GET_api_v1_temperature },
    { "/api/v1/fan",         HTTP_METHOD_GET,  restHandle_GET_api_v1_fan },
    { "/api/v1/fan",         HTTP_METHOD_POST, restHandle_POST_api_v1_fan },
    { "/api/v1/time",        HTTP_METHOD_GET,  restHandle_GET_api_v1_time },
};

static const unsigned int restEndpointCount =
    sizeof(restEndpoints) / sizeof(restEndpoints[0]);
```

> Importante: a tabela é `static const`, ou seja, pode ser incluída em
> mais de um módulo C sem gerar múltiplas definições globais.

---

## 6. Integração com o Firmware

### 6.1. Dispatcher REST

O arquivo `Sources/rest_dispatcher.h` declara:

```c
int restDispatch(const char *uri,
                 const char *method,
                 const char *body,
                 unsigned int bodyLength,
                 struct fs_file *fileOut);
```

O `rest_dispatcher.c` contém um stub inicial que deve ser estendido para:

1. **Percorrer** a tabela `restEndpoints[]`.
2. **Comparar** `uri` e `method` com cada entrada.
3. Se houver match, montar um `restRequestContext_t` e chamar o
   `handler` correspondente.
4. O handler deve produzir a resposta (por exemplo, JSON) e colocar
   os dados em um buffer associado a `fileOut` (conforme a estratégia
   de integração com o httpd/LwIP).

### 6.2. Hook no `fs_open_custom`

No arquivo `Sources/webpages.c`, a função `fs_open_custom` deve se ajustada
para:

1. Verificar se o caminho inicia com `/api/v`.
2. Em caso afirmativo, chamar `restDispatch(...)` antes de tentar servir
   um arquivo estático.
3. Se `restDispatch` retornar diferente de zero, considera-se que a
   requisição foi atendida pelo endpoint REST.

Pseudocódigo (simplificado):

```c
if (strncmp(name, "/api/v", 6) == 0)
{
    if (restDispatch(name, "GET", NULL, 0, file) != 0)
    {
        return 1; /* tratado via REST */
    }
}

/* caso contrário, segue a busca em fsdata.h */
```

> Nota: no futuro, a implementação pode ser estendida para distinguir
> métodos `GET`, `POST`, etc., extraindo o método real do request HTTP
> (esta parte depende de integrações mais profundas com o httpd do LwIP).

---

## 7. Implementando os Handlers REST

O arquivo `Sources/rest_handlers.c` contém stubs gerados/manualizados
para as funções declaradas em `rest_endpoints.h`, este exemplo é baseado no arquivo `swagger.json` que está na pasta do script swagger2rest.py, por exemplo:

```c
#include "rest_endpoints.h"

int restHandle_GET_api_v1_temperature(const restRequestContext_t *ctx)
{
    (void)ctx;
    return 0;
}

int restHandle_GET_api_v1_fan(const restRequestContext_t *ctx)
{
    (void)ctx;
    return 0;
}

int restHandle_POST_api_v1_fan(const restRequestContext_t *ctx)
{
    (void)ctx;
    return 0;
}

int restHandle_GET_api_v1_time(const restRequestContext_t *ctx)
{
    (void)ctx;
    return 0;
}
```

Você deve editar esse arquivo para implementar a lógica de domínio,
por exemplo:

- Ler temperatura de um sensor e retornar um JSON com `value` e `unit`.
- Ler e escrever o estado do ventilador (`on`/`off`).
- Calcular o uptime e retornar `uptimeSeconds`.

A forma exata de montar o JSON e devolver via `fs_file` depende da
estratégia adotada no `rest_dispatcher.c` (buffer estático, alocação
estática por endpoint, etc.).

---

## 8. Recomendações de Uso

1. **Sempre que o Swagger mudar**, rode novamente o comando:

   ```bash
   python makefs/swagger/swagger2rest.py RESTfull/ -o Sources/rest_endpoints.h -v 1
   ```

   para manter o header sincronizado.
2. **Não edite manualmente** o `rest_endpoints.h`, pois ele será
   sobrescrito na próxima geração.
3. Mantenha a lógica de negócio isolada em arquivos como
   `rest_handlers.c` (ou outros módulos específicos de domínio), para
   favorecer uma arquitetura limpa (DDD) e facilitar testes.
4. Se criar novos endpoints no Swagger, lembre-se de:

   - Regenerar o header.
   - Implementar as novas funções `restHandle_*` que aparecerem nele.

---

## 9. Resumo Rápido (Checklist)

1. Editar/atualizar `RESTfull/swagger.json`.
2. Rodar:
   ```bash
   python makefs/swagger/swagger2rest.py RESTfull/ -o Sources/rest_endpoints.h -v 1
   ```
3. Verificar `Sources/rest_endpoints.h` (novos endpoints/handlers).
4. Implementar/atualizar funções em `Sources/rest_handlers.c`.
5. Ajustar `rest_dispatcher.c` se necessário (roteamento e montagem
   de resposta HTTP).
6. Recompilar o projeto (`make -C Debug -j`).

Com isso, a API REST do STM32 passa a ser descrita e versionada a
partir de um arquivo Swagger/OpenAPI, mantendo o firmware alinhado com
as especificações da API.
