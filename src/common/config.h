#ifndef CONFIG_H
#define CONFIG_H

#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define EPS 1e-12

/*
 * These defaults match a common damped-oscillator configuration used in the
 * course material. They should be validated against slide 36 from Teorica_4.pdf.
 */
#define OSC_DEFAULT_MASS 70.0
#define OSC_DEFAULT_K 10000.0
#define OSC_DEFAULT_GAMMA 100.0
#define OSC_DEFAULT_X0 1.0
#define OSC_DEFAULT_V0 (-OSC_DEFAULT_GAMMA / (2.0 * OSC_DEFAULT_MASS))

#define OSC_DEFAULT_DT 0.001
#define OSC_DEFAULT_TF 5.0
#define OSC_DEFAULT_SAMPLE_EVERY 1

#define OSC_SWEEP_DT_COUNT 6

#endif
