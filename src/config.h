#ifndef CONFIG_H
#define CONFIG_H

#include <math.h>

/* ============================================================
 * Physical / Geometric Parameters
 * ============================================================ */

#define SYSTEM_DIAMETER       80.0
#define SYSTEM_RADIUS         (SYSTEM_DIAMETER / 2.0)

#define OBSTACLE_RADIUS       1.0

#define PARTICLE_RADIUS       1.0
#define PARTICLE_MASS         1.0
#define PARTICLE_SPEED        1.0


/* ============================================================
 * Simulation Defaults
 * ============================================================ */

#define DEFAULT_NUM_PARTICLES 30
#define DEFAULT_FINAL_TIME    2000.0
#define DEFAULT_SAVE_EVERY    1


/* ============================================================
 * Numerical Constants
 * ============================================================ */

#define EPS                  1e-9
#define INF                  1e18


/* ============================================================
 * Radial Profile Parameters
 * ============================================================ */

#define RADIAL_BIN_WIDTH      0.2


/* ============================================================
 * Utility Macros
 * ============================================================ */

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define SQR(x) ((x)*(x))

#endif
