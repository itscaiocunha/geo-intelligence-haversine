# API de Inteligência Geoespacial com a Fórmula de Haversine

**Distâncias, cercas virtuais e processamento em lote com controle de acesso por papéis e trilha de auditoria**

**Caio Grilo da Cunha**

Projeto de portfólio, 2026

---

## Resumo

Sistemas de monitoramento, logística e *geofencing* precisam responder rapidamente à pergunta "este alvo está dentro do perímetro?", e precisam registrar quem fez cada consulta. Este trabalho implementa uma API REST que calcula a distância ortodrômica entre coordenadas pela fórmula de Haversine, detecta violações de perímetro para um alvo ou para uma lista de alvos em CSV e mantém uma trilha de auditoria consultável.

- **Serviço:** quatro endpoints em FastAPI (cálculo unitário, cálculo em lote, emissão de chaves e relatório de auditoria), protegidos por chave de API com dois níveis de acesso (`COMMAND` e chaves emitidas por ele).
- **Arquitetura:** reescrita em camadas (domínio, aplicação, infraestrutura e interface HTTP), com as dependências apontando sempre para o domínio (Martin, 2017) e a fiação concentrada em uma única raiz de composição.
- **Refatoração segura:** antes da reescrita, **30 verificações de caracterização** (28 requisições HTTP, o schema OpenAPI e o conteúdo do log) registraram o comportamento original (Feathers, 2004). Depois da reescrita, **25 ficaram idênticas**. As 5 diferenças são exatamente os defeitos corrigidos.
- **Precisão:** em relação à geodésica sobre o elipsoide WGS-84 (Karney, 2013), o modelo esférico erra no máximo **0,44 %** nos pares testados, cerca de 3,8 km em São Paulo–Brasília.
- **Revisão:** a versão original retornava **erro 500** para a própria chave administradora, contava cada lote **duas vezes** na auditoria e tinha testes que **não passavam**. Os três problemas foram corrigidos (veja [Revisão](#revisão-da-versão-original)).

**Palavras-chave:** geoprocessamento; fórmula de Haversine; *geofencing*; arquitetura limpa; auditoria; controle de acesso; testes de caracterização.

## Motivação

Calcular a distância entre dois pontos da superfície terrestre é uma operação básica em rastreamento de frotas, cercas virtuais, resposta a incidentes e análise de proximidade. A fórmula de Haversine (Sinnott, 1984) é a escolha mais comum: é numericamente estável para distâncias curtas e custa poucas operações trigonométricas. O preço é tratar a Terra como uma esfera, e o erro dessa aproximação precisa ser quantificado, não presumido.

Em contextos operacionais, o resultado do cálculo não basta. É preciso saber **quem** consultou **o quê**, e quais consultas indicaram violação. Por isso, o controle de acesso e a trilha de auditoria fazem parte do núcleo do sistema, e não são um acessório.

Este trabalho combina:

- **Geodésia esférica** com a fórmula de Haversine, avaliada contra a solução elipsoidal de referência (Karney, 2013).
- **Arquitetura em camadas** com portas e adaptadores (Cockburn, 2005; Martin, 2017): as regras geoespaciais não dependem de FastAPI, de arquivos ou de variáveis de ambiente.
- **Refatoração guiada por testes de caracterização** (Feathers, 2004): o comportamento observável foi registrado antes de qualquer mudança e comparado depois dela.

## Dados

A API recebe coordenadas em graus decimais. A validação acontece no domínio: latitudes fora de [−90, 90] ou longitudes fora de [−180, 180] são rejeitadas.

| Item | Valor |
|------|-------|
| Modelo da Terra | esfera de raio **6.371,0 km** (raio médio; Moritz, 2000) |
| Entrada unitária | `origin` e `target` (`{"lat", "lon"}`) e `radius` em km (padrão 5,0) |
| Entrada em lote | origem e raio em formulário + arquivo CSV com `name,lat,lon` |
| Saída | distância em km, arredondada a 2 casas, e indicador de violação (distância ≤ raio) |

**Tabela 1.** Tratamento das linhas do CSV em lote.

| Situação | Exemplo | Tratamento |
|----------|---------|------------|
| Linha válida | `Alvo_Alpha,-23.5505,-46.6333` | processada |
| Sem coluna `name` | `-23.55,-46.63` | processada com o nome `Alvo Desconhecido` |
| Coordenada não numérica | `A,abc,1` | ignorada |
| Coordenada fora do intervalo | `B,95,1` | ignorada |
| Linha incompleta | `D,1` | ignorada |
| Arquivo fora de UTF-8 ou origem inválida | — | lote rejeitado (HTTP 400) |

O arquivo [`targets.csv`](targets.csv) traz três alvos de exemplo (dois em São Paulo e um no Rio de Janeiro).

## Metodologia

Implementado em Python 3.11 com FastAPI 0.128, Pydantic 2 e Uvicorn, empacotado em Docker e testado com pytest.

```
 HTTP          src/api/             FastAPI: rotas, schemas, autenticação por X-API-KEY
                  │                 (converte exceções de acesso em 403 e erros de entrada em 400)
                  ▼
 Aplicação     src/application/     casos de uso: análise geoespacial · controle de acesso · relatório de auditoria
                  │        ▲
                  │        └──────  portas (Protocol): CredentialRepository · AuditLog
                  ▼
 Domínio       src/domain/          Coordinate (validação) · HaversineEngine · Credential

 Infraestrutura src/infrastructure/ adaptadores: configuração (.env) · chaves em memória · log em arquivo
 Composição     src/bootstrap.py    liga adaptadores às portas; src/main.py expõe o app ASGI
```

A regra de dependência é estrita: o domínio não importa nada das outras camadas, e a aplicação conhece apenas as portas. Cada instância da API recebe o próprio contêiner de dependências (`create_app(settings)`), o que permite testá-la com chaves e arquivos de log isolados.

### Cálculo de distância

Para dois pontos com latitudes φ₁, φ₂ e diferença de longitude Δλ (em radianos), a distância sobre uma esfera de raio R é

$$
a = \sin^2\!\left(\tfrac{\Delta\varphi}{2}\right) + \cos\varphi_1 \cos\varphi_2 \sin^2\!\left(\tfrac{\Delta\lambda}{2}\right),
\qquad d = 2R \cdot \operatorname{atan2}\!\left(\sqrt{a}, \sqrt{1-a}\right)
$$

Um alvo viola o perímetro quando d ≤ raio. A borda do círculo conta como violação.

### Controle de acesso

1. **Chave de comando:** lida da variável `API_KEY_COMMAND` na inicialização, com papel `COMMAND`.
2. **Chaves emitidas:** somente `COMMAND` emite novas chaves (`geo_` + 32 bytes aleatórios de `secrets`), com papel, dono, emissor e data de expiração.
3. **Autorização:** as regras de permissão ficam nos casos de uso, não nas rotas. A camada HTTP apenas converte `AccessDenied` em 403.

### Auditoria

Cada operação grava uma linha em `data/operation.log` e a espelha no console (visível em `docker logs`):

```
2026-09-25 16:49:28,124 - INFO - [GEO-INT] - CALC_UNITARY | Agent: Agent-07 | Role: OPERATOR | Result: WARNING: Perimeter Violated!
2026-09-25 16:49:28,404 - INFO - [GEO-INT] - BATCH_OPERATION | Agent: Agent-07 | Role: OPERATOR | Origin: {...} | Targets: 3 | Violations: 2
2026-09-25 16:49:30,010 - INFO - [GEO-INT] - KEY_GEN | Issuer: MASTER_SYSTEM | Recipient: Agent-07 | Role: OPERATOR
```

O endpoint `/admin/stats` relê o arquivo e agrega totais globais e por agente. O parser também aceita o formato de lote das versões anteriores (`Batch processed by ...`), para que logs antigos continuem legíveis.

### Validação da refatoração

1. **Caracterização:** um script externo ao repositório exercitou o código original em 28 cenários (sucesso, bordas do raio, coordenadas inválidas, chaves ausentes ou erradas, CSVs malformados, arquivo fora de UTF-8) e salvou status, corpo das respostas, schema OpenAPI e log (com os carimbos de tempo removidos).
2. **Comparação:** o mesmo script rodou sobre o código novo, e cada diferença foi classificada como regressão ou como correção intencional.
3. **Compatibilidade do log:** o novo parser foi aplicado ao log gerado pela versão original e reproduziu o mesmo relatório.

## Resultados

### Precisão do modelo esférico

**Tabela 2.** Haversine (R = 6.371,0 km) contra a geodésica no elipsoide WGS-84 (Karney, 2013).

| Par de pontos | Haversine (km) | Geodésica WGS-84 (km) | Diferença | Erro relativo |
|---------------|---------------:|----------------------:|----------:|--------------:|
| Alvo_Alpha–Alvo_Bravo (São Paulo) | 1,258 | 1,255 | +3 m | +0,23 % |
| Brasília–alvo próximo | 1,293 | 1,292 | +1 m | +0,08 % |
| São Paulo–Rio de Janeiro | 360,749 | 361,261 | −0,51 km | −0,14 % |
| São Paulo–Brasília | 872,297 | 868,544 | +3,75 km | +0,43 % |
| Boa Vista–Porto Alegre | 3.789,449 | 3.772,951 | +16,50 km | +0,44 % |
| 1° de longitude no Equador | 111,195 | 111,319 | −0,12 km | −0,11 % |
| 1° de latitude a 60° N | 111,195 | 111,421 | −0,23 km | −0,20 % |

- **O erro relativo ficou abaixo de 0,5 % em todos os pares**, dentro do esperado para a aproximação esférica.
- **O sinal do erro depende da direção.** Distâncias no sentido norte–sul em latitudes baixas são superestimadas, e graus de latitude em latitudes altas são subestimados, porque o elipsoide é achatado nos polos.
- **Em raios de poucos quilômetros, o erro absoluto é de metros.** Para as cercas virtuais típicas da API (padrão de 5 km), o modelo esférico é suficiente.

### Caracterização

**Tabela 3.** Comparação do comportamento antes e depois da reescrita.

| Grupo de verificações | Qtd. | Resultado |
|-----------------------|-----:|-----------|
| Autenticação (sem chave, chave inválida, operador em rota administrativa) | 5 | idêntico |
| Emissão de chaves (sucesso, papel personalizado, campo obrigatório ausente) | 3 | idêntico |
| Cálculo unitário por operador (dentro e fora do raio, raio zero, coordenadas inválidas, corpo malformado) | 8 | idêntico |
| Lote por operador (CSV válido, raio padrão, linhas inválidas, colunas ausentes, UTF-8 inválido, origem inválida, arquivo ausente) | 9 | 8 idênticos, 1 corrigido |
| Chave `COMMAND` em `/calculate` e `/calculate/batch` | 2 | corrigidos (500 → 200) |
| Relatório de auditoria | 1 | corrigido (lotes contados uma vez) |
| Schema OpenAPI | 1 | **idêntico** |
| Conteúdo do log | 1 | corrigido (uma linha por lote) |
| **Total** | **30** | **25 idênticos, 5 correções intencionais** |

O schema OpenAPI idêntico garante que clientes existentes continuam compatíveis: rotas, parâmetros, corpos e nomes de schema não mudaram.

### Testes automatizados

A suíte tem **37 testes**, que rodam em menos de 1 segundo e a cada *push* no GitHub Actions:

| Arquivo | Camada | Cobre |
|---------|--------|-------|
| `tests/test_domain.py` | domínio | distância nula, simetria, 1° no Equador, antípodas, conversão de unidade, limites de coordenadas, borda do raio |
| `tests/test_application.py` | aplicação | autenticação, emissão e expiração de chaves, análise unitária e em lote, parser de auditoria (inclusive o formato antigo) |
| `tests/test_api.py` | HTTP | status e corpo de cada endpoint, permissões, CSVs inválidos, persistência do log, contagem da auditoria |

## Revisão da versão original

A primeira versão está no commit [`a649a4f`](../../tree/a649a4f). A caracterização revelou os problemas abaixo.

**Tabela 4.** Problemas encontrados e correções.

| # | Problema | Impacto | Correção |
|---|----------|---------|----------|
| 1 | A chave `COMMAND` não tem dono, e as rotas de cálculo liam `user['owner']` | `/calculate` e `/calculate/batch` retornavam **500** para o administrador, inclusive no tratamento do erro | O agente sem dono é registrado como `MASTER_SYSTEM`, o mesmo nome já usado na emissão de chaves |
| 2 | Cada lote era registrado **duas vezes** no log, com nomes de agente diferentes (`Agent-07` e `OPERATOR (Agent-07)`) | Em 5 lotes, a auditoria reportava 10 operações de lote, divididas entre dois "agentes" | Uma única linha por lote, com agente, papel, origem, total e violações |
| 3 | Uma linha incompleta no CSV gerava `TypeError`, que não era tratado | O lote inteiro era rejeitado, embora a documentação dissesse que linhas inválidas são ignoradas | `TypeError` passa a ser tratado como linha inválida |
| 4 | Os testes da API esperavam um campo `role_access` inexistente e omitiam o campo obrigatório `owner_name` | A suíte falhava; os testes também dependiam de um `.env` local e escreviam no log real | Testes reescritos contra o contrato real, com app, chave e log isolados por teste |
| 5 | `requirements.txt` estava em UTF-16 e sem versão para `python-multipart` | Frágil fora do pip (editores, ferramentas de análise); build não reprodutível | Arquivo em UTF-8 com todas as versões fixadas |
| 6 | `.dockerignore` não excluía `.venv/` nem `.git/` | Ambiente virtual e histórico copiados para a imagem | Exclusões adicionadas; `build-essential` removido da imagem, pois nenhuma dependência compila código nativo |
| 7 | Estado global no import (log, chaves) e regras de permissão dentro das rotas | Impossível testar instâncias isoladas; regra de negócio acoplada ao FastAPI | Fábrica `create_app(settings)`, portas e casos de uso com as regras de autorização |

## Discussão

**1. O modelo esférico é adequado ao uso, mas a decisão na borda pode mudar.** Um erro de 0,2 % em um raio de 5 km equivale a cerca de 10 m. Para alvos a poucos metros da borda, a diferença entre esfera e elipsoide pode inverter a classificação "dentro/fora". Aplicações que exigem essa precisão, como limites legais ou fronteiras, devem usar a solução elipsoidal.

**2. Um teste pode validar o modelo em vez da realidade.** O teste herdado da versão original chama a faixa de 870–875 km de "distância conhecida" entre São Paulo e Brasília. A geodésica WGS-84 dá 868,5 km, fora dessa faixa. O teste é útil como teste de regressão do modelo esférico, mas não prova que a distância está correta. A Tabela 2 separa essas duas perguntas.

**3. Preservar o contrato exigiu preservar imperfeições.** Pontos continuam sendo recebidos como dicionários livres, então uma latitude em texto gera 400 com a mensagem interna do Python, e não 422 com a validação do Pydantic. Tipar esses campos seria melhor, mas mudaria respostas e schema. A reescrita manteve o contrato e registrou a melhoria como trabalho futuro.

**4. O log em texto é, ao mesmo tempo, a trilha de auditoria e o banco de dados do relatório.** Isso funciona, mas acopla o relatório ao formato das mensagens: foi exatamente o que tornou o defeito 2 invisível. Por isso, o formato das linhas agora é produzido em um único lugar por tipo de operação, e o parser tem testes próprios.

## Conclusões

- A separação em camadas isolou as regras geoespaciais e de autorização de FastAPI, arquivos e ambiente: o domínio e os casos de uso são testados sem servidor HTTP.
- Registrar o comportamento **antes** de refatorar transformou "não mudou nada" em uma afirmação verificável: 25 de 30 verificações idênticas, schema OpenAPI incluído.
- A mesma caracterização expôs três defeitos que a suíte original não detectava, porque ela nem chegava a passar.
- A fórmula de Haversine erra menos de 0,5 % nos casos testados. Para cercas virtuais de quilômetros o erro é de metros, e a escolha do modelo deve considerar o quão perto da borda estão os alvos.

## Trabalhos futuros

Segurança e controle de acesso (OWASP, 2023):

- **Aplicar a expiração das chaves:** o campo `expires_at` é gravado, mas ainda não é verificado na autenticação.
- **Restringir os papéis** a um conjunto fechado (hoje qualquer texto é aceito) e **guardar apenas o hash** das chaves.
- **Persistir as chaves** em banco de dados: hoje elas ficam em memória e se perdem quando o serviço reinicia.

Precisão e contrato da API:

- **Modo elipsoidal** (Vincenty, 1975; Karney, 2013) como opção por requisição, ao lado do Haversine.
- **Schemas tipados** para os pontos, com erros 422 descritivos, em uma versão 2 da API.
- **Log estruturado** (JSON Lines) para que o relatório de auditoria não dependa de parsing de texto.

## Como executar

```bash
cp .env.example .env            # defina API_KEY_COMMAND
docker compose up --build       # API em http://localhost:8000 (documentação em /docs)

# ou localmente, com Python 3.11+:
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
pytest                          # suíte de testes
```

Todas as rotas exigem o cabeçalho `X-API-KEY`.

| Método e rota | Acesso | O que faz |
|---------------|--------|-----------|
| `POST /calculate` | qualquer chave | Distância e violação de perímetro entre `origin` e `target`. |
| `POST /calculate/batch` | qualquer chave | Mesmo cálculo para cada linha de um CSV (`lat`, `lon`, `radius` e `file` em *multipart*). |
| `POST /admin/generate-key` | `COMMAND` | Emite uma chave com `role`, `owner_name` e `expires_in_days`. |
| `GET /admin/stats` | `COMMAND` | Relatório de auditoria: totais globais e por agente. |

```bash
curl -X POST http://localhost:8000/calculate \
  -H "X-API-KEY: $API_KEY_COMMAND" -H "Content-Type: application/json" \
  -d '{"origin":{"lat":-15.7942,"lon":-47.8822},"target":{"lat":-15.8010,"lon":-47.8920},"radius":5.0}'
# {"status":"success","agent":"MASTER_SYSTEM","data":{"distance_km":1.29,"alert":true,"message":"WARNING: Perimeter Violated!"}}

curl -X POST http://localhost:8000/calculate/batch -H "X-API-KEY: $API_KEY_COMMAND" \
  -F lat=-23.5505 -F lon=-46.6333 -F radius=5.0 -F file=@targets.csv
```

## Estrutura do repositório

```
├── src/
│   ├── domain/              # Coordinate, HaversineEngine, Credential (sem dependências externas)
│   ├── application/         # casos de uso: geo_analysis, access_control, audit_report + portas
│   ├── infrastructure/      # adaptadores: config (.env), credential_store, audit_log
│   ├── api/                 # FastAPI: app, dependências, schemas, rotas geo e admin
│   ├── bootstrap.py         # raiz de composição (liga adaptadores aos casos de uso)
│   └── main.py              # entrada ASGI: uvicorn src.main:app
├── tests/                   # testes por camada: domínio, aplicação e HTTP
├── .github/workflows/       # CI: pytest a cada push
├── targets.csv              # alvos de exemplo para o endpoint em lote
├── Dockerfile · docker-compose.yml
└── data/                    # operation.log (gerado, não versionado)
```

## Referências

- COCKBURN, A. *Hexagonal architecture*. 2005. Disponível em: https://alistair.cockburn.us/hexagonal-architecture/.
- FEATHERS, M. *Working Effectively with Legacy Code*. Upper Saddle River: Prentice Hall, 2004.
- KARNEY, C. F. F. Algorithms for geodesics. *Journal of Geodesy*, v. 87, n. 1, p. 43–55, 2013.
- MARTIN, R. C. *Clean Architecture: a craftsman's guide to software structure and design*. Boston: Prentice Hall, 2017.
- MORITZ, H. Geodetic Reference System 1980. *Journal of Geodesy*, v. 74, n. 1, p. 128–133, 2000.
- OWASP FOUNDATION. *OWASP API Security Top 10 – 2023*. 2023. Disponível em: https://owasp.org/API-Security/.
- SINNOTT, R. W. Virtues of the Haversine. *Sky and Telescope*, v. 68, n. 2, p. 159, 1984.
- VINCENTY, T. Direct and inverse solutions of geodesics on the ellipsoid with application of nested equations. *Survey Review*, v. 23, n. 176, p. 88–93, 1975.

---

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE).
