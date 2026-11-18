import pytest
from pytest_inmanta.plugin import Project

LEAF = """
import tutorial

tutorial::Router(
    name="leaf1",
    mgmt_ip="172.30.0.210",
    interfaces=[tutorial::Interface(name="ethernet-1/1", ip="{ip}")],
)
"""


def test_one_router(project: Project) -> None:
    project.compile(LEAF.format(ip="10.10.11.2/30"))

    interfaces = project.get_instances("nokia_srlinux::Interface")
    assert [interface.name for interface in interfaces] == ["ethernet-1/1"]
    assert project.get_resource("yang::GnmiResource") is not None


SPINE = """
import tutorial

tutorial::Router(
    name="spine",
    mgmt_ip="172.30.0.100",
    interfaces=[
        tutorial::Interface(name="ethernet-1/1", ip="10.10.11.1/30"),
        tutorial::Interface(name="ethernet-1/2", ip="10.10.21.1/30"),
    ],
)
"""


def test_ospf_on_every_interface(project: Project) -> None:
    project.compile(SPINE)

    area = project.get_instances("nokia_srlinux::network_instance::protocols::ospf::instance::Area")[0]
    assert sorted(interface.interface_name for interface in area.interface) == ["ethernet-1/1.0", "ethernet-1/2.0"]


@pytest.mark.parametrize("ip", ["10.10.11.300/30", "10.10.11.2/33", "leaf1"])
def test_bad_interface_address(project: Project, ip: str) -> None:
    with pytest.raises(Exception, match="attribute `ip`"):
        project.compile(LEAF.format(ip=ip))


def test_router_without_interfaces(project: Project) -> None:
    with pytest.raises(Exception, match="interfaces"):
        project.compile(
            """
            import tutorial

            tutorial::Router(name="leaf3", mgmt_ip="172.30.0.230")
            """
        )

