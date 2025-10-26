Running the interactive UI and tests

Quick commands to run the interactive CLI and tests locally (from the repository root):

Run the interactive UI (starts automatically from `source-code/main.py`):

```bash
python3 source-code/main.py
```

Run the non-interactive demo runner (uses the first dataset from `config.json`):

```bash
python3 scripts/ui_runner.py --auto
```

Run the unit tests (verifies `ConfigManager.create_plot_from_ui` behavior):

```bash
python3 -m unittest tests.test_config_manager -v
```

Notes:
- If you see import errors like `ModuleNotFoundError: No module named 'errors'`, make sure you run commands from the repository root so the `source-code` folder is on the module search path (the test and runner scripts already handle this).
- After making changes, restart the Python language server in VS Code ("Python: Restart Language Server") if Pylance shows stale diagnostics.
