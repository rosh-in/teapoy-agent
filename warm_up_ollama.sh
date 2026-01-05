#!/bin/bash
# Warm up Ollama model to keep it loaded

echo "Warming up gemma3:4b model..."

curl -s -X POST http://192.168.1.43:11434/api/generate \
  -d '{"model":"gemma3:4b","prompt":"hello","stream":false,"keep_alive":"30m"}' \
  -H "Content-Type: application/json" > /dev/null

echo "✅ Model warmed up and will stay loaded for 30 minutes"
