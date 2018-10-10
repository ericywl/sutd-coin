"""Observer that doesn't participate in mining"""
import sys
import time
import threading

from miner import Miner
from block import Block


class Observer(Miner):
    """Oberver class"""

    def _clsname(self):
        return "Observer"

    def __init__(self, privkey, pubkey, address):
        super().__init__(privkey, pubkey, address)
        self.blk_count_lock = threading.RLock()
        self.blk_count = 0

    def add_block(self, blk_json):
        """Add new block to the blockchain"""
        block = Block.from_json(blk_json)
        self._blockchain_lock.acquire()
        try:
            self._blockchain.add(block)
        finally:
            self._blockchain_lock.release()
        self._update()
        with self.blk_count_lock:
            self.blk_count += 1


def main():
    """Main function"""
    # Execute miner routine
    obs = Observer.new(("127.0.0.1", int(sys.argv[1])))
    obs.startup()
    print(f"Observer established connection with {len(obs.peers)} peers")
    time.sleep(5)
    print(len(obs.peers))
    while True:
        if obs.blk_count == 100:
            name_balance = {}
            for key, val in obs.balance.items():
                items = [x for x in obs.peers if x["pubkey"] == key]
                if items:
                    item = items[0]
                    name_balance[item["name"]] = val
            print(name_balance)
            break


if __name__ == "__main__":
    main()
