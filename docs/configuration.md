# Configuration

Example configuration file:

```
{
    "access_key": "API_ACCESS_KEY",
    "max_concurrent": 2,
    "username": "cmsbhk",
    "docker_url": "ssh://user@192.168.5.10",
    "log_dir": "./logs",
    "log_level": "info"
}
```

- `access_key`: The key needed to authenticate and use Minke outside of 'localhost'.
- `max_concurrent`: Make number of analysis threads to start. Use according to available resources.
- `username`: Username internal to the Docker containers. This is auto-updated when building containers.
- `log_dir`: Directory for logs to go
- `log_level`: Level of log severity