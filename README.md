# Superpowers Kit

Небольшая публичная коллекция воспроизводимых скиллов для Codex и Claude Code.

## Скиллы

- `agent-dev-setup` — проверяет и поэтапно готовит окружение вокруг уже установленного Codex или Claude Code на macOS и Windows;
- `obsidian-git-knowledge-base` — создаёт и ведёт Obsidian vault как Markdown-базу знаний с Git, GitHub, `AGENTS.md` и `CLAUDE.md`;
- `hermes-vps-deploy` — разворачивает или обновляет Hermes на Ubuntu/Debian VPS, подключает Telegram и модель через ChatGPT/Codex OAuth.

Все три скилла можно запускать из Codex и Claude Code. У Hermes провайдер модели в данном сценарии — только ChatGPT/Codex OAuth; Claude Code используется как агент, выполняющий раскатку.

## Безопасность

- Секреты не передаются в чат и не попадают в отчёты.
- Любое внешнее изменение предваряется кратким объяснением.
- Hermes не отключает парольный SSH-доступ, пока вход по ключу не проверен отдельно.
- Перед публикацией репозитория выберите и добавьте лицензию.

## Структура

Плагин лежит в `plugins/superpowers-kit/skills/`. В корне есть marketplace-манифесты для Codex и Claude Code.
