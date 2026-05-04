#include "simulation.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "../common/config.h"

typedef struct {
    double x;
    double v;
} state_t;

static bool append_sample(sample_buffer_t *buffer, const sample_t *sample) {
    sample_t *new_items;
    size_t new_capacity;

    if (buffer->count < buffer->capacity) {
        buffer->items[buffer->count++] = *sample;
        return true;
    }

    new_capacity = (buffer->capacity == 0) ? 256 : buffer->capacity * 2;
    new_items = realloc(buffer->items, new_capacity * sizeof(*new_items));
    if (new_items == NULL) {
        return false;
    }

    buffer->items = new_items;
    buffer->capacity = new_capacity;
    buffer->items[buffer->count++] = *sample;
    return true;
}

bool init_sample_buffer(sample_buffer_t *buffer, size_t initial_capacity) {
    buffer->count = 0;
    buffer->capacity = initial_capacity;
    buffer->items = NULL;

    if (initial_capacity == 0) {
        return true;
    }

    buffer->items = malloc(initial_capacity * sizeof(*buffer->items));
    return buffer->items != NULL;
}

void free_sample_buffer(sample_buffer_t *buffer) {
    free(buffer->items);
    buffer->items = NULL;
    buffer->count = 0;
    buffer->capacity = 0;
}

static double acceleration(const oscillator_params_t *params, double x, double v) {
    return -(params->k * x + params->gamma * v) / params->mass;
}

static void derivatives(
    const oscillator_params_t *params,
    double x,
    double v,
    double *a,
    double *jerk,
    double *snap,
    double *crackle
) {
    const double beta = params->gamma / params->mass;

    *a = acceleration(params, x, v);
    *jerk = -beta * (*a) - (params->k / params->mass) * v;
    *snap = -beta * (*jerk) - (params->k / params->mass) * (*a);
    *crackle = -beta * (*snap) - (params->k / params->mass) * (*jerk);
}

bool parse_method(const char *text, integration_method_t *method) {
    static const struct {
        const char *name;
        integration_method_t method;
    } entries[] = {
        {"euler", METHOD_EULER},
        {"verlet", METHOD_VERLET},
        {"beeman", METHOD_BEEMAN},
        {"gear5", METHOD_GEAR5},
    };
    size_t i;

    for (i = 0; i < sizeof(entries) / sizeof(entries[0]); ++i) {
        if (strcmp(text, entries[i].name) == 0) {
            *method = entries[i].method;
            return true;
        }
    }

    return false;
}

const char *method_name(integration_method_t method) {
    switch (method) {
        case METHOD_EULER:
            return "euler";
        case METHOD_VERLET:
            return "verlet";
        case METHOD_BEEMAN:
            return "beeman";
        case METHOD_GEAR5:
            return "gear5";
        default:
            return "unknown";
    }
}

bool analytic_solution(
    const oscillator_params_t *params,
    double time,
    double *x,
    double *v
) {
    const double beta = params->gamma / (2.0 * params->mass);
    const double omega0_sq = params->k / params->mass;
    const double disc = omega0_sq - beta * beta;

    if (disc > EPS) {
        const double omega_d = sqrt(disc);
        const double exp_term = exp(-beta * time);
        const double cos_term = cos(omega_d * time);
        const double sin_term = sin(omega_d * time);
        const double c1 = params->x0;
        const double c2 = (params->v0 + beta * params->x0) / omega_d;
        const double envelope = c1 * cos_term + c2 * sin_term;
        const double derivative_inner = -c1 * omega_d * sin_term + c2 * omega_d * cos_term;

        *x = exp_term * envelope;
        *v = exp_term * (derivative_inner - beta * envelope);
        return true;
    }

    if (fabs(disc) <= EPS) {
        const double exp_term = exp(-beta * time);
        const double c1 = params->x0;
        const double c2 = params->v0 + beta * params->x0;

        *x = exp_term * (c1 + c2 * time);
        *v = exp_term * (c2 - beta * (c1 + c2 * time));
        return true;
    }

    {
        const double alpha = sqrt(beta * beta - omega0_sq);
        const double r1 = -beta + alpha;
        const double r2 = -beta - alpha;
        const double c1 = (params->v0 - r2 * params->x0) / (r1 - r2);
        const double c2 = params->x0 - c1;

        *x = c1 * exp(r1 * time) + c2 * exp(r2 * time);
        *v = c1 * r1 * exp(r1 * time) + c2 * r2 * exp(r2 * time);
        return true;
    }
}

static state_t step_euler(
    const oscillator_params_t *params,
    state_t current,
    double dt
) {
    const double a = acceleration(params, current.x, current.v);
    state_t next = current;

    //r(t+\Delta t) = r(t) + \Delta t\, v(t)
    next.x = current.x + current.v * dt;

    //esta comentado porque podemos este seria euler mejorado
    //x(t+\Delta t) = x(t) + v(t)\Delta t + \frac{1}{2} a(t)\Delta t^2
    //next.x = current.x + current.v * dt + 0.5 * a * dt * dt;


    //v(t+\Delta t) = v(t) + \Delta t\, a(t)
    next.v = current.v + a * dt;
    return next;
}

static state_t step_verlet(
    const oscillator_params_t *params,
    state_t previous,
    state_t current,
    double dt
) {
    //ctes para reemplazar la velocidad
    const double c = params->gamma * dt / (2.0 * params->mass);
    const double w = params->k * dt * dt / params->mass;
    state_t next = current;

    // r_{t+dt} = [(2 - w) r_t + (c - 1) r_{t-dt}] / (1 + c)
    // donde c = gamma*dt/(2m), w = k*dt^2/m    next.x = ((2.0 - w) * current.x + (c - 1.0) * previous.x) / (1.0 + c);
    next.x = ((2.0 - w) * current.x + (c - 1.0) * previous.x) / (1.0 + c);
    next.v = (next.x - previous.x) / (2.0 * dt);
    return next;
}

static state_t step_beeman(
    const oscillator_params_t *params,
    state_t current,
    double a_current,
    double a_previous,
    double dt
) {
    //r_p = r(t) + v(t)\Delta t + \left(\frac{2}{3}a(t) - \frac{1}{6}a(t-\Delta t)\right)\Delta t^2
    const double x_pred =
        current.x + current.v * dt + ((2.0 / 3.0) * a_current - (1.0 / 6.0) * a_previous) * dt * dt;

    //v_p = v(t) + \left(\frac{3}{2}a(t) - \frac{1}{2}a(t-\Delta t)\right)\Delta t
    const double v_pred = current.v + ((3.0 / 2.0) * a_current - 0.5 * a_previous) * dt;
    
    //a(t+\Delta t) = a(r_p, v_p)
    const double a_next = acceleration(params, x_pred, v_pred);
    state_t next;

    next.x = x_pred;
    
    //v(t+\Delta t) = v(t) + \left(\frac{1}{3}a(t+\Delta t) + \frac{5}{6}a(t) - \frac{1}{6}a(t-\Delta t)\right)\Delta t
    next.v =
        current.v + ((1.0 / 3.0) * a_next + (5.0 / 6.0) * a_current - (1.0 / 6.0) * a_previous) * dt;
    return next;
}

static state_t step_gear5(
    const oscillator_params_t *params,
    state_t current,
    double dt,
    double r[6]
) {
    static const double alpha[] = {
        3.0 / 16.0,
        251.0 / 360.0,
        1.0,
        11.0 / 18.0,
        1.0 / 6.0,
        1.0 / 60.0
    };
    const double dt2 = dt * dt;
    const double dt3 = dt2 * dt;
    const double dt4 = dt3 * dt;
    const double dt5 = dt4 * dt;
    double predicted[6];
    double corrected_acceleration;
    double delta_r2;

    (void) current;

    predicted[0] = r[0] + r[1] * dt + r[2] * dt2 + r[3] * dt3 + r[4] * dt4 + r[5] * dt5;
    predicted[1] = r[1] + 2.0 * r[2] * dt + 3.0 * r[3] * dt2 + 4.0 * r[4] * dt3 + 5.0 * r[5] * dt4;
    predicted[2] = r[2] + 3.0 * r[3] * dt + 6.0 * r[4] * dt2 + 10.0 * r[5] * dt3;
    predicted[3] = r[3] + 4.0 * r[4] * dt + 10.0 * r[5] * dt2;
    predicted[4] = r[4] + 5.0 * r[5] * dt;
    predicted[5] = r[5];

    corrected_acceleration = acceleration(params, predicted[0], predicted[1]);
    delta_r2 = (corrected_acceleration - 2.0 * predicted[2]) * dt2 / 2.0;

    r[0] = predicted[0] + alpha[0] * delta_r2;
    r[1] = predicted[1] + alpha[1] * delta_r2 / dt;
    r[2] = predicted[2] + alpha[2] * delta_r2 / dt2;
    r[3] = predicted[3] + alpha[3] * delta_r2 / dt3;
    r[4] = predicted[4] + alpha[4] * delta_r2 / dt4;
    r[5] = predicted[5] + alpha[5] * delta_r2 / dt5;

    return (state_t) {.x = r[0], .v = r[1]};
}

bool run_oscillator(
    const oscillator_params_t *params,
    const run_config_t *config,
    integration_method_t method,
    sample_buffer_t *samples,
    run_summary_t *summary
) {
    const size_t steps = (size_t) llround(config->tf / config->dt);
    const size_t sample_every = (config->sample_every == 0) ? 1 : config->sample_every;
    state_t current = {.x = params->x0, .v = params->v0};
    state_t previous = current;
    double a_previous = acceleration(params, params->x0, params->v0);
    double a_current = a_previous;
    double gear[6];
    double mse_position = 0.0;
    double mse_velocity = 0.0;
    double max_abs_position_error = 0.0;
    double max_abs_velocity_error = 0.0;
    size_t step;

    memset(gear, 0, sizeof(gear));
    if (method == METHOD_GEAR5) {
        double a;
        double jerk;
        double snap;
        double crackle;

        derivatives(params, params->x0, params->v0, &a, &jerk, &snap, &crackle);
        gear[0] = params->x0;
        gear[1] = params->v0;
        gear[2] = a / 2.0;
        gear[3] = jerk / 6.0;
        gear[4] = snap / 24.0;
        gear[5] = crackle / 120.0;
    }

    if (method == METHOD_VERLET) {
        //r(t - \Delta t) = r(t) - v(t)\Delta t + \frac{1}{2} a(t)\Delta t^2
        previous.x = params->x0 - params->v0 * config->dt + 0.5 * a_previous * config->dt * config->dt;
        previous.v = params->v0 - a_previous * config->dt;
    }

    for (step = 0; step <= steps; ++step) {
        const double time = step * config->dt;
        double x_analytic;
        double v_analytic;
        double dx;
        double dv;
        sample_t sample;

        analytic_solution(params, time, &x_analytic, &v_analytic);
        dx = current.x - x_analytic;
        dv = current.v - v_analytic;

        mse_position += dx * dx;
        mse_velocity += dv * dv;
        if (fabs(dx) > max_abs_position_error) {
            max_abs_position_error = fabs(dx);
        }
        if (fabs(dv) > max_abs_velocity_error) {
            max_abs_velocity_error = fabs(dv);
        }

        if (step % sample_every == 0) {
            sample.time = time;
            sample.x_numeric = current.x;
            sample.v_numeric = current.v;
            sample.x_analytic = x_analytic;
            sample.v_analytic = v_analytic;
            if (!append_sample(samples, &sample)) {
                return false;
            }
        }

        if (step == steps) {
            break;
        }

        switch (method) {
            case METHOD_EULER:
                current = step_euler(params, current, config->dt);
                break;
            case METHOD_VERLET: {
                const state_t next = step_verlet(params, previous, current, config->dt);
                previous = current;
                current = next;
                break;
            }
            case METHOD_BEEMAN: {
                const state_t next = step_beeman(params, current, a_current, a_previous, config->dt);
                a_previous = a_current;
                a_current = acceleration(params, next.x, next.v);
                current = next;
                break;
            }
            case METHOD_GEAR5:
                current = step_gear5(params, current, config->dt, gear);
                break;
            default:
                return false;
        }
    }

    summary->method = method;
    summary->dt = config->dt;
    summary->tf = steps * config->dt;
    summary->steps = steps;
    summary->mse_position = mse_position / (double) (steps + 1);
    summary->mse_velocity = mse_velocity / (double) (steps + 1);
    summary->max_abs_position_error = max_abs_position_error;
    summary->max_abs_velocity_error = max_abs_velocity_error;
    return true;
}
