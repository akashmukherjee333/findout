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

## Runtime model config

Inside Hermes usage, this command is expected to run against the currently
loaded model context rather than a dedicated `FINDOUT_*` env-var bundle.

For standalone CLI usage, pass endpoint settings explicitly:

```bash
findout run "your query here" \
  --model gpt-4o \
  --base-url https://api.openai.com/v1 \
  --api-key sk-...
```

`FINDOUT_TIMEOUT` is still accepted by the plugin as an optional timeout knob if
present in `~/.hermes/.env`, but model/base-url/api-key are no longer documented
as required plugin inputs.

## Verification

```bash
# Test CLI directly
findout run "your query here" \
  --model gpt-4o \
  --base-url https://api.openai.com/v1

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
TUI/gateway → /findout or /foundit <query> → Hermes plugin → subprocess findout run <query> → pipeline
```

The plugin shells out to the `findout` CLI — keeps the plugin lightweight,
avoids Python import/dependency coupling.

## Uninstall

```bash
rm -rf ~/.hermes/plugins/findout && /reset
```
