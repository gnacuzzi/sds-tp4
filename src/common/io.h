#ifndef IO_H
#define IO_H

#include <stdio.h>

#include "../oscillator/simulation.h"

bool write_samples_csv(const char *path, const sample_buffer_t *samples);
void print_summary(FILE *stream, const run_summary_t *summary);
void print_oscillator_usage(FILE *stream, const char *program_name);

#endif
