from block import *
import algo

import statistics

class Blockchain:
    def __init__(self, hash_block_map, endhash_clen_map):
        self._hash_block_map = hash_block_map
        self._endhash_clen_map = endhash_clen_map

    @classmethod
    def new(cls):
        genesis = Block.get_genesis()
        genesis_hash = algo.hash2_dic(genesis.header)
        hash_block_map = { genesis_hash: genesis }
        # Keep track of end blocks and chain length
        endhash_clen_map = { genesis_hash: 0 }
        return cls(hash_block_map, endhash_clen_map)

    # Compute chain length from block (not including genesis)
    def _get_chain_length(self, block):
        prev_hash = block.header["prev_hash"]
        chain_len = 0
        while prev_hash != Block.get_genesis().header["prev_hash"]:
            for b in self._hash_block_map.values():
                if prev_hash == algo.hash2_dic(b.header):
                    prev_hash = b.header["prev_hash"]
                    chain_len += 1
                    break
        return chain_len

    # Compute proof of work of chain from last block
    def _get_chain_pow(self, block):
        prev_hash = block.header["prev_hash"]
        chain_pow = block.header["nonce"]
        while prev_hash != Block.get_genesis().header["prev_hash"]:
            for b in self._hash_block_map.values():
                if prev_hash == algo.hash2_dic(b.header):
                    prev_hash = b.header["prev_hash"]
                    chain_pow += b.header["nonce"]
                    break
        return chain_pow

    # Add new block to chain
    def add(self, block):
        # Verify block
        self.verify(block)
        curr_hash = algo.hash2_dic(block.header)
        prev_hash = block.header["prev_hash"]
        self._hash_block_map[curr_hash] = block
        # If the previous block is one of the last blocks,
        # replace the previous hash out with the current one
        # ie. make the current block be one of the last blocks,
        # and increment its chain length
        if prev_hash in self._endhash_clen_map.keys():
            chain_len = self._endhash_clen_map.pop(prev_hash)
            self._endhash_clen_map[curr_hash] = chain_len + 1
        # Else, compute the chain length by traversing backwards
        # and add the current block hash into dictionary
        else:
            self._endhash_clen_map[curr_hash] = self._get_chain_length(block)

    # Check block with prev_hash exist in list
    def _check_prev_exist(self, prev_hash):
        try:
            b = self._hash_block_map[prev_hash]
        except KeyError:
            return False
        else:
            return True

    # Check if previous block is valid
    def _check_prev_valid(self, prev_hash):
        prev_block = self._hash_block_map[prev_hash]
        try:
            prev_block.validate()
            prev_block.verify()
        except Exception as e:
            return False
        else:
            return True

    # Check timestamp larger than previous block timestamp
    def _check_timestamp(self, block):
        prev_hash = block.header["prev_hash"]
        prev_block = self._hash_block_map[prev_hash]
        return block.header["timestamp"] > prev_block.header["timestamp"]

    # Check if block contains transactions that are already in chain
    def _check_trans_in_chain(self, blk_transactions):
        trans_set = set(self.transactions)
        blk_trans_set = set(blk_transactions)
        num_b_transactions = len(blk_trans_set)
        remaining_transactions = blk_trans_set - trans_set
        return len(remaining_transactions) == num_b_transactions

    def _check_accmap_state(self, prev_hash):
        return True

    # Verify the block
    def verify(self, block):
        # Check previous block exist in blocks list
        if not self._check_prev_exist(block.header["prev_hash"]):
            raise Exception("Previous block does not exist.")
        # Check that previous block is valid
        if not self._check_prev_valid(block.header["prev_hash"]):
            raise Exception("Previous block is invalid.")
        # Check timestamp in block header
        if not self._check_timestamp(block):
            raise Exception("Invalid timestamp in block.")
        # Verify and validate block (self-contained)
        block.validate()
        block.verify()
        # Check transactions in blockchain not reused in block
        if not self._check_trans_in_chain(block.transactions):
            raise Exception("Transaction is already in the blockchain.")
        # Check nonce is not reused
        return True

    # Convenience function for lambda in resolve()
    def _pow(block_hash):
        return self._get_chain_pow(self._hash_block_map[block_hash])

    # Resolve potential forks in block and return last block
    def resolve(self):
        # No forks
        if len(self._endhash_clen_map) == 1:
            blk_hash = list(self._endhash_clen_map.keys())[0]
            return self._hash_block_map[blk_hash]
        # Get hashes of end-blocks with longest chain length
        longest_clen = max(self._endhash_clen_map.values())
        block_hashes = [
            k for k, v in self._endhash_clen_map.items() if v == longest_clen
        ]
        # Multiple chain with same length exist,
        # use PoW ie. nonce to determine which to keep
        if len(block_hashes) != 1:
            block_hashes = [ max(block_hashes, key=lambda bh: self._pow(bh)) ]
        # Remove all blocks beloging to forks
        blk_hash = block_hashes[0]
        blk = self._hash_block_map[blk_hash]
        new_hash_block_map = { blk_hash: blk }
        prev_hash = blk.header["prev_hash"]
        while prev_hash != Block.get_genesis().header["prev_hash"]:
            b = self._hash_block_map[prev_hash]
            new_hash_block_map[prev_hash] = b
            prev_hash = b.header["prev_hash"]
        self._endhash_clen_map = { block_hashes[0]: longest_clen }
        self._hash_block_map = new_hash_block_map
        return blk

    @property
    def blocks(self):
        return list(self._hash_block_map.values())

    @property
    def transactions(self):
        res = []
        for b in self.blocks:
            for t in b.transactions:
                res.append(t)
        return res

    @property
    def hash_block_map(self):
        return self._hash_block_map

    @property
    def endhash_clen_map(self):
        return self._endhash_clen_map


def main():
    blockchain = Blockchain.new()
    hashes = []
    # Generate 10 blocks with 10 transactions per block
    for i in range(10):
        print("Creating block {}...".format(i))
        transactions = generate_transactions(10)
        prev_block = blockchain.resolve()
        prev_hash = algo.hash2_dic(prev_block.header)
        new_block = Block.new(prev_hash, transactions)
        hashes.append(algo.hash2_dic(new_block.header))
        blockchain.add(new_block)
    # Introduce fork
    prev_hash = hashes[2]
    for i in range(4):
        print("Creating fork block {}...".format(i))
        transactions = generate_transactions(10)
        fork_block = Block.new(prev_hash, transactions)
        blockchain.add(fork_block)
        prev_hash = algo.hash2_dic(fork_block.header)
    # Try to resolve
    print("Pre-resolve: " + str(blockchain.endhash_clen_map))
    last_blk = blockchain.resolve()
    print("Post-resolve: " + str(blockchain.endhash_clen_map))
    print("Last block hash: " + algo.hash2_dic(last_blk.header))

if __name__ == "__main__":
    from transaction import *
    from merkle_tree import *
    import ecdsa
    main()

