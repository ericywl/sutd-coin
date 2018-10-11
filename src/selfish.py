"""Adversary classes declaration file"""
import sys
import time
import threading
import json
import queue
# import random
import ecdsa

from miner import Miner, _MinerListener, miner_main_send_tx


BE_SELFISH = True


class SelfishMiner(Miner):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""

    def _clsname(self):
        return "SelfishMiner"

    def __init__(self, privkey, pubkey, address):
        super().__init__(privkey, pubkey, address, listen=False)
        self.withheld_blocks = queue.Queue()
        # Listener
        if BE_SELFISH:
            self._listener = _SelfishMinerListener(address, self)
        else:
            self._listener = _MinerListener(address, self)
        threading.Thread(target=self._listener.run).start()

    def create_block(self):
        """Create a new block"""
        # Update blockchain and balance state (thread safe)
        last_blk = self._update()
        gathered_tx = self._gather_transactions()
        block = self._mine_new_block(last_blk.header, gathered_tx)
        blk_json = block.to_json()
        # Add block to blockchain (thread safe)
        self.add_block(blk_json)
        if BE_SELFISH:
            self.withheld_blocks.put(block)
        else:
            self.broadcast_message("b" + json.dumps({"blk_json": blk_json}))
            self.broadcast_message("h" + json.dumps(block.header))
        # Remove gathered transactions from pool and them to added pile
        with self._added_tx_lock:
            self._added_transactions |= set(gathered_tx)
        self._update()
        print(f"{self._clsname()} {self.name} created a block.")
        return block

    def push_blocks(self, num):
        """Push out num blocks from withheld blocks"""
        if num > self.withheld_blocks.qsize():
            raise Exception("Not enough withheld blocks.")
        for _ in range(num):
            fker = self.withheld_blocks.get()
            b_msg = json.dumps({"blk_json": fker.to_json()})
            self.broadcast_message("b" + b_msg)
            self.broadcast_message("h" + json.dumps(fker.header))
            print(f"Block is pushed by selfish miner - {self._worker.name}")
            time.sleep(0.5)


class _SelfishMinerListener(_MinerListener):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""

    def handle_client_data(self, data, client_sock):
        """Handle receiving and sending"""
        prot = data[0].lower()
        if prot == "b":
            # Purposefully broadcast their own blocks when receive
            qlen = self._worker.withheld_blocks.qsize()
            if qlen >= 3:
                self._worker.push_blocks(2)
            elif qlen != 0:
                self._worker.push_blocks(qlen)
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
        # miner_main_send_tx(miner)
        miner.create_block()
        print(miner.balance)


if __name__ == "__main__":
    main()
