# Basemap Configuration

InfoDengue uses CARTO raster basemaps (*Positron / Light*) for municipality and regional alert maps rendered via Leaflet (`django-leaflet`).

## Environment Variable

CARTO requires an API key for raster basemap tile requests. This is configured via the environment variable:

```text
CARTO_BASEMAP_API_KEY
```

### Purpose

- Supplies the query parameter `?key=<api_key>` in HTTPS raster tile requests (`https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png?key=...`).
- Enables basemap raster tiles to render without the `API KEY REQUIRED` watermark.

### Staging and Production Management

- Staging and production environments should configure `CARTO_BASEMAP_API_KEY` independently with their respective CARTO keys.
- **Never commit real API keys** to version control, source code, fixtures, Dockerfiles, or tracked documentation.
- The environment variable template `.envs/.env.tpl` provides the placeholder `CARTO_BASEMAP_API_KEY=${CARTO_BASEMAP_API_KEY}`.

### Missing Configuration Behavior

If `CARTO_BASEMAP_API_KEY` is not set or is empty:

1. **System Check Warning**: Django's system check framework issues a warning (`ad_main.W001`):
   ```text
   CARTO_BASEMAP_API_KEY is not configured; CARTO basemap tiles cannot be loaded correctly.
   ```
2. **Application Log Warning**: A warning log is emitted during settings initialization.
3. **Application Availability**: Non-map APIs, database operations, and non-map views remain fully operational. Map layers fall back to HTTPS CARTO tile URLs without key parameter.

### Applying Changes

After setting or modifying `CARTO_BASEMAP_API_KEY` in the runtime environment (e.g. `.envs/.env` or container orchestration variables), the standard application restart or container redeployment is required to load the new environment variable.
