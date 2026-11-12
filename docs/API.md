# Local Bridge API

- GET /v1/health
- GET /v1/device/status
- POST /v1/device/configure (simulation acknowledgement only; no Wi-Fi provisioning implemented)
- POST /v1/capture
- GET /v1/captures/{capture_id}/image
- POST /v1/captures/{capture_id}/analyze (quality metrics only)
- DELETE /v1/captures/{capture_id}
