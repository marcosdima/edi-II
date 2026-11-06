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
└── README.md                 # Guía de defensa y glosario conceptual
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
*El backend recibió `X-Forwarded-Proto: https`. Esto demuestra que Nginx atendió la conexión segura y se la pasó al backend.*

### Paso 5: Demostración integrada con el Proyecto 01
Podés usar tu propio script de monitoreo del Proyecto 01 para auditar el servidor:
```bash
../01_monitoreo_http/check_http.sh http://localhost
```
*Mostrará que responde con `REDIRECT (301)` hacia HTTPS.*

---

## 4. Glosario y Conceptos Clave

### ¿Para qué sirve Nginx?
Nginx es un servidor web y proxy de alto rendimiento diseñado con una arquitectura asíncrona no bloqueante basada en eventos. Sus usos principales son:
- **Servidor web:** Sirve archivos estáticos (HTML, CSS, imágenes) a gran velocidad consumiendo muy poca memoria RAM.
- **Proxy reverso y balanceador:** Se ubica como puerta de entrada única y distribuye las peticiones entre varios servidores de backend (Python, Node.js, PHP, etc.).
- **Punto central de seguridad:** Gestiona certificados SSL/TLS, cortafuegos de aplicación y límites de tasa de peticiones (*rate limiting*).

### ¿Qué es un Proxy Reverso (*Reverse Proxy*)?
Es un intermediario que se coloca **delante** de uno o más servidores de aplicaciones.
- Para el cliente externo (navegador o cURL), Nginx **es** el servidor web de destino.
- Nginx recibe la petición, la procesa y la reenvía internamente al servicio correspondiente (`proxy_pass http://127.0.0.1:8080`).
- **Diferencia con Forward Proxy (ej. Squid):**
  - *Forward Proxy:* Se coloca del lado de los clientes de una red interna para controlar y filtrar cómo acceden a Internet.
  - *Reverse Proxy:* Se coloca del lado de los servidores para recibir y distribuir las visitas que llegan desde Internet hacia los servicios internos.

### Redirecciones HTTP: 301 vs 302 vs 303
Las redirecciones (familia 3xx) le indican al cliente que el recurso solicitado está disponible en una dirección diferente:
- **`301 Moved Permanently` (el que usamos en Nginx):**
  Indica que el recurso cambió de URL de forma **permanente** (en nuestro caso, migró de `http://` no seguro a `https://` seguro). Los navegadores y buscadores guardan esta redirección en caché para saltar automáticamente a HTTPS en visitas posteriores.
- **`302 Found` (Redirección Temporal):**
  Indica que el cambio de ubicación es temporal. Los clientes seguirán pidiendo la URL original en futuras ocasiones.
- **`303 See Other`:**
  Indica al cliente que debe buscar la respuesta en otra URL utilizando estrictamente el método **`GET`**. Es muy utilizado en aplicaciones web tras procesar un formulario con `POST` (patrón *Post/Redirect/Get*), para evitar que si el usuario presiona "recargar" en el navegador se vuelva a enviar la información duplicada.

### Terminación SSL/TLS (*SSL Termination*)
Es la práctica donde el proxy reverso (Nginx) asume todo el costo computacional del cifrado y descifrado criptográfico (el handshake TLS).
Una vez descifrado el paquete en el puerto 443, Nginx le transfiere la solicitud en HTTP plano al backend (`127.0.0.1:8080`) a través del loopback local. Esto simplifica la infraestructura porque el backend no necesita gestionar certificados y queda protegido detrás del proxy.

### Cabeceras `X-Forwarded-*`
Dado que Nginx intermedia la conexión, la conexión TCP con el backend nace en la IP de Nginx (`127.0.0.1`). Para que el backend conozca el contexto real del visitante, Nginx inyecta cabeceras especiales:
- **`Host`:** El nombre de dominio original que solicitó el cliente.
- **`X-Real-IP`:** La dirección IP real del visitante remoto.
- **`X-Forwarded-For`:** Lista de IPs por las que fue pasando la petición.
- **`X-Forwarded-Proto`:** Informa si la conexión del usuario original vino por `http` o por `https`.
