import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/splash_screen.dart';
import 'state/chat_provider.dart';
import 'theme/spendwise_theme.dart';

void main() {
  runApp(const SpendwiseApp());
}

class SpendwiseApp extends StatelessWidget {
  const SpendwiseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ChatProvider(),
      child: MaterialApp(
        title: 'Spendwise',
        debugShowCheckedModeBanner: false,
        // Light only: the look is built around a flat white base.
        theme: buildSpendwiseTheme(),
        darkTheme: buildSpendwiseTheme(),
        themeMode: ThemeMode.light,
        home: const SplashScreen(),
      ),
    );
  }
}
