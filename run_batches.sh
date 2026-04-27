echo "Running 10 iterations of N = 20 50 100 200 and 800"
R=10
make


for N in 50 100 200 300 400 500 600 700 800
do
    ./bin/tp4 $N 0 "$R"
done