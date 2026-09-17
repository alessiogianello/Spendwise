enum ReasoningStepType { status, thinking, toolCall, toolResult }

/// One intermediate step of the agent's turn, shown in the UI separately from
/// the final answer: a status ping, a chunk of visible reasoning, a tool call,
/// or that tool's result.
class ReasoningStep {
  final ReasoningStepType type;
  final String? message;
  final String? toolName;
  final Map<String, dynamic>? toolInput;
  final dynamic toolOutput;
  final bool isError;

  const ReasoningStep._({
    required this.type,
    this.message,
    this.toolName,
    this.toolInput,
    this.toolOutput,
    this.isError = false,
  });

  factory ReasoningStep.status(String message) =>
      ReasoningStep._(type: ReasoningStepType.status, message: message);

  factory ReasoningStep.thinking(String delta) =>
      ReasoningStep._(type: ReasoningStepType.thinking, message: delta);

  factory ReasoningStep.toolCall(String name, Map<String, dynamic> input) => ReasoningStep._(
        type: ReasoningStepType.toolCall,
        toolName: name,
        toolInput: input,
      );

  factory ReasoningStep.toolResult(String name, dynamic output, bool isError) => ReasoningStep._(
        type: ReasoningStepType.toolResult,
        toolName: name,
        toolOutput: output,
        isError: isError,
      );
}
