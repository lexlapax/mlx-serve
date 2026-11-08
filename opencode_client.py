"""Launch the pinned OpenCode client with private configuration and state."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
BINARY = ROOT / 'node_modules/@opencode/cli/bin/opencode.exe'


def environment(runtime=None, config=None):
    runtime = Path(runtime or ROOT / '.runtime/opencode').resolve()
    env = {k: v for k, v in os.environ.items()
           if k in {'HOME', 'USER', 'LOGNAME', 'SHELL', 'LANG', 'TERM', 'COLORTERM', 'TMPDIR', 'SSH_AUTH_SOCK'}
           or k.startswith('LC_')}
    env['PATH'] = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'
    for name, folder in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                         ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state')]:
        path = runtime / folder
        path.mkdir(parents=True, exist_ok=True)
        env[name] = str(path)
    directory = runtime / 'config/opencode'
    directory.mkdir(parents=True, exist_ok=True)
    selected = config or json.loads((ROOT / 'opencode.local.json').read_text())
    (directory / 'opencode.json').write_text(json.dumps(selected, indent=2) + '\n')
    catalog = runtime / 'models.json'
    catalog.write_text('{}\n')
    env.update({
        'OPENCODE_CONFIG_DIR': str(directory),
        'OPENCODE_MODELS_PATH': str(catalog),
        'OPENCODE_DISABLE_MODELS_FETCH': 'true',
        'OPENCODE_DISABLE_PROJECT_CONFIG': 'true',
        'OPENCODE_CONFIG_PROJECT_DISABLE': 'true',
        'OPENCODE_DISABLE_AUTOUPDATE': 'true',
        'OPENCODE_DISABLE_DEFAULT_PLUGINS': 'true',
        'OPENCODE_DISABLE_CLAUDE_CODE': 'true',
        'OPENCODE_DISABLE_LSP_DOWNLOAD': 'true',
        'OPENCODE_DISABLE_FILEWATCHER': 'true',
        'OPENCODE_PURE': 'true',
    })
    return env


if __name__ == '__main__':
    args = sys.argv[1:]
    local_only_command = args[:2] == ['debug', 'paths'] or args[:1] in [['serve'], ['service']]
    if not local_only_command and '--server' not in args and '--standalone' not in args:
        args += ['--standalone']
    os.execve(str(BINARY), [str(BINARY), *args], environment())
