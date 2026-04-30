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

bool initialize_particles(const scan_config_t *config, particle_t *particles) {
    size_t i;
    unsigned int rng = config->seed;
    const double min_radius = SCAN_OBSTACLE_RADIUS + SCAN_PARTICLE_RADIUS;
    const double max_radius = SCAN_SYSTEM_RADIUS - SCAN_PARTICLE_RADIUS;

    for (i = 0; i < config->count; ++i) {
        size_t attempts = 0;
        bool placed = false;

        while (attempts < SCAN_MAX_INIT_ATTEMPTS) {
            const double u = random_unit(&rng);
            const double v = random_unit(&rng);
            const double radius = sqrt(u) * (max_radius - min_radius) + min_radius;
            const double angle = 2.0 * M_PI * v;
            const vec2_t position = {
                .x = radius * cos(angle),
                .y = radius * sin(angle)
            };

            if (!overlaps_existing(particles, i, position)) {
                const double direction = 2.0 * M_PI * random_unit(&rng);

                particles[i].id = i;
                particles[i].position = position;
                particles[i].velocity.x = SCAN_PARTICLE_SPEED * cos(direction);
                particles[i].velocity.y = SCAN_PARTICLE_SPEED * sin(direction);
                particles[i].acceleration.x = 0.0;
                particles[i].acceleration.y = 0.0;
                particles[i].state = PARTICLE_FRESH;
                particles[i].was_touching_obstacle = false;
                particles[i].was_touching_wall = false;
                particles[i].touching_obstacle = false;
                particles[i].touching_wall = false;
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
