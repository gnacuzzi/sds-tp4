import multiprocessing
import subprocess


prosesses = int(multiprocessing.cpu_count())

#run the R iterations with diffent N parameters 

N = [50,100,200,300,400,500]

R_runs = 10


#./bin/tp3 $N 0 "$R"

import subprocess
commands = [] 

for num in N:
    commands.append(f'./bin/tp3 {num} 0 {R_runs}')


if prosesses > len(N):
    prosesses = len(N)

for j in range(max(int(len(commands)/n), 1)):
    procs = [subprocess.Popen(i, shell=True) for i in commands[j*n: min((j+1)*n, len(commands))] ]
    for p in procs:
        p.wait()

