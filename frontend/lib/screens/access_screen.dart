import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/chat_provider.dart';
import '../theme/spendwise_theme.dart';
import '../widgets/spendwise_mark.dart';
import 'chat_screen.dart';

/// Gate for the hosted demo: asks for the shared passphrase once, verifies it
/// against the backend, then opens the chat. Not shown when the backend has
/// no password configured (local development).
class AccessScreen extends StatefulWidget {
  const AccessScreen({super.key});

  @override
  State<AccessScreen> createState() => _AccessScreenState();
}

class _AccessScreenState extends State<AccessScreen> {
  final _controller = TextEditingController();
  bool _checking = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final password = _controller.text.trim();
    if (password.isEmpty || _checking) return;
    setState(() {
      _checking = true;
      _error = null;
    });
    final client = context.read<ChatProvider>().client;
    client.password = password;
    try {
      final ok = await client.checkAccess();
      if (!mounted) return;
      if (ok) {
        Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const ChatScreen()));
        return;
      }
      client.password = null;
      setState(() => _error = 'Password errata.');
    } catch (e) {
      client.password = null;
      if (mounted) setState(() => _error = 'Backend non raggiungibile: $e');
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: SwSpace.xl, vertical: SwSpace.section),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Align(alignment: Alignment.centerLeft, child: SpendwiseMark()),
                const SizedBox(height: SwSpace.xl),
                const Text('ACCESS', style: SwText.display),
                const SizedBox(height: SwSpace.md),
                Text(
                  'Questa demo è privata. Inserisci la password che ti è stata condivisa.',
                  style: SwText.body.copyWith(color: SwColors.textMuted),
                ),
                const SizedBox(height: SwSpace.xl),
                TextField(
                  controller: _controller,
                  autofocus: true,
                  obscureText: true,
                  style: SwText.body,
                  cursorWidth: 8,
                  cursorRadius: Radius.zero,
                  onSubmitted: (_) => _submit(),
                  decoration: const InputDecoration(hintText: 'Password'),
                ),
                if (_error != null) ...[
                  const SizedBox(height: SwSpace.sm),
                  Text(_error!, style: SwText.mono.copyWith(color: SwColors.error)),
                ],
                const SizedBox(height: SwSpace.md),
                FilledButton(
                  onPressed: _checking ? null : _submit,
                  child: Text(_checking ? 'CHECKING' : 'ENTER'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
