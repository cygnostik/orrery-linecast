# Contributing

This repository is the standalone Orrery companion for Linecast. It is not an official Linecast release.

Keep changes focused and test them against the pinned Linecast dependency. Default operation must not perform location inference, network requests or configuration writes. Inferred location is a deliberate, clearly labelled user action; tests must mock providers.

```sh
uv sync --locked
uv run python -B -m unittest discover -s tests -v
uv run python -B launch.py --diagnose
```

Preserve the original palette and quiet attribution. Native terminal themes are an option, not a reason to remove the companion's authored appearance. Document astronomical model assumptions and do not extend date limits without a model valid over that range.

Keep OS-specific claims tied to actual test results. CI unit coverage is not proof of native mouse, font, or terminal-emulator behavior. Include a regression for each defect and a bounded manual/PTY check for changed interactions.

Never commit configuration, credentials, caches, absolute developer machine paths, or unsanitized transcripts. Any generated demonstration must identify its time and distinguish simulated from live information.
