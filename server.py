import socket
import json
import threading


class Server:
    """Server class"""
    def __init__(self, server_addr, worker):
        self._server_addr = server_addr
        self._worker = worker
        # TCP socket configuration
        self._tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_sock.bind(server_addr)
        self._tcp_sock.listen(5)

    def run(self):
        """Start the server"""
        while True:
            conn, _ = self._tcp_sock.accept()
            # Start new thread to handle client
            new_thread = threading.Thread(target=self.handle_client,
                                          args=[conn])
            new_thread.start()

    def handle_client(self, client_sock):
        """Handle receiving and sending"""
        data = client_sock.recv(4096).decode()
        if data[0].lower() == "t":
            # Receive new transaction
            t_json = data[1:]
            client_sock.close()
            self._worker.add_transaction(t_json)
        elif data[0].lower() == "b":
            # Receive new block
            b_json = data[1:]
            client_sock.close()
            # Stop mining if new block is received
            self._worker.stop_mine.set()
            self._worker.add_block(b_json)
            self._worker.stop_mine.clear()
        elif data[0].lower() == "r":
            # Process request for transaction proof
            tup = self._worker.get_transaction_proof()
            if tup is None:
                msg = json.dumps({"blk_hash": None, "proof": None})
            else:
                msg = json.dumps({"blk_hash": tup[0], "proof": tup[1]})
            client_sock.send(msg)
            client_sock.close()
        else:
            print("Wrong message format")
            client_sock.close()

    @property
    def server_addr(self):
        """Server address which contains IP and port"""
        return self._server_addr
