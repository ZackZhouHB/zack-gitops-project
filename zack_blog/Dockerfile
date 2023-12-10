# Use a base image with Ruby and Node.js pre-installed
FROM ruby:2.7.4

# Set the working directory to /app
WORKDIR /app

# Copy the Gemfile and Gemfile.lock into the image
COPY Gemfile Gemfile.lock /app/

# Copy the current directory contents into the container at /app
COPY . /app

# Expose port 4000 for Jekyll to run ##
EXPOSE 4000

# Build the Jekyll site
CMD ["jekyll", "serve", "--host", "0.0.0.0"]
