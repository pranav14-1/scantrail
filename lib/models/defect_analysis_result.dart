class DefectAnalysisResult {
  final String defectId;
  final double latitude;
  final double longitude;
  final String timestamp;
  final String evolutionStatus; // 'New', 'Persistent', 'Worsening', 'Improving', 'Repaired'
  final double areaChangePercentage;
  final double currentArea;
  final double? previousArea;
  final String timeDeltaStr;
  final double severityScore;
  final String severityLevel; // 'Low', 'Medium', 'High', 'Critical'
  final Map<String, dynamic> engineeringAnalysis; // root_cause_analysis, recommended_remediation, municipal_priority_rank
  final String pdfReportUrl;

  DefectAnalysisResult({
    required this.defectId,
    required this.latitude,
    required this.longitude,
    required this.timestamp,
    required this.evolutionStatus,
    required this.areaChangePercentage,
    required this.currentArea,
    this.previousArea,
    required this.timeDeltaStr,
    required this.severityScore,
    required this.severityLevel,
    required this.engineeringAnalysis,
    required this.pdfReportUrl,
  });

  factory DefectAnalysisResult.fromJson(Map<String, dynamic> json) {
    final analysis = json['engineering_analysis'] as Map<String, dynamic>? ?? {};
    return DefectAnalysisResult(
      defectId: json['defect_id']?.toString() ?? '',
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0.0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0.0,
      timestamp: json['timestamp']?.toString() ?? '',
      evolutionStatus: json['evolution_status']?.toString() ?? 'New',
      areaChangePercentage: (json['area_change_percentage'] as num?)?.toDouble() ?? 0.0,
      currentArea: (json['current_area'] as num?)?.toDouble() ?? 0.0,
      previousArea: (json['previous_area'] as num?)?.toDouble(),
      timeDeltaStr: json['time_delta_str']?.toString() ?? 'Initial Scan',
      severityScore: (json['severity_score'] as num?)?.toDouble() ?? 0.0,
      severityLevel: json['severity_level']?.toString() ?? 'Medium',
      engineeringAnalysis: analysis,
      pdfReportUrl: json['pdf_report_url']?.toString() ?? '',
    );
  }

  String get rootCause =>
      engineeringAnalysis['root_cause_analysis']?.toString() ??
      'Pavement surface fatigue and cyclic environmental stress.';

  String get remediation =>
      engineeringAnalysis['recommended_remediation']?.toString() ??
      'Seal crack perimeter with hot-poured bituminous sealant.';

  int get municipalPriorityRank =>
      (engineeringAnalysis['municipal_priority_rank'] as num?)?.toInt() ?? 5;
}

