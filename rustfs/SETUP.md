# RustFS Setup (Podman)

Local, single-node [RustFS](https://rustfs.com) object storage running in a rootless Podman container. RustFS is an S3-compatible, high-performance object store (Apache 2.0 license), used here as an alternative to MinIO for the `livestream-viewbot-detection` project.

This guide follows the official [RustFS Podman documentation](https://docs.rustfs.com/en/installation/container/podman), with a few additions for rootless Podman.

## Overview

| Item | Value |
|------|-------|
| Runtime | Podman 5.8.9 (rootless) |
| Image | `docker.io/rustfs/rustfs:latest` |
| Container name | `rustfs` |
| S3 API | `http://127.0.0.1:9000` |
| Web console | `http://127.0.0.1:9001` |
| Health endpoint | `http://127.0.0.1:9000/health` |
| Data directory | `~/rustfs/data` |
| Config file | `~/rustfs/config/rustfs.env` |
| Container user | `rustfs` (UID/GID `10001`, non-root) |

Ports are bound to `127.0.0.1` only, so RustFS is **not** reachable from other machines. Without the `127.0.0.1:` prefix, Podman publishes the ports on all network interfaces.

## Directory layout

```
~/rustfs/
├── config/
│   └── rustfs.env     # credentials and settings (chmod 600)
└── data/              # persistent object storage (mounted at /data)
```

## 1. Pull the image

```bash
podman pull docker.io/rustfs/rustfs:latest
```

## 2. Create directories

```bash
mkdir -p ~/rustfs/data
mkdir -p ~/rustfs/config
```

## 3. Set data directory ownership (rootless Podman)

The container runs as UID `10001`. The official docs say to `chown -R 10001:10001` the host directory, which is correct for rootful Docker. **With rootless Podman, a plain `sudo chown 10001:10001` is wrong**: container UID 10001 is mapped to a different host UID (from your `subuid` range), so the directory would appear to belong to nobody inside the container and writes fail with `permission denied`.

Use `podman unshare`, which runs `chown` inside your user namespace:

```bash
# if you previously ran: sudo chown -R 10001:10001 ~/rustfs/data
# first hand the directory back to your own user:
sudo chown -R "$USER": ~/rustfs/data

# then set ownership as the container sees it:
podman unshare chown -R 10001:10001 ~/rustfs/data
```

Check it (on the host the numeric owner will be a high subuid number, not 10001; that is expected):

```bash
ls -ldn ~/rustfs/data
podman unshare ls -ldn ~/rustfs/data     # should show 10001 10001
```

**Alternative:** use a named volume, which needs no permission fixes. Run `podman volume create rustfs-data`, and in step 5 replace `-v ~/rustfs/data:/data:Z` with `-v rustfs-data:/data`.

## 4. Create the config file

Generate a random access key and secret key. The docs say not to use the well-known `rustfsadmin` value for either one.

```bash
RUSTFS_ACCESS=$(openssl rand -hex 8)
RUSTFS_PASSWORD=$(openssl rand -hex 32)

cat > ~/rustfs/config/rustfs.env <<EOF
RUSTFS_ACCESS_KEY=$RUSTFS_ACCESS
RUSTFS_SECRET_KEY=$RUSTFS_PASSWORD
RUSTFS_ADDRESS=:9000
RUSTFS_CONSOLE_ADDRESS=:9001
RUSTFS_CONSOLE_ENABLE=true
RUSTFS_OBS_LOGGER_LEVEL=info
RUSTFS_OBS_LOG_DIRECTORY=/var/log/rustfs/
EOF

chmod 600 ~/rustfs/config/rustfs.env
unset RUSTFS_ACCESS RUSTFS_PASSWORD
```

| Variable | Meaning |
|----------|---------|
| `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` | Root credentials (S3 keys and console login) |
| `RUSTFS_ADDRESS` | S3 API listen address inside the container |
| `RUSTFS_CONSOLE_ADDRESS` | Console listen address inside the container |
| `RUSTFS_CONSOLE_ENABLE` | Enables the web console |
| `RUSTFS_OBS_LOGGER_LEVEL` | Log verbosity (`error` is quieter; the official example uses `error`) |
| `RUSTFS_OBS_LOG_DIRECTORY` | Where RustFS writes log files inside the container |

> **Security notes**
> - Avoid running `cat` on this file in shared terminals, screenshots or chats. If the keys were exposed, rotate them (see [Rotating credentials](#rotating-credentials)).
> - Never commit `rustfs.env` to git.

## 5. Run the container

```bash
podman run -d \
  --name rustfs \
  --restart unless-stopped \
  -p 127.0.0.1:9000:9000 \
  -p 127.0.0.1:9001:9001 \
  -v ~/rustfs/data:/data:Z \
  --env-file ~/rustfs/config/rustfs.env \
  docker.io/rustfs/rustfs:latest \
  /data
```

| Option | Purpose |
|--------|---------|
| `--restart unless-stopped` | Restart the container if it exits (see the note on reboots below) |
| `-p 127.0.0.1:9000:9000` | S3 API, localhost only |
| `-p 127.0.0.1:9001:9001` | Web console, localhost only |
| `-v ~/rustfs/data:/data:Z` | Persist data on the host; `:Z` relabels the directory for SELinux |
| `--env-file ...` | Loads credentials and settings without putting them on the command line |
| `/data` | Directory RustFS serves |

> **Terminal tip:** if your shell shows `-- MULTILINE --` and does not run the pasted command, press `Ctrl+J` to run it (or `Ctrl+C` to cancel and start over). Typing it as a single line avoids the issue.

### Restart policy and reboots

With rootless Podman, `--restart unless-stopped` restarts the container after crashes, but restarting it after a **reboot** requires the Podman restart service:

```bash
systemctl --user enable --now podman-restart.service
loginctl enable-linger "$USER"    # keep user services running without a login session
```

## 6. Verify the deployment

```bash
podman ps --filter name=rustfs
curl --fail http://127.0.0.1:9000/health
podman logs rustfs
```

Open the console at <http://127.0.0.1:9001> and log in with the access key and secret key from `~/rustfs/config/rustfs.env`.

## Daily operations

```bash
podman stop rustfs       # stop
podman start rustfs      # start again (data and config persist)
podman restart rustfs
podman logs -f rustfs    # follow logs
podman rm -f rustfs      # remove container (data in ~/rustfs/data is kept)
```

## Using RustFS from code

RustFS speaks the S3 API, so standard S3 tools and SDKs work.

### RustFS CLI (`rc`)

```bash
rc alias set rustfs http://127.0.0.1:9000 <access-key> <secret-key>
```

See the [rc documentation](https://docs.rustfs.com/en/operations/rc). Other S3 clients (`aws` CLI, `mc`, `s3cmd`) also work when pointed at `http://127.0.0.1:9000`.

### Python (boto3)

```python
import os
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://127.0.0.1:9000",
    aws_access_key_id=os.environ["RUSTFS_ACCESS_KEY"],
    aws_secret_access_key=os.environ["RUSTFS_SECRET_KEY"],
)
s3.create_bucket(Bucket="my-bucket")
```

Load credentials from environment variables rather than hard-coding them.

## Rotating credentials

1. Generate new values and rewrite `~/rustfs/config/rustfs.env` (step 4).
2. Recreate the container so it reads the new file:

   ```bash
   podman rm -f rustfs
   # re-run the podman run command from step 5
   ```

3. Update every application or CLI alias that uses the old keys.

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `permission denied` on `/data`, container exits | Ownership was set with plain `chown`. Use `podman unshare chown -R 10001:10001 ~/rustfs/data` (step 3) |
| Errors about writing to `/var/log/rustfs` | The log directory is not writable by UID 10001. Set `RUSTFS_OBS_LOG_DIRECTORY` to a writable path, or mount a host log directory (prepared with `podman unshare chown -R 10001:10001`) at `/var/log/rustfs` |
| Shell shows `-- MULTILINE --` and nothing runs | Press `Ctrl+J` to execute the command |
| `podman run` printed nothing | Run `podman ps -a` and `podman logs rustfs` |
| `name "rustfs" is already in use` | `podman rm -f rustfs`, then run again |
| Port already in use | Another service (e.g. an old MinIO container) is on 9000/9001: `podman rm -f minio`, or change the host port, e.g. `-p 127.0.0.1:9100:9000` |
| Cannot log in to the console | Check `rustfs.env` has no stray spaces or quotes; recreate the container after editing it |
| Container not running after reboot | Enable `podman-restart.service` (see above) |

## Migrating from MinIO

If the MinIO container from the earlier setup is still present, remove it first so ports 9000 and 9001 are free:

```bash
podman rm -f minio
```

Copy objects between the two endpoints with an S3 client (e.g. `mc mirror` or `rclone sync`). Do not point RustFS at MinIO's `~/minio/data` directory; the on-disk formats are not interchangeable.

## Recommendations

- **Pin the image version** (e.g. `docker.io/rustfs/rustfs:<version>`) instead of `latest`, so upgrades are deliberate.
- **Back up** `~/rustfs/data` regularly.
- Create dedicated access keys/users for applications instead of using the root credentials.
- Add `rustfs/` or `*.env` to `.gitignore` if this folder lives inside a repository.
