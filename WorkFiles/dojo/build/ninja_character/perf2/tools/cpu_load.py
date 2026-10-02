"""perf2 contention probe: N busy-loop worker processes (normal priority) for T seconds, to reproduce a busy machine
(another chat's CPU work) while a -game perf run samples. Own processes only; they exit by themselves.
usage: cpu_load.py N T"""
import multiprocessing as mp
import sys
import time


def burn(t_end):
    x = 0
    while time.time() < t_end:
        for _ in range(100000):
            x = (x * 1103515245 + 12345) & 0xFFFFFFFF


if __name__ == "__main__":
    n, t = int(sys.argv[1]), float(sys.argv[2])
    end = time.time() + t
    ps = [mp.Process(target=burn, args=(end,)) for _ in range(n)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    print("load done", n, t)
