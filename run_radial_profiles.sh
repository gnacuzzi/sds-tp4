#!/bin/bash

# Crear carpeta de imágenes si no existe
mkdir -p images

# Detectar todos los N automáticamente desde los archivos dynamic
Ns=$(ls output/*_dynamic*.txt | sed 's/output\///' | sed 's/_dynamic.*//' | sort -n | uniq)

echo "Ns encontrados: $Ns"

for N in $Ns
do
    echo ">>> Procesando N=$N"
    python3 python/radial_profiles.py $N
done

echo "Listo 🚀"