import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:spendwise_app/main.dart';
import 'package:spendwise_app/screens/chat_screen.dart';
import 'package:spendwise_app/services/agent_api_client.dart';
import 'package:spendwise_app/state/chat_provider.dart';
import 'package:spendwise_app/theme/spendwise_theme.dart';

/// Emits a minimal complete turn without touching the network.
class _FakeClient extends AgentApiClient {
  @override
  Stream<SseEvent> streamChat({required String message, int? sessionId}) async* {
    yield const SseEvent('thinking', '{"delta":"controllo il budget"}');
    await Future<void>.delayed(const Duration(milliseconds: 50));
    yield const SseEvent('text', '{"delta":"Risposta"}');
    yield const SseEvent(
      'done',
      '{"session_id":1,"usage":{"input_tokens":10,"output_tokens":5},"cost_usd":0.01,"latency_ms":100}',
    );
  }
}

void main() {
  testWidgets('shows the empty state and lets the user type a message', (WidgetTester tester) async {
    await tester.pumpWidget(const SpendwiseApp());

    expect(find.text('SPENDWISE'), findsOneWidget);
    expect(find.textContaining('cena da 80€'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'Ciao');
    expect(find.text('Ciao'), findsOneWidget);
  });

  testWidgets('input keeps focus and accepts a second message after an answer', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => ChatProvider(client: _FakeClient()),
        child: MaterialApp(theme: buildSpendwiseTheme(), home: const ChatScreen()),
      ),
    );
    await tester.pump();

    await tester.enterText(find.byType(TextField), 'Prima domanda');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    // Enter while running must not clear a draft.
    await tester.enterText(find.byType(TextField), 'Bozza');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    expect(find.text('Bozza'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump();
    expect(find.text('Risposta'), findsOneWidget);

    final field = tester.widget<TextField>(find.byType(TextField));
    expect(field.focusNode?.hasFocus, isTrue);

    await tester.enterText(find.byType(TextField), 'Seconda domanda');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump();
    expect(find.text('Seconda domanda'), findsOneWidget);
    expect(find.text('Risposta'), findsNWidgets(2));
  });
}
