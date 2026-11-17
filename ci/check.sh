#!/usr/bin/env bash
# Run every tutorial stage against a fresh lab and check its checkpoint.
# Needs: containerlab with podman or docker, uv, sshpass. Usage: ci/check.sh [podman|docker]
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
RUNTIME=${1:-podman}
API="python $ROOT/ci/api.py"
step() { printf '\n== %s\n' "$*"; }

step "Lab"
containerlab --runtime "$RUNTIME" deploy -t lab/topology.yml --reconfigure
until curl -sf http://172.30.0.3:8888/api/v1/serverstatus >/dev/null; do sleep 5; done

step "Python $(cat .python-version)"
rm -rf .venv
uv venv -q -p "$(cat .python-version)" .venv
source .venv/bin/activate
uv pip install -q pip -r requirements.txt
inmanta --version 2>/dev/null | sed -n 1p

step "01-first-config: deploy, OSPF neighbors up"
rm -f "$ROOT"/0*/.inmanta
cd "$ROOT/01-first-config"
inmanta project install
inmanta-cli --host 172.30.0.3 project create -n tutorial-check
inmanta-cli --host 172.30.0.3 environment create -n "check-$(date +%s)" -p tutorial-check --save
inmanta export
$API . wait-deployed
for i in $(seq 1 30); do
  neighbors=$(SSHPASS='NokiaSrl1!' sshpass -e ssh -tt -o PubkeyAuthentication=no -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR admin@172.30.0.100 \
    "show network-instance default protocols ospf neighbor" | grep -c " full " || true)
  [ "$neighbors" = 2 ] && break
  sleep 5
done
[ "$neighbors" = 2 ] || { echo "spine has $neighbors full OSPF neighbors, expected 2"; exit 1; }
echo "spine: 2 full OSPF neighbors"

step "02-first-module: the dry run of the model is empty"
cd "$ROOT/02-first-module"
cp ../01-first-config/.inmanta .
pip install -q -e modules/training
inmanta project install
$API . auto-deploy-off
inmanta export
$API . dryrun-empty
$API . promote
$API . auto-deploy-on

step "03-test-your-module: six passing tests"
cd "$ROOT/03-test-your-module/modules/training"
pip install -q -e . -r requirements.dev.txt
pytest -q tests | tail -1

step "04-write-a-handler: lifecycle test, deploy to subscriber-east"
cd "$ROOT/04-write-a-handler"
cp ../01-first-config/.inmanta .
pip install -q -e modules/training -e modules/subscriber
(cd modules/subscriber && pytest -q tests | tail -1)
inmanta project install
inmanta export
$API . wait-deployed
mtu=$(curl -s http://172.30.0.6:8080/api/v2/interfaces/eth2 | python -c 'import json, sys; print(json.load(sys.stdin)["mtu"])')
[ "$mtu" = 1500 ] || { echo "eth2 has mtu $mtu, expected 1500"; exit 1; }
echo "subscriber-east: eth2 with mtu 1500"

step "All stages pass"
