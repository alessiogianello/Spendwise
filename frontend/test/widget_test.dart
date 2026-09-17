import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:spendwise_app/main.dart';

void main() {
  testWidgets('shows the empty state and lets the user type a message', (WidgetTester tester) async {
    await tester.pumpWidget(const SpendwiseApp());

    expect(find.text('Spendwise'), findsOneWidget);
    expect(find.textContaining('cena da 80€'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'Ciao');
    expect(find.text('Ciao'), findsOneWidget);
  });
}
