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
| `-d`      | Create one double-spend miner, one double-spend SPV client and one vendor |

___Note: The `-f` and `-d` option cannot be used together.___

## Selfish Mining

### Tests
The table below shows the percentage of reward pool that a majority miner gets
with vs. without selfish mining algorithm. A 1-on-1 test was chosen because it
showcases the difference between selfish mining and non-selfish mining more
clearly. In cases where there were more miners, the results were significantly
more chaotic, making it hard to interpret.

The tests were run with `nice -3` on the tested miner and `nice 0` (default) 
on the other. This means that the tested miner has slightly higher resource
priority in both cases. In real world, this would mean that the tested miner 
has slightly higher computational power and should therefore win the
competition more often than not even without selfish mining. Results are 
collected after the blockchain reach length of 100 ie. the longest chain 
reaches 100 blocks.

| Runs                      | 1    | 2    | 3    | 4    | 5    | 6    | 7    | 8    |
|---------------------------|------|------|------|------|------|------|------|------|
| Normal Mining Reward %    | 56%  | 50%  | 54%  | 55%  | 52%  | 51%  | 51%  | 52%  |
| Selfish Mining Reward %   | 62%  | 65%  | 66%  | 66%  | 63%  | 71%  | 63%  | 67%  |
