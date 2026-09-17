import 'package:flutter/material.dart';

import '../models/chat_turn.dart';
import '../theme/spendwise_theme.dart';
import 'blink_cursor.dart';
import 'reasoning_step_tile.dart';

/// One exchange, laid out as a log entry rather than a pair of bubbles:
/// a labelled user line, the reasoning trace in a bordered panel, then the
/// agent's answer and its cost metrics. Turns are separated by a 1px rule.
class ChatTurnView extends StatelessWidget {
  final int index;
  final ChatTurn turn;

  const ChatTurnView({super.key, required this.index, required this.turn});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: SwSpace.xxl),
        _SectionLabel(
          text: 'QUERY',
          trailing: index.toString().padLeft(3, '0'),
          marker: SwColors.accent,
        ),
        const SizedBox(height: SwSpace.sm),
        Text(turn.userMessage, style: SwText.body.copyWith(fontWeight: FontWeight.w500)),
        if (turn.steps.isNotEmpty) ...[
          const SizedBox(height: SwSpace.xl),
          _TracePanel(turn: turn),
        ],
        const SizedBox(height: SwSpace.xl),
        const _SectionLabel(text: 'AGENT'),
        const SizedBox(height: SwSpace.sm),
        if (turn.finalText.isNotEmpty || turn.isStreaming) _AnswerText(turn: turn),
        if (!turn.isStreaming && turn.costUsd != null) ...[
          const SizedBox(height: SwSpace.md),
          _Metrics(turn: turn),
        ],
        if (turn.hasError) ...[
          const SizedBox(height: SwSpace.md),
          _ErrorBox(message: turn.errorMessage ?? 'Errore sconosciuto'),
        ],
        const SizedBox(height: SwSpace.xxl),
        const Divider(),
      ],
    );
  }
}

/// `■ LABEL ............ 001` - uppercase tracked label, optional marker
/// square and right-aligned mono detail.
class _SectionLabel extends StatelessWidget {
  final String text;
  final String? trailing;
  final Color? marker;

  const _SectionLabel({required this.text, this.trailing, this.marker});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        if (marker != null) ...[
          SizedBox(width: 6, height: 6, child: ColoredBox(color: marker!)),
          const SizedBox(width: SwSpace.sm),
        ],
        Text(text, style: SwText.label),
        if (trailing != null) ...[
          const Spacer(),
          Text(trailing!, style: SwText.mono.copyWith(color: SwColors.textDim)),
        ],
      ],
    );
  }
}

class _AnswerText extends StatelessWidget {
  final ChatTurn turn;

  const _AnswerText({required this.turn});

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        style: SwText.monoBody,
        children: [
          TextSpan(text: turn.finalText),
          if (turn.isStreaming)
            const WidgetSpan(
              alignment: PlaceholderAlignment.middle,
              child: Padding(padding: EdgeInsets.only(left: 2), child: BlinkCursor(height: 13)),
            ),
        ],
      ),
    );
  }
}

/// Token/cost/latency in mono; only the cost figure gets the accent.
class _Metrics extends StatelessWidget {
  final ChatTurn turn;

  const _Metrics({required this.turn});

  @override
  Widget build(BuildContext context) {
    final dim = SwText.mono.copyWith(color: SwColors.textDim);
    final value = SwText.mono.copyWith(color: SwColors.textMuted);
    final seconds = ((turn.latencyMs ?? 0) / 1000).toStringAsFixed(1);

    return Wrap(
      spacing: SwSpace.lg,
      runSpacing: SwSpace.xs,
      children: [
        _metric('IN', '${turn.inputTokens ?? 0}', dim, value),
        _metric('OUT', '${turn.outputTokens ?? 0}', dim, value),
        _metric('COST', '\$${turn.costUsd!.toStringAsFixed(4)}', dim, value.copyWith(color: SwColors.accent)),
        _metric('LATENCY', '${seconds}s', dim, value),
      ],
    );
  }

  Widget _metric(String key, String val, TextStyle keyStyle, TextStyle valStyle) {
    return Text.rich(TextSpan(children: [
      TextSpan(text: '$key ', style: keyStyle),
      TextSpan(text: val, style: valStyle),
    ]));
  }
}

class _ErrorBox extends StatelessWidget {
  final String message;

  const _ErrorBox({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(SwSpace.md),
      decoration: const BoxDecoration(
        border: Border.fromBorderSide(BorderSide(color: SwColors.error)),
        borderRadius: swRadius,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('ERROR', style: SwText.label.copyWith(color: SwColors.error)),
          const SizedBox(height: SwSpace.xs),
          Text(message, style: SwText.mono.copyWith(color: SwColors.text)),
        ],
      ),
    );
  }
}

/// Bordered panel holding the reasoning trace, with a header row and a
/// SHOW/HIDE toggle. No expansion animation: it snaps open and closed.
class _TracePanel extends StatefulWidget {
  final ChatTurn turn;

  const _TracePanel({required this.turn});

  @override
  State<_TracePanel> createState() => _TracePanelState();
}

class _TracePanelState extends State<_TracePanel> {
  bool _expanded = true;

  @override
  Widget build(BuildContext context) {
    final turn = widget.turn;
    final title = turn.isStreaming ? 'TRACE · RUNNING' : 'TRACE · ${turn.steps.length} STEPS';

    return Container(
      decoration: const BoxDecoration(
        color: SwColors.surface,
        border: Border.fromBorderSide(BorderSide(color: SwColors.line)),
        borderRadius: swRadius,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(SwSpace.md, SwSpace.sm, SwSpace.sm, SwSpace.sm),
            child: Row(
              children: [
                Text(title, style: SwText.label),
                if (turn.isStreaming) ...[
                  const SizedBox(width: SwSpace.sm),
                  const BlinkCursor(height: 10),
                ],
                const Spacer(),
                TextButton(
                  onPressed: () => setState(() => _expanded = !_expanded),
                  child: Text(_expanded ? 'HIDE' : 'SHOW'),
                ),
              ],
            ),
          ),
          if (_expanded) ...[
            const Divider(),
            const SizedBox(height: SwSpace.xs),
            for (var i = 0; i < turn.steps.length; i++) ReasoningStepTile(index: i + 1, step: turn.steps[i]),
            const SizedBox(height: SwSpace.xs),
          ],
        ],
      ),
    );
  }
}
