import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/chat_provider.dart';
import '../theme/spendwise_theme.dart';
import '../widgets/chat_turn_view.dart';
import '../widgets/grid_background.dart';

const _suggestedQueries = [
  'Posso permettermi una cena da 80€ questo weekend?',
  'Quanto ho speso questo mese per categoria?',
  'Sono in linea con il mio obiettivo di risparmio?',
];

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final _inputFocus = FocusNode();

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _inputFocus.dispose();
    super.dispose();
  }

  void _send() {
    final chat = context.read<ChatProvider>();
    final text = _controller.text;
    // Submitting drops focus; take it back so the user can keep typing.
    _inputFocus.requestFocus();
    // While a turn is running the field stays editable, so Enter must not
    // discard what the user has typed.
    if (chat.isSending || text.trim().isEmpty) return;
    chat.sendMessage(text);
    _controller.clear();
    // Snap, don't glide.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
    });
  }

  void _useSuggestion(String text) {
    _controller.text = text;
    _controller.selection = TextSelection.collapsed(offset: text.length);
    _inputFocus.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const _TopBar(),
            const _ActivityLine(),
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  const GridBackground(),
                  Consumer<ChatProvider>(
                    builder: (context, chat, _) {
                      if (chat.turns.isEmpty) {
                        return _EmptyState(onSuggestion: _useSuggestion);
                      }
                      return SelectionArea(
                        child: ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.symmetric(horizontal: SwSpace.xl),
                          itemCount: chat.turns.length,
                          itemBuilder: (context, index) => _Centered(
                            child: ChatTurnView(index: index + 1, turn: chat.turns[index]),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
            const Divider(),
            _Composer(controller: _controller, focusNode: _inputFocus, onSend: _send),
          ],
        ),
      ),
    );
  }
}

/// Constrains children to the content column and centers it.
class _Centered extends StatelessWidget {
  final Widget child;

  const _Centered({required this.child});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: swContentMaxWidth), child: child),
    );
  }
}

/// Wordmark on the left, live agent status and session id on the right.
class _TopBar extends StatelessWidget {
  const _TopBar();

  @override
  Widget build(BuildContext context) {
    final chat = context.watch<ChatProvider>();
    final running = chat.isSending;
    final session = chat.sessionId?.toString().padLeft(4, '0') ?? '—';

    return SizedBox(
      height: 48,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: SwSpace.xl),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth >= 640;
            return Row(
              children: [
                const Text('SPENDWISE', style: SwText.heading),
                if (wide) ...[
                  const SizedBox(width: SwSpace.lg),
                  const SizedBox(height: 16, child: VerticalDivider()),
                  const SizedBox(width: SwSpace.lg),
                  const Text('FINANCIAL AGENT', style: SwText.label),
                ],
                const Spacer(),
                SizedBox(
                  width: 6,
                  height: 6,
                  child: ColoredBox(color: running ? SwColors.accent : SwColors.textDim),
                ),
                const SizedBox(width: SwSpace.sm),
                Text(running ? 'RUNNING' : 'IDLE', style: SwText.label),
                if (wide) ...[
                  const SizedBox(width: SwSpace.xl),
                  Text('SESSION $session', style: SwText.mono.copyWith(color: SwColors.textDim)),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

/// 1px line under the top bar: static separator when idle, indeterminate
/// progress in the accent colour while a turn is running.
class _ActivityLine extends StatelessWidget {
  const _ActivityLine();

  @override
  Widget build(BuildContext context) {
    final running = context.select<ChatProvider, bool>((c) => c.isSending);
    return running ? const LinearProgressIndicator() : const Divider();
  }
}

class _EmptyState extends StatelessWidget {
  final ValueChanged<String> onSuggestion;

  const _EmptyState({required this.onSuggestion});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: SwSpace.xl, vertical: SwSpace.section),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _Crosshair(),
              const SizedBox(height: SwSpace.xl),
              const Text('AGENT READY', style: SwText.display),
              const SizedBox(height: SwSpace.md),
              Text(
                'Interroga budget, spese e obiettivo di risparmio. '
                'L\'agente legge e scrive sul database e mostra ogni passaggio del ragionamento.',
                style: SwText.body.copyWith(color: SwColors.textMuted),
              ),
              const SizedBox(height: SwSpace.section),
              const Text('SUGGESTED QUERIES', style: SwText.label),
              const SizedBox(height: SwSpace.md),
              for (final q in _suggestedQueries) ...[
                _SuggestionButton(text: q, onTap: () => onSuggestion(q)),
                const SizedBox(height: SwSpace.sm),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Small wireframe mark: a square frame with a centred crosshair.
class _Crosshair extends StatelessWidget {
  const _Crosshair();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: SizedBox(
        width: 32,
        height: 32,
        child: CustomPaint(painter: _CrosshairPainter()),
      ),
    );
  }
}

class _CrosshairPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final frame = Paint()
      ..color = SwColors.lineStrong
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    final cross = Paint()
      ..color = SwColors.accent
      ..strokeWidth = 1;
    canvas.drawRect(Offset.zero & size, frame);
    final c = size.center(Offset.zero);
    canvas.drawLine(Offset(c.dx - 6, c.dy), Offset(c.dx + 6, c.dy), cross);
    canvas.drawLine(Offset(c.dx, c.dy - 6), Offset(c.dx, c.dy + 6), cross);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Full-width secondary button: query text on the left, arrow on the right.
class _SuggestionButton extends StatelessWidget {
  final String text;
  final VoidCallback onTap;

  const _SuggestionButton({required this.text, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onTap,
      style: const ButtonStyle(
        textStyle: WidgetStatePropertyAll(TextStyle(
          fontFamily: SwFonts.sans,
          fontSize: 13,
          fontWeight: FontWeight.w400,
          letterSpacing: 0,
        )),
        alignment: Alignment.centerLeft,
      ),
      child: Row(
        children: [
          Expanded(child: Text(text)),
          const SizedBox(width: SwSpace.md),
          const Text('→'),
        ],
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final VoidCallback onSend;

  const _Composer({required this.controller, required this.focusNode, required this.onSend});

  @override
  Widget build(BuildContext context) {
    final isSending = context.watch<ChatProvider>().isSending;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: SwSpace.xl, vertical: SwSpace.lg),
      child: _Centered(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                focusNode: focusNode,
                // Never disabled: disabling drops focus and the user would have
                // to click back into the field after every answer.
                autofocus: true,
                style: SwText.body,
                cursorWidth: 8,
                cursorRadius: Radius.zero,
                onSubmitted: (_) => onSend(),
                decoration: const InputDecoration(hintText: 'Scrivi una richiesta…'),
              ),
            ),
            const SizedBox(width: SwSpace.sm),
            FilledButton(
              onPressed: isSending ? null : onSend,
              child: Text(isSending ? 'RUNNING' : 'SEND'),
            ),
          ],
        ),
      ),
    );
  }
}
