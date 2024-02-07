FROM jekyll/builder:latest as builder

WORKDIR /srv/jekyll
COPY Gemfile Gemfile.lock ./

RUN bundle install
COPY . .
RUN jekyll build
RUN bundle exec jekyll serve




# Use an Nginx base image
FROM nginx:alpine

# Create directory for SSL certificates
RUN mkdir -p /etc/nginx/ssl/

# Copy SSL certificate files into the image
# COPY certificate.crt /etc/ssl/nginx/certificate.crt
# COPY private.key /etc/ssl/nginx/private.key

# Update Nginx configuration to use SSL certificates
#RUN sed -i 's|# SSL configuration|# SSL configuration\n    ssl_certificate /etc/nginx/ssl/certificate.crt;\n    ssl_certificate_key /etc/nginx/ssl/private.key;|' /etc/nginx/nginx.conf


# Set the working directory to /usr/share/nginx/html
WORKDIR /usr/share/nginx/html

# Copy the Jekyll-generated static site into the image
COPY _site/ .

# Expose port 443 for HTTPS
EXPOSE 443

# Command to start Nginx (runs in the foreground)
CMD ["nginx", "-g", "daemon off;"]
