# MAX Platform Nginx Configuration

This directory contains Nginx configuration files for serving the MAX Platform application.

## Files

- `nginx.conf` - Production-ready configuration with advanced features
- `nginx-dev.conf` - Simplified configuration for development

## Setup Instructions

### Prerequisites

1. Nginx installed on your system
2. MAX Platform backend running on ports 8000, 8001, 8002 (using PM2)
3. Frontend built and available in `frontend/dist/`

### Production Setup (nginx.conf)

1. **Copy configuration to Nginx directory:**
   ```bash
   sudo cp nginx.conf /etc/nginx/sites-available/maxplatform
   sudo ln -s /etc/nginx/sites-available/maxplatform /etc/nginx/sites-enabled/
   ```

2. **Test configuration:**
   ```bash
   sudo nginx -t
   ```

3. **Reload Nginx:**
   ```bash
   sudo systemctl reload nginx
   ```

4. **Access the application:**
   - Frontend: http://localhost
   - API: http://localhost/api/
   - Docs: http://localhost/docs

### Development Setup (nginx-dev.conf)

1. **Run with custom config:**
   ```bash
   nginx -c /path/to/maxplatform/nginx-dev.conf -p /tmp
   ```

2. **Access the application:**
   - Frontend: http://localhost:3000
   - API: http://localhost:3000/api/
   - Docs: http://localhost:3000/docs

### Features

#### Production Configuration (nginx.conf)
- **Load Balancing**: Distributes requests across 3 backend instances
- **Static File Serving**: Efficient serving of React frontend
- **Compression**: Gzip compression for better performance
- **Security Headers**: Basic security headers included
- **Caching**: Optimized caching for static assets
- **WebSocket Support**: For real-time features
- **Health Checks**: Backend health monitoring
- **Error Handling**: Custom error pages

#### Backend Load Balancing
- Uses `least_conn` method for optimal distribution
- Health checks with automatic failover
- Connection keepalive for performance

#### Frontend Routing
- SPA (Single Page Application) support
- Proper handling of client-side routing
- Optimized caching strategies

## PM2 Backend Setup

Make sure your backend is running with PM2:

```bash
# Start 3 instances
pm2 start backend/main.py --name "maxplatform-8000" -- --port 8000
pm2 start backend/main.py --name "maxplatform-8001" -- --port 8001
pm2 start backend/main.py --name "maxplatform-8002" -- --port 8002

# Check status
pm2 status
```

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**: Backend services not running
   ```bash
   pm2 status  # Check if backends are running
   ```

2. **404 for API routes**: Check upstream configuration
   ```bash
   curl http://localhost:8000/api/health  # Test backend directly
   ```

3. **Static files not found**: Check frontend build
   ```bash
   ls -la frontend/dist/  # Verify build exists
   ```

### Logs

- Nginx access logs: `/var/log/nginx/maxplatform_access.log`
- Nginx error logs: `/var/log/nginx/maxplatform_error.log`
- Development logs: `/tmp/nginx_access.log`, `/tmp/nginx_error.log`

### Health Check

Test the health check endpoint:
```bash
curl http://localhost/nginx-health
```

## SSL Configuration

To enable HTTPS in production, uncomment and configure the SSL server block in `nginx.conf`:

1. Obtain SSL certificates
2. Update certificate paths
3. Uncomment SSL server block
4. Add redirect from HTTP to HTTPS if needed

## Performance Tuning

For high-traffic scenarios, consider:

- Increasing `worker_connections`
- Tuning `proxy_buffer_size` and `proxy_buffers`
- Enabling `proxy_cache` for API responses
- Implementing rate limiting with `limit_req`