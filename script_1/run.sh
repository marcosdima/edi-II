#!/bin/bash

# Guarda la lista de archivos del directorio actual ordenado algabeticamente y lo archiva en script_1.txt.
ls | sort > script_1.txt

# Toma la fecha actual para nombrar el archivo comprimido.
now=$(date +"%Y-%m-%d-%H-%M-%S")

# Comprime los archivos del directorio (incluído el archivo de texto) y lo guarda en la raiz del mismo.
tar -czvf ../${now}.tar.gz .