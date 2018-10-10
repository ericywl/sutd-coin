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
has slightly higher computational power. Results are collected after the 
blockchain reach approximately length of 100 ie. the longest chain reaches 
about 100 blocks. The calculated percentages are rounded to nearest 0.5.

| Runs      | 1      | 2      | 3       | 4     |
|-----------|--------|--------|---------|-------|
| Normal    | 56%    | 50%    | 53.5%   | 55%   |
| Selfish   | 62%    | 65%    | 66%     | 66%   |
