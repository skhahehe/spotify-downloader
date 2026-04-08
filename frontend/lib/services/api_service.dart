import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/track.dart';

class ApiService {
  static String _baseUrl = 'http://127.0.0.1:${String.fromEnvironment('BACKEND_PORT', defaultValue: '17017')}';
  String get baseUrl => _baseUrl;

  static void updatePort(String port) {
    _baseUrl = 'http://127.0.0.1:$port';
    print("📡 ApiService: Global Base URL updated to $_baseUrl");
  }

  Future<void> setConfig({String? downloadPath, String? format, int? concurrency, int? minConfidence}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/config'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'download_path': downloadPath,
        'format': format ?? 'mp3',
        'concurrency': concurrency ?? 3,
        'min_confidence': minConfidence ?? 70,
      }),
    ).timeout(const Duration(seconds: 5));
    if (response.statusCode != 200) {
      throw Exception(jsonDecode(response.body)['detail'] ?? 'Failed to configure');
    }
  }

  Future<List<Track>> getPlaylistTracks(String url, {String? customName}) async {
    String endpoint = '$baseUrl/playlist?url=${Uri.encodeComponent(url)}';
    if (customName != null && customName.trim().isNotEmpty) {
      endpoint += '&custom_name=${Uri.encodeComponent(customName.trim())}';
    }
    final response = await http.get(Uri.parse(endpoint)).timeout(const Duration(seconds: 300)); // Playlists can take long during scraping
    if (response.statusCode == 200) {
      List<dynamic> body = jsonDecode(response.body);
      return body.map((dynamic item) => Track.fromJson(item)).toList();
    } else {
      throw Exception(jsonDecode(response.body)['detail'] ?? 'Failed to fetch playlist');
    }
  }

  Future<List<YouTubeMatch>> searchTrack(String trackId) async {
    final response = await http.get(Uri.parse('$baseUrl/search?track_id=$trackId')).timeout(const Duration(seconds: 20));
    if (response.statusCode == 200) {
      List<dynamic> body = jsonDecode(response.body);
      return body.map((dynamic item) => YouTubeMatch.fromJson(item)).toList();
    } else {
      throw Exception('Failed to search matches');
    }
  }

  Future<void> startDownload(String trackId, {String? youtubeUrl}) async {
    String query = '$baseUrl/download?track_id=$trackId';
    if (youtubeUrl != null) {
      query += '&youtube_url=${Uri.encodeComponent(youtubeUrl)}';
    }
    final response = await http.post(Uri.parse(query)).timeout(const Duration(seconds: 5));
    if (response.statusCode != 200) {
      throw Exception('Failed to start download');
    }
  }

  Future<Map<String, dynamic>> getStatus() async {
    final response = await http.get(Uri.parse('$baseUrl/status')).timeout(const Duration(seconds: 2));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get status');
    }
  }

  Future<Map<String, dynamic>> getScrapeStatus() async {
    final response = await http.get(Uri.parse('$baseUrl/scrape_status')).timeout(const Duration(seconds: 2));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get scrape status');
    }
  }

  Future<void> retryFailed() async {
    final response = await http.post(Uri.parse('$baseUrl/retry_failed')).timeout(const Duration(seconds: 5));
    if (response.statusCode != 200) {
      throw Exception('Failed to retry');
    }
  }
}
