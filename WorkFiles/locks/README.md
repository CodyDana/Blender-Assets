# Asset locks

One JSON file per asset (`<Asset>.json` with asset, agent, blend, port, pid, since) written by `Scripts/pipeline/lock.py`: claim before opening a .blend (`py Scripts/pipeline/lock.py claim <Asset> --agent claude|codex`), call `pipeline.lock.assert_owner(asset, agent)` at the top of scripts that open it, release when done; CLI exit code 2 means another agent holds the lock.
