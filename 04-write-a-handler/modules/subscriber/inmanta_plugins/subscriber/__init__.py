import requests

import inmanta.execute.proxy
import inmanta.export
from inmanta.agent.handler import CRUDHandler, HandlerContext, ResourcePurged, provider
from inmanta.resources import PurgeableResource, resource


@resource("subscriber::Interface", agent="subscriber.name", id_attribute="name")
class Interface(PurgeableResource):
    fields = ("name", "mtu", "api_url")

    @staticmethod
    def get_api_url(_: inmanta.export.Exporter, entity: inmanta.execute.proxy.DynamicProxy) -> str:
        return f"http://{entity.subscriber.mgmt_ip}:{entity.subscriber.api_port}/api/v2/interfaces"


@provider("subscriber::Interface", name="subscriber")
class InterfaceHandler(CRUDHandler[Interface]):
    def read_resource(self, ctx: HandlerContext, resource: Interface) -> None:
        response = requests.get(f"{resource.api_url}/{resource.name}", timeout=10)
        if response.status_code == 404:
            raise ResourcePurged()
        response.raise_for_status()
        resource.mtu = response.json()["mtu"]

    def create_resource(self, ctx: HandlerContext, resource: Interface) -> None:
        response = requests.post(
            resource.api_url,
            json={"name": resource.name, "mtu": resource.mtu, "type": "veth"},
            timeout=10,
        )
        response.raise_for_status()
        ctx.set_created()

    def update_resource(self, ctx: HandlerContext, changes: dict, resource: Interface) -> None:
        response = requests.patch(
            f"{resource.api_url}/{resource.name}",
            json={"mtu": changes["mtu"]["desired"]},
            timeout=10,
        )
        response.raise_for_status()
        ctx.set_updated()

    def delete_resource(self, ctx: HandlerContext, resource: Interface) -> None:
        response = requests.delete(f"{resource.api_url}/{resource.name}", timeout=10)
        response.raise_for_status()
        ctx.set_purged()
