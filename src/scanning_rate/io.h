#ifndef SCANNING_RATE_IO_H
#define SCANNING_RATE_IO_H

#include <stdbool.h>
#include <stdio.h>

#include "types.h"

typedef struct {
    FILE *dynamic_file;
    FILE *events_file;
    FILE *energy_file;
} scan_output_t;

bool open_scan_output(scan_output_t *output, size_t count, int run_id);
void close_scan_output(scan_output_t *output);
bool write_dynamic_snapshot(
    scan_output_t *output,
    const particle_t *particles,
    size_t count,
    const scan_observables_t *observables
);
bool write_event_line(scan_output_t *output, const scan_observables_t *observables);
bool write_energy_line(scan_output_t *output, const scan_observables_t *observables);

#endif
