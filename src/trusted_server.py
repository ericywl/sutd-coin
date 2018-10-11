"""Trusted Server class declaration file"""
from concurrent.futures import ThreadPoolExecutor
import threading
import socket
import json

import algo


class TrustedServer:
    """
    This TrustedServer is a Node in the network that stores a list of Nodes.
    Currently it is singleton.
    """
    HOST = "localhost"
    PORT = 44444

    def __init__(self):
        print("Starting Trusted server..")
        self._addresses = []
        # Host here is different from TrustedServer.HOST
        # because it's local to the server
        self._listener = _TrustedServerListener(
            ("localhost", TrustedServer.PORT), self)
        threading.Thread(target=self._listener.run).start()

    def add_address(self, address):
        """Add address to list if not already in list"""
        if address not in self._addresses:
            self._addresses.append(address)

    @property
    def addresses(self):
        """List of node addresses"""
        return self._addresses

    def broadcast_address(self, req):
        """Broadcast the new address to peers"""
        with ThreadPoolExecutor(max_workers=len(self.addresses)) as executor:
            for node in self.addresses:
                executor.submit(TrustedServer._send_address,
                                req, node['address'])

    @staticmethod
    def _send_address(msg, address):
        """Send address to a single node"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(address)
            client.sendall(msg.encode())
        finally:
            client.close()


class _TrustedServerListener:
    """Trusted Server's Listener class"""

    def __init__(self, server_addr, trusted_server):
        self._server_addr = server_addr
        self._trusted_server = trusted_server
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
        data = client_sock.recv(algo.BUFSIZE).decode()
        prot = data[0].lower()
        if prot == "a":
            # Receive a request for addresses
            msg = "a" + json.dumps(
                {"addresses": self._trusted_server.addresses})
            client_sock.sendall(msg.encode())
            client_sock.close()
        elif prot == "n":
            # We are assuming that all messages are legitimate.
            # should probably have a challenge to ensure that it is indeed
            # either a miner or spv_client instead of adding the address
            # blindly pubkey is spread here to simulate transactions in miner.
            node_address = json.loads(data[1:])
            node_address["address"] = tuple(node_address["address"])
            self._trusted_server.add_address(node_address)
            # Broadcast to the rest of the nodes
            self._trusted_server.broadcast_address(
                "n" + json.dumps(node_address))
            client_sock.close()


if __name__ == "__main__":
    TrustedServer()
