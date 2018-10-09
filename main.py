"""Main class"""
from concurrent.futures import ThreadPoolExecutor
import time
import threading
import random
import itertools

from typing import List, Tuple

import algo
from miner import Miner
from spv_client import SPVClient


pubkey_index_map: dict = {}
tx_index_map: dict = {}
# Thread lock just to be safe
LOCK = threading.RLock()
Network = Tuple[List[Miner], List[SPVClient]]


def create_coin_network(
        num_miners: int, num_spv: int, starting_port: int) -> Network:
    """Create a network with miners and SPV clients"""
    if num_miners < 2:
        raise Exception("Network must have at least 2 miners")
    if num_spv < 1:
        raise Exception("Network must have at least 1 SPV client.")
    nodes = []
    for i in range(num_miners + num_spv):
        addr = ("localhost", starting_port + i)
        if i < num_miners:
            nodes.append(Miner.new(addr))
            pubkey_index_map[nodes[i].pubkey] = i + 1
        else:
            nodes.append(SPVClient.new(addr))
            pubkey_index_map[nodes[i].pubkey] = i + 1 - num_miners
    for node, other_node in itertools.permutations(nodes, 2):
        node.add_peer(other_node.address)
    return nodes[:num_miners], nodes[num_miners:]

def miner_run(miner: Miner):
    """Execute miner routine"""
    miner_index = pubkey_index_map[miner.pubkey]
    # Create new transaction
    if miner.pubkey in miner.balance:
        if miner.balance[miner.pubkey] > 50:
            peer_index = random.randint(0, len(miner.peers) - 1)
            peer = miner.peers[peer_index]
            index = pubkey_index_map[peer.pubkey]
            tx_json = miner.create_transaction(peer.pubkey, 50).to_json()
            tx_hash = algo.hash1(tx_json)
            LOCK.acquire()
            try:
                tx_index_map[tx_hash] = len(tx_index_map) + 1
                tx_index = tx_index_map[tx_hash]
            finally:
                LOCK.release()
            peer_str = f"Miner {index}" if isinstance(peer, Miner) \
                       else f"SPV {index}"
            print(f"Miner {miner_index} send TX{tx_index} to {peer_str}")
    time.sleep(5)
    # Miner new block
    blk = miner.create_block()
    if blk is None:
        print(f"Miner {miner_index} stopped mining")
    else:
        print(f"Miner {miner_index} mined block")


def spv_client_run(spv_client: SPVClient):
    """Execute SPV client routine"""
    spv_index = pubkey_index_map[spv_client.pubkey]
    # Request transaction proof
    transactions = spv_client.transactions
    if transactions:
        i = random.randint(0, len(transactions) - 1)
        tx_hash = algo.hash1(transactions[i])
        LOCK.acquire()
        try:
            tx_index = tx_index_map[tx_hash]
        finally:
            LOCK.release()
        tx_in_bc = spv_client.verify_transaction_proof(tx_hash)
        print(f"SPV {spv_index} check TX{tx_index} in blockchain: {tx_in_bc}")
    time.sleep(1)
    # Create new transaction
    bal = spv_client.request_balance()
    if bal > 10:
        peer_index = random.randint(0, len(spv_client.peers) - 1)
        peer = spv_client.peers[peer_index]
        index = pubkey_index_map[peer.pubkey]
        tx_json = spv_client.create_transaction(peer.pubkey, 10).to_json()
        tx_hash = algo.hash1(tx_json)
        LOCK.acquire()
        try:
            tx_index_map[tx_hash] = len(tx_index_map) + 1
            tx_index = tx_index_map[tx_hash]
        finally:
            LOCK.release()
        peer_str = f"Miner {index}" if isinstance(peer, Miner) \
                   else f"SPV {index}"
        print(f"SPV {spv_index} send TX{tx_index} to {peer_str}")


def parallel_nodes_run(miners: List[Miner], spv_clients: List[SPVClient]):
    """Run SPV client routine in parallel"""
    num_nodes = len(miners) + len(spv_clients)
    with ThreadPoolExecutor(max_workers=num_nodes) as executor:
        for miner in miners:
            executor.submit(miner_run, miner)
        for spv in spv_clients:
            executor.submit(spv_client_run, spv)
    time.sleep(3)
    print(f"Blockchain ends: {miners[0].blockchain.endhash_clen_map}\n")

if __name__ == "__main__":
    miners, spv_clients = create_coin_network(4, 4, 12345)
    for _ in range(7):
        parallel_nodes_run(miners, spv_clients)
