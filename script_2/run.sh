#!/bin/bash

# Valida recibir el nombre del archivo como argumento.
if [ -z "$1" ]; then
    echo "Error: debes proporcionar un nombre de archivo"
    echo "Uso: $0 <nombre_archivo>"
    exit 1
fi

# Crea el archivo...
touch $1

# Asigna permisos de ejecución...
chmod +x $1

# Copia el contenido al archivo...
echo "#!/bin/bash" > $1
echo 'echo "Archivo creado y con permisos de ejecución"' >> $1
echo 'echo "Enter para salir..."' >> $1
echo 'read -n 1 -s' >> $1