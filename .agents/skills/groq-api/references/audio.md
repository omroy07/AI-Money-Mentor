# Audio API Reference

Groq provides fast speech-to-text and text-to-speech APIs with OpenAI-compatible endpoints.

## Contents

- [Endpoints](#endpoints)
- [Models](#models)
- [Transcription](#transcription)
- [Translation](#translation)
- [Text-to-Speech](#text-to-speech)
  - [PlayAI TTS](#playai-tts)
  - [Orpheus TTS](#orpheus-tts-expressive-speech)
  - [Vocal Directions](#vocal-directions)
- [Audio File Handling](#audio-file-handling)
- [Response Metadata](#response-metadata)
- [Prompting Guidelines](#prompting-guidelines)

---

## Endpoints

| Endpoint       | Usage                           | API URL                                               |
| -------------- | ------------------------------- | ----------------------------------------------------- |
| Transcriptions | Convert audio to text           | `https://api.groq.com/openai/v1/audio/transcriptions` |
| Translations   | Translate audio to English text | `https://api.groq.com/openai/v1/audio/translations`   |
| Speech         | Convert text to audio           | `https://api.groq.com/openai/v1/audio/speech`         |

---

## Models

### Speech-to-Text Models

| Model ID                 | Description                                                               | Languages    |
| ------------------------ | ------------------------------------------------------------------------- | ------------ |
| `whisper-large-v3-turbo` | Pruned Whisper Large V3, optimized for speed. Best price/performance.     | Multilingual |
| `whisper-large-v3`       | Full Whisper Large V3. Highest accuracy for error-sensitive applications. | Multilingual |

### Model Comparison

| Model                    | Cost/Hour | Transcription | Translation | Speed Factor | Word Error Rate |
| ------------------------ | --------- | ------------- | ----------- | ------------ | --------------- |
| `whisper-large-v3`       | $0.111    | Yes           | Yes         | 189x         | 10.3%           |
| `whisper-large-v3-turbo` | $0.04     | Yes           | No          | 216x         | 12%             |

**Selection guide:**

- Error-sensitive + multilingual: Use `whisper-large-v3`
- Best price/performance + multilingual: Use `whisper-large-v3-turbo`

### Text-to-Speech Models

| Model ID                        | Description                                  | Languages |
| ------------------------------- | -------------------------------------------- | --------- |
| `playai-tts`                    | High-quality text-to-speech                  | English   |
| `canopylabs/orpheus-v1-english` | Expressive TTS with vocal directions support | English   |
| `canopylabs/orpheus-v1-arabic`  | Expressive TTS with vocal directions support | Arabic    |

---

## Transcription

Convert audio to text in the same language.

### Request Parameters

| Parameter                 | Type   | Default              | Description                                                                |
| ------------------------- | ------ | -------------------- | -------------------------------------------------------------------------- |
| `file`                    | file   | Required (or `url`)  | Audio file to transcribe                                                   |
| `url`                     | string | Required (or `file`) | URL to audio file (supports Base64URL)                                     |
| `model`                   | string | Required             | Model ID (`whisper-large-v3-turbo` or `whisper-large-v3`)                  |
| `language`                | string | Optional             | ISO-639-1 language code (e.g., `en`, `es`). Improves accuracy and latency. |
| `prompt`                  | string | Optional             | Context/spelling hints (max 224 tokens)                                    |
| `response_format`         | string | `json`               | Output format: `json`, `verbose_json`, `text`                              |
| `temperature`             | float  | 0                    | Sampling temperature (0-1). Use 0 for deterministic output.                |
| `timestamp_granularities` | array  | `["segment"]`        | Timestamp detail: `segment`, `word`, or both. Requires `verbose_json`.     |

### Basic Transcription

```python
from groq import Groq

client = Groq()

with open("audio.mp3", "rb") as f:
    transcription = client.audio.transcriptions.create(
        file=f,
        model="whisper-large-v3-turbo"
    )
print(transcription.text)
```

### Transcription with Timestamps

```python
import json

with open("audio.mp3", "rb") as f:
    transcription = client.audio.transcriptions.create(
        file=f,
        model="whisper-large-v3-turbo",
        response_format="verbose_json",
        timestamp_granularities=["word", "segment"],
        language="en"
    )
print(json.dumps(transcription, indent=2, default=str))
```

### TypeScript Example

```typescript
import Groq from 'groq-sdk';
import fs from 'fs';

const client = new Groq();

const transcription = await client.audio.transcriptions.create({
  file: fs.createReadStream('audio.mp3'),
  model: 'whisper-large-v3-turbo',
  response_format: 'verbose_json',
  timestamp_granularities: ['word', 'segment'],
});
console.log(transcription.text);
```

---

## Translation

Translate audio from any supported language to English text.

**Note:** Only `whisper-large-v3` supports translation. The `language` parameter only accepts `en`.

### Basic Translation

```python
with open("french_audio.mp3", "rb") as f:
    translation = client.audio.translations.create(
        file=f,
        model="whisper-large-v3"
    )
print(translation.text)  # English text
```

### TypeScript Example

```typescript
const translation = await client.audio.translations.create({
  file: fs.createReadStream('german_audio.mp3'),
  model: 'whisper-large-v3',
});
console.log(translation.text);
```

---

## Text-to-Speech

Convert text to spoken audio. Groq provides fast TTS with support for English and Arabic voices, enabling lifelike audio for customer support agents, game characters, narration, and more.

### Request Parameters

| Parameter         | Type   | Default  | Description                                         |
| ----------------- | ------ | -------- | --------------------------------------------------- |
| `model`           | string | Required | Model ID (see TTS models table)                     |
| `input`           | string | Required | Text to convert to speech                           |
| `voice`           | string | Required | Voice ID (model-specific)                           |
| `response_format` | string | `mp3`    | Output format: `flac`, `mp3`, `mulaw`, `ogg`, `wav` |
| `speed`           | float  | 1.0      | Playback speed (0.5 to 5.0)                         |

### PlayAI TTS

Basic high-quality English text-to-speech.

**Python:**

```python
response = client.audio.speech.create(
    model="playai-tts",
    input="Hello, world!",
    voice="Fritz-PlayAI",
    response_format="wav",
    speed=1.0
)
response.write_to_file("output.wav")
```

**TypeScript:**

```typescript
import Groq from 'groq-sdk';
import fs from 'fs';

const client = new Groq();

const response = await client.audio.speech.create({
  model: 'playai-tts',
  input: 'Hello, world!',
  voice: 'Fritz-PlayAI',
  response_format: 'wav',
});

const buffer = Buffer.from(await response.arrayBuffer());
await fs.promises.writeFile('output.wav', buffer);
```

### Orpheus TTS (Expressive Speech)

Orpheus models support vocal directions for expressive speech generation.

#### Orpheus English

**Voices:** `tara`, `leah`, `jess`, `leo`, `dan`, `mia`, `zac`, `zoe`, `austin`

**Python:**

```python
response = client.audio.speech.create(
    model="canopylabs/orpheus-v1-english",
    input="Welcome to Orpheus text-to-speech. [cheerful] This is an example of expressive audio generation.",
    voice="austin",
    response_format="wav"
)
response.write_to_file("orpheus-english.wav")
```

**TypeScript:**

```typescript
const response = await client.audio.speech.create({
  model: 'canopylabs/orpheus-v1-english',
  input:
    'Welcome to Orpheus. [cheerful] This demonstrates vocal directions support.',
  voice: 'austin',
  response_format: 'wav',
});

const buffer = Buffer.from(await response.arrayBuffer());
await fs.promises.writeFile('orpheus-english.wav', buffer);
```

#### Orpheus Arabic

**Voices:** `farah`, `hadi`, `jad`, `leila`, `lina`, `malik`, `marco`, `rami`, `sakura`, `talia`, `zain`

```python
response = client.audio.speech.create(
    model="canopylabs/orpheus-v1-arabic",
    input="مرحبا بكم في نظام تحويل النص إلى كلام",
    voice="farah",
    response_format="wav"
)
response.write_to_file("orpheus-arabic.wav")
```

#### Vocal Directions

Orpheus models support inline vocal directions in square brackets to control tone and emotion:

```python
input_text = """
[cheerful] Great news! Your order has shipped.
[serious] Please review the terms carefully.
[whisper] This is a secret message.
[excited] You won the grand prize!
"""

response = client.audio.speech.create(
    model="canopylabs/orpheus-v1-english",
    input=input_text,
    voice="tara",
    response_format="wav"
)
```

### Streaming TTS

Stream audio output for lower latency:

```python
with client.audio.speech.with_streaming_response.create(
    model="playai-tts",
    input="This is streamed audio output.",
    voice="Fritz-PlayAI",
    response_format="mp3"
) as response:
    response.stream_to_file("streamed_output.mp3")
```

### Use Cases

- **Customer support agents**: Generate natural voice responses
- **Game characters**: Create expressive NPC dialogue
- **Narration**: Produce audiobook or podcast content
- **Accessibility**: Convert text content to audio
- **IVR systems**: Build interactive voice response menus

---

## Audio File Handling

### File Limitations

| Constraint              | Value                                                             |
| ----------------------- | ----------------------------------------------------------------- |
| Max file size           | 25 MB (free tier), 100 MB (dev tier)                              |
| Max attachment size     | 25 MB. Use `url` parameter for larger files.                      |
| Min file length         | 0.01 seconds                                                      |
| Min billed length       | 10 seconds (shorter files still billed for 10s)                   |
| Supported formats       | `flac`, `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `ogg`, `wav`, `webm` |
| Audio tracks            | Only first track transcribed for multi-track files                |
| Response formats        | `json`, `verbose_json`, `text`                                    |
| Timestamp granularities | `segment`, `word`                                                 |

### Audio Preprocessing

Groq downsamples audio to 16KHz mono before transcription. For lower latency, preprocess files client-side:

```bash
ffmpeg \
  -i input.mp3 \
  -ar 16000 \
  -ac 1 \
  -map 0:a \
  -c:a flac \
  output.flac
```

### Working with Large Files

For files exceeding size limits, implement audio chunking:

1. Break audio into smaller, overlapping segments
2. Process each segment independently
3. Combine results while handling overlap

See the [Groq API Cookbook audio chunking tutorial](https://github.com/groq/groq-api-cookbook/tree/main/tutorials/audio-chunking) for implementation details.

---

## Response Metadata

With `response_format="verbose_json"`, each segment includes quality metadata:

```json
{
  "id": 8,
  "seek": 3000,
  "start": 43.92,
  "end": 50.16,
  "text": " document that the functional specification...",
  "tokens": [51061, 4166, 300, 264, 11745, 31256],
  "temperature": 0,
  "avg_logprob": -0.097569615,
  "compression_ratio": 1.6637554,
  "no_speech_prob": 0.012814695
}
```

### Metadata Fields

| Field               | Description                                                                        |
| ------------------- | ---------------------------------------------------------------------------------- |
| `id`                | Segment index (0-based)                                                            |
| `seek`              | Position in audio file where segment begins                                        |
| `start`, `end`      | Timestamps in seconds                                                              |
| `avg_logprob`       | Confidence score. Closer to 0 = higher confidence. Below -0.5 may indicate issues. |
| `no_speech_prob`    | Probability of non-speech. Low values confirm speech content.                      |
| `compression_ratio` | Speech pattern indicator. Unusual values may indicate clarity issues.              |

### Debugging with Metadata

**Low confidence (`avg_logprob` very negative):**

- Background noise
- Multiple speakers
- Unclear pronunciation
- Strong accents

**High `no_speech_prob`:**

- Silence periods
- Background music
- Non-verbal sounds

**Unusual `compression_ratio`:**

- Stuttering or repetition
- Unusually fast/slow speech
- Audio quality issues

---

## Prompting Guidelines

The `prompt` parameter (max 224 tokens) provides context and style guidance.

**Best practices:**

- Provide context about audio content (topic, speakers, conversation type)
- Use the same language as the audio
- Specify proper spellings for names, technical terms, or acronyms
- Guide output style or tone
- Keep prompts concise and focused on style

**Example:**

```python
transcription = client.audio.transcriptions.create(
    file=f,
    model="whisper-large-v3-turbo",
    prompt="Technical podcast discussion about Kubernetes and microservices. Speakers: Alice (host), Bob (DevOps engineer).",
    language="en"
)
```
