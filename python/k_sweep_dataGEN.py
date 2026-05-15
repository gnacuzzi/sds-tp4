#Multithread k_sweep for data generation
from multiprocessing import Process
from pathlib import Path
import subprocess

REPO_ROOT = "./"
FIXED_ARGS = ""
ITER = 10
TF = 500
DT =0.001
DT2_VALUE = 0.1

list_of_N = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

prosesses = []
print(subprocess.run("pwd"))

def run_simulation(num_N, k_val):
    iterations = ITER
    for i in range(iterations):
        if k_val == 1000:
            run_id = i
        else:
            run_id = k_val + i
        result = subprocess.run(
            [
                "./bin/scanning_rate",
                str(num_N),
                str(run_id),
                str(TF),
                str(DT),
                str(DT2_VALUE),
                "0",
                str(k_val)
            ],
            cwd = REPO_ROOT,
            capture_output=True,
            text=True
        )
        print(result.stdout)


def start_multiprosess():
    for num_N in list_of_N:
        #To get to 10⁵
        for k_num in range(1,6):
            k_val = 10**k_num
            p = Process(target=run_simulation, args=[num_N, k_val])
            p.start()
            prosesses.append(p)

        for p in prosesses:
            p.join()

def find_git_root(start_path=None):

    if start_path is None:
        start_path = Path(__file__).resolve().parent

    current = Path(start_path).resolve()

    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    raise RuntimeError("No git repository root found.")

if __name__ == "__main__":
    REPO_ROOT = find_git_root()
    start_multiprosess()