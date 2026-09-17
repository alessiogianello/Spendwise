import 'package:flutter/material.dart';

/// Design tokens for the "control room" look: a deep, flat black base, thin
/// 1px lines instead of shadows, off-white text, and a single cold accent
/// reserved for calls to action and highlighted data.
abstract final class SwColors {
  static const bg = Color(0xFF0A0A0A);
  static const surface = Color(0xFF111111); // inputs, panels
  static const surfaceRaised = Color(0xFF171717); // hovered rows
  static const grid = Color(0xFF131313); // decorative background grid
  static const line = Color(0xFF242424); // separators
  static const lineStrong = Color(0xFF3A3A3A); // borders on interactive elements
  static const text = Color(0xFFF2F2EF);
  static const textMuted = Color(0xFF8F8F8A);
  static const textDim = Color(0xFF5C5C58);
  static const accent = Color(0xFF4D8DFF); // electric blue - use sparingly
  static const onAccent = Color(0xFF0A0A0A);
  static const error = Color(0xFFE5484D);
}

abstract final class SwFonts {
  static const sans = 'Inter';
  static const mono = 'JetBrainsMono';
}

/// Fixed spacing scale - every gap in the UI is one of these.
abstract final class SwSpace {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double xxl = 32;
  static const double section = 48;
}

/// The only radius in the app: near-square.
const swRadius = BorderRadius.all(Radius.circular(2));

/// Widest column the content is allowed to span.
const double swContentMaxWidth = 800;

/// Named text styles beyond Material's TextTheme: uppercase labels with wide
/// tracking, and the monospace face used for the reasoning trace and metrics.
abstract final class SwText {
  static const label = TextStyle(
    fontFamily: SwFonts.sans,
    fontSize: 11,
    fontWeight: FontWeight.w500,
    letterSpacing: 1.3,
    height: 1.2,
    color: SwColors.textMuted,
  );

  static const heading = TextStyle(
    fontFamily: SwFonts.sans,
    fontSize: 13,
    fontWeight: FontWeight.w600,
    letterSpacing: 2.4,
    height: 1.2,
    color: SwColors.text,
  );

  static const display = TextStyle(
    fontFamily: SwFonts.sans,
    fontSize: 22,
    fontWeight: FontWeight.w600,
    letterSpacing: 4,
    height: 1.2,
    color: SwColors.text,
  );

  static const body = TextStyle(
    fontFamily: SwFonts.sans,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.55,
    color: SwColors.text,
  );

  static const mono = TextStyle(
    fontFamily: SwFonts.mono,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    height: 1.5,
    color: SwColors.textMuted,
  );

  /// Agent output: machine text, so it shares the trace's face but at
  /// reading size and full contrast.
  static const monoBody = TextStyle(
    fontFamily: SwFonts.mono,
    fontSize: 13,
    fontWeight: FontWeight.w400,
    height: 1.65,
    color: SwColors.text,
  );
}

ThemeData buildSpendwiseTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.dark,
    primary: SwColors.accent,
    onPrimary: SwColors.onAccent,
    secondary: SwColors.text,
    onSecondary: SwColors.bg,
    error: SwColors.error,
    onError: SwColors.bg,
    surface: SwColors.bg,
    onSurface: SwColors.text,
    onSurfaceVariant: SwColors.textMuted,
    outline: SwColors.lineStrong,
    outlineVariant: SwColors.line,
    surfaceContainerLow: SwColors.surface,
    surfaceContainerHigh: SwColors.surfaceRaised,
  );

  final textTheme = ThemeData.dark().textTheme.apply(
        fontFamily: SwFonts.sans,
        bodyColor: SwColors.text,
        displayColor: SwColors.text,
      );

  // Hover = hard colour inversion, no ripple, no easing.
  const noAnimation = Duration.zero;

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: scheme,
    scaffoldBackgroundColor: SwColors.bg,
    canvasColor: SwColors.bg,
    fontFamily: SwFonts.sans,
    textTheme: textTheme,
    visualDensity: VisualDensity.compact,
    splashFactory: NoSplash.splashFactory,
    highlightColor: Colors.transparent,
    hoverColor: Colors.transparent,
    focusColor: Colors.transparent,
    dividerTheme: const DividerThemeData(color: SwColors.line, thickness: 1, space: 1),
    iconTheme: const IconThemeData(color: SwColors.textMuted, size: 16),
    textSelectionTheme: const TextSelectionThemeData(
      cursorColor: SwColors.accent,
      selectionColor: Color(0x334D8DFF),
      selectionHandleColor: SwColors.accent,
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: SwColors.accent,
      linearTrackColor: SwColors.line,
      linearMinHeight: 1,
    ),
    inputDecorationTheme: const InputDecorationTheme(
      filled: true,
      fillColor: SwColors.surface,
      isDense: true,
      contentPadding: EdgeInsets.symmetric(horizontal: SwSpace.md, vertical: SwSpace.md),
      hintStyle: TextStyle(color: SwColors.textDim, fontFamily: SwFonts.sans, fontSize: 14),
      border: OutlineInputBorder(borderRadius: swRadius, borderSide: BorderSide(color: SwColors.lineStrong)),
      enabledBorder: OutlineInputBorder(borderRadius: swRadius, borderSide: BorderSide(color: SwColors.lineStrong)),
      disabledBorder: OutlineInputBorder(borderRadius: swRadius, borderSide: BorderSide(color: SwColors.line)),
      focusedBorder: OutlineInputBorder(borderRadius: swRadius, borderSide: BorderSide(color: SwColors.accent)),
      errorBorder: OutlineInputBorder(borderRadius: swRadius, borderSide: BorderSide(color: SwColors.error)),
      focusedErrorBorder: OutlineInputBorder(borderRadius: swRadius, borderSide: BorderSide(color: SwColors.error)),
    ),
    // Primary CTA: solid accent; on hover the fill drops out and the accent
    // moves to border + text.
    filledButtonTheme: FilledButtonThemeData(
      style: ButtonStyle(
        animationDuration: noAnimation,
        elevation: const WidgetStatePropertyAll(0),
        shape: const WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: swRadius)),
        padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: SwSpace.lg, vertical: SwSpace.md)),
        minimumSize: const WidgetStatePropertyAll(Size(0, 40)),
        textStyle: const WidgetStatePropertyAll(SwText.label),
        overlayColor: const WidgetStatePropertyAll(Colors.transparent),
        backgroundColor: WidgetStateProperty.resolveWith((s) {
          if (s.contains(WidgetState.disabled)) return SwColors.surface;
          if (s.contains(WidgetState.hovered) || s.contains(WidgetState.pressed)) return SwColors.bg;
          return SwColors.accent;
        }),
        foregroundColor: WidgetStateProperty.resolveWith((s) {
          if (s.contains(WidgetState.disabled)) return SwColors.textDim;
          if (s.contains(WidgetState.hovered) || s.contains(WidgetState.pressed)) return SwColors.accent;
          return SwColors.onAccent;
        }),
        side: WidgetStateProperty.resolveWith((s) {
          if (s.contains(WidgetState.disabled)) return const BorderSide(color: SwColors.line);
          return const BorderSide(color: SwColors.accent);
        }),
      ),
    ),
    // Secondary: 1px border, transparent fill; hover inverts to off-white on black.
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: ButtonStyle(
        animationDuration: noAnimation,
        shape: const WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: swRadius)),
        padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: SwSpace.lg, vertical: SwSpace.md)),
        minimumSize: const WidgetStatePropertyAll(Size(0, 40)),
        textStyle: const WidgetStatePropertyAll(SwText.label),
        overlayColor: const WidgetStatePropertyAll(Colors.transparent),
        backgroundColor: WidgetStateProperty.resolveWith((s) {
          if (s.contains(WidgetState.hovered) || s.contains(WidgetState.pressed)) return SwColors.text;
          return Colors.transparent;
        }),
        foregroundColor: WidgetStateProperty.resolveWith((s) {
          if (s.contains(WidgetState.disabled)) return SwColors.textDim;
          if (s.contains(WidgetState.hovered) || s.contains(WidgetState.pressed)) return SwColors.bg;
          return SwColors.text;
        }),
        side: WidgetStateProperty.resolveWith((s) {
          if (s.contains(WidgetState.disabled)) return const BorderSide(color: SwColors.line);
          if (s.contains(WidgetState.hovered) || s.contains(WidgetState.pressed)) {
            return const BorderSide(color: SwColors.text);
          }
          return const BorderSide(color: SwColors.lineStrong);
        }),
      ),
    ),
    // Tertiary / inline: bare label, hover inverts.
    textButtonTheme: TextButtonThemeData(
      style: ButtonStyle(
        animationDuration: noAnimation,
        shape: const WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: swRadius)),
        padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: SwSpace.sm, vertical: SwSpace.xs)),
        minimumSize: const WidgetStatePropertyAll(Size(0, 24)),
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        textStyle: const WidgetStatePropertyAll(SwText.label),
        overlayColor: const WidgetStatePropertyAll(Colors.transparent),
        backgroundColor: WidgetStateProperty.resolveWith((s) {
          if (s.contains(WidgetState.hovered) || s.contains(WidgetState.pressed)) return SwColors.text;
          return Colors.transparent;
        }),
        foregroundColor: WidgetStateProperty.resolveWith((s) {
          if (s.contains(WidgetState.disabled)) return SwColors.textDim;
          if (s.contains(WidgetState.hovered) || s.contains(WidgetState.pressed)) return SwColors.bg;
          return SwColors.textMuted;
        }),
      ),
    ),
    tooltipTheme: const TooltipThemeData(
      waitDuration: Duration(milliseconds: 400),
      decoration: BoxDecoration(
        color: SwColors.surfaceRaised,
        border: Border.fromBorderSide(BorderSide(color: SwColors.lineStrong)),
        borderRadius: swRadius,
      ),
      textStyle: SwText.mono,
    ),
  );
}
