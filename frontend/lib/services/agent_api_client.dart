import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

class SseEvent {
  final String event;
  final String data;
  const SseEvent(this.event, this.data);
}

/// Talks to the Spendwise FastAPI backend.
///
/// Base URL resolution: `--dart-define=API_BASE_URL=...` wins; otherwise a web
/// build talks to its own origin (the backend serves the build in the hosted
/// demo) and everything else uses localhost - on an Android emulator pass
/// API_BASE_URL=http://10.0.2.2:8000.
class AgentApiClient {
  static const _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const passwordHeader = 'X-Demo-Password';

  final String baseUrl;

  /// Shared demo passphrase, sent on every request once the user enters it.
  String? password;

  AgentApiClient({String? baseUrl}) : baseUrl = baseUrl ?? defaultBaseUrl();

  static String defaultBaseUrl() {
    if (_configuredBaseUrl.isNotEmpty) return _configuredBaseUrl;
    if (kIsWeb) return Uri.base.origin;
    return 'http://127.0.0.1:8000';
  }

  Map<String, String> get _authHeaders => {passwordHeader: ?password};

  /// True when the backend lets us in: either no password is configured
  /// server-side, or the one we hold is right. False on 401.
  Future<bool> checkAccess() async {
    final response = await http.get(Uri.parse('$baseUrl/auth/check'), headers: _authHeaders);
    if (response.statusCode == 200) return true;
    if (response.statusCode == 401) return false;
    throw Exception('HTTP ${response.statusCode}: ${response.body}');
  }

  /// Streams one agent turn as parsed Server-Sent Events. sse-starlette also
  /// emits keep-alive comment lines starting with ':' - those are skipped.
  Stream<SseEvent> streamChat({required String message, int? sessionId}) async* {
    final request = http.Request('POST', Uri.parse('$baseUrl/chat/stream'))
      ..headers['Content-Type'] = 'application/json'
      ..headers['Accept'] = 'text/event-stream'
      ..headers.addAll(_authHeaders)
      ..body = jsonEncode({
        'message': message,
        'session_id': ?sessionId,
      });

    final client = http.Client();
    try {
      final streamedResponse = await client.send(request);
      if (streamedResponse.statusCode != 200) {
        final body = await streamedResponse.stream.bytesToString();
        throw Exception('HTTP ${streamedResponse.statusCode}: $body');
      }

      String? currentEvent;
      final dataLines = <String>[];

      await for (final line in streamedResponse.stream.transform(utf8.decoder).transform(const LineSplitter())) {
        if (line.isEmpty) {
          if (currentEvent != null && dataLines.isNotEmpty) {
            yield SseEvent(currentEvent, dataLines.join('\n'));
          }
          currentEvent = null;
          dataLines.clear();
          continue;
        }
        if (line.startsWith(':')) continue; // keep-alive comment
        if (line.startsWith('event:')) {
          currentEvent = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.add(line.substring(5).trim());
        }
      }
    } finally {
      client.close();
    }
  }
}
