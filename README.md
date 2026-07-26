# 🤖 AI Startup — Telegram Bot с командой AI-агентов

> Собственный AI-стартап: Telegram-бот, который сам пишет код, создаёт сайты, ботов, SaaS, деплоит их и помнит всё, что ты делал.

## ✨ Возможности

- 🧠 **Команда AI-агентов**: orchestrator, planner, coder, analyst, searcher, tester, deployer, memory
- 🏗 **Создаёт**: сайты, Telegram-ботов, SaaS, утилиты, скрипты
- 💾 **Память**: долговременная через Postgres + Vector + Obsidian vault
- 🚀 **Деплой**: GitHub + Cloudflare (Pages, Workers, R2, Workers AI)
- 🔁 **Параллельные задачи** с семафором
- 👥 **Роли и подписки** (Free / Pro / Team / Business)
- 🛠 **Админ-панель** с рассылками, бэкапами, логами
- 🔐 **Безопасность**: rate limit, JWT, Fernet-шифрование, RBAC
- 🤖 **Open-source модели**: легко подменить OpenAI на Ollama (llama, qwen, mistral) или Cloudflare Workers AI
- 📡 **MCP-сервер** для интеграции с Claude Desktop и другими клиентами

## 🏗 Архитектура

```
ai-startup/
├── bot/                  # Telegram-бот (aiogram 3)
│   ├── handlers/         # commands, callbacks, FSM
│   ├── keyboards/        # inline + reply
│   ├── middlewares/      # auth, admin
│   └── states/           # FSM-состояния
├── agents/               # Команда AI-агентов
│   ├── base/             # BaseAgent, AgentState
│   ├── orchestrator/     # главный диспетчер + task queue
│   ├── specialists/      # 7 агентов
│   └── tools/            # tools для агентов
├── memory/               # долговременная память
│   ├── supabase/         # Supabase SDK
│   ├── obsidian/         # Obsidian vault (markdown)
│   ├── vector/           # ChromaDB embeddings
│   └── manager.py        # unified API
├── services/             # внешние интеграции
│   ├── llm/              # OpenAI / Ollama / Cloudflare
│   ├── cloudflare/       # Pages, Workers, R2, Workers AI
│   ├── github/           # repos, push code
│   ├── mcp/              # MCP-сервер
│   ├── security/         # JWT, bcrypt, Fernet
│   ├── backup/           # pg_dump + tar
│   ├── notifications/    # push, webhooks
│   └── subscription/     # plans, limits
├── db/                   # SQLAlchemy async
│   ├── models/           # User, Project, Task, Memory, ...
│   ├── repositories/     # CRUD
│   └── migrations/       # Alembic
├── workers/              # фоновые сервисы
│   ├── cloudflare/       # Cloudflare Worker
│   └── mcp_server/       # standalone MCP
├── config/               # settings + logging
├── docker/               # Docker
├── tests/                # pytest
└── main.py               # entry point
```

## 🚀 Быстрый старт

### 1. Клонируй и настрой

```bash
git clone <your-repo> ai-startup
cd ai-startup
cp .env.example .env
nano .env   # укажи TELEGRAM_BOT_TOKEN, DATABASE_URL и т.д.
```

### 2. Запуск через Docker (рекомендуется)

```bash
docker-compose up -d
docker-compose logs -f bot
```

Поднимет: Postgres, Redis, бот, scheduler (бэкапы, сброс лимитов), MCP-сервер.

### 3. Локальный запуск

```bash
bash scripts/dev.sh              # создаст venv, установит deps
source .venv/bin/activate
alembic upgrade head              # миграции БД
python main.py                    # polling mode
```

### 4. Альтернативные режимы

```bash
python main.py --mode webhook --webhook-url https://your.domain/webhook
python main.py --mode scheduler
python main.py --mode mcp
```

## 🧠 Команда агентов

| Агент | Что делает |
|---|---|
| **Orchestrator** | Главный диспетчер. Получает задачу, решает, какого агента звать, ведёт state |
| **Planner** | Разбивает цель на 3-12 атомарных шагов с зависимостями |
| **Coder** | Пишет/правит код, создаёт файлы, запускает тесты |
| **Analyst** | Анализирует требования, данные, код, выдаёт рекомендации |
| **Searcher** | Ищет в интернете через DuckDuckGo, фетчит и суммирует страницы |
| **Tester** | Пишет и запускает тесты (pytest) |
| **Deployer** | Пушит код в GitHub, деплоит на Cloudflare Pages/Workers |
| **Memory** | Решает что запомнить, расставляет важность |

Поток задачи:
```
User → Orchestrator → Planner → Coder → Tester → Deployer → Memory → done
                 ↘ Searcher (если нужна инфа) ↗
                 ↘ Analyst (если сложный вопрос) ↗
```

## 🤖 Выбор LLM

В `.env`:
```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Self-hosted Ollama (бесплатно, локально)
USE_SELF_HOSTED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:70b

# Cloudflare Workers AI
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...
```

Поддерживается любой OpenAI-compatible endpoint (Together, Groq, vLLM, llama.cpp).

## 💎 Подписки

| План | Токены/мес | Проекты | Параллельных задач |
|---|---|---|---|
| 🆓 Free | 100K | 3 | 1 |
| ⚡ Pro ($19) | 5M | 20 | 3 |
| 👥 Team ($49) | 20M | 100 | 10 |
| 🏢 Business ($199) | ∞ | ∞ | 50 |

## 🗄 Долговременная память

Три уровня:
1. **PostgreSQL** (через Supabase) — структурированные записи с метаданными
2. **ChromaDB** — векторный поиск по семантике
3. **Obsidian** — markdown-файлы в vault, которые ты можешь читать и редактировать сам

Агент автоматически запоминает: предпочтения пользователя, проектные решения, удачные паттерны кода.

## 🔌 MCP

Запусти MCP-сервер: `python main.py --mode mcp` (порт 8765).

Подключай из Claude Desktop или Cursor:
```json
{
  "mcpServers": {
    "ai-startup": {
      "url": "ws://localhost:8765"
    }
  }
}
```

Доступные tools: `web_search`, `fetch_url`, `write_file`, `read_file`, `run_python`, `run_shell`, `search_and_summarize`.

## ☁️ Cloudflare Worker

Деплой AI-гейтвея:
```bash
cd workers/cloudflare
wrangler deploy
```

Воркер проксирует Telegram-webhook и предоставляет `/ai` endpoint на Workers AI.

## 🔐 Безопасность

- **JWT** для API-доступа
- **Fernet-шифрование** секретов
- **bcrypt** для паролей
- **Rate limiting** per user
- **RBAC** (user / pro / team / admin / owner)
- **Audit log** всех действий

## 📊 Мониторинг

- Логи: `logs/app.log` (с ротацией), `logs/errors.log`
- Метрики: `AgentRun` хранит токены, длительность, статус каждого вызова
- Админ-команды: `/admin`, статистика, рассылка, бэкап одной кнопкой

## 🧪 Тесты

```bash
pytest -v
```

## 📜 Лицензия

MIT. Делай что хочешь.

---

**Главное**: бот работает 24/7, сам выбирает нужного агента, сам деплоит, сам помнит. Просто напиши ему, что хочешь сделать.
