"""Small LSM client for check-iso.sh: update the catalog, order and update router services."""

import argparse
import configparser
import json
import sys
import time
import urllib.error
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


def wait(what: str, check, timeout: int) -> None:
    deadline = time.time() + timeout
    while not check():
        if time.time() > deadline:
            sys.exit(f"timed out waiting for {what}")
        time.sleep(5)


def instances(env: str) -> dict[str, dict]:
    return {
        (i["active_attributes"] or i["candidate_attributes"])["name"]: i
        for i in call(env, "GET", "/lsm/v1/service_inventory/router?limit=100")["data"]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("env")
    parser.add_argument("action", choices=["update-catalog", "order", "add-interface", "wait-up"])
    parser.add_argument("args", nargs="*")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    env = args.env

    if args.action == "update-catalog":
        call(env, "POST", "/lsm/v1/exporter/export_service_definition")
        wait("the router service", lambda: any(e["name"] == "router" for e in call(env, "GET", "/lsm/v1/service_catalog")["data"]), args.timeout)
        print("catalog: router")
    elif args.action == "order":
        name, mgmt_ip, interface, ip = args.args
        attributes = {"name": name, "mgmt_ip": mgmt_ip, "interfaces": [{"name": interface, "ip": ip}]}
        call(env, "POST", "/lsm/v1/service_inventory/router", {"attributes": attributes})
    elif args.action == "add-interface":
        name, interface, ip = args.args
        instance = instances(env)[name]
        interfaces = instance["active_attributes"]["interfaces"] + [{"name": interface, "ip": ip}]
        call(env, "PATCH", f"/lsm/v1/service_inventory/router/{instance['id']}?current_version={instance['version']}",
             {"attributes": {"interfaces": interfaces}})
    else:
        names = set(args.args)
        def all_up() -> bool:
            current = instances(env)
            return names <= current.keys() and all(current[n]["state"] == "up" for n in names)
        wait(f"{', '.join(sorted(names))} up", all_up, args.timeout)
        print(f"up: {', '.join(sorted(names))}")


if __name__ == "__main__":
    main()
