# Superpowers Kit

Небольшая публичная коллекция воспроизводимых скиллов для Codex и Claude Code.

## Скиллы

- `skill-audit` — проверяет сторонний скилл перед установкой, не запуская его код.
- `agent-dev-setup` — готовит рабочее окружение для уже установленного Codex или Claude Code.
- `obsidian-git-knowledge-base` — создаёт базу знаний в Obsidian с Git и GitHub.
- `hermes-vps-deploy` — разворачивает личного Hermes-бота с Telegram на VPS.
- `telegram-telethon-connect` — подключает личный Telegram через Telethon: QR или код, 2FA и безопасная read-only проверка.

Все пять скиллов можно запускать из Codex и Claude Code. У Hermes провайдер модели в данном сценарии — только ChatGPT/Codex OAuth; Claude Code используется как агент, выполняющий раскатку.

## Быстрая установка

Каждая строка устанавливает весь набор из пяти скиллов. После установки
откройте новую сессию агента.

**Codex:**

```bash
codex plugin marketplace add brenao777/superpowers-kit --ref main && codex plugin add superpowers-kit@superpowers-kit
```

**Claude Code:**

```bash
claude plugin marketplace add brenao777/superpowers-kit && claude plugin install superpowers-kit@superpowers-kit
```

## Безопасность

- Секреты не передаются в чат и не попадают в отчёты.
- Любое внешнее изменение предваряется кратким объяснением.
- Hermes не отключает парольный SSH-доступ, пока вход по ключу не проверен отдельно.
- Telegram-сессия, `api_hash`, коды входа и 2FA остаются только локально и исключены из Git.

## Структура

Плагин лежит в `plugins/superpowers-kit/skills/`. В корне есть marketplace-манифесты для Codex и Claude Code.
