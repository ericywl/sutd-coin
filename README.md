# Blockchain Technology - SUTDCoin

<img src="https://steamuserimages-a.akamaihd.net/ugc/847091252321971372/B89526245165AFEE7127402085A036967829D278/" width=50>

Mid-term project for Blockchain Technology course, all done in Python 3.6.5.

**_Note: `.python-version` is for `pyenv` to keep track of local Python
version._**

## Pre-resquisites

If using blockchain.ova, you'll need to do `pip install monsterurl` to install a
random name generator that we use to identify nodes.

## Usage

To start the demonstration, use `sudo ./main.sh {OPTIONS}`. The options include
the following:

| Options  | Details                                         |
| -------- | ----------------------------------------------- |
| `-m NUM` | Create NUM miners, where NUM is an integer      |
| `-s NUM` | Create NUM SPV clients, where NUM is an integer |
| `-f`     | Create one selfish miner                        |
| `-d`     | Simulate double spending                        |

**_Notes_**:

-   **_At least 2 miners should be included when running the simulation_**.
-   **_The simulation is not meant to be run with a large number of nodes (e.g. 20)_**

## Mining and Coin Creation

`sudo ./main.sh -m NUM`

Using the demonstration,
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

`python src/blockchain.py`

Fork resolution is implemented in `blockchain.py:resolve`. The blockchain
object maintains a list of tails whenever a block is added. This list is
used afterwards to find a chain that has the longest length in terms of
blocks - the shorter chains are "removed", resolving the fork. If chains
of similar length are found, we simulate a pseudo **proof of work** by
summing the hash values in a chain to determine which chain to accept ie.
the chain with the lowest cummulative hash will be accepted.

We can also see fork resolution in action when running
`sudo ./main.sh -m NUM`. Since multiple miners are competing, there will be
occasions where two (or more) miners mine a new block at the same time, thus
requiring fork resolution.

## Transaction Resending Protection

`python src/blockchain.py`

Transaction resending protection is achieved by adding a 4-byte nonce onto the
transaction object. Therefore, two transactions with the exact same sender,
receiver, amount and comment will still be differentiable from each other.
When a block is added to the blockchain, the miner compares the previous
transactions in the blockchain and the transactions in the added block to
ensure that the same transaction cannot be included twice.

An exception is thrown when an existing transaction is attempted to be
added back into the blockchain.

## Payments between Miners and SPV Clients

`sudo ./main.sh -m NUM1 -s NUM2`

Setting a random number of miners and SPV clients will enable them to
send random transactions to one another. The miners will mine blocks and get
rewarded for their mining, and will then use the reward to send transactions
to others. The SPV clients will try to verify transactions by requesting
transaction proof, if they have transactions, as well as send random
transactions to others, if they have any coins.

## Double-Spending Attack

`sudo ./main.sh -m 1 -d`

The following is a step-by-step description of what happens in the demonstration.
In this scenario, **BadMiner** and **BadSPVClient** can be the same person
but with different accounts.

1. **BadMiner** is initialized with an arbitary amount of coins (through first
   block mining).
2. **BadMiner** sends X amount to a **BadSPVClient** and the transaction is
   validated by any miner.
3. Upon receiving the coins, **BadSPVClient** spends X amount at a **Vendor**,
   leaving him with nothing. The block, with the aforementioned transaction,
   is mined by any miner.
4. **Vendor** authorizes the request and sends over an iPad
   (let's imagine this happening).
5. **BadSPVClient** then creates a transaction that directs X amount of coins
   to **BadMiner's** account.
6. **BadMiner** excludes the **BadSPVClient-Vendor** transaction from his/her
   transaction pool but includes the **BadSPVClient-BadMiner** transaction
   in (5) (which will be valid in the **BadMiner**'s fork), and starts mining
   to create a fork at the block that has the **BadSPV-Vendor** transaction.
7. **BadMiner** pushes a series of blocks, which after being resolved,
   invalidates the **BadSPV-Vendor** transaction since it is not in the
   blockchain.
8. **BadSPVClient** has the imaginary iPad sent by Vendor, while **BadMiner**
   still has the same X amount unspent. **Vendor** can't charge **BadSPV** because
   the **BadSPV** does not have any coins left.

### What you should see:

After running `./main.sh -m 1 -d`, both **BadMiner** and **Miner** will mine
as per normal. Once **BadMiner** mines a block (may take some time),
**BadMiner** sends 50 coins over to **BadSPVClient**. **BadSPVClient** waits
for the transaction to be approved and sends the coins over to **Vendor**. A
constant stream of _True_ and _False_ are being printed by **Vendor** to
validate the purchase transaction.

After receiving the product, **BadSPVClient** will send 50 coins to
**BadMiner** (an invalid transaction) which will only be valid to
**BadMiner**. **BadMiner** will be fighting for his life (50 coins) to win
the **Miner**. Eventually he would publish his blocks and invalidate the
**Vendor** transaction.

**Vendor** will start printing _False_ because they are sad now and their
previous payment from **BadSPVClient** was invalidated from the blockchain.

_The demonstration may have a chance of failing due to some unforeseen race
conditions (the adversary losing), so run the same command again!_

## Selfish Mining Attack

`sudo ./main.sh -m 1 -f`

This will create 1 normal miner and 1 selfish miner that will compete with
one another for block mining. For the tests, we introduced a `BE_SELFISH`
class variable to SelfishMiner so as to see the difference that selfish
mining can make. A 1-on-1 test was chosen because it showcases the difference
between selfish mining and non-selfish mining more clearly. In cases where
more miners were involded, the results were significantly more chaotic,
making it hard to interpret. There are no transactions involved as we are
using the rewards as an indicator to number of blocks mined.

The tests were run with `nice -5` on the tested miner and `nice 0` (default)
on the other. This means that the tested miner has slightly higher resource
priority in both cases. In real world, this would mean that the tested miner
has slightly higher computational power and should therefore win the
competition more often than not, even without selfish mining. Results are
collected after the blockchain reach length of 100 ie. the longest chain
reaches 100 blocks. The table below shows the percentage of reward pool that
a majority miner gets with vs. without selfish mining algorithm.

| Runs                    | 1   | 2   | 3   | 4   | 5   | 6   | 7   | 8   | Average |
| ----------------------- | --- | --- | --- | --- | --- | --- | --- | --- | ------- |
| Normal Mining Reward %  | 56% | 50% | 54% | 55% | 52% | 51% | 51% | 52% | 52.625% |
| Selfish Mining Reward % | 62% | 65% | 66% | 66% | 63% | 71% | 63% | 67% | 65.375% |

As we can see from the table above, using selfish mining algorithm increases
the rewards that the miners gets from ~53% to ~65%.

### Example

```python
SelfishMiner PungentPastFungus created a block.
SelfishMiner balance state: {'PungentPastFungus': 100}
Miner WarmWretchedWraith created a block.
Block pushed by SelfishMiner - PungentPastFungus ------> (first publish)
SelfishMiner balance state: {'PungentPastFungus': 100}
SelfishMiner PungentPastFungus created a block.
SelfishMiner balance state: {'PungentPastFungus': 200}
SelfishMiner PungentPastFungus created a block.
SelfishMiner balance state: {'PungentPastFungus': 300}
Miner WarmWretchedWraith created a block.
Block pushed by SelfishMiner - PungentPastFungus ------> (second publish)
Block pushed by SelfishMiner - PungentPastFungus
SelfishMiner balance state: {'PungentPastFungus': 300}
```

The above is a console output snippet taken from one of the runs.
Here, we can see that the first publish happens when the public and private
blockchains are both 1-block long. In our implementation, the selfish mining
algorithm with publish the head of private chain if the public and private
blockchains are of same length. This is due to the deterministic nature of
SUTDCoin's fork resolution. Our fork resolution uses cummulative hash if forks
are of the same length. Since cummulative hash is fairly random (dependent
on nonce which is random), the **SelfishMiner** has a 50/50 chance of getting
the reward by publishing when its private chain is at the same length as
public, instead of not getting anything at all. In this case, the
**SelfishMiner** won (shown by the balance state not changing), so yeah!

On the second publish, we can see that **SelfishMiner** has amassed two private
blocks. So when the normal **Miner** creates a block and broadcasts it, the
**SelfishMiner** bamboozles the normal **Miner** by publishing two blocks, thus
wasting the normal **Miner**'s effort. After these two events, the
**SelfishMiner**'s balance is at 300.

**_Note: The balance state shown is the selfish miner's. We assume that the
selfish miner will be ahead in most cases and hence have a lastest balance
state._**

## Major Differences between Bitcoin and SUTDCoin

|                    | Bitcoin                                                               | SUTDCoin                                                                                                                    |
| ------------------ | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Transaction Model  | UTXO model                                                            | Address:Balance model                                                                                                       |
| Spending Coins     | Receivers must fulfill scriptSig or scriptPubKey to spend outputs     | Receivers can spend after transaction is added to blockchain                                                                |
| Fork Resolution    | Uses Proof-of-Work and first-come-first-serve if forks have same PoW  | Uses chain length and cummulative hash if forks are same length                                                             |
| Timestamp Validity | Timestamp of block has to be larger than median of previous 11 blocks | Timestamp of block has to be larger than previous block                                                                     |
| Block Difficulty   | Dynamic and changes every 2016 blocks                                 | Static, currently always 000018fffff...                                                                                     |
| Market Value       | Can be exchanged for SGD8856 per Bitcoin as of writing                | Absolutely worthless <img src="https://ih0.redbubble.net/image.500553700.1057/sticker,375x360-bg,ffffff.u2.png" width="70"> |
