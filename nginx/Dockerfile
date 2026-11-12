FROM nginx:1.27-alpine

# Install openssl to generate self-signed TLS certificates during container build
RUN apk add --no-cache openssl

WORKDIR /etc/nginx

# Generate SSL certificates
COPY generate_certs.sh /docker-entrypoint.d/00-generate-certs.sh
RUN chmod +x /docker-entrypoint.d/00-generate-certs.sh && \
    /docker-entrypoint.d/00-generate-certs.sh

# Copy custom Nginx configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/proxy.conf /etc/nginx/conf.d/proxy.conf

# Remove default site configuration if present
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
