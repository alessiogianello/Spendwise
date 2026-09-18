import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../models/chat_turn.dart';
import '../models/reasoning_step.dart';
import '../services/agent_api_client.dart';

class ChatProvider extends ChangeNotifier {
  final AgentApiClient _client;
  final List<ChatTurn> turns = [];
  int? sessionId;
  bool isSending = false;

  ChatProvider({AgentApiClient? client}) : _client = client ?? AgentApiClient();

  AgentApiClient get client => _client;

  Future<void> sendMessage(String message) async {
    if (message.trim().isEmpty || isSending) return;

    final turn = ChatTurn(message);
    turns.add(turn);
    isSending = true;
    notifyListeners();

    try {
      await for (final event in _client.streamChat(message: message, sessionId: sessionId)) {
        _applyEvent(turn, event);
        notifyListeners();
      }
    } catch (e) {
      turn.hasError = true;
      turn.errorMessage = e.toString();
    } finally {
      turn.isStreaming = false;
      isSending = false;
      notifyListeners();
    }
  }

  void _applyEvent(ChatTurn turn, SseEvent event) {
    final Map<String, dynamic> data = event.data.isEmpty ? {} : jsonDecode(event.data) as Map<String, dynamic>;

    switch (event.event) {
      case 'status':
        turn.steps.add(ReasoningStep.status(data['message'] as String));
      case 'thinking':
        // Deltas arrive token by token; merge them into one trace row.
        final delta = data['delta'] as String;
        final last = turn.steps.isEmpty ? null : turn.steps.last;
        if (last != null && last.type == ReasoningStepType.thinking) {
          turn.steps[turn.steps.length - 1] = ReasoningStep.thinking((last.message ?? '') + delta);
        } else {
          turn.steps.add(ReasoningStep.thinking(delta));
        }
      case 'tool_call':
        turn.steps.add(
          ReasoningStep.toolCall(data['name'] as String, (data['input'] as Map?)?.cast<String, dynamic>() ?? {}),
        );
      case 'tool_result':
        turn.steps.add(
          ReasoningStep.toolResult(data['name'] as String, data['output'], data['is_error'] == true),
        );
      case 'text':
        turn.finalText += data['delta'] as String;
      case 'done':
        sessionId = data['session_id'] as int?;
        final usage = (data['usage'] as Map?)?.cast<String, dynamic>();
        turn.inputTokens = usage?['input_tokens'] as int?;
        turn.outputTokens = usage?['output_tokens'] as int?;
        turn.costUsd = (data['cost_usd'] as num?)?.toDouble();
        turn.latencyMs = data['latency_ms'] as int?;
      case 'error':
        turn.hasError = true;
        turn.errorMessage = data['message'] as String?;
    }
  }
}
