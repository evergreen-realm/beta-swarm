# Use official Nginx image as a base
FROM nginx:alpine

# Set working directory
WORKDIR /app

# Copy index.html and styles.css to /app
COPY index.html /app/
COPY styles.css /app/

# Copy script.js to /app
COPY script.js /app/

# Expose port 80 (default Nginx port)
EXPOSE 80

# Run Nginx command to serve files
CMD ["nginx", "-g", "daemon off;"]