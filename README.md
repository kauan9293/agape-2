# Confeitaria Ágape Artesanal

Loja responsiva em português com catálogo, encomendas, API FastAPI, PostgreSQL, painel administrativo autenticado e armazenamento persistente de imagens.

## Arquitetura

- **Frontend:** React 18 + TypeScript + Vite; o estado da sacola fica no navegador, sem credenciais administrativas.
- **Backend:** FastAPI + Pydantic + SQLAlchemy 2.0; valida, autoriza e calcula os pedidos no servidor.
- **Dados:** PostgreSQL em produção/Compose e SQLite para desenvolvimento local simples; migrações Alembic.
- **Sessões:** cookies aleatórios HttpOnly, token CSRF em mutações, senha Argon2 e limite de tentativas de login.
- **Imagens:** uploads validados, redimensionados e convertidos para WebP em volume persistente local. Em operação com múltiplas instâncias, trocar o volume por armazenamento de objetos privado (S3 compatível) e CDN.
- O checkout registra uma **solicitação pendente**; não processa pagamento. WhatsApp só é oferecido quando `BUSINESS_WHATSAPP` estiver configurado.

## Executar localmente (Windows / PowerShell)

Requisitos: Node.js 20+, Python 3.11+ e npm.

```powershell
Copy-Item .env.example .env
Set-Location backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "sqlite:///./agape.db"
alembic upgrade head
python -m app.cli seed-demo
python -m app.cli create-admin
uvicorn app.main:app --reload --port 8000
```

Em outro terminal, na raiz do projeto:

```powershell
Set-Location frontend
npm install
npm run dev
```

A loja fica em `http://localhost:5173`, o painel em `/admin` e a documentação interativa da API em `http://localhost:8000/docs`. O proxy do Vite encaminha `/api` e `/media` ao backend.

Para criar o administrador, informe o e-mail no terminal e digite uma senha com pelo menos 12 caracteres quando solicitado. A senha é lida sem eco, armazenada com Argon2 e nunca fica no código ou no navegador. Crie a conta só depois de aplicar as migrações. Não há credencial padrão.

Se esquecer a senha, execute `py -3 -m app.cli reset-admin-password` dentro de `backend`, informe o e-mail da conta e cadastre uma nova senha. As sessões anteriores serão encerradas.

## PostgreSQL com Docker

Copie `.env.example` para `.env`, troque `POSTGRES_PASSWORD` por uma senha exclusiva e confira `DATABASE_URL`/`CORS_ORIGINS`. Depois, na raiz:

```powershell
docker compose up --build -d
docker compose exec app python -m app.cli seed-demo
docker compose exec app python -m app.cli create-admin
```

A aplicação fica em `http://localhost:8000`. Os dados PostgreSQL e as imagens usam volumes nomeados. Para produção, use HTTPS atrás de proxy confiável, configure `COOKIE_SECURE=true`, `APP_ENV=production`, `CORS_ORIGINS` apenas com o domínio da loja e segredos exclusivos via gerenciador de segredos. Faça backup dos dois volumes. Não publique o banco nem o endpoint de administração diretamente na internet sem TLS e controles de rede.

## Deploy no Vercel

O arquivo `vercel.json` configura os serviços `backend` (FastAPI) e `frontend` (Vite) no mesmo projeto. As rotas `/api/*` e `/media/*` são encaminhadas ao backend; as demais rotas, incluindo as páginas do React Router, são encaminhadas ao frontend e reescritas para `index.html` dentro do serviço. O navegador chama `/api` no mesmo domínio, então não é necessário definir `VITE_API_URL` nem um binding entre esses serviços.

Configure no ambiente do serviço backend as variáveis de produção necessárias, incluindo `DATABASE_URL` apontando para um PostgreSQL acessível pelo Vercel, `SECRET_KEY` exclusiva, `COOKIE_SECURE=true`, `APP_ENV=production` e `CORS_ORIGINS` com as origens reais da loja. Não use valores de desenvolvimento em produção.

URLs PostgreSQL padrão como `postgresql://` ou `postgres://` são adaptadas automaticamente ao driver psycopg 3 usado pelo projeto.

Antes de usar a aplicação, aplique as migrações no mesmo banco indicado por `DATABASE_URL`, executando `alembic upgrade head` dentro de `backend`. As tabelas não são criadas automaticamente pela função do Vercel. Depois, crie a conta administrativa nesse banco com `python -m app.cli create-admin`; não existe senha padrão. Mantenha a URL e as credenciais fora do repositório.

No Vercel, os uploads usam `/tmp/uploads`, que é gravável pela função mas temporário e não persistente entre execuções. Antes de usar uploads administrativos em produção, configure armazenamento de objetos persistente compatível e adapte o backend para gravar e servir imagens por esse armazenamento. O banco também precisa ser um serviço PostgreSQL externo; o Vercel não provisiona banco ou armazenamento com esta configuração.

## Demonstração

`python -m app.cli seed-demo` insere três categorias e três produtos com **nomes, descrições e preços fictícios**, marcados como demonstração no banco e na loja. As imagens são referências ilustrativas remotas. Edite ou despublique/remova esses itens e envie imagens autorizadas antes de aceitar encomendas reais. O seed pode ser executado mais de uma vez sem duplicar os dados de exemplo.

## Banco e pedidos

As tabelas relacionam `users`, `user_sessions`, `categories`, `products`, `product_images`, `product_variants`, `customers`, `orders`, `order_items` e `order_history`. Valores usam `NUMERIC(10,2)`, restrições de não negatividade/quantidade e índices para busca, disponibilidade e status. Os itens guardam nome, variação e preço unitário no momento do pedido; a FK do produto pode ser removida sem apagar esse registro histórico. Não guardamos cartão de crédito.

Dados de contato são limitados a nome, telefone e e-mail opcional para atender o pedido. Não há conta de cliente nem coleta de endereço separado; em pedidos de entrega, o texto informado fica nos dados do pedido. Defina aviso de privacidade, retenção e processo de exclusão/atendimento LGPD antes da operação comercial.

## API

Todos os corpos e parâmetros são validados pelo Pydantic. Erros de autorização não revelam credenciais.

| Método | Rota | Acesso | Uso |
|---|---|---|---|
| GET | `/api/health` | Público | Saúde da API |
| GET | `/api/storefront-config` | Público | Instagram e antecedência mínima configurada |
| GET | `/api/categories` | Público | Categorias |
| GET | `/api/products?q=&category=&featured=` | Público | Catálogo pesquisável e filtrável |
| GET | `/api/products/{slug}` | Público | Detalhe de produto publicado |
| POST | `/api/orders` | Público | Cria pedido pendente, recalculando preço/estoque no banco |
| GET | `/api/auth/csrf` | Público | Emite token CSRF |
| POST | `/api/auth/login` | Público + CSRF + rate limit | Cria sessão administrativa |
| GET | `/api/auth/me` | Sessão | Identidade da sessão |
| POST | `/api/auth/logout` | Sessão + CSRF | Revoga a sessão |
| GET | `/api/admin/dashboard` | Admin | Indicadores reais e vendas com status pago |
| GET/POST | `/api/admin/categories` | Admin (POST + CSRF) | Listar/criar categorias |
| GET/POST | `/api/admin/products` | Admin (POST + CSRF) | Listar/criar produtos |
| PUT | `/api/admin/products/{id}` | Admin + CSRF | Substituir dados, imagens e variações |
| POST | `/api/admin/products/{id}/archive` | Admin + CSRF | Arquivar e retirar da loja |
| POST | `/api/admin/uploads` | Admin + CSRF | Enviar JPG/PNG/WebP de até 8 MB |
| GET | `/api/admin/orders` | Admin | Consultar pedidos e histórico |
| PATCH | `/api/admin/orders/{id}/status` | Admin + CSRF | Atualizar status com auditoria |

## Testes

```powershell
Set-Location backend
python -m pytest -q
```

Os testes cobrem rejeição de acesso anônimo, CSRF, listagem de produtos publicados, preço calculado no servidor e estoque insuficiente.

## Configurações comerciais pendentes

- Confirmar o telefone `+55 11 93329-3434` e o e-mail `agapeconfeitaria06@gmail.com` em `BUSINESS_WHATSAPP`/`BUSINESS_EMAIL` antes de publicar.
- Confirmação do perfil do Instagram e identidade visual/fotografias autorizadas.
- Produtos reais: nomes, descrições, preços, categorias, fotos, tamanhos/sabores, estoque e itens em destaque.
- Prazo mínimo de encomenda (`MINIMUM_ORDER_NOTICE_HOURS`), disponibilidade de retirada/entrega, regiões, taxas e instruções de entrega.
- Política de confirmação, cancelamento, pagamento, privacidade, retenção e atendimento LGPD.
- Se desejar pagamento online, credenciais e conta de testes de um provedor legítimo; não habilitar antes da integração de webhooks e validação no servidor.
- Domínio, TLS, política de backup e fornecedor de armazenamento de imagens para produção.