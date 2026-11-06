# Proyecto 03: Nginx con SSL y Proxy Reverso

Implementación de un servidor Nginx actuando como **Proxy Reverso con Terminación SSL/TLS**, redirigiendo tráfico seguro hacia un backend interno.

---

## 1. Arquitectura de la Solución

```text
Cliente (Navegador / cURL)
        |
        |  HTTPS (Puerto 443)  [o HTTP Puerto 80 -> Redirige a 443]
        v
+---------------------------------------+
| NGINX (Proxy Reverso)                 |
| - Desencripta TLS (Terminación SSL)   |
| - Agrega cabeceras X-Forwarded-*      |
+---------------------------------------+
        |
        |  HTTP no cifrado (Puerto 8080 interno)
        v
+---------------------------------------+
| Servidor Backend (backend.py)         |
| - Procesa la solicitud                |
| - Lee la IP y protocolo original      |
+---------------------------------------+
```

---

## 2. Archivos del Proyecto

```text
03_nginx_proxy_ssl/
├── generate_cert.sh          # Genera el par de claves SSL autofirmadas con OpenSSL
├── backend.py                # Servidor HTTP interno de prueba en puerto 8080
├── nginx_reverse_proxy.conf  # Configuración del VirtualHost de Nginx
├── install_and_setup.sh      # Script que instala Nginx, despliega la configuración y certificados
├── certs/                    # Carpeta local donde se crean server.crt y server.key
└── README.md                 # Guía de defensa oral y conceptos teóricos
```

---

## 3. Demostración en Vivo Paso a Paso

### Paso 1: Configurar y levantar Nginx
Ejecutar el script de despliegue con permisos de administrador:
```bash
cd "03_nginx_proxy_ssl"
sudo ./install_and_setup.sh
```
*Este script instala Nginx (si no está instalado), genera los certificados SSL autofirmados, copia la configuración a `/etc/nginx/sites-available/`, la activa y reinicia el servicio.*

### Paso 2: Iniciar el servidor Backend
En una terminal, iniciamos el backend que escuchará en el puerto 8080:
```bash
./backend.py
```
*Dejalo corriendo en primer plano para ver los logs en tiempo real.*

### Paso 3: Probar la redirección HTTP -> HTTPS
En otra terminal, hacemos una petición por HTTP clásico (puerto 80):
```bash
curl -I http://localhost
```
*Salida esperada:* Retorna un código **`301 Moved Permanently`** con la cabecera `Location: https://localhost/`.

### Paso 4: Probar el acceso seguro por HTTPS (Puerto 443)
Hacemos la consulta segura por HTTPS:
```bash
curl -k https://localhost
```
*(Usamos `-k` porque el certificado es autofirmado para la demo y no proviene de una CA pública).*

*Salida esperada:*
```text
========================================
Backend Server Response (Port 8080)
========================================
Host Header:       localhost
Direct Client IP:  127.0.0.1
X-Real-IP:         127.0.0.1
X-Forwarded-Proto: https
========================================
Status: Request handled successfully via Reverse Proxy.
```
*Nota que el backend recibió `X-Forwarded-Proto: https`. Esto demuestra que Nginx atendió la conexión segura y se la pasó al backend.*

### Paso 5: Demostración integrada con el Proyecto 01
Podés usar tu propio script de monitoreo del Proyecto 01 para auditar el servidor:
```bash
../01_monitoreo_http/check_http.sh http://localhost
```
*Mostrará que responde con `REDIRECT (301)` hacia HTTPS.*

---

## 4. Preguntas Teóricas de Examen

**¿Qué es un Proxy Reverso y en qué se diferencia de un Proxy Directo (*Forward Proxy*)?**  
- **Forward Proxy (ej. Squid):** Se ubica del lado del cliente. Los usuarios de una red interna pasan por él para salir a Internet (control de contenidos, caché de navegación, anonimato).
- **Reverse Proxy (ej. Nginx):** Se ubica del lado del servidor. Los clientes de Internet se conectan al proxy creyendo que es el servidor final; el proxy recibe las peticiones y las reparte a los servidores internos (balanceo de carga, terminación SSL, seguridad).

**¿Qué es la Terminación SSL (*SSL Termination*)?**  
Es la práctica donde el proxy reverso (Nginx) se encarga de todo el procesamiento criptográfico pesado del handshake TLS y descifra los datos. Luego, le transfiere el tráfico sin cifrar a través de la red local o loopback (`127.0.0.1`) al backend. Esto libera de consumo de CPU a los servidores de aplicaciones.

**¿Por qué son necesarias las directivas `proxy_set_header`?**  
Cuando Nginx reenvía la petición al backend, la conexión TCP se origina en la IP de Nginx (`127.0.0.1`). Si el backend mirara la IP de origen, creería que todas las visitas son locales. Mediante `X-Real-IP` y `X-Forwarded-For`, Nginx le pasa la verdadera dirección IP del cliente remoto. Con `X-Forwarded-Proto: https`, le avisa que la conexión original vino cifrada.
