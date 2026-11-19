#!/usr/bin/env bash
# Run stage 05 (Expose the model as a service) against a fresh lab with the Service Orchestrator.
# Needs: what check.sh needs, a license in lab/license/, and in ISO_INDEX_URL the package index of the Service
# Orchestrator. ORCHESTRATOR_IMAGE overrides the image. Usage: ci/check-iso.sh [podman|docker]
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
RUNTIME=${1:-podman}
: "${ISO_INDEX_URL:?set ISO_INDEX_URL to the package index of the Service Orchestrator}"
step() { printf '\n== %s\n' "$*"; }
neighbors() {
  SSHPASS='NokiaSrl1!' sshpass -e ssh -tt -o PubkeyAuthentication=no -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR admin@172.30.0.100 \
    "show network-instance default protocols ospf neighbor" | grep -c " full " || true
}
expect_neighbors() {
  for i in $(seq 1 30); do [ "$(neighbors)" = "$1" ] && { echo "spine: $1 full OSPF neighbors"; return; }; sleep 5; done
  echo "spine has $(neighbors) full OSPF neighbors, expected $1"; exit 1
}

step "Lab with the Service Orchestrator"
containerlab --runtime "$RUNTIME" deploy -t lab/topology-iso.yml --reconfigure
until curl -sf http://172.30.0.3:8888/api/v1/serverstatus >/dev/null; do sleep 5; done

step "Python $(cat .python-version)"
[ -d .venv ] || uv venv -q -p "$(cat .python-version)" .venv
source .venv/bin/activate
uv pip install -q pip -r requirements.txt

step "Publish the tutorial module"
rm -f packages/*.whl
(cd 03-test-your-module/modules/tutorial && rm -rf dist && inmanta module build >/dev/null && cp dist/*.whl "$ROOT/packages/")
ls packages/*.whl

step "05-expose-as-service: the service model in git"
rm -rf "$ROOT/my-services-check"
cp -r 05-expose-as-service "$ROOT/my-services-check"
cd "$ROOT/my-services-check"
sed -i "s|https://packages.inmanta.com/<token>/inmanta-service-orchestrator-10-stable/python/simple/|$ISO_INDEX_URL|" project.yml
printf '.inmanta\nlibs/\n' > .gitignore
git init -q -b main
git add . && git -c user.name=check -c user.email=check@example.com commit -q -m "Offer the routers as a service"
inmanta-cli --host 172.30.0.3 project create -n tutorial-check >/dev/null
inmanta-cli --host 172.30.0.3 environment create -p tutorial-check -n "check-$(date +%s)" \
  --repo-url /tutorials/my-services-check --branch main --save >/dev/null
ENV=$(sed -n 's/^environment=//p' .inmanta)
LSM="python $ROOT/ci/lsm.py $ENV"
$LSM update-catalog

step "Order the routers: the spine has one neighbor"
$LSM order spine 172.30.0.100 ethernet-1/1 10.10.11.1/30
$LSM order leaf1 172.30.0.210 ethernet-1/1 10.10.11.2/30
$LSM order leaf2 172.30.0.220 ethernet-1/1 10.10.21.2/30
$LSM wait-up spine leaf1 leaf2
expect_neighbors 1

step "Update the spine: two neighbors"
$LSM add-interface spine ethernet-1/2 10.10.21.1/30
sleep 10
$LSM wait-up spine
expect_neighbors 2

step "Stage 05 passes"
