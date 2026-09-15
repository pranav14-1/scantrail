import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';
import '../models/defect_analysis_result.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class ReportScreen extends StatefulWidget {
  final DefectAnalysisResult result;
  final File? scannedImage;

  const ReportScreen({
    super.key,
    required this.result,
    this.scannedImage,
  });

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  bool _isDownloadingPdf = false;

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'worsening':
        return AppTheme.statusWorsening;
      case 'improving':
        return AppTheme.statusImproving;
      case 'persistent':
        return AppTheme.statusPersistent;
      case 'repaired':
        return AppTheme.statusRepaired;
      case 'new':
      default:
        return AppTheme.statusNew;
    }
  }

  Future<void> _openOrDownloadPdf() async {
    setState(() => _isDownloadingPdf = true);
    try {
      final Uint8List pdfBytes =
          await ApiService.downloadPdfReport(widget.result.pdfReportUrl);

      final tempDir = await getTemporaryDirectory();
      final filePath =
          '${tempDir.path}/ScanTrail_Report_${widget.result.defectId}.pdf';
      final file = File(filePath);
      await file.writeAsBytes(pdfBytes);

      final openResult = await OpenFile.open(filePath);
      if (openResult.type != ResultType.done && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Report saved at: $filePath')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not open PDF: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isDownloadingPdf = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final res = widget.result;
    final statusColor = _getStatusColor(res.evolutionStatus);

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: const Text(
          'ScanTrail Diagnostic',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 1. Status Badge & Telemetry Header
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'ROAD ASSET STATE',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.subTextColor,
                            letterSpacing: 0.8,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: statusColor.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: statusColor, width: 1.5),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.lens, size: 8, color: statusColor),
                              const SizedBox(width: 6),
                              Text(
                                res.evolutionStatus.toUpperCase(),
                                style: TextStyle(
                                  color: statusColor,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const Divider(height: 24),
                    Row(
                      children: [
                        const Icon(Icons.location_on_outlined,
                            size: 20, color: AppTheme.primaryColor),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'GPS: ${res.latitude.toStringAsFixed(6)}, ${res.longitude.toStringAsFixed(6)}',
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textColor,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        const Icon(Icons.access_time,
                            size: 20, color: AppTheme.subTextColor),
                        const SizedBox(width: 8),
                        Text(
                          'Temporal Reference: ${res.timeDeltaStr}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppTheme.subTextColor,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),

            // 2. Two-Frame Comparative Metrics Card
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.compare_arrows, color: AppTheme.primaryColor),
                        const SizedBox(width: 8),
                        const Text(
                          'Two-Frame Dimensional Delta',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.textColor,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildMetricCol(
                          title: 'Current Area',
                          value: '${res.currentArea.toStringAsFixed(3)} m²',
                          caption: 'Present visit',
                          color: AppTheme.textColor,
                        ),
                        Container(height: 40, width: 1, color: AppTheme.borderColor),
                        _buildMetricCol(
                          title: 'Historical Area',
                          value: res.previousArea != null
                              ? '${res.previousArea!.toStringAsFixed(3)} m²'
                              : 'Base Frame',
                          caption: 'Preceding visit',
                          color: AppTheme.subTextColor,
                        ),
                        Container(height: 40, width: 1, color: AppTheme.borderColor),
                        _buildMetricCol(
                          title: 'Expansion Delta',
                          value: '${res.areaChangePercentage > 0 ? "+" : ""}${res.areaChangePercentage.toStringAsFixed(1)}%',
                          caption: res.evolutionStatus,
                          color: statusColor,
                          boldValue: true,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),

            // 3. Civil Engineering AI Recommendations Widget
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.engineering_outlined, color: AppTheme.primaryColor),
                            SizedBox(width: 8),
                            Text(
                              'Civil AI Advisory',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.textColor,
                              ),
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryColor.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            'Priority: ${res.municipalPriorityRank}/10',
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.primaryColor,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const Divider(height: 20),
                    const Text(
                      'Root Cause Analysis',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.subTextColor,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      res.rootCause,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppTheme.textColor,
                        height: 1.3,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Recommended Remediation',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.subTextColor,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      res.remediation,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppTheme.textColor,
                        height: 1.3,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // 4. Download / View PDF Button
            ElevatedButton.icon(
              onPressed: _isDownloadingPdf ? null : _openOrDownloadPdf,
              icon: _isDownloadingPdf
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.picture_as_pdf, color: Colors.white),
              label: Text(
                _isDownloadingPdf
                    ? 'Preparing PDF Report...'
                    : 'View / Download Official Engineering PDF',
                style: const TextStyle(fontSize: 14),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCol({
    required String title,
    required String value,
    required String caption,
    required Color color,
    bool boldValue = false,
  }) {
    return Column(
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 11,
            color: AppTheme.subTextColor,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 15,
            fontWeight: boldValue ? FontWeight.bold : FontWeight.w600,
            color: color,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          caption,
          style: const TextStyle(fontSize: 10, color: AppTheme.subTextColor),
        ),
      ],
    );
  }
}

