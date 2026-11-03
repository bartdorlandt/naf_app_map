# NAF App Map

A small, locally running web app to map the tools and applications in your network automation stack onto the building blocks of the [Network Automation Forum (NAF) framework](https://reference.networkautomation.forum/Framework/Framework/#architecture).

![Overview](images/overview.png)

## Why

When you discuss an automation architecture, the same questions keep coming back: *what do we use for intent? who collects state? is anything orchestrating this?* The NAF framework gives a shared vocabulary for that. This project makes it visual and editable:

- Put each app in the block(s) it fulfils, so you can see gaps and overlaps at a glance.
- Keep one map per team, customer or "current vs. target" state.
- Store each map as a single JSON file that you can share, diff and check into git.

## Features

- The six NAF building blocks (Presentation, Observability, Orchestrator, Intent, Collector, Executor) on top of the network infrastructure, colored per the [NAF brand guidelines](https://reference.networkautomation.forum/Framework/brand-guidelines/#4-color-palette).
- Add apps with a name, a description, a link and a code link (for example, the git repo, shown as `(code)`).
- Drag an app to move it to another block. Hold **Alt/Option** while you drop to copy it instead. ⧉ duplicates it in place.
- Sort per block: manual, A→Z or Z→A. New files default to A→Z.
- Every change is saved to disk immediately. After a restart, the app opens the last file you used.
- Switch between state files, or create new ones, from the menu at the top. Each state is its own file, so they never interfere with each other.

## Getting started

Requirements: [Docker](https://www.docker.com/) and [Task](https://taskfile.dev/).

```sh
task start     # build if needed, run, and open http://localhost:8080
```

| Task           | What it does                                          |
|----------------|-------------------------------------------------------|
| `task build`   | Build the image                                       |
| `task rebuild` | Rebuild without cache and restart                     |
| `task start`   | Start the service and open the browser                |
| `task stop`    | Stop the service                                      |
| `task destroy` | Remove container and image (files in `data/` remain)  |
| `task logs`    | Follow logs                                           |

Without Docker: `python3 server.py` (Python 3.9+, no dependencies). The data is then stored in `./data`.

## Data

State files live in `./data/` (mounted into the container), one JSON file per map:

```json
{
  "blocks": {
    "intent":   [{ "id": "…", "name": "Infrahub", "description": "by Opsmill", "url": "", "code": "https://github.com/opsmill/infrahub" }],
    "executor": [{ "id": "…", "name": "Nornir", "description": "", "url": "", "code": "https://github.com/nornir-automation/nornir" }]
  },
  "sort": { "intent": "asc", "executor": "asc" }
}
```

To share a map, copy its file into someone else's `data/` folder, or commit it to git.

## How it is built

This project is deliberately small:
- `server.py`: a Python standard-library HTTP server that serves the page and reads and writes the JSON files.
- `static/index.html`: a single HTML page in plain JavaScript, with native drag-and-drop and a `<dialog>` form.
- `Dockerfile`, `compose.yaml`, `Taskfile.yml`: packaging and control.

## License

[MIT](LICENSE)
