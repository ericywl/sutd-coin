"""Adversary classes declaration file"""
import sys
import time
import threading
import json
import queue
import os.path

from miner import Miner, _MinerListener


class SelfishMiner(Miner):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""
    BE_SELFISH = True

    def __init__(self, privkey, pubkey, address):
        super().__init__(privkey, pubkey, address, listen=False)
        self.withheld_blocks = queue.Queue()
        # Listener
        if SelfishMiner.BE_SELFISH:
            self._listener = _SelfishMinerListener(address, self)
        else:
            self._listener = _MinerListener(address, self)
        threading.Thread(target=self._listener.run).start()

    def push_blocks(self, num):
        """Push out num blocks from withheld blocks"""
        if num > self.withheld_blocks.qsize():
            raise Exception("Not enough withheld blocks.")
        for _ in range(num):
            fker = self.withheld_blocks.get()
            b_msg = json.dumps({"blk_json": fker.to_json()})
            self.broadcast_message("b" + b_msg)
            self.broadcast_message("h" + json.dumps(fker.header))
            print(f"Block pushed by {self.__class__.__name__} - {self.name}")

    def _broadcast_block(self, block):
        if SelfishMiner.BE_SELFISH:
            self.withheld_blocks.put(block)
        else:
            super()._broadcast_block(block)


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
    while not os.path.exists("mine_lock"):
        time.sleep(0.5)
    while True:
        miner.create_block()
        print(miner.balance)
        time.sleep(1)


if __name__ == "__main__":
    main()
