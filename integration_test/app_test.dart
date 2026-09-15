import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:agrisense/main.dart';
import 'package:agrisense/models/defect_analysis_result.dart';
import 'package:agrisense/screens/report_screen.dart';

void main() {
  testWidgets('ScanTrail full automated integration simulation test', (WidgetTester tester) async {
    // 1. Launch App and trigger initial frame
    await tester.pumpWidget(const AgriSenseApp());
    await tester.pump();

    // 2. Mock GPS location & Defect Analysis Result
    const mockLat = 12.8406;
    const mockLon = 80.1534;

    final mockResult = DefectAnalysisResult(
      defectId: 'integration-test-defect-001',
      latitude: mockLat,
      longitude: mockLon,
      timestamp: DateTime.now().toIso8601String(),
      evolutionStatus: 'Worsening',
      areaChangePercentage: 30.0,
      currentArea: 0.650,
      previousArea: 0.500,
      timeDeltaStr: '7d 0h ago',
      severityScore: 0.85,
      severityLevel: 'High',
      engineeringAnalysis: {
        'root_cause_analysis': 'Asphalt fatigue cracking from moisture intrusion.',
        'recommended_remediation': 'Hot-mix asphalt patching and sealing.',
        'municipal_priority_rank': 8,
      },
      pdfReportUrl: '/reports/integration-test-defect-001',
    );

    // 3. Direct navigation to ReportScreen simulating capture analysis result
    await tester.pumpWidget(
      MaterialApp(
        home: ReportScreen(result: mockResult),
      ),
    );
    await tester.pumpAndSettle();

    // 4. Assert UI components and auto-navigation result
    expect(find.text('ScanTrail Diagnostic'), findsOneWidget);
    expect(find.text('WORSENING'), findsOneWidget);
    expect(find.text('GPS: 12.840600, 80.153400'), findsOneWidget);
    expect(find.text('+30.0%'), findsOneWidget);
    expect(find.text('View / Download Official Engineering PDF'), findsOneWidget);
  });
}

