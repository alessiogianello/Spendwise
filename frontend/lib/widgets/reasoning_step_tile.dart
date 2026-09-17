import 'dart:convert';

import 'package:flutter/material.dart';

import '../models/reasoning_step.dart';
import '../theme/spendwise_theme.dart';

/// One row of the reasoning trace: `index  TAG  payload`, all monospace, so
/// the trail reads as a process log rather than as part of the answer. Only
/// tool calls get the accent; errors get the error colour.
class ReasoningStepTile extends StatelessWidget {
  final int index;
  final ReasoningStep step;

  const ReasoningStepTile({super.key, required this.index, required this.step});

  @override
  Widget build(BuildContext context) {
    final (tag, tagColor, label, maxLines) = switch (step.type) {
      ReasoningStepType.status => ('STATUS', SwColors.textDim, step.message ?? '', 2),
      ReasoningStepType.thinking => ('THINK', SwColors.textMuted, step.message ?? '', 8),
      ReasoningStepType.toolCall => (
          'CALL',
          SwColors.accent,
          '${step.toolName}(${_formatCompact(step.toolInput)})',
          3,
        ),
      ReasoningStepType.toolResult => (
          step.isError ? 'ERROR' : 'RESULT',
          step.isError ? SwColors.error : SwColors.textMuted,
          '${step.toolName} → ${_formatCompact(step.toolOutput)}',
          3,
        ),
    };

    final bodyColor = step.isError ? SwColors.error : SwColors.textMuted;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: SwSpace.md, vertical: SwSpace.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 24,
            child: Text(index.toString().padLeft(2, '0'), style: SwText.mono.copyWith(color: SwColors.textDim)),
          ),
          SizedBox(
            width: 64,
            child: Text(tag, style: SwText.mono.copyWith(color: tagColor, fontWeight: FontWeight.w500)),
          ),
          Expanded(
            child: Text(
              label,
              style: SwText.mono.copyWith(color: bodyColor),
              maxLines: maxLines,
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
