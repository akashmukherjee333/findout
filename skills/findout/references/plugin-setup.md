# /findout + /foundit Hermes Plugin Setup

## What it is

A Hermes plugin at `plugins/hermes/` in the findout repo that registers
`/findout <query>` and `/foundit <query>` as native slash commands. Works in
TUI, CLI, and gateway. `/foundit` is an alias for the same pipeline.

## Quick install

```bash
mkdir -p ~/.hermes/plugins/findout
cp -r plugins/hermes/* ~/.hermes/plugins/findout/
```

Then `/reset` the session (or `hermes gateway restart` for gateway).

## Env vars (must be set)

```
FINDOUT_MODEL=<model>
FINDOUT_BASE_URL=<api-base-url>
FINDOUT_API_KEY=<key>
FINDOUT_TIMEOUT=300
FINDOUT_MAX_TOKENS=32768
```

These go in `~/.hermes/.env`. The plugin loads that file itself before launching
`findout`, so a fresh Hermes session does not need the variables exported in the
shell. The timeout/token values are important for reasoning models that spend
tokens before producing visible answer text.

## Verification

```bash
# Test CLI directly
findout run --skip-gate "your query here"

# Test plugin loads and registers both command names
python3 -c "
import os, sys, importlib.util
sys.path.insert(0, os.path.expanduser('~/.hermes/plugins'))
spec = importlib.util.spec_from_file_location(
    'findout_plugin',
    os.path.expanduser('~/.hermes/plugins/findout/__init__.py')
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class Ctx:
    def __init__(self): self.commands = []
    def register_command(self, name, **kwargs): self.commands.append(name)
ctx = Ctx()
mod.register(ctx)
assert {'findout', 'foundit'} <= set(ctx.commands), ctx.commands
print('OK', ctx.commands)
"
```

## Architecture

```
TUI/gateway → /findout or /foundit <query> → Hermes plugin → ~/.hermes/.env → subprocess findout run <query> → pipeline
```

The plugin shells out to the `findout` CLI — keeps the plugin lightweight,
avoids Python import/dependency coupling.

## Uninstall

```bash
rm -rf ~/.hermes/plugins/findout && /reset
```
