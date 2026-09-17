import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/chat_screen.dart';
import 'state/chat_provider.dart';

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
        theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal)),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal, brightness: Brightness.dark),
        ),
        home: const ChatScreen(),
      ),
    );
  }
}
