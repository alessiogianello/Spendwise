import 'package:flutter/material.dart';

import '../models/chat_turn.dart';
import 'reasoning_step_tile.dart';

class ChatTurnView extends StatelessWidget {
  final ChatTurn turn;

  const ChatTurnView({super.key, required this.turn});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: Container(
            constraints: const BoxConstraints(maxWidth: 480),
            margin: const EdgeInsets.symmetric(vertical: 6),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: theme.colorScheme.primary,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Text(turn.userMessage, style: TextStyle(color: theme.colorScheme.onPrimary)),
          ),
        ),
        if (turn.steps.isNotEmpty) _ReasoningTrail(turn: turn),
        if (turn.finalText.isNotEmpty)
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              constraints: const BoxConstraints(maxWidth: 480),
              margin: const EdgeInsets.only(top: 4, bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHigh,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(turn.finalText),
                  if (!turn.isStreaming && turn.costUsd != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      '${turn.inputTokens}+${turn.outputTokens} token · '
                      '\$${turn.costUsd!.toStringAsFixed(4)} · ${turn.latencyMs}ms',
                      style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.outline),
                    ),
                  ],
                ],
              ),
            ),
          )
        else if (turn.isStreaming)
          const Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: EdgeInsets.symmetric(vertical: 6),
              child: SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          ),
        if (turn.hasError)
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              margin: const EdgeInsets.only(top: 4, bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: theme.colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                turn.errorMessage ?? 'Errore sconosciuto',
                style: TextStyle(color: theme.colorScheme.onErrorContainer),
              ),
            ),
          ),
      ],
    );
  }
}

class _ReasoningTrail extends StatelessWidget {
  final ChatTurn turn;

  const _ReasoningTrail({required this.turn});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.only(top: 2, bottom: 4),
      constraints: const BoxConstraints(maxWidth: 480),
      alignment: Alignment.centerLeft,
      child: Theme(
        data: theme.copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: turn.isStreaming,
          tilePadding: const EdgeInsets.symmetric(horizontal: 8),
          childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
          title: Text(
            turn.isStreaming ? 'Ragionamento in corso…' : '${turn.steps.length} passaggi di ragionamento',
            style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
          leading: Icon(Icons.route_outlined, size: 18, color: theme.colorScheme.onSurfaceVariant),
          backgroundColor: theme.colorScheme.surfaceContainerLow,
          collapsedBackgroundColor: theme.colorScheme.surfaceContainerLow,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          collapsedShape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          children: turn.steps.map((s) => ReasoningStepTile(step: s)).toList(),
        ),
      ),
    );
  }
}
