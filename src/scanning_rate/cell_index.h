#ifndef SCANNING_RATE_CELL_INDEX_H
#define SCANNING_RATE_CELL_INDEX_H

#include <stdbool.h>
#include <stddef.h>

#include "types.h"

typedef struct {
    double min_coord;
    double cell_size;
    int cells_per_side;
    int cell_count;
    int *head;
    int *next;
} cell_index_t;

bool cell_index_init(cell_index_t *index, size_t particle_count);
void cell_index_free(cell_index_t *index);
void cell_index_build(cell_index_t *index, const particle_t *particles, size_t particle_count);
int cell_index_flat_index(const cell_index_t *index, int cell_x, int cell_y);

#endif
