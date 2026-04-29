#ifndef OSCILLATOR_SIMULATION_H
#define OSCILLATOR_SIMULATION_H

#include <stdbool.h>
#include <stddef.h>

typedef enum {
    METHOD_EULER = 0,
    METHOD_VERLET,
    METHOD_BEEMAN,
    METHOD_GEAR5,
    METHOD_COUNT
} integration_method_t;

typedef struct {
    double mass;
    double k;
    double gamma;
    double x0;
    double v0;
} oscillator_params_t;

typedef struct {
    double dt;
    double tf;
    size_t sample_every;
} run_config_t;

typedef struct {
    double time;
    double x_numeric;
    double v_numeric;
    double x_analytic;
    double v_analytic;
} sample_t;

typedef struct {
    sample_t *items;
    size_t count;
    size_t capacity;
} sample_buffer_t;

typedef struct {
    integration_method_t method;
    double dt;
    double tf;
    size_t steps;
    double mse_position;
    double mse_velocity;
    double max_abs_position_error;
    double max_abs_velocity_error;
} run_summary_t;

bool parse_method(const char *text, integration_method_t *method);
const char *method_name(integration_method_t method);

bool analytic_solution(
    const oscillator_params_t *params,
    double time,
    double *x,
    double *v
);

bool run_oscillator(
    const oscillator_params_t *params,
    const run_config_t *config,
    integration_method_t method,
    sample_buffer_t *samples,
    run_summary_t *summary
);

bool init_sample_buffer(sample_buffer_t *buffer, size_t initial_capacity);
void free_sample_buffer(sample_buffer_t *buffer);

#endif
