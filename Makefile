CC = gcc
CFLAGS = -Wall -Wextra -Werror -pedantic -std=c11 -O2
LDFLAGS = -lm

SRC_DIR = src
BIN_DIR = bin
OUT_DIR = output
IMG_DIR = images
VID_DIR = videos

TARGET = $(BIN_DIR)/tp3

SRC = $(wildcard $(SRC_DIR)/*.c)
OBJ_DIR = obj
OBJ = $(patsubst $(SRC_DIR)/%.c,$(OBJ_DIR)/%.o,$(SRC))


all: $(TARGET)


$(TARGET): $(OBJ)
	@mkdir -p $(BIN_DIR)
	@mkdir -p $(IMG_DIR)
	@mkdir -p $(VID_DIR)
	$(CC) $(OBJ) -o $(TARGET) $(LDFLAGS)


$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c
	@mkdir -p $(OBJ_DIR)
	$(CC) $(CFLAGS) -c $< -o $@


run: $(TARGET)
	@mkdir -p $(OUT_DIR)
	./$(TARGET) $(N) $(BENCHMARK) $(ITTERATIONS)

benchmark: $(TARGET)
	@mkdir -p $(OUT_DIR)
	@./$(TARGET) $(N) 1


clean:
	rm -rf $(OBJ_DIR)
	rm -f $(TARGET)


fclean: clean
	rm -rf $(OUT_DIR)/
	rm -rf $(IMG_DIR)/
	rm -rf $(VID_DIR)/


re: clean all


.PHONY: all run benchmark clean fclean re