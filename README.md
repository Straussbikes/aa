# Mobify - Loja de Móveis Online

Projeto demo de e-commerce estilo IKEA com:

- Catálogo de móveis com filtros por pesquisa/categoria
- Página de detalhe de produto
- Registo/login de utilizadores
- Painel de administração para gerir móveis
- Base de dados SQLite para metadados de móveis e users/admin

## 1) Upload do código para o teu Git (GitHub/GitLab/Bitbucket)

No teu terminal (dentro deste projeto), cria um repositório remoto e faz push:

```bash
git remote add origin <URL_DO_TEU_REPO>
git branch -M main
git push -u origin main
```

> Exemplo de URL: `git@github.com:teu-user/mobify.git` ou `https://github.com/teu-user/mobify.git`

## 2) Como abrir na tua máquina (via Git)

Depois de fazeres push, na tua máquina local:

```bash
git clone <URL_DO_TEU_REPO>
cd <NOME_DA_PASTA>
```

### Opção A — Correr com Python (venv)

```bash
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows PowerShell
pip install -r requirements.txt
python app.py
```

A aplicação arranca em `http://localhost:5000`.

### Opção B — Correr com Docker (recomendado para evitar problemas de ambiente)

```bash
docker compose up --build
```

A app ficará disponível em `http://localhost:5000`.

## Utilizador admin inicial

- Email: `admin@mobify.pt`
- Password: `admin123`

## Estrutura da base de dados

Definida em `schema.sql` com duas tabelas principais:

- `users`: `name`, `email`, `password_hash`, `role` (`user`/`admin`)
- `furniture`: nome, categoria, descrição, preço, stock, imagem e metadados
