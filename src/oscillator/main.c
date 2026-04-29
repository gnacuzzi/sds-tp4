#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

#include "../common/config.h"
#include "../common/io.h"
#include "simulation.h"

static bool parse_double_arg(const char *text, double *value) {
    char *end = NULL;

    errno = 0;
    *value = strtod(text, &end);
    return errno == 0 && end != NULL && *end == '\0';
}

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

int main(int argc, char **argv) {
    oscillator_params_t params = {
        .mass = OSC_DEFAULT_MASS,
        .k = OSC_DEFAULT_K,
        .gamma = OSC_DEFAULT_GAMMA,
        .x0 = OSC_DEFAULT_X0,
        .v0 = OSC_DEFAULT_V0
    };
    run_config_t config = {
        .dt = OSC_DEFAULT_DT,
        .tf = OSC_DEFAULT_TF,
        .sample_every = OSC_DEFAULT_SAMPLE_EVERY
    };
    integration_method_t method;
    sample_buffer_t samples;
    run_summary_t summary;

    if (argc < 3) {
        print_oscillator_usage(stderr, argv[0]);
        return EXIT_FAILURE;
    }

    if (!parse_method(argv[1], &method)) {
        fprintf(stderr, "Metodo invalido: %s\n", argv[1]);
        print_oscillator_usage(stderr, argv[0]);
        return EXIT_FAILURE;
    }

    if (argc >= 4 && !parse_double_arg(argv[3], &config.dt)) {
        fprintf(stderr, "dt invalido: %s\n", argv[3]);
        return EXIT_FAILURE;
    }

    if (argc >= 5 && !parse_double_arg(argv[4], &config.tf)) {
        fprintf(stderr, "tf invalido: %s\n", argv[4]);
        return EXIT_FAILURE;
    }

    if (argc >= 6 && !parse_size_arg(argv[5], &config.sample_every)) {
        fprintf(stderr, "sample_every invalido: %s\n", argv[5]);
        return EXIT_FAILURE;
    }

    if (config.dt <= 0.0 || config.tf <= 0.0) {
        fprintf(stderr, "dt y tf deben ser positivos\n");
        return EXIT_FAILURE;
    }

    if (!init_sample_buffer(&samples, 0)) {
        fprintf(stderr, "No se pudo reservar memoria para las muestras\n");
        return EXIT_FAILURE;
    }

    if (!run_oscillator(&params, &config, method, &samples, &summary)) {
        free_sample_buffer(&samples);
        fprintf(stderr, "Fallo la simulacion\n");
        return EXIT_FAILURE;
    }

    if (!write_samples_csv(argv[2], &samples)) {
        free_sample_buffer(&samples);
        return EXIT_FAILURE;
    }

    print_summary(stdout, &summary);
    free_sample_buffer(&samples);
    return EXIT_SUCCESS;
}
