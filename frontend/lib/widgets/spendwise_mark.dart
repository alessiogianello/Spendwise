import 'package:flutter/material.dart';

import '../theme/spendwise_theme.dart';

/// The Spendwise mark: a square frame with a centred crosshair. Shared by the
/// empty state, the splash screen and (as an asset) the launcher icon.
class SpendwiseMark extends StatelessWidget {
  final double size;
  final Color frameColor;
  final Color crossColor;

  const SpendwiseMark({
    super.key,
    this.size = 32,
    this.frameColor = SwColors.lineStrong,
    this.crossColor = SwColors.accent,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _MarkPainter(frameColor: frameColor, crossColor: crossColor)),
    );
  }
}

class _MarkPainter extends CustomPainter {
  final Color frameColor;
  final Color crossColor;

  const _MarkPainter({required this.frameColor, required this.crossColor});

  @override
  void paint(Canvas canvas, Size size) {
    // Proportions follow the 32px original: 1px strokes, 12px cross.
    final unit = size.width / 32;
    final frame = Paint()
      ..color = frameColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = unit;
    final cross = Paint()
      ..color = crossColor
      ..strokeWidth = unit;
    canvas.drawRect(Offset.zero & size, frame);
    final c = size.center(Offset.zero);
    final arm = 6 * unit;
    canvas.drawLine(Offset(c.dx - arm, c.dy), Offset(c.dx + arm, c.dy), cross);
    canvas.drawLine(Offset(c.dx, c.dy - arm), Offset(c.dx, c.dy + arm), cross);
  }

  @override
  bool shouldRepaint(_MarkPainter old) => old.frameColor != frameColor || old.crossColor != crossColor;
}
