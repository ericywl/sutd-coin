import threading
import ecdsa

from miner import Miner, _MinerListener


class SelfishMiner(Miner):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""

    def __init__(self, privkey, pubkey, address):
        super().__init__(privkey, pubkey, address)
        # Listener
        self._listener = _SelfishMinerListener(address, self)
        threading.Thread(target=self._listener.run).start()

    @classmethod
    def new(cls, address):
        """Create new SelfishMiner instance"""
        signing_key = ecdsa.SigningKey.generate()
        verifying_key = signing_key.get_verifying_key()
        privkey = signing_key.to_string().hex()
        pubkey = verifying_key.to_string().hex()
        return cls(privkey, pubkey, address)


class _SelfishMinerListener(_MinerListener):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""

    def handle_client(self, client_sock):
        """Handle receiving and sending"""
        data = client_sock.recv(4096).decode()
        prot = data[0].lower()
        if prot == "b":
            # purposefully submit their own blocks
            pass
        else:
            super().handle_client_data(data, client_sock)
