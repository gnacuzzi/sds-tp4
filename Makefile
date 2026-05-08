CC = gcc
CFLAGS = -Wall -Wextra -Werror -pedantic -std=c11 -O2
LDFLAGS = -lm

SRC_DIR = src
OBJ_DIR = obj
BIN_DIR = bin
OUT_DIR = output

OSC_TARGET = $(BIN_DIR)/oscillator
SCAN_TARGET = $(BIN_DIR)/scanning_rate

OSC_SRC = \
	$(SRC_DIR)/common/io.c \
	$(SRC_DIR)/oscillator/main.c \
	$(SRC_DIR)/oscillator/simulation.c

SCAN_SRC = \
	$(SRC_DIR)/scanning_rate/cell_index.c \
	$(SRC_DIR)/scanning_rate/init.c \
	$(SRC_DIR)/scanning_rate/io.c \
	$(SRC_DIR)/scanning_rate/main.c \
	$(SRC_DIR)/scanning_rate/simulation.c

OSC_OBJ = $(patsubst $(SRC_DIR)/%.c,$(OBJ_DIR)/%.o,$(OSC_SRC))
SCAN_OBJ = $(patsubst $(SRC_DIR)/%.c,$(OBJ_DIR)/%.o,$(SCAN_SRC))

all: $(OSC_TARGET) $(SCAN_TARGET)

$(OSC_TARGET): $(OSC_OBJ)
	@mkdir -p $(BIN_DIR)
	@mkdir -p $(OUT_DIR)
	$(CC) $(OSC_OBJ) -o $(OSC_TARGET) $(LDFLAGS)

$(SCAN_TARGET): $(SCAN_OBJ)
	@mkdir -p $(BIN_DIR)
	$(CC) $(SCAN_OBJ) -o $(SCAN_TARGET) $(LDFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

run-oscillator: $(OSC_TARGET)
	./$(OSC_TARGET) euler $(OUT_DIR)/oscillator_euler.csv

run-scanning-rate: $(SCAN_TARGET)
	./$(SCAN_TARGET)

benchmark-scanning-rate: $(SCAN_TARGET)
	./$(SCAN_TARGET) $(N) $(RUN_ID) $(TF) $(DT) $(DT2) $(SEED) $(K) 0

clean:
	rm -rf $(OBJ_DIR)
	rm -f $(OSC_TARGET) $(SCAN_TARGET)

fclean: clean
	rm -rf $(OUT_DIR)

re: clean all

.PHONY: all run-oscillator run-scanning-rate benchmark-scanning-rate clean fclean re
