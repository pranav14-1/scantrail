import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart'; // Required for Uint8List
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../models/defect_analysis_result.dart';

class ApiService {
  static const String _apiUrl = "https://agrisense-backend-trdc.onrender.com/analyze";
  // Configurable base URL for ScanTrail backend
  static const String baseUrl = "http://10.0.2.2:8000"; // Default Android emulator host loopback / localhost

  /// Analyzes the plant image and returns a PDF report as a byte list.
  ///
  /// Takes the image [File], the current [languageCode], and the plant's
  /// coordinates ([row], [col]) as input.
  static Future<Uint8List> analyzePlantAndGetPdf(
      File imageFile, String languageCode, int row, int col) async {
  /// Sends multipart upload to POST /scan/analyze
  /// with image, latitude, longitude, timestamp, bounding_box_area.
  static Future<DefectAnalysisResult> analyzeRoadDefect({
    required File imageFile,
    required double latitude,
    required double longitude,
    required double boundingBoxArea,
    double severityScore = 0.5,
    String? customBaseUrl,
  }) async {
    final host = customBaseUrl ?? baseUrl;
    final uri = Uri.parse('$host/scan/analyze');

    try {
      var request = http.MultipartRequest('POST', Uri.parse(_apiUrl));
      final request = http.MultipartRequest('POST', uri);
      request.fields['latitude'] = latitude.toString();
      request.fields['longitude'] = longitude.toString();
      request.fields['timestamp'] = DateTime.now().toUtc().toIso8601String();
      request.fields['bounding_box_area'] = boundingBoxArea.toString();
      request.fields['severity_score'] = severityScore.toString();

      // Add all required fields to the multipart request.
      request.fields['language_code'] = languageCode;
      request.fields['row'] = row.toString();
      request.fields['col'] = col.toString();

      // Attach the image file.
      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      var response = await request.send();
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        // The function now returns the raw bytes of the PDF file,
        // which is represented as a Uint8List in Dart.
        return await response.stream.toBytes();
        final Map<String, dynamic> data = jsonDecode(response.body);
        return DefectAnalysisResult.fromJson(data);
      } else {
        // Handle server-side errors.
        final errorBody = await response.stream.bytesToString();
        throw Exception(
            'Backend Error: ${response.statusCode}\nResponse: $errorBody');
        throw Exception('Server error ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      // Handle network or other client-side errors.
      print('Error calling backend: $e');
      throw Exception(
          'Failed to connect to the backend service. Please check your internet connection.');
      print('ApiService analyzeRoadDefect error: $e');
      rethrow;
    }
  }

  /// Downloads generated PDF report bytes from GET /reports/{report_id}
  static Future<Uint8List> downloadPdfReport(String pdfReportUrl, {String? customBaseUrl}) async {
    final host = customBaseUrl ?? baseUrl;
    final normalizedUrl = pdfReportUrl.startsWith('http')
        ? pdfReportUrl
        : '$host$pdfReportUrl';

    final response = await http.get(Uri.parse(normalizedUrl));
    if (response.statusCode == 200) {
      return response.bodyBytes;
    } else {
      throw Exception('Failed to download report (${response.statusCode})');
    }
  }
}

