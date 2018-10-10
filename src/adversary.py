"""Adversary classes declaration file"""
import sys
import time
import threading
import json
# import random
import ecdsa

import algo

from block import Block
from miner import Miner, _MinerListener, main_send_transaction


class SelfishMiner(Miner):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""

    def __init__(self, privkey, pubkey, address):
        super().__init__(privkey, pubkey, address, listen=False)
        self.withheld_blocks = []
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
        self.withheld_blocks.append(block)
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

    def _push_blocks(self, num):
        """Push out num blocks from withheld blocks"""
        if num > len(self._worker.withheld_blocks):
            raise Exception("Not enough withheld blocks.")
        for _ in range(num):
            fker = self._worker.withheld_blocks.pop(0)
            b_msg = json.dumps({"blk_json": fker.to_json()})
            self._worker.broadcast_message("b" + b_msg)
            self._worker.broadcast_message("h" + json.dumps(fker.header))
            print(f"Block is pushed by selfish miner - {self._worker.name}")
            time.sleep(0.5)

    def handle_client(self, client_sock):
        """Handle receiving and sending"""
        data = client_sock.recv(4096).decode()
        prot = data[0].lower()
        if prot == "b":
            # Purposefully broadcast their own blocks when receive
            if len(self._worker.withheld_blocks) >= 3:
                self._push_blocks(2)
            elif self._worker.withheld_blocks:
                self._push_blocks(len(self._worker.withheld_blocks))
            self._handle_block(data, client_sock)
        else:
            super().handle_client_data(data, client_sock)


def main():
    """Main function"""
    # Execute miner routine
    miner = SelfishMiner.new(("127.0.0.1", int(sys.argv[1])))
    miner.startup()
    print(f"SelfishMiner established connection with {len(miner.peers)} peers")
    time.sleep(5)
    while True:
        # main_send_transaction(miner)
        miner.create_block()
        print(miner.balance)


if __name__ == "__main__":
    main()
