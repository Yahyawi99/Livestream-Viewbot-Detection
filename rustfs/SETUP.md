# RustFS Setup (Podman)

Local, single-node [RustFS](https://rustfs.com) object storage running in a rootless Podman container with a Podman named volume for persistent data. RustFS is an S3-compatible, high-performance object store (Apache 2.0 license), used here as an alternative to MinIO for the `livestream-viewbot-detection` project.

This guide follows the official [RustFS Podman documentation](https://docs.rustfs.com/en/installation/container/podman).

## Overview

| Item            | Value                                                  |
| --------------- | ------------------------------------------------------ |
| Runtime         | Podman 5.8.9 (rootless)                                |
| Image           | `docker.io/rustfs/rustfs:latest`                       |
| Container name  | `rustfs`                                               |
| S3 API          | `http://127.0.0.1:9000`                                |
| Web console     | `http://127.0.0.1:9001`                                |
| Health endpoint | `http://127.0.0.1:9000/health`                         |
| Data storage    | Podman named volume `rustfs-data` (mounted at `/data`) |
| Config file     | `~/rustfs/config/rustfs.env`                           |
| Container user  | `rustfs` (UID/GID `10001`, non-root)                   |

Ports are bound to `127.0.0.1` only, so RustFS is **not** reachable from other machines. Without the `127.0.0.1:` prefix, Podman publishes the ports on all network interfaces.

## Why a named volume

A named volume is managed by Podman and needs no ownership or SELinux fixes. The container runs as non-root UID `10001`, and with a host bind mount in rootless Podman you must set ownership with `podman unshare chown`; a named volume avoids that entirely. The volume also survives container removal and replacement.

## 1. Pull the image

```bash
podman pull docker.io/rustfs/rustfs:latest
```

## 2. Create the volume and config directory

```bash
podman volume create rustfs-data
mkdir -p ~/rustfs/config
```

## 3. Create the config file

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

| Variable                                  | Meaning                                                               |
| ----------------------------------------- | --------------------------------------------------------------------- |
| `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` | Root credentials (S3 keys and console login)                          |
| `RUSTFS_ADDRESS`                          | S3 API listen address inside the container                            |
| `RUSTFS_CONSOLE_ADDRESS`                  | Console listen address inside the container                           |
| `RUSTFS_CONSOLE_ENABLE`                   | Enables the web console                                               |
| `RUSTFS_OBS_LOGGER_LEVEL`                 | Log verbosity (`error` is quieter; the official example uses `error`) |
| `RUSTFS_OBS_LOG_DIRECTORY`                | Where RustFS writes log files inside the container                    |

> **Security notes**
>
> - Avoid running `cat` on this file in shared terminals, screenshots or chats. If the keys were exposed, rotate them (see [Rotating credentials](#rotating-credentials)).
> - Never commit `rustfs.env` to git.

## 4. Run the container

```bash
podman run -d \
  --name rustfs \
  --restart unless-stopped \
  -p 127.0.0.1:9000:9000 \
  -p 127.0.0.1:9001:9001 \
  -v rustfs-data:/data \
  --env-file ~/rustfs/config/rustfs.env \
  docker.io/rustfs/rustfs:latest \
  /data
```

| Option                     | Purpose                                                                 |
| -------------------------- | ----------------------------------------------------------------------- |
| `--restart unless-stopped` | Restart the container if it exits (see the note on reboots below)       |
| `-p 127.0.0.1:9000:9000`   | S3 API, localhost only                                                  |
| `-p 127.0.0.1:9001:9001`   | Web console, localhost only                                             |
| `-v rustfs-data:/data`     | Mount the named volume for persistent data                              |
| `--env-file ...`           | Loads credentials and settings without putting them on the command line |
| `/data`                    | Directory RustFS serves                                                 |

On success, Podman prints the new container ID.

> **Terminal tip:** if your shell shows `-- MULTILINE --` and does not run a pasted command, press `Ctrl+J` to run it (or `Ctrl+C` to cancel).

### Restart policy and reboots

With rootless Podman, `--restart unless-stopped` restarts the container after crashes, but restarting it after a **reboot** requires the Podman restart service:

```bash
systemctl --user enable --now podman-restart.service
loginctl enable-linger "$USER"    # keep user services running without a login session
```

## 5. Verify the deployment

```bash
podman ps --filter name=rustfs
curl --fail http://127.0.0.1:9000/health
podman logs rustfs
```

Open the console at <http://127.0.0.1:9001>. You should see the RustFS login page:

![RustFS console login page](images/rustfs-login.png)

On the **Key Login** tab, enter the values from `~/rustfs/config/rustfs.env`:

| Login field | Value               |
| ----------- | ------------------- |
| **Account** | `RUSTFS_ACCESS_KEY` |
| **Key**     | `RUSTFS_SECRET_KEY` |

If the login page loads, the container is running and the console is reachable. (The **STS Login** tab is for temporary credentials and isn't needed for this setup.)

## Daily operations

```bash
podman stop rustfs       # stop
podman start rustfs      # start again (data and config persist)
podman restart rustfs
podman logs -f rustfs    # follow logs
podman rm -f rustfs      # remove container (the rustfs-data volume is kept)
```

## Managing the volume

```bash
podman volume ls                       # list volumes
podman volume inspect rustfs-data      # shows the Mountpoint on the host
```

> **Warning:** `podman volume rm rustfs-data` permanently deletes all stored objects. `podman system prune --volumes` can also remove volumes that no container is using, so don't run it while the container is stopped and removed unless you have a backup.

### Backup and restore

```bash
# backup (stop the container first for a consistent copy)
podman stop rustfs
podman volume export rustfs-data --output ~/rustfs-data-backup.tar
podman start rustfs

# restore into a new, empty volume
podman volume create rustfs-data-restored
podman volume import rustfs-data-restored ~/rustfs-data-backup.tar
```

## Bucket: `twitch-raw-data`

Raw, unprocessed Twitch data collected for `livestream-viewbot-detection`. Files are stored as JSON Lines (`.jsonl`, one JSON record per line) and partitioned by date using Hive-style `year=/month=/day=` prefixes.

### Layout

```
twitch-raw-data/
│
├── streams/
│   └── year=2026/
│       └── month=11/
│           └── day=12/
│               ├── collection_001.jsonl
│               └── collection_002.jsonl
│
├── viewer-snapshots/
│   └── year=2026/
│       └── month=11/
│           └── day=12/
│               └── snapshots_001.jsonl
│
└── chat-events/
    └── year=2026/
        └── month=11/
            └── day=12/
                └── chat_001.jsonl
```

### Prefixes

| Prefix              | Contents                              | File naming            |
| ------------------- | ------------------------------------- | ---------------------- |
| `streams/`          | Stream metadata collected from Twitch | `collection_NNN.jsonl` |
| `viewer-snapshots/` | Periodic viewer-count snapshots       | `snapshots_NNN.jsonl`  |
| `chat-events/`      | Chat events                           | `chat_NNN.jsonl`       |

Object key pattern:

```
<dataset>/year=YYYY/month=MM/day=DD/<file-prefix>_NNN.jsonl
```

### Conventions

- **Raw and immutable:** write new files instead of modifying existing ones, and do transformations in a separate (processed) bucket or prefix.
- **Zero-padded numbering:** `NNN` increments per file within a day (`001`, `002`, ...), and `MM`/`DD` are zero-padded so keys sort correctly.
- **One timezone:** pick one for the date partitions and use it everywhere (UTC is the usual choice).
- **Folders are prefixes:** S3-compatible storage has no real directories. The "folders" above exist only as key prefixes, and appear once the first object is uploaded under them.
- **Hive-style partitions** let tools such as DuckDB, Spark, Athena or pandas/pyarrow filter by `year`, `month` and `day` automatically.

### Create the bucket and upload a file

```bash
aws --endpoint-url http://127.0.0.1:9000 s3 mb s3://twitch-raw-data

aws --endpoint-url http://127.0.0.1:9000 s3 cp collection_001.jsonl \
  s3://twitch-raw-data/streams/year=2026/month=11/day=12/collection_001.jsonl
```

Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to your RustFS access key and secret key first, or use the equivalent boto3 calls below.

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

1. Generate new values and rewrite `~/rustfs/config/rustfs.env` (step 3).
2. Recreate the container so it reads the new file. The volume and your data stay intact:

   ```bash
   podman rm -f rustfs
   # re-run the podman run command from step 4
   ```

3. Update every application or CLI alias that uses the old keys.

## Troubleshooting

| Symptom                                        | Likely cause / fix                                                                                                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Errors about writing to `/var/log/rustfs`      | The log directory is not writable by UID 10001. Set `RUSTFS_OBS_LOG_DIRECTORY` to a writable path, or mount a second named volume (e.g. `-v rustfs-logs:/var/log/rustfs`) |
| Shell shows `-- MULTILINE --` and nothing runs | Press `Ctrl+J` to execute the command                                                                                                                                     |
| `podman run` printed nothing                   | Run `podman ps -a` and `podman logs rustfs`                                                                                                                               |
| `name "rustfs" is already in use`              | `podman rm -f rustfs`, then run again                                                                                                                                     |
| `rustfs-data` volume missing                   | Run `podman volume create rustfs-data`; if it was deleted, restore from a backup                                                                                          |
| Port already in use                            | Another service (e.g. an old MinIO container) is on 9000/9001: `podman rm -f minio`, or change the host port, e.g. `-p 127.0.0.1:9100:9000`                               |
| Cannot log in to the console                   | Check `rustfs.env` has no stray spaces or quotes; recreate the container after editing it                                                                                 |
| Container not running after reboot             | Enable `podman-restart.service` (see above)                                                                                                                               |

## Migrating from MinIO

If the MinIO container from the earlier setup is still present, remove it first so ports 9000 and 9001 are free:

```bash
podman rm -f minio
```

Copy objects between the two endpoints with an S3 client (e.g. `mc mirror` or `rclone sync`). Do not point RustFS at MinIO's `~/minio/data` directory; the on-disk formats are not interchangeable.

## Recommendations

- **Pin the image version** (e.g. `docker.io/rustfs/rustfs:<version>`) instead of `latest`, so upgrades are deliberate.
- **Back up** the `rustfs-data` volume regularly (see above).
- Create dedicated access keys/users for applications instead of using the root credentials.
- Add `rustfs/` or `*.env` to `.gitignore` if this folder lives inside a repository.
