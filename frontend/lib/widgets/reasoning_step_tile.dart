import 'dart:convert';

import 'package:flutter/material.dart';

import '../models/reasoning_step.dart';

/// One row inside the reasoning trail - visually distinct (icon + muted
/// monospace-ish text) from the final chat bubble, so it reads as "process",
/// not "answer".
class ReasoningStepTile extends StatelessWidget {
  final ReasoningStep step;

  const ReasoningStepTile({super.key, required this.step});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mutedStyle = theme.textTheme.bodySmall?.copyWith(
      color: theme.colorScheme.onSurfaceVariant,
      fontFamily: 'monospace',
    );

    final (icon, label) = switch (step.type) {
      ReasoningStepType.status => (Icons.hourglass_top, step.message ?? ''),
      ReasoningStepType.thinking => (Icons.psychology_outlined, step.message ?? ''),
      ReasoningStepType.toolCall => (
          Icons.build_outlined,
          '${step.toolName}(${_formatCompact(step.toolInput)})',
        ),
      ReasoningStepType.toolResult => (
          step.isError ? Icons.error_outline : Icons.check_circle_outline,
          '${step.toolName} → ${_formatCompact(step.toolOutput)}',
        ),
    };

    final color = step.isError ? theme.colorScheme.error : theme.colorScheme.onSurfaceVariant;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              label,
              style: mutedStyle?.copyWith(color: step.isError ? theme.colorScheme.error : null),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  String _formatCompact(dynamic value) {
    if (value == null) return '';
    try {
      return jsonEncode(value);
    } catch (_) {
      return value.toString();
    }
  }
}
