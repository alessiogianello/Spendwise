import 'dart:async';

import 'package:flutter/material.dart';

import '../theme/spendwise_theme.dart';

/// Terminal-style block cursor that toggles on/off with no fade - the app's
/// only "something is happening" indicator besides the top progress line.
class BlinkCursor extends StatefulWidget {
  final Color color;
  final double height;

  const BlinkCursor({super.key, this.color = SwColors.accent, this.height = 14});

  @override
  State<BlinkCursor> createState() => _BlinkCursorState();
}

class _BlinkCursorState extends State<BlinkCursor> {
  Timer? _timer;
  bool _on = true;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(milliseconds: 530), (_) => setState(() => _on = !_on));
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 8,
      height: widget.height,
      child: _on ? ColoredBox(color: widget.color) : null,
    );
  }
}
