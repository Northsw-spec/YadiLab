"""Independent table fixtures for schema 1.3 XLSX/ODS import acceptance.

A real five-node network with two explicit VLAN-aware switches, a trunk,
a router, two static routes and explicit endpoint MAC addresses.
"""
from __future__ import annotations

from network_core.model import validate_project
from ods_fixture import make_ods
from xlsx_fixture import make_workbook

TABLES_13 = {
    "Project": "schemaVersion\n1.3\n",
    "Devices": (
        "id,label,kind,x,y,zoneId\n"
        "ha,Source host,host,20,30,office\n"
        "sa,Left switch,switch,120,30,office\n"
        "sb,Right switch,switch,220,30,office\n"
        "r,Router,router,330,30,office\n"
        "hb,Destination host,host,440,30,office\n"
    ),
    "Zones": "id,label\noffice,Office network\n",
    "Interfaces": (
        "nodeId,id,name,enabled,ipv4,mac,vlanMode,accessVlan,allowedVlans\n"
        "ha,eth0,ethernet0,true,192.0.2.10/24,02:00:00:00:00:0A,,,\n"
        "sa,host,Host access,true,,,access,10,\n"
        "sa,uplink,Tagged trunk,true,,,trunk,,10|20\n"
        "sb,uplink,Tagged trunk,true,,,trunk,,10|20\n"
        "sb,lan,Router access,true,,,access,10,\n"
        "r,lan,LAN port,true,192.0.2.1/24,02:00:00:00:00:0B,,,\n"
        "r,wan,WAN port,true,203.0.113.1/24,02:00:00:00:00:0C,,,\n"
        "hb,eth0,ethernet0,true,203.0.113.20/24,02:00:00:00:00:0D,,,\n"
    ),
    "Links": (
        "id,aNode,aPort,bNode,bPort,enabled\n"
        "cable-a,ha,eth0,sa,host,true\n"
        "trunk,sa,uplink,sb,uplink,true\n"
        "router-lan,sb,lan,r,lan,true\n"
        "router-wan,r,wan,hb,eth0,true\n"
    ),
    "StaticRoutes": (
        "nodeId,id,destination,nextHop,outPort\n"
        "ha,to-network-b,203.0.113.0/24,192.0.2.1,eth0\n"
        "hb,to-network-a,192.0.2.0/24,203.0.113.1,eth0\n"
    ),
}


def expected_v13(name="V13 laboratory"):
    return validate_project({
        "schemaVersion":"1.3", "name":name,
        "zones":[{"id":"office","label":"Office network"}],
        "nodes":[
            {"id":"ha","label":"Source host","kind":"host","x":20.0,"y":30.0,
             "zoneId":"office","ports":[{"id":"eth0","name":"ethernet0","enabled":True,
                                        "ipv4":"192.0.2.10/24","mac":"02:00:00:00:00:0A"}],
             "staticRoutes":[{"id":"to-network-b","destination":"203.0.113.0/24",
                              "nextHop":"192.0.2.1","outPort":"eth0"}]},
            {"id":"sa","label":"Left switch","kind":"switch","x":120.0,"y":30.0,
             "zoneId":"office","ports":[
                {"id":"host","name":"Host access","enabled":True,"ipv4":None,
                 "vlan":{"mode":"access","vlan":10}},
                {"id":"uplink","name":"Tagged trunk","enabled":True,"ipv4":None,
                 "vlan":{"mode":"trunk","allowedVlans":[10,20]}},
             ]},
            {"id":"sb","label":"Right switch","kind":"switch","x":220.0,"y":30.0,
             "zoneId":"office","ports":[
                {"id":"uplink","name":"Tagged trunk","enabled":True,"ipv4":None,
                 "vlan":{"mode":"trunk","allowedVlans":[10,20]}},
                {"id":"lan","name":"Router access","enabled":True,"ipv4":None,
                 "vlan":{"mode":"access","vlan":10}},
             ]},
            {"id":"r","label":"Router","kind":"router","x":330.0,"y":30.0,
             "zoneId":"office","ports":[
                {"id":"lan","name":"LAN port","enabled":True,
                 "ipv4":"192.0.2.1/24","mac":"02:00:00:00:00:0B"},
                {"id":"wan","name":"WAN port","enabled":True,
                 "ipv4":"203.0.113.1/24","mac":"02:00:00:00:00:0C"},
             ]},
            {"id":"hb","label":"Destination host","kind":"host","x":440.0,"y":30.0,
             "zoneId":"office","ports":[
                {"id":"eth0","name":"ethernet0","enabled":True,
                 "ipv4":"203.0.113.20/24","mac":"02:00:00:00:00:0D"},
             ],"staticRoutes":[{"id":"to-network-a","destination":"192.0.2.0/24",
                                "nextHop":"203.0.113.1","outPort":"eth0"}]},
        ],
        "links":[
            {"id":"cable-a","a":{"node":"ha","port":"eth0"},
             "b":{"node":"sa","port":"host"},"enabled":True},
            {"id":"trunk","a":{"node":"sa","port":"uplink"},
             "b":{"node":"sb","port":"uplink"},"enabled":True},
            {"id":"router-lan","a":{"node":"sb","port":"lan"},
             "b":{"node":"r","port":"lan"},"enabled":True},
            {"id":"router-wan","a":{"node":"r","port":"wan"},
             "b":{"node":"hb","port":"eth0"},"enabled":True},
        ],
    })


def xlsx_v13(**kwargs):
    return make_workbook(TABLES_13, **kwargs)


def ods_v13(**kwargs):
    return make_ods(TABLES_13, **kwargs)
