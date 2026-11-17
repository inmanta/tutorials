# Inmanta tutorials

The lab and the code of the tutorials in the [Inmanta documentation](https://docs.inmanta.com/). Each directory is
the end state of one tutorial and the starting point of the next: when you skip a tutorial, or want to start over,
copy the directory of the previous one.

| Directory             | Tutorial                        | Checkpoint                                       |
| --------------------- | ------------------------------- | ------------------------------------------------ |
| `01-first-config`     | Deploy your first configuration | The spine has two OSPF neighbors in state `full` |
| `02-first-module`     | From configuration to a model   | The dry run of the model is empty                |
| `03-test-your-module` | Test your module                | Six passing tests                                |
| `04-write-a-handler`  | Write a handler                 | The lifecycle test passes, `eth2` is deployed    |

## Versions

The tutorials are tested with the versions pinned in this repository. Use them together:

| Component                 | Version | Where                              |
| ------------------------- | ------- | ---------------------------------- |
| Orchestrator image        | 2027.2  | `lab/topology.yml`                 |
| `inmanta` (CLI, compiler) | 2027.2  | `requirements.txt`                 |
| Python                    | 3.14    | `.python-version`                  |
| SR Linux                  | 26.7.2  | `lab/topology.yml`                 |
| Modules                   | pinned  | `requirements.txt` of each project |

The Python version of your virtual environment must be the one of the orchestrator image: modules are published per
Python version, and the orchestrator installs the same module versions as your compiler.

## Start the lab

The lab runs in [containerlab](https://containerlab.dev/install/), with Docker or Podman:

```sh
containerlab deploy -t lab/topology.yml                    # Docker
containerlab --runtime podman deploy -t lab/topology.yml   # Podman
```

| Node              | Address        | Access                                                                  |
| ----------------- | -------------- | ----------------------------------------------------------------------- |
| `inmanta-server`  | `172.30.0.3`   | Web console at `http://172.30.0.3:8888`                                 |
| `spine`           | `172.30.0.100` | `ssh admin@172.30.0.100`, password `NokiaSrl1!`                         |
| `leaf1`           | `172.30.0.210` | `ssh admin@172.30.0.210`, password `NokiaSrl1!`                         |
| `leaf2`           | `172.30.0.220` | `ssh admin@172.30.0.220`, password `NokiaSrl1!`                         |
| `subscriber-east` | `172.30.0.6`   | Web console at `http://172.30.0.6:8080`, REST API under `/api/v2/docs` |

Remove it with `containerlab destroy -t lab/topology.yml`, with the same `--runtime` option.

## Set up Python

```sh
uv venv -p "$(cat .python-version)" .venv    # or: python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Check all stages

`ci/check.sh` starts a fresh lab, runs every directory in order and checks its checkpoint. Run it after a version
change. It needs containerlab, uv and sshpass.

```sh
ci/check.sh podman    # or: ci/check.sh docker
```
