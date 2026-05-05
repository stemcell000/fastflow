FROM nginx:1.25-alpine

# Supprime la config par défaut
RUN rm /etc/nginx/conf.d/default.conf

COPY docker/nginx/nginx.conf /etc/nginx/conf.d/app.conf

EXPOSE 80
