# spendwise_app

Flutter client for Spendwise — renders the agent's answer and its intermediate
reasoning (tool calls, tool results) as they stream in over SSE.

Setup, architecture, and the backend it talks to are documented in the
[root README](../README.md).

```bash
flutter pub get
flutter run   # -d chrome / -d macos / a simulator
```

The backend base URL is set in `lib/services/agent_api_client.dart`.
