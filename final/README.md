# EDI II - Examen Final: Proyectos Prácticos de Administración Linux

Repositorio con los proyectos prácticos preparados para la defensa en el examen final.

---

## Estructura de Proyectos

| # | Proyecto | Carpeta | Enfoque Principal |
|---|---|---|---|
| 1 | **Monitoreo HTTP con cURL** | [`01_monitoreo_http/`](./01_monitoreo_http) | Scripting Bash, códigos de estado HTTP, latencia y diagnóstico de red |
| 2 | **Firma Digital con PGP + CRON** | [`02_firma_pgp_cron/`](./02_firma_pgp_cron) | Criptografía asimétrica, llaves GPG, pipelines de procesamiento y automatización periódica |
| 3 | **Nginx con SSL y Proxy Reverso** | [`03_nginx_proxy_ssl/`](./03_nginx_proxy_ssl) | Servidores web, certificados SSL/TLS, reverse proxy y arquitectura de servicios |

---

## Resumen de los Proyectos

1. **`01_monitoreo_http`:**
   - Script Bash simple (`check_http.sh`) para consultar cualquier URL.
   - Analiza el código HTTP y mide el tiempo de respuesta.
   - Distingue servidores activos (200), redirecciones (301/302), errores (404/500) y caídas (000).

2. **`02_firma_pgp_cron`:**
   - Flujo de procesamiento de documentos (`ParaFirmar` -> `Firmados` + firma `.asc`).
   - Firma desatendida mediante llaves GPG.
   - Script de comprobación de autenticidad e integridad ante modificaciones.
   - Programación periódica mediante `crontab`.

3. **`03_nginx_proxy_ssl`:**
   - Servidor Nginx configurado como Reverse Proxy con terminación SSL/TLS.
   - Redirección automática de HTTP (puerto 80) hacia HTTPS (puerto 443).
   - Reenvío de cabeceras (`X-Real-IP`, `X-Forwarded-Proto`) hacia un backend interno en puerto 8080.
   - Certificado autofirmado generado con OpenSSL.

---

## Instrucciones Rápidas
Cada carpeta cuenta con su propio archivo `README.md` con:
- Explicación técnica y práctica del funcionamiento interno.
- Guía de demostración paso a paso con comandos listos para copiar y pegar.
- Banco de preguntas teóricas de examen y respuestas sugeridas.
