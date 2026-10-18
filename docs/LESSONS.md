# Lessons

### Settings file is the repo root
- Step: scaffold
- Symptom: The Token Factory key was set in `.env` and the probe still reported it missing.
- Root cause: `papertrail/config.py` resolved the repo root one directory too low.
- Rule: Count parents from the file that loads `.env`, and print only whether a secret is set.

### Embedding width is part of the schema
- Step: scaffold
- Symptom: `Qwen/Qwen3-Embedding-8B` returned 4096 floats, not 1024.
- Root cause: The vector column width was a guess.
- Rule: Set `EMBEDDING_DIMENSIONS` from the probe before the first analyze.

### Some chat models return an empty message
- Step: scaffold
- Symptom: A connectivity chat call succeeded and `message.content` was empty.
- Root cause: That model id does not put the reply in `content`.
- Rule: Probe the small and large model ids and keep ones that return text.
