# Usage

Minke is primarily used through its API and a handful of CLI commands.

!!! info

    The API key must be used with any external access. Local access does not require authentication.

## CLI Commands

A few CLI commands are available to perform server maintenance.

### `run`

- `web`: Runs the web server

### `submissions`

- `clean`: Removes all submissions

### `containers`

- `info`: View info of built Minke container images
- `list`: Lists all Minke container images
- `build [--force] [--images <IMAGE>]`: Build Minke container images, optionally force to rebuild with `--force`. To limit the build to certain images, use `--image <IMAGE>` to limit to `<IMAGE>`. This can be used multiple times.

## API Usage

Minke utilizes [FastAPI](https://fastapi.tiangolo.com/) to make API documentation easy. On your instance of Minke, go to:

```
http://<MINKE_IP>:8000/docs
```

to get the Swagger UI and start interacting with the API. 

### Submit Script

A script to submit files is available in `scripts/curl_submit.sh`, usage is:

```
scripts/curl_submit.sh <FILE> <SAMPLE_ARGUMENTS>
```

