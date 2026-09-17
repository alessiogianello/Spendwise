import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/chat_provider.dart';
import '../widgets/chat_turn_view.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _send() {
    final text = _controller.text;
    if (text.trim().isEmpty) return;
    context.read<ChatProvider>().sendMessage(text);
    _controller.clear();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Spendwise')),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Consumer<ChatProvider>(
                builder: (context, chat, _) {
                  if (chat.turns.isEmpty) {
                    return const _EmptyState();
                  }
                  return ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    itemCount: chat.turns.length,
                    itemBuilder: (context, index) => ChatTurnView(turn: chat.turns[index]),
                  );
                },
              ),
            ),
            const Divider(height: 1),
            _Composer(controller: _controller, onSend: _send),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.savings_outlined, size: 48, color: theme.colorScheme.outline),
            const SizedBox(height: 12),
            Text(
              'Chiedimi qualcosa sulle tue spese, es. "Posso permettermi una '
              'cena da 80€ questo weekend?"',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.outline),
            ),
          ],
        ),
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  final TextEditingController controller;
  final VoidCallback onSend;

  const _Composer({required this.controller, required this.onSend});

  @override
  Widget build(BuildContext context) {
    final isSending = context.watch<ChatProvider>().isSending;
    return Padding(
      padding: const EdgeInsets.all(8.0),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              enabled: !isSending,
              onSubmitted: (_) => onSend(),
              decoration: const InputDecoration(
                hintText: 'Scrivi un messaggio...',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            onPressed: isSending ? null : onSend,
            icon: const Icon(Icons.send),
          ),
        ],
      ),
    );
  }
}
