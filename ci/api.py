"""Small client for the orchestrator API, used by check.sh: wait for a deploy, dry run, promote, settings."""

import argparse
import configparser
import json
import sys
import time
import urllib.request

SERVER = "http://172.30.0.3:8888"


def call(env: str, method: str, path: str, body: object = None) -> dict:
    request = urllib.request.Request(
        SERVER + path,
        method=method,
        headers={"X-Inmanta-tid": env, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(request) as response:
        content = response.read()
    return json.loads(content) if content else {}


def latest_version(env: str) -> int:
    return call(env, "GET", "/api/v2/desiredstate?limit=1")["data"][0]["version"]


def wait_deployed(env: str, timeout: int) -> None:
    """Wait until every resource of the active version is deployed."""
    deadline = time.time() + timeout
    while True:
        resources = call(env, "GET", "/api/v2/resource?limit=1000")["data"]
        states = {r["resource_id"]: r["status"] for r in resources}
        if states and all(s == "deployed" for s in states.values()):
            print(f"{len(states)} resources deployed")
            return
        if time.time() > deadline:
            sys.exit(f"not deployed after {timeout}s: {states}")
        time.sleep(5)


def dryrun(env: str) -> list[str]:
    """Dry run the latest version, return the ids of the resources that would change."""
    version = latest_version(env)
    report_id = call(env, "POST", f"/api/v2/dryrun/{version}")["data"]
    while True:
        report = call(env, "GET", f"/api/v2/dryrun/{version}/{report_id}")["data"]
        if report["summary"]["todo"] == 0:
            return [d["resource_id"] for d in report["diff"] if d["status"] != "unmodified"]
        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", help="project directory with the .inmanta file")
    parser.add_argument("action", choices=["wait-deployed", "dryrun-empty", "dryrun", "promote", "auto-deploy-on", "auto-deploy-off"])
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read(f"{args.project}/.inmanta")
    env = config["config"]["environment"]

    if args.action == "wait-deployed":
        wait_deployed(env, args.timeout)
    elif args.action in ("dryrun", "dryrun-empty"):
        changed = dryrun(env)
        print("changed:", changed)
        if args.action == "dryrun-empty" and changed:
            sys.exit("dry run is not empty")
    elif args.action == "promote":
        call(env, "POST", f"/api/v2/desiredstate/{latest_version(env)}/promote")
    else:
        call(env, "POST", "/api/v2/environment_settings/auto_deploy", {"value": args.action == "auto-deploy-on"})


if __name__ == "__main__":
    main()
