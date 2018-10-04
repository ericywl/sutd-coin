"""MerkleTree class declaration file"""
import math
import random
from collections import deque

import algo


class MerkleTree:
    """MerkleTree class"""
    class Node:
        """Node class"""

        def __init__(self, id_no, left, right, hash_val):
            self._id = id_no
            self.left = left
            self.right = right
            self.hash_val = hash_val
            self.parent = None
            self.height = left.height + 1 if left is None else 0

        # Return id string for test purposes
        def __str__(self):
            return str(self._id)

        @property
        def id_no(self):
            """ID number"""
            return self._id

    def __init__(self, items=None):
        if items is None:
            items = []
        self.is_built = False
        self.leaves_map = self._hash_items(items)
        self.tree_height \
            = math.ceil(math.log(len(items), 2)) if items else 0
        self.root = None
        self.build()

    # Create hash table from list of items
    def _hash_items(self, items):
        # Items should be JSON strings
        res = {}
        for i in enumerate(items):
            item = items[i]
            item_hash = algo.hash1(item)
            item_node = self.Node(i + 1, None, None, item_hash)
            res[item] = item_node
        return res

    @staticmethod
    def _concat_hash(left, right):
        """Hash the concatenation of hashes in left and right node"""
        return algo.hash1(left.hash_val + right.hash_val)

    def add(self, entry):
        """Add entries to tree"""
        entry_hash = algo.hash1(entry)
        entry_node = self.Node(len(self.leaves_map) + 1,
                               None, None, entry_hash)
        self.leaves_map[entry] = entry_node
        self.tree_height = math.ceil(math.log(len(self.leaves_map), 2))
        self.root = None
        self.is_built = False

    def build(self):
        """Build tree computing new root"""
        leaves = list(self.leaves_map.values())
        leaves_len = len(leaves)
        if leaves_len <= 0:
            self.is_built = True
            return
        # Reset node height and parent
        for node in leaves:
            node.parent = None
            node.height = 0
        deq = deque(leaves)
        index = leaves_len + 1
        # Single leaf case
        if len(deq) == 1:
            self.root = deq[0]
        while self.root is None:
            if len(deq) >= 2 and deq[0].height == deq[1].height:
                # Pop first two nodes
                left = deq.popleft()
                right = deq.popleft()
                # Create parent node
                node_hash = self._concat_hash(left, right)
                node = self.Node(index, left, right, node_hash)
                index += 1
                left.parent = node
                right.parent = node
                if node.height == self.tree_height:
                    self.root = node
                deq.append(node)
            else:
                # Elevate node in tree and move node to back of deque
                node = deq.popleft()
                node.height += 1
                deq.append(node)
        self.is_built = True

    def get_proof(self, entry):
        """Get membership proof for entry"""
        if not self.is_built:
            self.build()
        proof = []
        node = self.leaves_map[entry]
        while node != self.root:
            parent = node.parent
            if parent.left == node:
                proof.append((parent.right.hash_val, "right"))
            else:
                proof.append((parent.left.hash_val, "left"))
            node = parent
        return proof

    def get_root(self):
        """Return the current root"""
        if not self.is_built:
            self.build()
        return self.root.hash_val if self.root else None


def verify_proof(entry, proof, root):
    """Verifies proof for entry and given root. Returns boolean."""
    temp = algo.hash1(entry)
    for p_hash, direction in proof:
        if direction == "right":
            inp = temp + p_hash
        elif direction == "left":
            inp = p_hash + temp
        else:
            raise Exception("Invalid direction in proofs.")
        temp = algo.hash1(inp)
    return temp == root


def main():
    """Main function"""
    from block import generate_transactions
    trans_strings = []
    tree = MerkleTree()
    print("Generating transactions...")
    transactions = generate_transactions(random.randint(10, 100))
    for t_json in transactions:
        tree.add(t_json)
        trans_strings.append(t_json)
    print("Computing root...")
    root = tree.get_root()
    print("Root: " + root)
    print("Computing proof for random entry...")
    ent = trans_strings[random.randint(0, len(trans_strings) - 1)]
    proof = tree.get_proof(ent)
    print("Proof: " + str(proof))
    ver = verify_proof(ent, proof, root)
    print("Verify: " + ("Success" if ver else "Failure"))


if __name__ == "__main__":
    main()
