# spendwise_app

Flutter client for Spendwise — renders the agent's answer and its intermediate
reasoning (tool calls, tool results) as they stream in over SSE.

Setup, architecture, and the backend it talks to are documented in the
[root README](../README.md).

```bash
flutter pub get
flutter run   # -d chrome / -d macos / a simulator
```

The backend base URL defaults to `http://127.0.0.1:8000` on desktop and
simulators, and to the page's own origin on web. Override it with
`--dart-define=API_BASE_URL=http://10.0.2.2:8000` (Android emulator) or any
other host - see `lib/services/agent_api_client.dart`.
