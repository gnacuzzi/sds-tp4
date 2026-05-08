#include "init.h"

#include <limits.h>
#include <math.h>
#include <stdlib.h>

#include "../common/config.h"
#include "config.h"

static double random_unit(unsigned int *state) {
    *state = (*state * 1664525u) + 1013904223u;
    return (double) (*state) / (double) UINT_MAX;
}

static bool overlaps_existing(const particle_t *particles, size_t count, vec2_t candidate) {
    size_t i;
    const double min_distance = 2.0 * SCAN_PARTICLE_RADIUS;
    const double min_distance_sq = min_distance * min_distance;

    for (i = 0; i < count; ++i) {
        const double dx = candidate.x - particles[i].position.x;
        const double dy = candidate.y - particles[i].position.y;
        const double distance_sq = dx * dx + dy * dy;

        if (distance_sq < min_distance_sq) {
            return true;
        }
    }

    return false;
}

static void initialize_particle(
    particle_t *particle,
    size_t id,
    vec2_t position,
    unsigned int *rng
) {
    const double direction = 2.0 * M_PI * random_unit(rng);

    particle->id = id;
    particle->position = position;
    particle->velocity.x = SCAN_PARTICLE_SPEED * cos(direction);
    particle->velocity.y = SCAN_PARTICLE_SPEED * sin(direction);
    particle->acceleration.x = 0.0;
    particle->acceleration.y = 0.0;
    particle->state = PARTICLE_FRESH;
    particle->was_touching_obstacle = false;
    particle->was_touching_wall = false;
    particle->touching_obstacle = false;
    particle->touching_wall = false;
}

static bool append_candidate(vec2_t **candidates, size_t *count, size_t *capacity, vec2_t value) {
    vec2_t *new_candidates;
    size_t new_capacity;

    if (*count < *capacity) {
        (*candidates)[(*count)++] = value;
        return true;
    }

    new_capacity = (*capacity == 0) ? 1024 : (*capacity * 2);
    new_candidates = realloc(*candidates, new_capacity * sizeof(*new_candidates));
    if (new_candidates == NULL) {
        return false;
    }

    *candidates = new_candidates;
    *capacity = new_capacity;
    (*candidates)[(*count)++] = value;
    return true;
}

static void shuffle_candidates(vec2_t *candidates, size_t count, unsigned int *rng) {
    size_t i;

    for (i = count; i > 1; --i) {
        const size_t j = (size_t) floor(random_unit(rng) * (double) i);
        const vec2_t tmp = candidates[i - 1];

        candidates[i - 1] = candidates[j];
        candidates[j] = tmp;
    }
}

static bool initialize_grid_particles(const scan_config_t *config, particle_t *particles, unsigned int *rng) {
    vec2_t *candidates = NULL;
    size_t candidate_count = 0;
    size_t candidate_capacity = 0;
    size_t i;
    int row = 0;
    const double min_radius = SCAN_OBSTACLE_RADIUS + SCAN_PARTICLE_RADIUS;
    const double max_radius = SCAN_SYSTEM_RADIUS - SCAN_PARTICLE_RADIUS;
    const double spacing = 2.05 * SCAN_PARTICLE_RADIUS;
    const double row_spacing = spacing * sqrt(3.0) / 2.0;
    double y;

    for (y = -max_radius; y <= max_radius; y += row_spacing) {
        const double x_offset = (row % 2 == 0) ? 0.0 : spacing / 2.0;
        double x;

        for (x = -max_radius + x_offset; x <= max_radius; x += spacing) {
            const double radius = sqrt(x * x + y * y);
            const vec2_t position = {.x = x, .y = y};

            if (radius >= min_radius && radius <= max_radius) {
                if (!append_candidate(&candidates, &candidate_count, &candidate_capacity, position)) {
                    free(candidates);
                    return false;
                }
            }
        }

        row++;
    }

    if (candidate_count < config->count) {
        free(candidates);
        return false;
    }

    shuffle_candidates(candidates, candidate_count, rng);

    for (i = 0; i < config->count; ++i) {
        initialize_particle(&particles[i], i, candidates[i], rng);
    }

    free(candidates);
    return true;
}

static bool initialize_random_particles(const scan_config_t *config, particle_t *particles, unsigned int *rng) {
    size_t i;
    const double min_radius = SCAN_OBSTACLE_RADIUS + SCAN_PARTICLE_RADIUS;
    const double max_radius = SCAN_SYSTEM_RADIUS - SCAN_PARTICLE_RADIUS;

    for (i = 0; i < config->count; ++i) {
        size_t attempts = 0;
        bool placed = false;

        while (attempts < SCAN_MAX_INIT_ATTEMPTS) {
            const double u = random_unit(rng);
            const double v = random_unit(rng);
            const double radius = sqrt(u) * (max_radius - min_radius) + min_radius;
            const double angle = 2.0 * M_PI * v;
            const vec2_t position = {
                .x = radius * cos(angle),
                .y = radius * sin(angle)
            };

            if (!overlaps_existing(particles, i, position)) {
                initialize_particle(&particles[i], i, position, rng);
                placed = true;
                break;
            }

            attempts++;
        }

        if (!placed) {
            return false;
        }
    }

    return true;
}

bool initialize_particles(const scan_config_t *config, particle_t *particles) {
    unsigned int rng = config->seed;

    if (config->count > 800) {
        return initialize_grid_particles(config, particles, &rng);
    }

    if (initialize_random_particles(config, particles, &rng)) {
        return true;
    }

    rng = config->seed;
    return initialize_grid_particles(config, particles, &rng);
}
