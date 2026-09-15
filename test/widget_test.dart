import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:agrisense/models/defect_analysis_result.dart';
import 'package:agrisense/screens/report_screen.dart';

void main() {
  group('DefectAnalysisResult Model Parsing Tests', () {
    test('Correctly maps JSON fields across all evolution states (New, Worsening, Improving, Persistent, Repaired)', () {
      final states = ['New', 'Worsening', 'Improving', 'Persistent', 'Repaired'];
      for (final state in states) {
        final jsonMap = {
          'defect_id': 'defect-uuid-$state',
          'latitude': 12.8406,
          'longitude': 80.1534,
          'timestamp': '2026-09-15T12:00:00Z',
          'evolution_status': state,
          'area_change_percentage': state == 'Worsening' ? 30.0 : (state == 'Improving' ? -46.0 : 0.0),
          'current_area': 0.65,
          'previous_area': 0.50,
          'time_delta_str': '7d 0h ago',
          'severity_score': 0.85,
          'severity_level': 'High',
          'engineering_analysis': {
            'root_cause_analysis': 'Sub-surface water intrusion and cyclic axle fatigue.',
            'recommended_remediation': 'Full-depth asphalt patching and edge drainage.',
            'municipal_priority_rank': 8,
          },
          'pdf_report_url': '/reports/defect-uuid-$state',
        };

        final result = DefectAnalysisResult.fromJson(jsonMap);
        expect(result.defectId, 'defect-uuid-$state');
        expect(result.latitude, 12.8406);
        expect(result.longitude, 80.1534);
        expect(result.evolutionStatus, state);
        expect(result.severityLevel, 'High');
        expect(result.rootCause, contains('Sub-surface water intrusion'));
        expect(result.remediation, contains('Full-depth asphalt patching'));
        expect(result.municipalPriorityRank, 8);
        expect(result.pdfReportUrl, '/reports/defect-uuid-$state');
      }
    });
  });

  group('Spatial-Temporal Report Screen Widget Tests', () {
    testWidgets('Renders Red status badge, area delta (+30.0%), and civil advisory card',
        (WidgetTester tester) async {
      final mockResult = DefectAnalysisResult(
        defectId: 'test-widget-defect-001',
        latitude: 12.8406,
        longitude: 80.1534,
        timestamp: '2026-09-15T21:00:00Z',
        evolutionStatus: 'Worsening',
        areaChangePercentage: 30.0,
        currentArea: 0.650,
        previousArea: 0.500,
        timeDeltaStr: '7d 0h ago',
        severityScore: 0.85,
        severityLevel: 'High',
        engineeringAnalysis: {
          'root_cause_analysis': 'Subgrade moisture intrusion causing pavement fatigue.',
          'recommended_remediation': 'Full-depth asphalt patch and perimeter sealing.',
          'municipal_priority_rank': 8,
        },
        pdfReportUrl: '/reports/test-widget-defect-001',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ReportScreen(result: mockResult),
        ),
      );

      // Verify header and title
      expect(find.text('ScanTrail Diagnostic'), findsOneWidget);

      // Verify Status Badge text
      expect(find.text('WORSENING'), findsOneWidget);

      // Verify Two-Frame comparison metrics text
      expect(find.text('Two-Frame Dimensional Delta'), findsOneWidget);
      expect(find.text('0.650 m²'), findsOneWidget);
      expect(find.text('0.500 m²'), findsOneWidget);
      expect(find.text('+30.0%'), findsOneWidget);

      // Verify Civil AI Advisory
      expect(find.text('Civil AI Advisory'), findsOneWidget);
      expect(find.text('Priority: 8/10'), findsOneWidget);
      expect(find.text('Subgrade moisture intrusion causing pavement fatigue.'), findsOneWidget);
      expect(find.text('Full-depth asphalt patch and perimeter sealing.'), findsOneWidget);

      // Verify Action Button
      expect(find.text('View / Download Official Engineering PDF'), findsOneWidget);
    });
  });
}
