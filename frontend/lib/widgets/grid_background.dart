import 'package:flutter/material.dart';

import '../theme/spendwise_theme.dart';

/// Faint engineering-grid drawn behind the content: thin lines on a fixed
/// pitch with a small tick at every intersection. Pure decoration.
class GridBackground extends StatelessWidget {
  final double pitch;

  const GridBackground({super.key, this.pitch = 40});

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: CustomPaint(painter: _GridPainter(pitch), size: Size.infinite),
    );
  }
}

class _GridPainter extends CustomPainter {
  final double pitch;

  const _GridPainter(this.pitch);

  @override
  void paint(Canvas canvas, Size size) {
    final line = Paint()
      ..color = SwColors.grid
      ..strokeWidth = 1;
    final tick = Paint()
      ..color = SwColors.line
      ..strokeWidth = 1;

    for (var x = 0.0; x <= size.width; x += pitch) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), line);
    }
    for (var y = 0.0; y <= size.height; y += pitch) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), line);
    }
    // Crosshair ticks on a coarser pitch so the grid reads as instrumentation.
    final coarse = pitch * 4;
    for (var x = coarse; x < size.width; x += coarse) {
      for (var y = coarse; y < size.height; y += coarse) {
        canvas.drawLine(Offset(x - 3, y), Offset(x + 4, y), tick);
        canvas.drawLine(Offset(x, y - 3), Offset(x, y + 4), tick);
      }
    }
  }

  @override
  bool shouldRepaint(_GridPainter old) => old.pitch != pitch;
}
