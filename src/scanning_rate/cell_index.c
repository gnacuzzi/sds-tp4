#include "cell_index.h"

#include <limits.h>
#include <math.h>
#include <stdlib.h>

#include "config.h"

static int clamp_cell(int value, int max_value) {
    if (value < 0) {
        return 0;
    }
    if (value >= max_value) {
        return max_value - 1;
    }
    return value;
}

static int position_to_cell(const cell_index_t *index, double coordinate) {
    const double shifted = coordinate - index->min_coord;
    const int raw_cell = (int) floor(shifted / index->cell_size);

    return clamp_cell(raw_cell, index->cells_per_side);
}

bool cell_index_init(cell_index_t *index, size_t particle_count) {
    const double domain_size = 2.0 * SCAN_SYSTEM_RADIUS;

    if (index == NULL || particle_count > (size_t) INT_MAX) {
        return false;
    }

    index->min_coord = -SCAN_SYSTEM_RADIUS;
    index->cell_size = 2.0 * SCAN_PARTICLE_RADIUS;
    index->cells_per_side = (int) ceil(domain_size / index->cell_size);
    index->cell_count = index->cells_per_side * index->cells_per_side;
    index->head = malloc((size_t) index->cell_count * sizeof(*index->head));
    index->next = malloc(particle_count * sizeof(*index->next));

    if (index->head == NULL || index->next == NULL) {
        cell_index_free(index);
        return false;
    }

    return true;
}

void cell_index_free(cell_index_t *index) {
    if (index == NULL) {
        return;
    }

    free(index->head);
    free(index->next);
    index->head = NULL;
    index->next = NULL;
    index->cell_count = 0;
    index->cells_per_side = 0;
}

int cell_index_flat_index(const cell_index_t *index, int cell_x, int cell_y) {
    return cell_y * index->cells_per_side + cell_x;
}

void cell_index_build(cell_index_t *index, const particle_t *particles, size_t particle_count) {
    int cell;
    size_t i;

    for (cell = 0; cell < index->cell_count; ++cell) {
        index->head[cell] = -1;
    }

    for (i = 0; i < particle_count; ++i) {
        const int cell_x = position_to_cell(index, particles[i].position.x);
        const int cell_y = position_to_cell(index, particles[i].position.y);
        const int flat_cell = cell_index_flat_index(index, cell_x, cell_y);

        index->next[i] = index->head[flat_cell];
        index->head[flat_cell] = (int) i;
    }
}
