#ifndef SCANNING_RATE_TYPES_H
#define SCANNING_RATE_TYPES_H

#include <stdbool.h>
#include <stddef.h>

typedef struct {
    double x;
    double y;
} vec2_t;

typedef enum {
    PARTICLE_FRESH = 0,
    PARTICLE_USED = 1
} particle_state_t;

typedef struct {
    size_t id;
    vec2_t position;
    vec2_t velocity;
    vec2_t acceleration;
    particle_state_t state;
    bool was_touching_obstacle;
    bool was_touching_wall;
    bool touching_obstacle;
    bool touching_wall;
} particle_t;

typedef struct {
    size_t count;
    double tf;
    double dt;
    double dt2;
    double k;
    unsigned int seed;
    int run_id;
    bool write_output;
} scan_config_t;

typedef struct {
    double time;
    size_t cfc;
    double kinetic;
    double potential_pairs;
    double potential_wall;
    double potential_obstacle;
} scan_observables_t;

typedef struct {
    double elapsed_seconds;
    size_t steps;
    size_t cfc;
} scan_summary_t;

#endif
