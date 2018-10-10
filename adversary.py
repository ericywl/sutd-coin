"""definition"""
import sys
import time
import threading
import json
import ecdsa

import algo

from block import Block
from miner import Miner, _MinerListener


class SelfishMiner(Miner):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""

    def __init__(self, privkey, pubkey, address):
        super().__init__(privkey, pubkey, address, False)
        self._selfishfuckers = []
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

    def create_block(self):
        """Create a new block, but don't add it to blockchain"""
        # Update blockchain and balance state (thread safe)
        last_blk = self._update()
        # Get a set of random transactions from pending transactions
        self._added_tx_lock.acquire()
        self._all_tx_lock.acquire()
        try:
            pending_tx = self._all_transactions - self._added_transactions
            gathered_tx = self._gather_transactions(pending_tx)
        finally:
            self._added_tx_lock.release()
            self._all_tx_lock.release()
        # Mine new block
        prev_hash = algo.hash1_dic(last_blk.header)
        block = Block.new(prev_hash, gathered_tx, self._stop_mine)
        if block is None:
            # Mining stopped because a new block is received
            return None
        blk_json = block.to_json()
        # Add block to blockchain (thread safe)
        self.add_block(blk_json)
        self._selfishfuckers.append(block)
        # Remove gathered transactions from pool and them to added pile
        self._added_tx_lock.acquire()
        try:
            self._added_transactions |= set(gathered_tx)
        finally:
            self._added_tx_lock.release()
            print("{} created a block.".format(self._name))
        return block

class _SelfishMinerListener(_MinerListener):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""

    def push_block(self, fucker):
        self._miner._broadcast_message("b" + json.dumps({"blk_json": fucker.to_json()}))
        self._miner._broadcast_message("h" + json.dumps(fucker.header))
        print("Block is pushed by fucker - {}".format(self._miner.name))

    def handle_client(self, client_sock):
        """Handle receiving and sending"""
        data = client_sock.recv(4096).decode()
        prot = data[0].lower()
        if prot == "b":
            # purposefully submit their own blocks
            if len(self._miner._selfishfuckers) >= 3:
                # be greedy and pop only the first one
                fucker = self._miner._selfishfuckers.pop(0)
                self.push_block(fucker)
            elif self._miner._selfishfuckers:
                for fucker in self._miner._selfishfuckers:
                    self.push_block(fucker)
                    time.sleep(0.5)
            self._miner._selfishfuckers = []
            client_sock.close()
        else:
            super().handle_client_data(data, client_sock)

if __name__ == "__main__":
    # Execute miner routine
    miner = SelfishMiner.new(("127.0.0.1", int(sys.argv[1])))
    miner.startup()
    print("SelfishMiner established connection with {} peers".format(len(miner.peers)))
    while True:
        # if miner.pubkey in miner.balance:
        #     if miner.balance[miner.pubkey] > 50:
        #         peer_index = random.randint(0, len(miner.peers) - 1)
        #         miner.create_transaction(miner.peers[peer_index]["pubkey"], 50)
        # time.sleep(5)
        miner.create_block()