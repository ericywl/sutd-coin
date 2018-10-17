# Blockchain Technology
Mid-term project for Blockchain Technology course, all done in Python 3.6.5.

___Note: `.python-version` is for `pyenv` to keep track of local Python
version.___

## Usage
To start the demonstration, use `sudo ./main.sh {OPTIONS}`. The options include
the following:

| Options   | Details                   |
|-----------|---------------------------|
| `-m NUM`  | Create NUM miners         |
| `-s NUM`  | Create NUM SPV clients    |
| `-f`      | Create one selfish miner  |

For double spending, we will be using `python src/double_spend.py` for a
sequential demonstration because the results are more obvious compared to
in a multi-process case and it is also easier to implement.

___Note: At least 2 miners should be included when running the simulation.___

## Mining and Coin Creation

Mining is demonstrated in `sudo ./main.sh -m NUM`. Using the demonstration,
we can see multiple miners competing with each other to append to the
blockchain. Occasionally, two or more miners will create blocks at the same
time, resulting in forks. This is resolved through fork resolution, which will
be discussed later.

The coin creation is done by having miners compete to create the first 
block with no transactions in it. The first miner that creates a block will
be the miner that gets the first coins in the network. This is because adding
blocks to the blockchain will reward the miner, which in this case means the
generation of the first coins.

## Fork Resolution

Fork resolution is implemented in `blockchain.py:resolve`. The blockchain 
object maintains a list of tails whenever a block is added. This list is 
used afterwards to find a chain that has the longest length in terms of 
blocks - the shorter chains are "removed", resolving the fork. If chains 
of similar length are found, we simulate a pseudo **proof of work** by summing 
the hash values in a chain to determine which chain to accept ie. the 
chain with the lowest cummulative hash will be accepted.

Fork Resolution is demonstrated with `python src/blockchain.py`.

## Transaction Resending Protection

Transaction resending protection is achieved by adding a 4-byte nonce onto the
transaction object. Therefore, two transactions with the exact same sender, 
receiver, amount and comment will still be differentiable from each other. 
When a block is added to the blockchain, the miner compares the previous 
transactions in the blockchain and the transactions in the added block to
ensure that the same transaction cannot be included twice.

Transaction Resending Protection is also demonstrated with 
`python src/blockchain.py`.

## Payments between Miners and SPV Clients

This is demonstrated with `sudo ./main.sh -m NUM1 -s NUM2`. 
Setting a random number of miners and SPV clients will enable them to 
send random transactions to one another. The miners will mine blocks and get
rewarded for their mining, and will then use the reward to send transactions
to others. The SPV clients will try to verify transactions by requesting
transaction proof, if they have transactions, as well as send random 
transactions to others, if they have any coins.

## Attacks

### Double-Spending

Demonstrated with `python src/double_spend.py`. The following is a
step-by-step description of what happens in the demonstration. In this
scenario, **BadMiner** and **BadSPVClient** can be the same person but with
different accounts.

1. **BadMiner** is initialized with an arbitary amount of coins (through first
   block mining).
2. **BadMiner** sends X amount to a **BadSPVClient** and the transaction is
   validated by any miner.
3. When **BadSPVClient** receives the coins, **BadMiner** starts their own private fork. **BadSPVClient** spends X amount at a **Vendor**, 
   leaving him with nothing. The block, with the aforementioned transaction, 
   is mined by any miner.
4. **Vendor** authorizes the request and sends over an iPad 
   (let's imagine this happening).
5. **BadSPVClient** then creates a transaction that directs X amount of coins
   to **BadMiner's** account. (This transaction is also added to **BadMiner**'s private fork)
6. **BadMiner** pushes their own private fork (which will be longer than the main chain), which after being resolved, 
   invalidates the **BadSPV-Vendor** transaction since it is not in the
   blockchain. 
8. **BadSPVClient** has the imaginary iPad sent by Vendor, while **BadMiner** 
   still has the same X amount unspent. **Vendor** can't charge **BadSPV** because 
   the **BadSPV** does not have any coins left.

### Selfish Mining

Demonstrated with `sudo ./main.sh -m 1 -f`. This will create 1 normal miner and
1 selfish miner that will compete with one another for block mining. For the 
tests, we introduced a `BE_SELFISH` class variable to SelfishMiner so as to 
see the difference that selfish mining can make. A 1-on-1 test was chosen 
because it showcases the difference between selfish mining and non-selfish 
mining more clearly. In cases where more miners were involded, the results 
were significantly more chaotic, making it hard to interpret. There are no 
transactions involved as we are using the rewards as an indicator to number 
of blocks mined.

The tests were run with `nice -3` on the tested miner and `nice 0` (default) 
on the other. This means that the tested miner has slightly higher resource
priority in both cases. In real world, this would mean that the tested miner 
has slightly higher computational power and should therefore win the
competition more often than not even without selfish mining. Results are 
collected after the blockchain reach length of 100 ie. the longest chain 
reaches 100 blocks. The table below shows the percentage of reward pool that
a majority miner gets with vs. without selfish mining algorithm. 

| Runs                      | 1    | 2    | 3    | 4    | 5    | 6    | 7    | 8    | Average |
|---------------------------|------|------|------|------|------|------|------|------|---------|
| Normal Mining Reward %    | 56%  | 50%  | 54%  | 55%  | 52%  | 51%  | 51%  | 52%  | 52.625% |
| Selfish Mining Reward %   | 62%  | 65%  | 66%  | 66%  | 63%  | 71%  | 63%  | 67%  | 65.375% |

As we can see from the table above, using selfish mining algorithm increases
the rewards that the miners gets from ~53% to ~65%.


## Major Differences between Bitcoin and SUTDCoin

|                    | Bitcoin                                                               | SUTDCoin              |
|--------------------|-----------------------------------------------------------------------|-----------------------|
| Transaction Model  | UTXO model                                                            | Address:Balance model |
| Spending Coins     | Receivers must fulfill scriptSig or scriptPubKey to spend outputs     | Receivers can spend after transaction is added to blockchain |
| Fork Resolution    | Uses Proof-of-Work and first-come-first-serve if forks have same PoW  | Uses chain length and cummulative hash if forks are same length |
| Timestamp Validity | Timestamp of block has to be larger than median of previous 11 blocks | Timestamp of block has to be larger than previous block |
| Block Difficulty   | Dynamic and changes every 2016 blocks                                 | Static, currently always 000029fffffffff... |
| Market Value       | Can be exchanged for SGD8856 per Bitcoin as of writing                | Absolutely worthless <img src="https://ih0.redbubble.net/image.500553700.1057/sticker,375x360-bg,ffffff.u2.png" width="70"> |


