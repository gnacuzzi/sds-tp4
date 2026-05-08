#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "config.h"
#include "io.h"
#include "simulation.h"
#include "types.h"

static bool parse_size_arg(const char *text, size_t *value) {
    char *end = NULL;
    unsigned long parsed;

    errno = 0;
    parsed = strtoul(text, &end, 10);
    if (errno != 0 || end == NULL || *end != '\0') {
        return false;
    }

    *value = (size_t) parsed;
    return true;
}

static bool parse_int_arg(const char *text, int *value) {
    char *end = NULL;
    long parsed;

    errno = 0;
    parsed = strtol(text, &end, 10);
    if (errno != 0 || end == NULL || *end != '\0') {
        return false;
    }

    *value = (int) parsed;
    return true;
}

static bool parse_double_arg(const char *text, double *value) {
    char *end = NULL;

    errno = 0;
    *value = strtod(text, &end);
    return errno == 0 && end != NULL && *end == '\0';
}

static bool parse_unsigned_arg(const char *text, unsigned int *value) {
    char *end = NULL;
    unsigned long parsed;

    errno = 0;
    parsed = strtoul(text, &end, 10);
    if (errno != 0 || end == NULL || *end != '\0') {
        return false;
    }

    *value = (unsigned int) parsed;
    return true;
}

int main(int argc, char **argv) {
    scan_config_t config = {
        .count = SCAN_DEFAULT_PARTICLES,
        .tf = SCAN_DEFAULT_TF,
        .dt = SCAN_DEFAULT_DT,
        .dt2 = SCAN_DEFAULT_DT2,
        .k = SCAN_DEFAULT_K,
        .seed = SCAN_DEFAULT_SEED,
        .run_id = 0,
        .write_output = true
    };
    scan_output_t output;
    scan_summary_t summary;

    if (argc >= 2 && !parse_size_arg(argv[1], &config.count)) {
        fprintf(stderr, "Invalid N: %s\n", argv[1]);
        print_scan_usage(stderr, argv[0]);
        return EXIT_FAILURE;
    }
    if (argc >= 3 && !parse_int_arg(argv[2], &config.run_id)) {
        fprintf(stderr, "Invalid run_id: %s\n", argv[2]);
        return EXIT_FAILURE;
    }
    if (argc >= 4 && !parse_double_arg(argv[3], &config.tf)) {
        fprintf(stderr, "Invalid tf: %s\n", argv[3]);
        return EXIT_FAILURE;
    }
    if (argc >= 5 && !parse_double_arg(argv[4], &config.dt)) {
        fprintf(stderr, "Invalid dt: %s\n", argv[4]);
        return EXIT_FAILURE;
    }
    if (argc >= 6 && !parse_double_arg(argv[5], &config.dt2)) {
        fprintf(stderr, "Invalid dt2: %s\n", argv[5]);
        return EXIT_FAILURE;
    }
    if (argc >= 7 && !parse_unsigned_arg(argv[6], &config.seed)) {
        fprintf(stderr, "Invalid seed: %s\n", argv[6]);
        return EXIT_FAILURE;
    }
    if (argc >= 8 && !parse_double_arg(argv[7], &config.k)) {
        fprintf(stderr, "Invalid k: %s\n", argv[7]);
        return EXIT_FAILURE;
    }
    if (argc >= 9) {
        int write_output_flag;

        if (!parse_int_arg(argv[8], &write_output_flag)) {
            fprintf(stderr, "Invalid write_output flag: %s\n", argv[8]);
            return EXIT_FAILURE;
        }

        config.write_output = write_output_flag != 0;
    }

    if (config.count == 0 || config.tf <= 0.0 || config.dt <= 0.0 || config.dt2 <= 0.0 || config.k <= 0.0) {
        fprintf(stderr, "N, tf, dt, dt2 and k must be positive.\n");
        return EXIT_FAILURE;
    }

    if (config.seed == 0u) {
        config.seed = (unsigned int) time(NULL);
    }

    output.dynamic_file = NULL;
    output.events_file = NULL;
    output.energy_file = NULL;

    if (config.write_output) {
        if (!open_scan_output(&output, config.count, config.run_id)) {
            return EXIT_FAILURE;
        }
    }

    if (!run_scan_simulation(&config, &output, &summary)) {
        close_scan_output(&output);
        fprintf(stderr, "Simulation failed.\n");
        return EXIT_FAILURE;
    }

    close_scan_output(&output);

    if (!config.write_output) {
        if (!append_performance_row(config.count, summary.elapsed_seconds)) {
            return EXIT_FAILURE;
        }
    }

    printf(
        "scanning_rate completed: N=%zu run_id=%d tf=%.6f dt=%.6f dt2=%.6f seed=%u k=%.6f write_output=%d\n",
        config.count,
        config.run_id,
        config.tf,
        config.dt,
        config.dt2,
        config.seed,
        config.k,
        (int) config.write_output
    );
    printf("simulation_time=%.9f\n", summary.elapsed_seconds);
    printf("steps=%zu\n", summary.steps);
    printf("cfc=%zu\n", summary.cfc);
    printf("fu=%.12f\n", summary.fu);
    return EXIT_SUCCESS;
}
