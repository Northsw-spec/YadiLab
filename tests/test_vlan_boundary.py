"""Cross-boundary regression: ARP endpoint parsing must not accept tagged frames."""
import unittest

from network_core.arp import ArpMessage
from network_core.ethernet_frame import EthernetFrame
from network_core.model import ProjectValidationError
from test_ethernet import A, B


class TaggedArpBoundaryTests(unittest.TestCase):
    def test_tagged_arp_is_not_treated_as_endpoint_arp(self):
        request = ArpMessage(1, A, "192.0.2.10",
                             "00:00:00:00:00:00", "192.0.2.20")
        original = request.to_frame()
        tagged = EthernetFrame(original.destination, original.source,
                               original.ether_type, original.payload, vlan_id=10)
        parsed = EthernetFrame.parse(tagged.serialize())
        self.assertEqual(parsed.vlan_id, 10)
        with self.assertRaisesRegex(ProjectValidationError, "tagged VLAN frames unsupported"):
            ArpMessage.from_frame(parsed)
        self.assertEqual(ArpMessage.from_frame(EthernetFrame.parse(original.serialize())), request)


if __name__ == "__main__":
    unittest.main()
