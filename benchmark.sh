#!/bin/bash

echo "N,time" > output/performance.csv

for N in 50 100 200 300 400 500 600 700 
do
    for RUN in $(seq 1 10)
    do
        make benchmark N=$N >> output/performance.csv
    done
done