# Proyecto 01: Monitoreo HTTP con cURL

Script básico para comprobar el estado de un servidor web utilizando `curl`.

---

## 1. ¿Cómo funciona el script?

El script recibe una URL por parámetro y ejecuta una consulta HTTP:

1. **`curl -s -o /dev/null -w "%{http_code} %{time_total}" --max-time 5 "$URL"`**
   - `-s`: No muestra la barra de progreso (*silent*).
   - `-o /dev/null`: Descarta el cuerpo de la página (el HTML), porque solo queremos las cabeceras.
   - `-w "%{http_code} %{time_total}"`: Le pide a `curl` que imprima únicamente el código HTTP y el tiempo total de respuesta.
   - `--max-time 5`: Si el servidor no responde en 5 segundos, corta la conexión.

2. **`cut -d ' ' -f 1` y `-f 2`:**
   Separa la salida de curl para guardar el código HTTP en una variable y los segundos en otra.

3. **Estructura condicional (`if / elif / else`):**
   - Si el código está entre **200 y 299**, el servicio responde correctamente (**ONLINE**).
   - Si está entre **300 y 399**, es una redirección (**REDIRECT**).
   - Si es **000**, el servidor está apagado o no existe dominio/red (**DOWN / UNREACHABLE**).
   - Cualquier otro código (como **404** o **500**) se marca como error.

4. **Registro en archivo (`monitor.log`):**
   Cada consulta guarda la fecha, hora, URL y resultado en `monitor.log`.

---

## 2. Comandos para la Demostración

Entrar a la carpeta:
```bash
cd "01_monitoreo_http"
```

### Probar un servidor disponible (200 OK)
```bash
./check_http.sh https://example.com
```

### Probar una redirección (301)
```bash
./check_http.sh http://google.com
```

### Probar un recurso no encontrado (404)
```bash
./check_http.sh https://example.com/pagina-no-existe
```

### Probar un servidor caído o inalcanzable (000)
```bash
./check_http.sh http://servidor-caido-demo.local
```

### Ver el archivo de log generado
```bash
cat monitor.log
```

---

## 3. Preguntas de Examen (Teoría)

**¿Por qué usar cURL y no un ping?**  
`ping` funciona sobre el protocolo ICMP (Capa de Red). Un servidor puede responder al ping perfectamente aunque el servicio web (Apache/Nginx) esté apagado o caído. `curl` consulta directamente el protocolo HTTP (Capa de Aplicación).

**¿Qué significa el código 000 en curl?**  
Significa que cURL ni siquiera pudo establecer la conexión TCP con el servidor (por ejemplo: error de DNS, timeout o puerto cerrado).

**¿Cuáles son las familias de códigos HTTP más comunes?**  
- **2xx:** Éxito (ej. 200 OK).
- **3xx:** Redirección (ej. 301 Moved Permanently).
- **4xx:** Error del cliente (ej. 404 Not Found, 403 Forbidden).
- **5xx:** Error del servidor (ej. 500 Internal Server Error, 502 Bad Gateway).
