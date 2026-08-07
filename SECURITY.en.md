# Security Configuration

[中文](SECURITY.md)

1. `.env`, model files, uploaded assets, generated artifacts, and job JSON files are excluded through `.gitignore`.
2. The installer generates a random incognito access code and restricts `.env` permissions to the current user.
3. ComfyUI listens only on `127.0.0.1` by default.
4. The API listens on `0.0.0.0:8193` by default. Public deployments require upstream TLS, authentication, rate limiting, and request-body limits.
5. `H3_API_KEY` protects `/api/v1/*`. The current web interface does not automatically attach this header. Web deployments can apply unified authentication at the reverse-proxy layer.
6. Do not commit SSH passwords, cloud-provider credentials, OpenAI API keys, Hugging Face tokens, or incognito access codes.
7. AI prompt-optimization requests send user input to the OpenAI-compatible service configured in the browser. Operators must review that service's data policy.
