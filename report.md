# Selfish Mining

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

| Runs                      | 1      | 2      | 3       | 4     | 5     | 6     | 7     |
|---------------------------|--------|--------|---------|-------|-------|-------|-------|
| Normal Mining Reward %    | 56%    | 50%    | 54%     | 55%   | 52%   | 51%   | 51%   |
| Selfish Mining Reward %   | 62%    | 65%    | 66%     | 66%   | 63%   | 71%   | 63%   |
