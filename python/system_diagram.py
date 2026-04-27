import numpy as np
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
R = 40          # radio del sistema
R_PARTICLE = 1   # radio de las partículas
R_OBS = R_PARTICLE  # obstáculo mismo tamaño que partículas
N = 30          # cantidad de partículas (reducido para visualización)

np.random.seed(0)

# =========================
# GENERAR PARTÍCULAS
# =========================
particles = []

while len(particles) < N:
    x = np.random.uniform(-R, R)
    y = np.random.uniform(-R, R)

    r2 = x**2 + y**2
    if r2 < R**2 and r2 > (R_OBS + R_PARTICLE)**2:
        valid = True
        for (px, py) in particles:
            if (x - px)**2 + (y - py)**2 < (2 * R_PARTICLE)**2:
                valid = False
                break
        if valid:
            particles.append((x, y))

particles = np.array(particles)

# =========================
# PLOT
# =========================
fig, ax = plt.subplots(figsize=(6,6))

# círculo externo
outer = plt.Circle((0, 0), R, fill=False, linewidth=2, color='blue')
ax.add_patch(outer)

# obstáculo central
inner = plt.Circle((0, 0), R_OBS, color='red', alpha=0.9)
ax.add_patch(inner)

# partículas
# asignar colores (algunas usadas en violeta, otras frescas en verde)
colors = np.array(['blue'] * len(particles), dtype=object)
used_indices = np.random.choice(len(particles), size=len(particles)//3, replace=False)
colors[used_indices] = 'red'


ax.scatter(particles[:,0], particles[:,1], s=20, c=colors)

# =========================
# FLECHAS DE VELOCIDAD (mejoradas)
# =========================
arrow_x_p = []
arrow_y_p = []
arrow_vx_p = []
arrow_vy_p = []

arrow_x_g = []
arrow_y_g = []
arrow_vx_g = []
arrow_vy_g = []

for (x, y), c in zip(particles, colors):
    norm = np.sqrt(x**2 + y**2)
    if norm == 0:
        continue

    # dirección radial
    ux = x / norm
    uy = y / norm

    if c == 'red':
        # violetas salen hacia afuera
        arrow_x_p.append(x)
        arrow_y_p.append(y)
        arrow_vx_p.append(2.5 * ux)
        arrow_vy_p.append(2.5 * uy)
    else:
        # verdes apuntan hacia el centro
        arrow_x_g.append(x)
        arrow_y_g.append(y)
        arrow_vx_g.append(-2.0 * ux)
        arrow_vy_g.append(-2.0 * uy)

# flechas violetas (salientes)
ax.quiver(
    arrow_x_p, arrow_y_p,
    arrow_vx_p, arrow_vy_p,
    angles='xy',
    scale_units='xy',
    scale=1,
    width=0.003,
    color='red',
    pivot='tail',
    alpha=0.9,
    zorder=4
)

# flechas verdes (entrantes)
ax.quiver(
    arrow_x_g, arrow_y_g,
    arrow_vx_g, arrow_vy_g,
    angles='xy',
    scale_units='xy',
    scale=1,
    width=0.003,
    color='blue',
    pivot='tail',
    alpha=0.7,
    zorder=3
)

# estética
ax.set_aspect('equal')
ax.set_xlim(-R-5, R+5)
ax.set_ylim(-R-5, R+5)

ax.axis('off')

# guardar
plt.savefig("images/system_diagram.png", dpi=300, bbox_inches='tight')
plt.show()