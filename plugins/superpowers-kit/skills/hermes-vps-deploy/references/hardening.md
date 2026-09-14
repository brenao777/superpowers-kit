# Базовый хардненинг VPS

Сначала обеспечь и проверь ключевой доступ оператору. Только затем меняй SSH и firewall.

## 1. SSH-ключ оператора

На локальной машине найди подходящий существующий публичный ключ. Не перезаписывай существующий приватный ключ. Если ключей нет, создай отдельную пару для этого VPS и сообщи пользователю путь и необходимость резервной копии.

Добавь публичный ключ в `~/.ssh/authorized_keys` административного SSH-пользователя идемпотентно. Выставь `700` на `.ssh` и `600` на `authorized_keys`.

## 2. Независимая проверка

Из новой SSH-сессии запрети парольный fallback и потребуй явный ключ:

```bash
ssh -i <PRIVATE_KEY> \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no \
  -o IdentitiesOnly=yes \
  <SSH_USER>@<VPS_IP> 'echo KEY_OK'
```

Если ответ не `KEY_OK`, остановись. Не включай UFW и не отключай пароль.

## 3. Firewall

До включения firewall разреши фактический SSH-порт. Не предполагай порт 22: узнай его через эффективную конфигурацию sshd или текущую SSH-сессию.

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow <SSH_PORT>/tcp
ufw --force enable
ufw status verbose
```

## 4. fail2ban

Создай отдельный drop-in `/etc/fail2ban/jail.d/sshd.local`, не заменяя чужой `jail.local`:

```ini
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
```

Проверь конфигурацию доступной в установленной версии командой, затем включи сервис и проверь jail `sshd`.

## 5. Отключение пароля

Сначала посмотри эффективную конфигурацию и все drop-in:

```bash
sshd -T | grep -Ei 'passwordauthentication|kbdinteractiveauthentication|permitrootlogin|port'
grep -RnsE '^[[:space:]]*(PasswordAuthentication|KbdInteractiveAuthentication|PermitRootLogin)' \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d 2>/dev/null || true
```

Создай управляемый drop-in с ранним именем, не редактируя cloud-init файл без необходимости. Если административный вход выполняется напрямую как `root`, оставь ключевой вход через `PermitRootLogin prohibit-password`. Если используется отдельный sudo-пользователь и его ключ уже проверен, установи более строгий `PermitRootLogin no`:

```text
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
```

На Ubuntu учитывай порядок обработки: первое полученное значение параметра может победить. Проверь итог через `sshd -T`. Если ранний drop-in не дает ожидаемого результата, выясни порядок include и конфликтующие значения; не применяй случайный `sed` к файлам провайдера.

Перед reload/restart выполни `sshd -t`. Сохраняй текущую SSH-сессию открытой, перезагрузи конфигурацию и еще раз проверь вход отдельной сессией по ключу.

## 6. Финал

Подтверди:

- вход по ключу работает;
- парольный вход отклонен;
- UFW active и разрешает фактический SSH-порт;
- jail `sshd` активен;
- gateway Hermes остается активным и отвечает после изменений.

Если доступ потерян, используй только веб-консоль/VNC провайдера. Не маскируй локаут как успешную установку.
