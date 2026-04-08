class Track {
  final String id;
  final String title;
  final String artist;
  final String album;
  final String year;
  final String? imageUrl;
  final int durationMs;
  String status; // 'pending', 'starting', 'downloading', 'tagging', 'done', 'error'
  double progress;
  String? youtubeUrl;
  
  // Download metrics
  String? speed;
  String? downloadedMb;
  String? totalMb;

  Track({
    required this.id,
    required this.title,
    required this.artist,
    required this.album,
    required this.year,
    this.imageUrl,
    required this.durationMs,
    this.status = 'pending',
    this.progress = 0.0,
    this.youtubeUrl,
    this.speed,
    this.downloadedMb,
    this.totalMb,
  });

  factory Track.fromJson(Map<String, dynamic> json) {
    return Track(
      id: json['id'],
      title: json['title'],
      artist: json['artist'],
      album: json['album'],
      year: json['year'],
      imageUrl: json['image_url'],
      durationMs: json['duration_ms'],
      status: json['status'] ?? 'pending',
      progress: (json['progress'] ?? 0.0).toDouble(),
      youtubeUrl: json['youtube_url'],
      speed: json['speed'],
      downloadedMb: json['downloadedMb'],
      totalMb: json['totalMb'],
    );
  }
}

class YouTubeMatch {
  final String id;
  final String title;
  final String url;
  final int durationS;
  final String channel;
  final int confidence;
  final String type;

  YouTubeMatch({
    required this.id,
    required this.title,
    required this.url,
    required this.durationS,
    required this.channel,
    required this.confidence,
    required this.type,
  });

  factory YouTubeMatch.fromJson(Map<String, dynamic> json) {
    return YouTubeMatch(
      id: json['id'],
      title: json['title'],
      url: json['url'],
      durationS: (json['duration_s'] ?? 0).toInt(),
      channel: json['channel'],
      confidence: (json['confidence'] ?? 0).toInt(),
      type: json['type'],
    );
  }
}
