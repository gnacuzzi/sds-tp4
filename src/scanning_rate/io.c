#include "io.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>

static bool open_file(FILE **file, const char *path) {
    *file = fopen(path, "w");
    if (*file == NULL) {
        fprintf(stderr, "Could not open '%s': %s\n", path, strerror(errno));
        return false;
    }

    return true;
}

bool open_scan_output(scan_output_t *output, size_t count, int run_id) {
    char dynamic_path[256];
    char cfc_path[256];
    char energy_path[256];

    snprintf(dynamic_path, sizeof(dynamic_path), "output/%zu_dynamic%d.txt", count, run_id);
    snprintf(cfc_path, sizeof(cfc_path), "output/%zu_cfc%d.txt", count, run_id);
    snprintf(energy_path, sizeof(energy_path), "output/%zu_energy%d.txt", count, run_id);

    output->dynamic_file = NULL;
    output->cfc_file = NULL;
    output->energy_file = NULL;

    if (!open_file(&output->dynamic_file, dynamic_path)) {
        return false;
    }

    if (!open_file(&output->cfc_file, cfc_path)) {
        close_scan_output(output);
        return false;
    }

    if (!open_file(&output->energy_file, energy_path)) {
        close_scan_output(output);
        return false;
    }

    fprintf(output->energy_file, "time kinetic pair_potential wall_potential obstacle_potential total\n");
    return true;
}

void close_scan_output(scan_output_t *output) {
    if (output->dynamic_file != NULL) {
        fclose(output->dynamic_file);
        output->dynamic_file = NULL;
    }
    if (output->cfc_file != NULL) {
        fclose(output->cfc_file);
        output->cfc_file = NULL;
    }
    if (output->energy_file != NULL) {
        fclose(output->energy_file);
        output->energy_file = NULL;
    }
}

bool write_dynamic_snapshot(
    scan_output_t *output,
    const particle_t *particles,
    size_t count,
    const scan_observables_t *observables
) {
    size_t i;

    fprintf(output->dynamic_file, "%zu\n", count);
    fprintf(
        output->dynamic_file,
        "t %.12f %zu\n",
        observables->time,
        observables->cfc
    );

    for (i = 0; i < count; ++i) {
        fprintf(
            output->dynamic_file,
            "%zu %.12f %.12f %.12f %.12f %d\n",
            particles[i].id,
            particles[i].position.x,
            particles[i].position.y,
            particles[i].velocity.x,
            particles[i].velocity.y,
            (int) particles[i].state
        );
    }

    return !ferror(output->dynamic_file);
}

bool write_cfc_line(scan_output_t *output, const scan_observables_t *observables) {
    fprintf(
        output->cfc_file,
        "t %.12f %zu\n",
        observables->time,
        observables->cfc
    );
    return !ferror(output->cfc_file);
}

bool write_energy_line(scan_output_t *output, const scan_observables_t *observables) {
    const double total = observables->kinetic
        + observables->potential_pairs
        + observables->potential_wall
        + observables->potential_obstacle;

    fprintf(
        output->energy_file,
        "%.12f %.12f %.12f %.12f %.12f %.12f\n",
        observables->time,
        observables->kinetic,
        observables->potential_pairs,
        observables->potential_wall,
        observables->potential_obstacle,
        total
    );
    return !ferror(output->energy_file);
}

bool append_performance_row(size_t count, double elapsed_seconds) {
    FILE *file = fopen("output/performance.csv", "a");

    if (file == NULL) {
        fprintf(stderr, "Could not open 'output/performance.csv': %s\n", strerror(errno));
        return false;
    }

    fprintf(file, "%zu,%.9f\n", count, elapsed_seconds);
    fclose(file);
    return true;
}
