# /findout Hermes Plugin Setup

## What it is

A Hermes plugin at `plugins/hermes/` in the findout repo that registers
`/findout <query>` as a native slash command. Works in TUI, CLI, and gateway.

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
```

These go in `~/.hermes/.env`. The CLI reads them at runtime.

## Verification

```bash
# Test CLI directly
findout run --skip-gate "your query here"

# Test plugin loads
python3 -c "
import os, sys, importlib.util
sys.path.insert(0, os.path.expanduser('~/.hermes/plugins'))
spec = importlib.util.spec_from_file_location(
    'findout_plugin',
    os.path.expanduser('~/.hermes/plugins/findout/__init__.py')
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('OK' if hasattr(mod, 'register') else 'FAIL')
"
```

## Architecture

```
TUI/gateway → /findout <query> → Hermes plugin → subprocess findout run <query> → pipeline
```

The plugin shells out to the `findout` CLI — keeps the plugin lightweight,
avoids Python import/dependency coupling.

## Uninstall

```bash
rm -rf ~/.hermes/plugins/findout && /reset
```
