import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/chat_provider.dart';
import '../theme/spendwise_theme.dart';
import '../widgets/spendwise_mark.dart';
import 'access_screen.dart';
import 'chat_screen.dart';

/// Animated splash: the mark breathes - scales up and down a few percent while
/// its colour swings between grey and black - on one shared sinusoidal phase.
/// Meanwhile it asks the backend whether a password is needed, and after the
/// minimum duration cross-fades into the chat or the access gate.
class SplashScreen extends StatefulWidget {
  /// How long the splash stays on screen before handing over to the chat.
  final Duration duration;

  const SplashScreen({super.key, this.duration = const Duration(milliseconds: 2200)});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with SingleTickerProviderStateMixin {
  static const _period = Duration(milliseconds: 1600);
  static const _maxScale = 1.06;
  static const _dimColor = SwColors.textDim;
  static const _fullColor = SwColors.text;

  late final AnimationController _clock;
  late final Future<bool> _access;
  Timer? _handover;

  @override
  void initState() {
    super.initState();
    _clock = AnimationController(vsync: this, duration: _period)..repeat();
    // Unreachable backend counts as "open": the chat surfaces the real error
    // on the first message, which is more useful than a password prompt.
    _access = context.read<ChatProvider>().client.checkAccess().catchError((_) => true);
    _handover = Timer(widget.duration, _handOver);
  }

  @override
  void dispose() {
    _handover?.cancel();
    _clock.dispose();
    super.dispose();
  }

  Future<void> _handOver() async {
    final open = await _access;
    if (!mounted) return;
    final Widget next = open ? const ChatScreen() : const AccessScreen();
    Navigator.of(context).pushReplacement(
      PageRouteBuilder<void>(
        transitionDuration: const Duration(milliseconds: 350),
        pageBuilder: (_, _, _) => next,
        transitionsBuilder: (_, animation, _, child) => FadeTransition(opacity: animation, child: child),
      ),
    );
  }

  /// 0 → 1 → 0 over one period, with continuous velocity at both ends so the
  /// loop has no visible kink (unlike a reversed ease curve).
  double _phase(double t) => (1 - math.cos(2 * math.pi * t)) / 2;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: AnimatedBuilder(
          animation: _clock,
          builder: (context, _) {
            final phase = _phase(_clock.value);
            final color = Color.lerp(_dimColor, _fullColor, phase)!;
            return Transform.scale(
              scale: 1 + (_maxScale - 1) * phase,
              child: SpendwiseMark(size: 64, frameColor: color, crossColor: color),
            );
          },
        ),
      ),
    );
  }
}
