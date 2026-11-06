# Proyecto 02: Automatización de Firmas Digitales con PGP y CRON

Sistema automatizado para firmar documentos digitales mediante GPG (GNU Privacy Guard) y programar su ejecución periódica en Linux.

---

## 1. Estructura del Proyecto

```text
02_firma_pgp_cron/
├── ParaFirmar/         # Carpeta donde se depositan los archivos a firmar
├── Firmados/           # Carpeta donde se guardan los archivos firmados y sus firmas .asc
├── Logs/               # Registro de auditoría (signing.log)
├── setup_keys.sh       # Genera un par de llaves GPG de prueba en modo desatendido
├── sign_documents.sh   # Script principal que procesa y firma los documentos pendientes
├── verify_document.sh  # Script para comprobar si un archivo firmado es auténtico o fue modificado
└── README.md           # Guía de defensa y conceptos teóricos
```

---

## 2. ¿Cómo funciona?

1. **Generación de firma desatendida:**
   ```bash
   gpg --batch --yes --armor --detach-sign -o "$OUTPUT_DIR/$FILENAME.asc" "$FILE"
   ```
   - `--batch`: Modo no interactivo (imprescindible para que no pida confirmaciones en consola ni en CRON).
   - `--yes`: Sobrescribe si ya existía una firma previa.
   - `--armor`: Genera la firma en formato de texto ASCII legible (`.asc`) en lugar de binario.
   - `--detach-sign`: Crea una firma separada sin alterar ni encapsular el archivo original.

2. **Rutas seguras para CRON:**
   `BASE_DIR="$(cd "$(dirname "$0")" && pwd)"` garantiza que el script siempre ubique las carpetas de entrada y salida sin importar desde qué directorio lo ejecute el demonio `cron`.

---

## 3. Demostración en Vivo Paso a Paso

### Paso 1: Generar llaves de prueba (solo la primera vez)
```bash
cd "02_firma_pgp_cron"
./setup_keys.sh
```

### Paso 2: Crear un documento de prueba en `ParaFirmar/`
```bash
echo "Contrato de examen final EDI II" > ParaFirmar/contrato.txt
```

### Paso 3: Ejecutar el script de firma
```bash
./sign_documents.sh
```
*Salida esperada:*
```text
[OK] Successfully signed: contrato.txt
```

### Paso 4: Comprobar el resultado en `Firmados/` y `Logs/`
```bash
ls -l Firmados/
cat Logs/signing.log
```
*Verás dos archivos: `contrato.txt` (el documento original) y `contrato.txt.asc` (su firma digital).*

### Paso 5: Verificar la autenticidad del documento
```bash
./verify_document.sh contrato.txt
```
*Salida:* `[VALID] The signature is authentic and the document has not been modified.`

### Paso 6: Demostrar detección de adulteración (Integridad)
Si alguien altera una sola letra del archivo firmado:
```bash
echo "Texto no autorizado" >> Firmados/contrato.txt
./verify_document.sh contrato.txt
```
*Salida:* `[INVALID] Signature check failed! The document has been modified or signature is invalid.`

---

## 4. Automatización con CRON

Para que este script se ejecute automáticamente cada 5 minutos:

1. Abrir el editor de tareas de cron del usuario:
   ```bash
   crontab -e
   ```
2. Agregar la siguiente línea al final del archivo (usando la ruta absoluta del script):
   ```text
   */5 * * * * /ruta/absoluta/a/02_firma_pgp_cron/sign_documents.sh
   ```
3. Guardar y verificar que quedó programado:
   ```bash
   crontab -l
   ```

### Explicación de los campos de CRON:
```text
 *  *  *  *  *
 ┬  ┬  ┬  ┬  ┬
 │  │  │  │  └───── Día de la semana (0 - 7) (0 o 7 = Domingo)
 │  │  │  └──────── Mes (1 - 12)
 │  │  └─────────── Día del mes (1 - 31)
 │  └────────────── Hora (0 - 23)
 └───────────────── Minuto (0 - 59) -> */5 significa "cada 5 minutos"
```

---

## 5. Glosario y Conceptos Teóricos (PGP / Criptografía)

### PGP y GPG
- **PGP (*Pretty Good Privacy*):** Estándar de cifrado y firma digital para proteger la privacidad e integridad de los datos.
- **GPG (*GNU Privacy Guard*):** Herramienta libre y de código abierto en Linux que implementa el estándar OpenPGP. Es el comando `gpg` que usamos en la terminal.

### Criptografía Asimétrica (Par de Claves)
A diferencia del cifrado simétrico (donde una sola clave cifra y descifra):
- **Clave Privada:** Es estrictamente secreta y solo la posee su dueño. Nunca se comparte. Se utiliza para **firmar** documentos o para descifrar mensajes recibidos.
- **Clave Pública:** Es accesible y conocida por cualquiera. Se utiliza para **verificar** las firmas emitidas por el dueño o para cifrarle mensajes que solo él podrá leer.

### Función Hash (Resumen Criptográfico)
Un algoritmo matemático (como SHA-256) que calcula una "huella digital" de longitud fija para cualquier documento:
- **Unidireccional:** A partir del hash es imposible reconstruir el archivo original.
- **Sensible y Determinista:** El mismo archivo siempre produce el mismo hash, pero si se altera un solo byte o coma, el hash resultante cambia totalmente (efecto avalancha).

### ¿Cómo funciona la Firma Digital?
1. El script toma el documento y calcula su **hash**.
2. Ese hash se cifra utilizando la **clave privada** del firmante. El resultado cifrado es la firma (`.asc`).
3. Para comprobar la autenticidad (`gpg --verify`):
   - El receptor calcula el hash del documento recibido.
   - Descifra el archivo `.asc` usando la **clave pública** del firmante (obteniendo el hash original).
   - Si ambos hashes coinciden, se comprueba que el archivo es legítimo y no fue alterado.

### Principios de Seguridad que Garantiza
- **Autenticidad:** Confirma la identidad del emisor (solo quien posee la clave privada pudo haber generado la firma).
- **Integridad:** Garantiza que el contenido del documento no sufrió modificaciones tras la firma.
- **No Repudio:** El emisor no puede negar haber firmado el documento, ya que su clave privada es personal e intransferible.
