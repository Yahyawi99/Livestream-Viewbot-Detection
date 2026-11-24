# Livestream Viewbot Detection

**Can we spot livestreams whose audiences don't behave like real audiences?**

This project collects live audience data from streaming platforms, learns what "normal" viewer behavior looks like, and flags streams whose audience patterns look unusual. It is a research project about finding suspicious audience behavior, such as artificially inflated viewer counts ("viewbots"), without needing anyone to label examples first.

---

## The idea in plain words

A real audience is messy. Viewers trickle in, spike when a streamer raids or goes viral, and drift away as the stream goes on. A bought or automated audience often moves differently: it may jump up suddenly, stay oddly flat, or rise and fall in ways that don't match a human crowd.

Instead of writing rules for every suspicious pattern, we let a model learn normal behavior from lots of real data. Anything it struggles to reproduce is treated as unusual and worth a closer look.

> **A note on what this does and doesn't claim.** An unusual pattern is not proof of a viewbot. A stream can look strange because of a big raid, a front-page feature, or a viral clip. This project surfaces *unusual audience behavior* for investigation; it does not accuse any streamer.

---

## How it works

The project is a pipeline with four stages:

1. **Collect.** Every minute, the project asks Twitch which streams are live and records roughly the top 1,000 of them, including their viewer counts.
2. **Store.** Raw observations are saved exactly as received, so nothing is lost and we can revisit our analysis later. Data is grouped into hourly files, compressed to save space, and organized by date and hour.
3. **Prepare.** The raw snapshots are turned into one audience timeline per stream, and from those timelines we calculate how quickly viewership grows, how bumpy it is, how sudden its spikes are, and how long changes last.
4. **Detect.** A neural network called an **LSTM autoencoder** studies those timelines. It learns to compress a normal audience pattern and rebuild it. When it meets a pattern it can't rebuild well, that stream gets a high "unusualness" score.

### Why two platforms?

- **Twitch** data is used for *learning*. We assume most of it reflects genuine audiences, though we accept it may contain some contamination.
- **Kick** data is used for *testing*. Suspicious audience behavior may be more common there, which makes it a good place to see whether the model picks up something meaningful.

Because the two platforms have different audience sizes and habits, a model trained on one won't automatically transfer to the other. This **domain shift** is a central research question, and we treat it as something to study.

---

## What's inside

```
livestream-viewbot-detection/
├── scripts/       Ready-to-run entry points (start collecting data here)
├── src/
│   ├── clients/       Talks to the Twitch API
│   ├── collectors/    Runs the once-a-minute collection loop
│   ├── ingestion/     Decides how and where collected data is saved
│   ├── storage/       Writes data to local or cloud object storage
│   └── config/        Reads settings and credentials
├── rustfs/        Guide for setting up local storage for development
├── tests/         Checks that the API client and storage work
├── .env.example   Template for your credentials
└── requirements.txt
```

The pieces are deliberately separate. The part that fetches data doesn't care where it's stored, and the storage doesn't care where the data came from. That makes it easy to swap in a different storage service or add a new platform without rewriting everything.

---

## How the data is stored

We follow a "bronze layer" approach: keep the raw data untouched, and do all cleaning and feature-building in later steps. This way we can change our minds about features or models without having to recollect anything.

- Observations are collected every **60 seconds**.
- They are gathered into one file per **hour**, then compressed.
- Files are organized by date and hour, so it's easy to find any slice of time:

```
streams/
├── 2026-11-24/
│   ├── 14.jsonl.gz
│   ├── 15.jsonl.gz
│   └── 16.jsonl.gz
└── 2026-11-25/
    └── 09.jsonl.gz
```

- A completed hour is only removed from the local machine after it has been safely uploaded. If an upload fails, it is kept and retried.
- If the collector is stopped normally, the partial hour is saved before it exits.

During development, storage runs on your own computer using a local S3-compatible service (RustFS). For long-term storage, the same approach points to Backblaze B2. Because I don't have access to free cloud services, I ran the collection script on Termux (Android) and uploaded the hourly archives to B2 from there.

---

## Getting started

You will need Python 3.10+, a free Twitch developer account, and (for local storage) Podman.

1. **Get the code**
   ```bash
   git clone https://github.com/Yahyawi99/Livestream-Viewbot-Detection
   cd Livestream-Viewbot-Detection
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add your credentials.** Copy `.env.example` to `.env` and fill in your Twitch client ID and secret, plus your storage settings.

4. **Set up local storage.** Follow the step-by-step guide in [`rustfs/SETUP.md`](rustfs/SETUP.md).

5. **Start collecting**
   ```bash
   python -m scripts.collect_streams
   ```

Leave it running and it will keep gathering data every minute. Press `Ctrl+C` to stop it cleanly.

I ran this on Termux (Android) to upload data to B2, since I don't have access to free cloud services; the same `python -m scripts.collect_streams` command works there once dependencies are installed.

---

## Where this is headed

The collection and storage foundation is the base for a larger pipeline:

| Stage | Purpose |
|---|---|
| Streaming ingestion (Apache Kafka) | Handle a continuous flow of observations |
| Large-scale processing (Apache Spark) | Turn raw snapshots into timelines efficiently |
| Data preparation (Python, Pandas, NumPy) | Build the features the model learns from |
| Modeling (TensorFlow / Keras) | Train and run the LSTM autoencoder |

---

## Limitations worth knowing

- **No ground truth.** We don't have a confirmed list of viewbotted streams, so results are indicators, not verdicts.
- **Contaminated training data.** Twitch data is assumed to be mostly genuine, but some suspicious streams may be mixed in.
- **Platform differences.** Twitch and Kick audiences differ, which affects how well one can inform the other.
- **Public data only.** We use what the platform exposes publicly, so we can't see things like individual viewer accounts or chat membership.
