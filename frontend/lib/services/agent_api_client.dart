import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

class SseEvent {
  final String event;
  final String data;
  const SseEvent(this.event, this.data);
}

/// Talks to the Spendwise FastAPI backend. Base URL defaults to localhost,
/// which works for iOS Simulator, desktop, and web - on an Android emulator
/// use 10.0.2.2 instead (see README note at the call site).
class AgentApiClient {
  final String baseUrl;

  AgentApiClient({this.baseUrl = 'http://127.0.0.1:8000'});

  /// Streams one agent turn as parsed Server-Sent Events. sse-starlette also
  /// emits keep-alive comment lines starting with ':' - those are skipped.
  Stream<SseEvent> streamChat({required String message, int? sessionId}) async* {
    final request = http.Request('POST', Uri.parse('$baseUrl/chat/stream'))
      ..headers['Content-Type'] = 'application/json'
      ..headers['Accept'] = 'text/event-stream'
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
