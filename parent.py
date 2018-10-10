"""Parent"""
from concurrent.futures import ThreadPoolExecutor
import json
import socket

from monsterurl import get_monster
from trusted_server import TrustedServer


class Parent:
    def __init__(self, privkey, pubkey, address):
        self._keypair = (privkey, pubkey)
        self._address = address
        self._peers = []
        self._name = get_monster()

    @property
    def name(self):
        """name"""
        return self._name

    @property
    def privkey(self):
        """Private key"""
        return self._keypair[0]

    @property
    def pubkey(self):
        """Public key"""
        return self._keypair[1]

    @property
    def address(self):
        """Address tuple with IP and port"""
        return self._address

    @property
    def peers(self):
        """List of peers"""
        return self._peers

    def set_peers(self, peers):
        """set peers on first discovery"""
        for peer in peers:
            peer["address"] = tuple(peer["address"])
        self._peers = peers

    def add_peer(self, peer):
        """Add miner to peer list"""
        peer["address"] = tuple(peer["address"])
        if peer["address"] != self.address:
            self._peers.append(peer)

    def startup(self):
        """Obtain nodes with TrustedServer"""
        reply = Parent._send_request(
            "a", (TrustedServer.HOST, TrustedServer.PORT))
        prot = reply[0].lower()
        if prot == "a":
            # sent by the central server when requested for a list of addresses
            addresses = json.loads(reply[1:])["addresses"]
            self.set_peers(addresses)
        # print("Established connections with {} nodes".format(len(self._peers)))
        data = {"address": self.address, "pubkey": self.pubkey, "name": self.name}
        Parent._send_message("n"+json.dumps(data),
                             (TrustedServer.HOST, TrustedServer.PORT))

    def _broadcast_message(self, msg):
        """Broadcast the message to peers"""
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        if not self._peers:
            raise Exception("Not connected to network.")
        with ThreadPoolExecutor(max_workers=len(self._peers)) as executor:
            for peer in self._peers:
                executor.submit(Parent._send_message, msg, peer['address'])

    @staticmethod
    def _send_request(req, addr):
        """Send request to a single node"""
        try:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect(addr)
            client_sock.sendall(req.encode())
            reply = client_sock.recv(4096).decode()
        finally:
            client_sock.close()
        return reply

    @staticmethod
    def _send_message(msg, address):
        """Send transaction to a single node"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(address)
            client.sendall(msg.encode())
        finally:
            client.close()
