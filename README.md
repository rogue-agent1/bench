# bench

Command benchmarking tool with statistics and comparison.

## Usage

```bash
python3 bench.py run "sleep 0.1" -n 20 -w 3
python3 bench.py compare "cat file" "bat file" "less file" -n 10
python3 bench.py profile "seq {N}" "100,1000,10000,100000"
python3 bench.py run "make build" -n 5 -o results.json
```

## Features

- Statistical analysis (mean, stdev, median, min, max)
- Distribution histogram
- Multi-command comparison with relative speedup
- Scaling profile with {N} placeholder
- Warmup runs
- JSON export
- Zero dependencies
