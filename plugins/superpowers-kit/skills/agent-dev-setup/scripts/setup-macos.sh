#!/usr/bin/env bash

set -u

ACTION="${1:-}"
COMPONENT="${2:-}"

ids=(homebrew git node python uv ripgrep jq curl docker gh pnpm yarn bun ffmpeg go deno)

label() {
  case "$1" in
    homebrew) echo "Homebrew" ;;
    git) echo "Git" ;;
    node) echo "Node.js и npm" ;;
    python) echo "Python" ;;
    uv) echo "uv" ;;
    ripgrep) echo "ripgrep (rg)" ;;
    jq) echo "jq" ;;
    curl) echo "curl" ;;
    docker) echo "Docker Desktop" ;;
    gh) echo "GitHub CLI" ;;
    pnpm) echo "pnpm" ;;
    yarn) echo "Yarn" ;;
    bun) echo "Bun" ;;
    ffmpeg) echo "FFmpeg" ;;
    go) echo "Go" ;;
    deno) echo "Deno" ;;
    *) echo "$1" ;;
  esac
}

category() {
  case "$1" in
    homebrew|git|node|python|uv|ripgrep|jq|curl) echo "базовый" ;;
    *) echo "расширенный" ;;
  esac
}

command_for() {
  case "$1" in
    homebrew) echo "brew" ;;
    git) echo "git" ;;
    node) echo "node" ;;
    python) echo "python3" ;;
    uv) echo "uv" ;;
    ripgrep) echo "rg" ;;
    jq) echo "jq" ;;
    curl) echo "curl" ;;
    docker) echo "docker" ;;
    gh) echo "gh" ;;
    pnpm) echo "pnpm" ;;
    yarn) echo "yarn" ;;
    bun) echo "bun" ;;
    ffmpeg) echo "ffmpeg" ;;
    go) echo "go" ;;
    deno) echo "deno" ;;
  esac
}

brew_bin() {
  if command -v brew >/dev/null 2>&1; then
    command -v brew
  elif [ -x /opt/homebrew/bin/brew ]; then
    echo /opt/homebrew/bin/brew
  elif [ -x /usr/local/bin/brew ]; then
    echo /usr/local/bin/brew
  else
    return 1
  fi
}

is_known() {
  local wanted="$1"
  local item
  for item in "${ids[@]}"; do
    [ "$item" = "$wanted" ] && return 0
  done
  return 1
}

is_ready() {
  local id="$1"
  local cmd
  case "$id" in
    homebrew) brew_bin >/dev/null 2>&1 ;;
    node) command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1 ;;
    docker)
      command -v docker >/dev/null 2>&1 || [ -d /Applications/Docker.app ] || [ -d "$HOME/Applications/Docker.app" ]
      ;;
    *)
      cmd="$(command_for "$id")"
      command -v "$cmd" >/dev/null 2>&1
      ;;
  esac
}

version_text() {
  local id="$1"
  local cmd
  case "$id" in
    homebrew) "$(brew_bin)" --version 2>/dev/null | head -n 1 ;;
    node) node --version 2>/dev/null ;;
    python) python3 --version 2>/dev/null ;;
    ffmpeg) ffmpeg -version 2>/dev/null | head -n 1 ;;
    go) go version 2>/dev/null ;;
    docker)
      if command -v docker >/dev/null 2>&1; then docker --version 2>/dev/null; else echo "приложение установлено, нужен первый запуск"; fi
      ;;
    *)
      cmd="$(command_for "$id")"
      "$cmd" --version 2>/dev/null | head -n 1
      ;;
  esac
}

hint_for() {
  case "$1" in
    homebrew) echo "Повторите установку Homebrew и выполните подсказку brew shellenv, которую покажет установщик." ;;
    pnpm|yarn) echo "Проверьте Node.js и npm, перезапустите терминал и повторите этап без sudo npm." ;;
    docker) echo "Откройте Docker Desktop, пройдите первый запуск и дождитесь, когда приложение будет готово." ;;
    *) echo "Проверьте интернет и Homebrew, затем выполните brew update и повторите этот этап." ;;
  esac
}

install_homebrew() {
  if ! command -v curl >/dev/null 2>&1; then
    echo "В macOS не найден curl, поэтому официальный установщик Homebrew нельзя загрузить."
    return 20
  fi
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
}

install_with_brew() {
  local formula="$1"
  local brew
  brew="$(brew_bin)" || {
    echo "Сначала требуется Homebrew."
    return 20
  }
  "$brew" install "$formula"
}

install_component() {
  local id="$1"
  case "$id" in
    homebrew) install_homebrew ;;
    git) install_with_brew git ;;
    node) install_with_brew node ;;
    python) install_with_brew python ;;
    uv) install_with_brew uv ;;
    ripgrep) install_with_brew ripgrep ;;
    jq) install_with_brew jq ;;
    curl) install_with_brew curl ;;
    docker)
      local brew
      brew="$(brew_bin)" || { echo "Сначала требуется Homebrew."; return 20; }
      "$brew" install --cask docker
      ;;
    gh) install_with_brew gh ;;
    pnpm|yarn)
      if ! command -v npm >/dev/null 2>&1; then echo "Сначала требуется Node.js и npm."; return 20; fi
      npm install -g "$id"
      ;;
    bun) install_with_brew bun ;;
    ffmpeg) install_with_brew ffmpeg ;;
    go) install_with_brew go ;;
    deno) install_with_brew deno ;;
  esac
}

print_list() {
  local id
  printf '%-12s %-23s %s\n' "ID" "ИНСТРУМЕНТ" "ГРУППА"
  for id in "${ids[@]}"; do
    printf '%-12s %-23s %s\n' "$id" "$(label "$id")" "$(category "$id")"
  done
}

print_check() {
  local id="$1"
  if is_ready "$id"; then
    echo "READY|$id|$(label "$id")|$(version_text "$id")"
    return 0
  fi
  echo "MISSING|$id|$(label "$id")|$(hint_for "$id")"
  return 10
}

print_summary() {
  local id
  local missing=0
  printf '%-23s %-16s %s\n' "ИНСТРУМЕНТ" "СТАТУС" "ПОДРОБНОСТИ"
  for id in "${ids[@]}"; do
    if is_ready "$id"; then
      printf '%-23s %-16s %s\n' "$(label "$id")" "готово" "$(version_text "$id")"
    else
      printf '%-23s %-16s %s\n' "$(label "$id")" "требует внимания" "$(hint_for "$id")"
      missing=$((missing + 1))
    fi
  done
  [ "$missing" -eq 0 ] && return 0
  return 10
}

if [ "$(uname -s 2>/dev/null)" != "Darwin" ]; then
  echo "Этот сценарий предназначен только для macOS."
  exit 20
fi

case "$ACTION" in
  list) print_list ;;
  check)
    is_known "$COMPONENT" || { echo "Неизвестный компонент: $COMPONENT"; exit 20; }
    print_check "$COMPONENT"
    exit $?
    ;;
  install)
    is_known "$COMPONENT" || { echo "Неизвестный компонент: $COMPONENT"; exit 20; }
    if is_ready "$COMPONENT"; then
      echo "SKIPPED|$COMPONENT|$(label "$COMPONENT")|уже установлено"
      exit 0
    fi
    echo "INSTALLING|$COMPONENT|$(label "$COMPONENT")"
    install_component "$COMPONENT"
    result=$?
    if [ "$result" -ne 0 ]; then
      echo "FAILED|$COMPONENT|$(label "$COMPONENT")|$(hint_for "$COMPONENT")"
      exit 20
    fi
    print_check "$COMPONENT"
    result=$?
    if [ "$result" -ne 0 ]; then
      echo "ACTION_REQUIRED|$COMPONENT|$(label "$COMPONENT")|Перезапустите терминал или выполните ручной шаг из подсказки."
      exit 30
    fi
    ;;
  summary) print_summary; exit $? ;;
  *)
    echo "Использование: $0 {list|check <id>|install <id>|summary}"
    exit 20
    ;;
esac
