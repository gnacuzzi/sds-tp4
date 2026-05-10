#include "simulation.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "../common/config.h"
#include "cell_index.h"
#include "config.h"
#include "init.h"

static vec2_t vec_add(vec2_t a, vec2_t b) {
    return (vec2_t) {.x = a.x + b.x, .y = a.y + b.y};
}

static vec2_t vec_sub(vec2_t a, vec2_t b) {
    return (vec2_t) {.x = a.x - b.x, .y = a.y - b.y};
}

static vec2_t vec_scale(vec2_t v, double s) {
    return (vec2_t) {.x = v.x * s, .y = v.y * s};
}

static double vec_norm(vec2_t v) {
    return sqrt(v.x * v.x + v.y * v.y);
}

static double compute_forces(
    cell_index_t *cell_index,
    particle_t *particles,
    size_t count,
    double k,
    double *pair_potential,
    double *wall_potential,
    double *obstacle_potential
) {
    size_t i;
    double kinetic = 0.0;
    const double wall_limit = SCAN_SYSTEM_RADIUS - SCAN_PARTICLE_RADIUS;
    const double obstacle_limit = SCAN_OBSTACLE_RADIUS + SCAN_PARTICLE_RADIUS;
    static const int offsets[5][2] = {
        {0, 0},
        {1, 0},
        {0, 1},
        {1, 1},
        {-1, 1}
    };

    *pair_potential = 0.0;
    *wall_potential = 0.0;
    *obstacle_potential = 0.0;

    for (i = 0; i < count; ++i) {
        particles[i].was_touching_obstacle = particles[i].touching_obstacle;
        particles[i].was_touching_wall = particles[i].touching_wall;
        particles[i].acceleration.x = 0.0;
        particles[i].acceleration.y = 0.0;
        particles[i].touching_obstacle = false;
        particles[i].touching_wall = false;
    }

    cell_index_build(cell_index, particles, count);

    for (int cell_y = 0; cell_y < cell_index->cells_per_side; ++cell_y) {
        for (int cell_x = 0; cell_x < cell_index->cells_per_side; ++cell_x) {
            const int cell = cell_index_flat_index(cell_index, cell_x, cell_y);

            for (int i_index = cell_index->head[cell]; i_index != -1; i_index = cell_index->next[i_index]) {
                for (size_t offset = 0; offset < 5; ++offset) {
                    const int neighbor_x = cell_x + offsets[offset][0];
                    const int neighbor_y = cell_y + offsets[offset][1];
                    int neighbor_cell;

                    if (
                        neighbor_x < 0 ||
                        neighbor_x >= cell_index->cells_per_side ||
                        neighbor_y < 0 ||
                        neighbor_y >= cell_index->cells_per_side
                    ) {
                        continue;
                    }

                    neighbor_cell = cell_index_flat_index(cell_index, neighbor_x, neighbor_y);

                    for (
                        int j_index = cell_index->head[neighbor_cell];
                        j_index != -1;
                        j_index = cell_index->next[j_index]
                    ) {
                        if (neighbor_cell == cell && j_index <= i_index) {
                            continue;
                        }

                        const size_t j = (size_t) j_index;
                        const vec2_t delta = vec_sub(particles[i_index].position, particles[j].position);
                        const double distance = vec_norm(delta);
                        const double overlap = 2.0 * SCAN_PARTICLE_RADIUS - distance;

                        if (overlap > 0.0 && distance > EPS) {
                            const vec2_t direction = vec_scale(delta, 1.0 / distance);
                            const vec2_t force = vec_scale(direction, k * overlap);

                            particles[i_index].acceleration = vec_add(
                                particles[i_index].acceleration,
                                force
                            );
                            particles[j].acceleration = vec_sub(particles[j].acceleration, force);
                            *pair_potential += 0.5 * k * overlap * overlap;
                        }
                    }
                }
            }
        }
    }

    for (i = 0; i < count; ++i) {
        const double radius = vec_norm(particles[i].position);

        if (radius > wall_limit && radius > EPS) {
            const double overlap = radius - wall_limit;
            const vec2_t direction = vec_scale(particles[i].position, 1.0 / radius);
            const vec2_t force = vec_scale(direction, -k * overlap);

            particles[i].acceleration = vec_add(particles[i].acceleration, force);
            particles[i].touching_wall = true;
            *wall_potential += 0.5 * k * overlap * overlap;
        }

        if (radius < obstacle_limit && radius > EPS) {
            const double overlap = obstacle_limit - radius;
            const vec2_t direction = vec_scale(particles[i].position, 1.0 / radius);
            const vec2_t force = vec_scale(direction, k * overlap);

            particles[i].acceleration = vec_add(particles[i].acceleration, force);
            particles[i].touching_obstacle = true;
            *obstacle_potential += 0.5 * k * overlap * overlap;
        }

        if (radius <= EPS) {
            particles[i].acceleration.x += k * obstacle_limit;
            particles[i].touching_obstacle = true;
            *obstacle_potential += 0.5 * k * obstacle_limit * obstacle_limit;
        }

        particles[i].acceleration = vec_scale(particles[i].acceleration, 1.0 / SCAN_PARTICLE_MASS);
        kinetic += 0.5 * SCAN_PARTICLE_MASS * (
            particles[i].velocity.x * particles[i].velocity.x +
            particles[i].velocity.y * particles[i].velocity.y
        );
    }

    return kinetic;
}

static double compute_fu(const particle_t *particles, size_t count) {
    size_t i;
    size_t used = 0;

    for (i = 0; i < count; ++i) {
        if (particles[i].state == PARTICLE_USED) {
            used++;
        }
    }

    return (double) used / (double) count;
}

static void update_states(particle_t *particles, size_t count, size_t *cfc) {
    size_t i;

    for (i = 0; i < count; ++i) {
        const bool entered_obstacle_contact =
            particles[i].touching_obstacle && !particles[i].was_touching_obstacle;
        const bool entered_wall_contact =
            particles[i].touching_wall && !particles[i].was_touching_wall;

        if (entered_obstacle_contact && particles[i].state == PARTICLE_FRESH) {
            particles[i].state = PARTICLE_USED;
            (*cfc)++;
        }

        if (entered_wall_contact && particles[i].state == PARTICLE_USED) {
            particles[i].state = PARTICLE_FRESH;
        }
    }
}

bool run_scan_simulation(const scan_config_t *config, scan_output_t *output, scan_summary_t *summary) {
    particle_t *particles;
    cell_index_t cell_index;
    size_t step;
    size_t cfc = 0;
    const size_t total_steps = (size_t) llround(config->tf / config->dt);
    size_t sample_every = (size_t) llround(config->dt2 / config->dt);
    double pair_potential = 0.0;
    double wall_potential = 0.0;
    double obstacle_potential = 0.0;
    double kinetic = 0.0;
    double final_fu = 0.0;
    const clock_t start_clock = clock();

    if (sample_every == 0) {
        sample_every = 1;
    }

    particles = calloc(config->count, sizeof(*particles));
    if (particles == NULL) {
        return false;
    }

    if (!initialize_particles(config, particles)) {
        free(particles);
        return false;
    }

    if (!cell_index_init(&cell_index, config->count)) {
        free(particles);
        return false;
    }

    kinetic = compute_forces(
        &cell_index,
        particles,
        config->count,
        config->k,
        &pair_potential,
        &wall_potential,
        &obstacle_potential
    );

    for (step = 0; step <= total_steps; ++step) {
        const double time = step * config->dt;
        scan_observables_t observables;
        size_t i;

        update_states(particles, config->count, &cfc);

        observables.time = time;
        observables.cfc = cfc;
        observables.fu = compute_fu(particles, config->count);
        observables.kinetic = kinetic;
        observables.potential_pairs = pair_potential;
        observables.potential_wall = wall_potential;
        observables.potential_obstacle = obstacle_potential;

        if (config->write_output) {
            if (!write_cfc_line(output, &observables) || !write_energy_line(output, &observables)) {
                cell_index_free(&cell_index);
                free(particles);
                return false;
            }

            if (step % sample_every == 0) {
                if (!write_dynamic_snapshot(output, particles, config->count, &observables)) {
                    cell_index_free(&cell_index);
                    free(particles);
                    return false;
                }
            }
        }

        if (step == total_steps) {
            break;
        }

        for (i = 0; i < config->count; ++i) {
            particles[i].position = vec_add(
                particles[i].position,
                vec_add(
                    vec_scale(particles[i].velocity, config->dt),
                    vec_scale(particles[i].acceleration, 0.5 * config->dt * config->dt)
                )
            );
            particles[i].velocity = vec_add(
                particles[i].velocity,
                vec_scale(particles[i].acceleration, 0.5 * config->dt)
            );
        }

        kinetic = compute_forces(
            &cell_index,
            particles,
            config->count,
            config->k,
            &pair_potential,
            &wall_potential,
            &obstacle_potential
        );

        for (i = 0; i < config->count; ++i) {
            particles[i].velocity = vec_add(
                particles[i].velocity,
                vec_scale(particles[i].acceleration, 0.5 * config->dt)
            );
        }

        kinetic = 0.0;
        for (i = 0; i < config->count; ++i) {
            kinetic += 0.5 * SCAN_PARTICLE_MASS * (
                particles[i].velocity.x * particles[i].velocity.x +
                particles[i].velocity.y * particles[i].velocity.y
            );
        }
    }

    final_fu = compute_fu(particles, config->count);
    cell_index_free(&cell_index);
    free(particles);

    if (summary != NULL) {
        const clock_t end_clock = clock();

        summary->elapsed_seconds = (double) (end_clock - start_clock) / (double) CLOCKS_PER_SEC;
        summary->steps = total_steps;
        summary->cfc = cfc;
        summary->fu = final_fu;
    }

    return true;
}

void print_scan_usage(FILE *stream, const char *program_name) {
    fprintf(
        stream,
        "Usage:\n"
        "  %s [N] [run_id] [tf] [dt] [dt2] [seed] [k] [write_output]\n"
        "\n"
        "write_output defaults to 1. Use 0 for benchmark runs without file I/O.\n"
        "Outputs are written to output/<N>_dynamic<run_id>.txt,\n"
        "output/<N>_cfc<run_id>.txt and output/<N>_energy<run_id>.txt\n",
        program_name
    );
}
