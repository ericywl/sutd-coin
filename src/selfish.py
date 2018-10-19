"""Adversary classes declaration file"""
import sys
import time
import json
import queue
import os.path

from miner import Miner, _MinerListener


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
            # Handle any other protocols
            super().handle_client_data(data, client_sock)


class SelfishMiner(Miner):
    """☠️ ☠️ ☠️ ☠️ ☠️ ☠️ ☠️"""
    BE_SELFISH = True

    def __init__(self, privkey, pubkey, address):
        if SelfishMiner.BE_SELFISH:
            super().__init__(privkey, pubkey, address, _SelfishMinerListener)
        else:
            super().__init__(privkey, pubkey, address)
        self.withheld_blocks = queue.Queue()

    def push_blocks(self, num):
        """Push out num blocks from withheld blocks"""
        if num > self.withheld_blocks.qsize():
            raise Exception("Not enough withheld blocks.")
        # Get num blocks from queue and publish them
        for _ in range(num):
            blk = self.withheld_blocks.get()
            b_msg = json.dumps({"blk_json": blk.to_json()})
            self.broadcast_message("b" + b_msg)
            self.broadcast_message("h" + json.dumps(blk.header))
            print(f"Block pushed by {self.__class__.__name__} - {self.name}")

    def _broadcast_block(self, block):
        if SelfishMiner.BE_SELFISH:
            self.withheld_blocks.put(block)
        else:
            super()._broadcast_block(block)


def main():
    """Main function"""
    # Execute miner routine
    miner = SelfishMiner.new(("127.0.0.1", int(sys.argv[1])))
    miner.startup()
    while not os.path.exists("mine_lock"):
        time.sleep(0.5)
    while True:
        miner.create_block()
        print("SelfishMiner balance state:", miner.verbose_balance)
        time.sleep(1)


if __name__ == "__main__":
    main()
