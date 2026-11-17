import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pytest_inmanta.plugin import Project


class FakeSubscriberApi(BaseHTTPRequestHandler):
    """The interfaces endpoint of the subscriber API, in memory."""

    interfaces: dict[str, dict[str, object]] = {}

    def _reply(self, status: int, body: object = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if body is not None:
            self.wfile.write(json.dumps(body).encode())

    def _name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    def _body(self) -> dict[str, object]:
        return json.loads(self.rfile.read(int(self.headers["Content-Length"])))

    def do_GET(self) -> None:
        interface = self.interfaces.get(self._name())
        self._reply(404) if interface is None else self._reply(200, interface)

    def do_POST(self) -> None:
        body = self._body()
        self.interfaces[str(body["name"])] = body
        self._reply(201, body)

    def do_PATCH(self) -> None:
        self.interfaces[self._name()].update(self._body())
        self._reply(200, self.interfaces[self._name()])

    def do_DELETE(self) -> None:
        del self.interfaces[self._name()]
        self._reply(204)


@pytest.fixture
def api_port() -> Iterator[int]:
    FakeSubscriberApi.interfaces = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSubscriberApi)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()


def model(port: int, mtu: int, purged: bool = False) -> str:
    return f"""
import subscriber

sub = subscriber::Subscriber(name="subscriber1", mgmt_ip="127.0.0.1", api_port={port})
subscriber::Interface(subscriber=sub, name="eth1", mtu={mtu}, purged={str(purged).lower()})
"""


def test_interface_lifecycle(project: Project, api_port: int) -> None:
    # create
    project.compile(model(api_port, mtu=1500))
    project.deploy_resource("subscriber::Interface")
    assert FakeSubscriberApi.interfaces["eth1"]["mtu"] == 1500

    # nothing to do when the interface is as desired
    assert not project.dryrun_resource("subscriber::Interface")

    # update
    project.compile(model(api_port, mtu=9000))
    changes = project.dryrun_resource("subscriber::Interface")
    assert (changes["mtu"].current, changes["mtu"].desired) == (1500, 9000)
    project.deploy_resource("subscriber::Interface")
    assert FakeSubscriberApi.interfaces["eth1"]["mtu"] == 9000

    # delete
    project.compile(model(api_port, mtu=9000, purged=True))
    project.deploy_resource("subscriber::Interface")
    assert "eth1" not in FakeSubscriberApi.interfaces
