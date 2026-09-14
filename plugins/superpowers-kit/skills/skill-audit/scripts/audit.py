#!/usr/bin/env python3
"""Read-only heuristic skill audit. Python 3.9+, standard library only."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

VERSION = '2.0'
EXTENSIONS = {'.md', '.txt', '.sh', '.bash', '.zsh', '.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.json', '.toml', '.yaml', '.yml', '.ps1', '.psm1', '.bat', '.cmd'}
EXCLUDED = {'.git', 'node_modules', '.venv', 'venv', '__pycache__'}
RULES = [
 ('CRITICAL', 'secret-in-network-line', r'(curl|wget|requests\.post|fetch\(|Invoke-(WebRequest|RestMethod)).*(\$[\w:]*(KEY|TOKEN|SECRET|PASSWORD)|\.env|id_rsa|credentials)'),
 ('CRITICAL', 'decoded-code-execution', r'base64.*(-d|--decode).*\|\s*(ba)?sh|exec\(\s*(base64|codecs)'),
 ('CRITICAL', 'reverse-shell', r'\b(nc|ncat|netcat)\s+-[a-z]*e\b|/dev/tcp/'),
 ('HIGH', 'pipe-to-shell', r'(curl|wget)[^|]*\|\s*(sudo\s+)?(ba|z)?sh|\b(iex|Invoke-Expression)\s*\(?\s*(iwr|irm|Invoke-WebRequest|Invoke-RestMethod)'),
 ('HIGH', 'credential-access', r'(~|\$HOME)/\.ssh/|id_rsa|security find-generic-password|\.aws[/\\]credentials|(zsh|bash)_history|login\.keychain|cmdkey\s+/list|Get-StoredCredential'),
 ('HIGH', 'destructive-operation', r'rm\s+-[rf]{2}\s+(/|~|\$HOME)|git\s+push.*--force|DROP\s+(TABLE|DATABASE)|Remove-Item.*-Recurse|\b(rd|rmdir)\s+/s'),
 ('HIGH', 'privilege-escalation', r'\bsudo\s+[a-z]|Start-Process.*-Verb\s+RunAs'),
 ('HIGH', 'agent-permission-change', r'(settings|settings\.local)\.json.*(>|write|json\.dump)|bypassPermissions|allowedTools.*\*|dangerously-skip-permissions'),
 ('HIGH', 'dynamic-shell-eval', r'eval\s*["\x27]?\$\(|\bInvoke-Expression\b|\b(iex)\s+'),
 ('MEDIUM', 'concealment', r"(do not|don't|never)\s+(tell|inform|show|mention|notify|reveal).{0,30}(the\s+)?user|без ведома пользователя|не сообщай пользовател"),
 ('MEDIUM', 'telemetry-candidate', r'(curl|wget|requests\.(get|post)).*(telemetry|analytics|beacon|track).*(\?|=)'),
 ('MEDIUM', 'prompt-injection', r'ignore\s+(all\s+)?(previous|prior|above)\s+instructions|disregard\s+(the\s+)?(system|previous)|you\s+are\s+now\s+in\s+developer\s+mode'),
 ('MEDIUM', 'persistence', r'crontab\s+-|launchctl\s+load|LaunchAgents|systemctl\s+enable|schtasks.*(/create|/change)|Register-ScheduledTask|CurrentVersion\\Run'),
 ('MEDIUM', 'shell-command-boundary', r'shell\s*=\s*True|child_process\.exec\('),
]
COMPILED = [(s, n, re.compile(p, re.I)) for s, n, p in RULES]

def discover(roots, follow, max_bytes):
    files, skipped, errors, seen = {}, [], [], set()
    def visit(path, root):
        try:
            if path.is_symlink() and not follow:
                skipped.append({'path': str(path), 'reason': 'symlink (use --follow-symlinks after checking target)'})
                return
            real = path.resolve(strict=True)
            if real in seen:
                return
            seen.add(real)
            mode = path.stat().st_mode
            if stat.S_ISDIR(mode):
                for child in sorted(path.iterdir()):
                    if child.name in EXCLUDED:
                        skipped.append({'path': str(child), 'reason': 'excluded dependency/cache directory'})
                    else:
                        visit(child, root)
            elif stat.S_ISREG(mode):
                if path.suffix.lower() not in EXTENSIONS and path.name not in {'Makefile', 'Dockerfile'}:
                    skipped.append({'path': str(path), 'reason': 'unsupported extension'})
                    return
                if path.stat().st_size > max_bytes:
                    skipped.append({'path': str(path), 'reason': 'size limit'})
                    return
                data = path.read_bytes()
                if len(data) > max_bytes:
                    raise ValueError('file grew beyond size limit')
                try:
                    text = data.decode('utf-8-sig')
                except UnicodeDecodeError:
                    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
                        text = data.decode('utf-16')
                    else:
                        skipped.append({'path': str(path), 'reason': 'not UTF-8/UTF-16 text'})
                        return
                if '\x00' in text:
                    skipped.append({'path': str(path), 'reason': 'binary content'})
                    return
                files[str(real)] = {'hash': hashlib.sha256(data).hexdigest(), 'text': text}
            else:
                skipped.append({'path': str(path), 'reason': 'not a regular file'})
        except (OSError, ValueError, RuntimeError) as e:
            errors.append({'path': str(path), 'error': str(e)})
    for root in roots:
        visit(root, root)
    return files, skipped, errors

def audit(files, targets):
    hits, domains = [], collections.Counter()
    for path in targets:
        for number, line in enumerate(files[path]['text'].splitlines(), 1):
            for domain in re.findall(r'https?://([a-zA-Z0-9._-]+)', line):
                domains[domain.lower()] += 1
            for severity, rule, pattern in COMPILED:
                if pattern.search(line):
                    # No source snippets: avoid leaking embedded credentials into reports.
                    hits.append({'severity': severity, 'rule': rule, 'file': path, 'line': number})
    return hits, dict(domains.most_common())

def markdown(r):
    lines = ['# Аудит скиллов', '', 'Эвристические совпадения, не вердикт о безопасности.', '',
             f"Режим: {r['mode']}. Прочитано: {r['read_files']}. Проверено: {r['scanned_files']}. Пропущено: {len(r['skipped'])}. Ошибок: {len(r['errors'])}.", '',
             'Корни: ' + ', '.join(r['roots']), '', '## Совпадения']
    for h in r['findings']:
        lines.append(f"- {h['severity']} / {h['rule']} — {h['file']}:{h['line']}")
    if not r['findings']:
        lines.append('Совпадений по этим правилам нет в проверенном объёме.')
    for title, key in [('Удалённые файлы', 'deleted'), ('Пропуски', 'skipped'), ('Ошибки', 'errors')]:
        lines += ['', '## ' + title]
        lines.extend('- ' + json.dumps(x, ensure_ascii=False) for x in r[key])
    lines += ['', '## Домены, упомянутые в тексте', 'Это не журнал реальных сетевых обращений.']
    lines.extend(f'- {k}: {v}' for k, v in r['domains'].items())
    return '\n'.join(lines) + '\n'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group()
    for mode in ('full', 'diff', 'snapshot'):
        modes.add_argument('--' + mode, action='store_true')
    p.add_argument('roots', nargs='*', help='Explicit local directories; no downloads or execution')
    p.add_argument('--state-dir', type=Path, default=Path(os.environ.get('SKILL_AUDIT_HOME', str(Path.home() / '.skill-audit'))))
    p.add_argument('--follow-symlinks', action='store_true')
    p.add_argument('--max-bytes', type=int, default=2_000_000)
    p.add_argument('--format', choices=('md', 'json'), default='md')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.max_bytes < 1:
        p.error('--max-bytes must be positive')
    roots = [Path(x).expanduser().resolve() for x in args.roots]
    if not roots:
        roots = [d for d in [Path.home()/'.claude/skills', Path.home()/'.agents/skills', Path.home()/'.codex/skills', Path.cwd()/'.claude/skills', Path.cwd()/'.agents/skills'] if d.is_dir()]
    roots = sorted(set(roots))
    if not roots or any(not d.is_dir() for d in roots):
        p.error('No roots found, or an explicit root is not a directory')
    # Keep mutable state/report outside the target, so an audit never changes its input.
    def within(path):
        return any(path.resolve() == r or r in path.resolve().parents for r in roots)
    if (args.output and within(args.output)) or within(args.state_dir):
        p.error('Output and state directory must be outside audited roots')
    scope = {'roots': [str(r) for r in roots], 'follow_symlinks': args.follow_symlinks, 'max_bytes': args.max_bytes, 'version': VERSION}
    key = hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()[:24]
    snapshot = args.state_dir / (key + '.json')
    files, skipped, errors = discover(roots, args.follow_symlinks, args.max_bytes)
    current = {k: v['hash'] for k, v in files.items()}
    if args.snapshot:
        if errors or not files:
            p.error('Snapshot not written: read errors or no supported text files')
        args.state_dir.mkdir(parents=True, exist_ok=True)
        data = json.dumps({'scope': scope, 'files': current, 'skipped': skipped}, ensure_ascii=False, indent=2)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=args.state_dir, delete=False) as f:
            f.write(data)
            temp = f.name
        os.replace(temp, snapshot)
        print(f'Snapshot recorded (not a trust verdict): {snapshot}; {len(files)} files; {len(skipped)} skipped')
        return 0
    targets, deleted = sorted(files), []
    if args.diff:
        try:
            old = json.loads(snapshot.read_text(encoding='utf-8'))
            if old['scope'] != scope or not isinstance(old['files'], dict):
                raise ValueError('scope mismatch')
        except (OSError, ValueError, KeyError) as e:
            p.error(f'No valid snapshot for these roots/options; run --snapshot after review: {e}')
        targets = sorted(k for k, v in current.items() if old['files'].get(k) != v)
        # Missing from scan != deleted (could be unreadable, oversized, or excluded).
        deleted = sorted(k for k in old['files'] if not os.path.lexists(k))
    if not files:
        errors.append({'error': 'No supported text files read'})
    hits, domains = audit(files, targets)
    report = dict(scope, mode='diff' if args.diff else 'full', read_files=len(files), scanned_files=len(targets), findings=hits, domains=domains, skipped=skipped, errors=errors, deleted=deleted, snapshot=str(snapshot))
    output = json.dumps(report, ensure_ascii=False, indent=2) + '\n' if args.format == 'json' else markdown(report)
    if args.output:
        args.output.write_text(output, encoding='utf-8')
    else:
        print(output, end='')
    return 2 if errors else (1 if hits else 0)

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
