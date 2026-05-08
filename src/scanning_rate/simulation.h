#ifndef SCANNING_RATE_SIMULATION_H
#define SCANNING_RATE_SIMULATION_H

#include <stdbool.h>

#include "io.h"
#include "types.h"

bool run_scan_simulation(const scan_config_t *config, scan_output_t *output, scan_summary_t *summary);
void print_scan_usage(FILE *stream, const char *program_name);

#endif
