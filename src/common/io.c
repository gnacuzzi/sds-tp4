#include "io.h"

#include <errno.h>
#include <string.h>

bool write_samples_csv(const char *path, const sample_buffer_t *samples) {
    FILE *file = fopen(path, "w");
    size_t i;

    if (file == NULL) {
        fprintf(stderr, "No se pudo abrir '%s': %s\n", path, strerror(errno));
        return false;
    }

    fprintf(file, "time,x_numeric,v_numeric,x_analytic,v_analytic\n");
    for (i = 0; i < samples->count; ++i) {
        const sample_t *sample = &samples->items[i];
        fprintf(
            file,
            "%.12f,%.12f,%.12f,%.12f,%.12f\n",
            sample->time,
            sample->x_numeric,
            sample->v_numeric,
            sample->x_analytic,
            sample->v_analytic
        );
    }

    fclose(file);
    return true;
}

void print_summary(FILE *stream, const run_summary_t *summary) {
    fprintf(stream, "method=%s\n", method_name(summary->method));
    fprintf(stream, "dt=%.12g\n", summary->dt);
    fprintf(stream, "tf=%.12g\n", summary->tf);
    fprintf(stream, "steps=%zu\n", summary->steps);
    fprintf(stream, "mse_position=%.12e\n", summary->mse_position);
    fprintf(stream, "mse_velocity=%.12e\n", summary->mse_velocity);
    fprintf(stream, "max_abs_position_error=%.12e\n", summary->max_abs_position_error);
    fprintf(stream, "max_abs_velocity_error=%.12e\n", summary->max_abs_velocity_error);
}

void print_oscillator_usage(FILE *stream, const char *program_name) {
    fprintf(
        stream,
        "Uso:\n"
        "  %s METHOD OUTPUT.csv [dt] [tf] [sample_every]\n"
        "\n"
        "METHOD: euler | verlet | beeman | gear5\n",
        program_name
    );
}
