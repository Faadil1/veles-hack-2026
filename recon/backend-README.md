# IDE Backend

This is the backend Expess server for the HyperAI IDE


## Getting Started

Prerequisites: [Node.js](https://nodejs.org/)

```bash
npm install
node src/server.js
```

## Docker

Build the image:
```bash
docker build -t ide-backend .
```

Run the container:
```bash
docker run --rm \
  -p 3001:3001 \
  -v ide_helm_charts:/app/helm-charts \
  -v ide_templates:/app/templates \
  --name ide-backend \
  ide-backend
```


The service will be available at http://localhost:3001/

## License

Apache 2.0 — see [LICENCE](LICENCE).