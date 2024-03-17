FROM jekyll/builder:latest as builder

WORKDIR /srv/jekyll
COPY Gemfile Gemfile.lock ./

RUN bundle install
COPY . .
RUN jekyll build
RUN bundle exec jekyll serve




# Use an Nginx base image
FROM nginx:alpine

# Set the working directory to /usr/share/nginx/html
WORKDIR /usr/share/nginx/html

# Copy the Jekyll-generated static site into the image
COPY _site/ .

# Expose port 80 for the Nginx web server
EXPOSE 80

# Command to start Nginx (runs in the foreground)
CMD ["nginx", "-g", "daemon off;"]
