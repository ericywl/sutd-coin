"""Adversary classes declaration file"""
import sys
import time
import threading
import json
import queue
# import random
import ecdsa

import algo

from block import Block
from miner import Miner, _MinerListener, main_send_transaction


class SelfishMiner(Miner):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""

    def _clsname(self):
        return "SelfishMiner"

    def __init__(self, privkey, pubkey, address, be_ass=True):
        super().__init__(privkey, pubkey, address, listen=False)
        self._be_ass = be_ass
        self.withheld_blocks = queue.Queue()
        # Listener
        if be_ass:
            self._listener = _SelfishMinerListener(address, self)
        else:
            self._listener = _MinerListener(address, self)
        threading.Thread(target=self._listener.run).start()

    @classmethod
    def new(cls, address, be_ass):
        """Create new SelfishMiner instance"""
        signing_key = ecdsa.SigningKey.generate()
        verifying_key = signing_key.get_verifying_key()
        privkey = signing_key.to_string().hex()
        pubkey = verifying_key.to_string().hex()
        return cls(privkey, pubkey, address, be_ass)

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
        if self._be_ass:
            self.withheld_blocks.put(block)
        else:
            self.broadcast_message("b" + json.dumps({"blk_json": blk_json}))
            self.broadcast_message("h" + json.dumps(block.header))
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
    def __init__(self, server_addr, worker):
        super().__init__(server_addr, worker)
        self._blk_queue = queue.Queue()

    def _push_blocks(self, num):
        """Push out num blocks from withheld blocks"""
        if num > self._worker.withheld_blocks.qsize():
            raise Exception("Not enough withheld blocks.")
        for _ in range(num):
            fker = self._worker.withheld_blocks.get()
            b_msg = json.dumps({"blk_json": fker.to_json()})
            self._worker.broadcast_message("b" + b_msg)
            self._worker.broadcast_message("h" + json.dumps(fker.header))
            print(f"Block is pushed by selfish miner - {self._worker.name}")
            time.sleep(0.2)

    def _handle_block(self, data):
        # Receive new block
        # Purposely broadcast own blocks if more than 1
        delta = self._worker.withheld_blocks.qsize()
        if delta == 0:
            with self._worker._blockchain_lock:
                for _ in range(self._blk_queue.qsize()):
                    old_data = self._blk_queue.get()
                    super()._handle_block(old_data)
                super()._handle_block(data)
        elif delta == 2:
            self._push_blocks(2)
            self._blk_queue.put(data)
        else:
            self._push_blocks(1)
            self._blk_queue.put(data)


def main():
    """Main function"""
    # Execute miner routine
    miner = SelfishMiner.new(("127.0.0.1", int(sys.argv[1])), be_ass=False)
    miner.startup()
    print(f"SelfishMiner established connection with {len(miner.peers)} peers")
    time.sleep(5)
    print(len(miner.peers))
    while True:
        # main_send_transaction(miner)
        miner.create_block()


if __name__ == "__main__":
    main()
