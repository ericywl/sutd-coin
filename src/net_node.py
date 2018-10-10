"""NetNode class declaration file"""
from concurrent.futures import ThreadPoolExecutor
import json
import socket
import threading

from monsterurl import get_monster
from trusted_server import TrustedServer


def recvall_helper(sock, bufsize=4096):
    """Helper function to receive all bytes from socket"""
    fragments = []
    while True:
        frgm = sock.recv(bufsize)
        if not frgm:
            break
        fragments.append(frgm.decode())
    return "".join(fragments)


class NetNode:
    """NetNode class"""
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
        reply = NetNode._send_request(
            "a", (TrustedServer.HOST, TrustedServer.PORT))
        prot = reply[0].lower()
        if prot == "a":
            # sent by the central server when requested for a list of addresses
            addresses = json.loads(reply[1:])["addresses"]
            self.set_peers(addresses)
        # print(f"Established connections with {len(self._peers)} nodes")
        data = {
            "address": self.address,
            "pubkey": self.pubkey,
            "name": self.name
        }
        NetNode._send_message("n" + json.dumps(data),
                              (TrustedServer.HOST, TrustedServer.PORT))

    def broadcast_message(self, msg):
        """Broadcast the message to peers"""
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        if not self._peers:
            raise Exception("Not connected to network.")
        with ThreadPoolExecutor(max_workers=5) as executor:
            for peer in self._peers:
                executor.submit(NetNode._send_message, msg, peer['address'])

    @staticmethod
    def _send_request(req, addr):
        """Send request to a single node"""
        try:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect(addr)
            client_sock.sendall(req.encode())
            reply = recvall_helper(client_sock)
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


class _NetNodeListener:
    """NetNodeListener class"""

    def __init__(self, server_addr, worker):
        self._server_addr = server_addr
        self._worker = worker
        # TCP socket configuration
        self._tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_sock.bind(server_addr)
        self._tcp_sock.listen(5)

    def run(self):
        """Start the listener"""
        while True:
            conn, _ = self._tcp_sock.accept()
            # Start new thread to handle client
            new_thread = threading.Thread(target=self.handle_client,
                                          args=[conn])
            new_thread.start()

    def handle_client(self, client_sock):
        """Handle receiving and sending"""
        data = recvall_helper(client_sock)
        self.handle_client_data(data, client_sock)

    def handle_client_data(self, data, client_sock):
        """To be overwritten when extending"""
        raise Exception("Override handle_client_data when extending "
                        + "from _NetNodeListener")
