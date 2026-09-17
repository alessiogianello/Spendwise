import 'reasoning_step.dart';

/// One user message + the agent's (possibly still-streaming) response: the
/// intermediate reasoning trail plus the final answer text, kept separate so
/// the UI can render them differently.
class ChatTurn {
  final String userMessage;
  String finalText = '';
  final List<ReasoningStep> steps = [];
  bool isStreaming = true;
  bool hasError = false;
  String? errorMessage;
  int? inputTokens;
  int? outputTokens;
  double? costUsd;
  int? latencyMs;

  ChatTurn(this.userMessage);
}
