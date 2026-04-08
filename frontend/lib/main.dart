import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_fonts/google_fonts.dart';
import 'screens/setup_screen.dart';
import 'screens/home_screen.dart';
import 'services/api_service.dart';
import 'services/python_bridge.dart';
import 'screens/splash_screen.dart';
import 'models/track.dart';
import 'dart:async';
import 'dart:io';
import 'package:path/path.dart' as p;

Process? _backendProcess;
String _discoveredPort = String.fromEnvironment('BACKEND_PORT', defaultValue: '17017');

void _log(String message) {
  final logFile = File('/tmp/spotify_app.log');
  print(message);
  try {
    logFile.writeAsStringSync("${DateTime.now().toIso8601String()}: $message\n", mode: FileMode.append);
  } catch (e) {
    // Ignore log errors
  }
}

Future<String?> startDesktopBackend() async {
  if (Platform.environment["SKIP_BACKEND_SPAWN"] == "1") return "17017";
  
  String execPath = Platform.resolvedExecutable;
  String envPath = "";
  if (Platform.isMacOS) {
    envPath = p.join(p.dirname(p.dirname(execPath)), 'Resources', 'BackendEnv');
  } else {
    envPath = p.join(p.dirname(execPath), 'BackendEnv');
  }

  String projectRoot = Directory.current.path;
  if (projectRoot.endsWith('frontend')) projectRoot = p.dirname(projectRoot);
  
  String launcherScript = "";
  String workingDir = projectRoot;

  if (Directory(envPath).existsSync()) {
    workingDir = envPath;
    launcherScript = p.join(envPath, 'launch_backend.app.sh');
  }

  await _spawnBackend(
    launcherScript: launcherScript, 
    workingDir: workingDir,
  );
  
  return "17017";
}

Future<void> _spawnBackend({
  required String launcherScript,
  required String workingDir,
}) async {
  if (launcherScript.isEmpty) {
    _log("❌ Error: Launcher script not found.");
    return;
  }

  _log("Spawning backend via shell script: $launcherScript");
  _log("Working Directory: $workingDir");

  try {
    _backendProcess = await Process.start(
      'sh',
      [launcherScript],
      workingDirectory: workingDir,
    );
    print("🚀 Backend spawned with PID: ${_backendProcess?.pid}");
    
    // Stream backend output directly to our unified log
    _backendProcess?.stdout.transform(SystemEncoding().decoder).listen((data) {
      _log("Backend StdOut: $data");
    });
    _backendProcess?.stderr.transform(SystemEncoding().decoder).listen((data) {
      _log("Backend StdErr: $data");
    });

  } catch (e) {
    print("\n\n❌ 🔥 FATAL BACKEND ERROR 🔥 ❌");
    print("Failed to start embedded backend: $e");
    print("Check /tmp/spotify_backend.log for full Python traceback.\n\n");
  }
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final apiService = ApiService();

  runApp(
    ChangeNotifierProvider(
      create: (context) => AppState(prefs, apiService),
      child: const SpotifyDownloaderApp(),
    ),
  );
}

class AppState extends ChangeNotifier {
  final SharedPreferences prefs;
  final ApiService api;
  
  List<Track> tracks = [];
  bool isInitializing = true;
  bool isConfigured = false;
  String statusMessage = "Initializing...";
  int scrapeCount = 0;
  int scrapeTarget = 0;
  bool _isPolling = false;
  Timer? _statusTimer;

  AppState(this.prefs, this.api) {
    _init();
  }

  Future<void> _init() async {
    // 1. Backend Startup
    if (Platform.isAndroid || Platform.isIOS) {
      statusMessage = "Starting Backend...";
      notifyListeners();
      await PythonBridge.startBackend();
    } else {
      statusMessage = "Starting Backend...";
      notifyListeners();
      String? port = await startDesktopBackend();
      if (port != null) {
        ApiService.updatePort(port);
      } else {
        statusMessage = "Error: Backend failed to start.";
        notifyListeners();
        return; // Stop initialization
      }
    }

    // 2. Handshake
    statusMessage = "Connecting...";
    notifyListeners();
    bool handshakeSuccess = false;
    _log("📡 Handshake Target: ${api.baseUrl}");
    for (int i = 0; i < 30; i++) {
        try {
            await api.getStatus();
            _log("✅ BACKEND RESPONDED: Handshake complete after $i retries");
            handshakeSuccess = true;
            break;
        } catch (e) {
            _log("⏳ Handshake attempt $i: Still waiting for ${api.baseUrl}... Error: $e");
            await Future.delayed(const Duration(seconds: 1));
        }
    }
    
    if (!handshakeSuccess) {
      statusMessage = "Error: Connection timeout.";
      notifyListeners();
      return;
    }

    // 3. Config Check
    statusMessage = "Optimizing...";
    notifyListeners();
    await checkConfig();
    
    // 4. Finalize
    statusMessage = "Ready!";
    notifyListeners();
    await Future.delayed(const Duration(milliseconds: 500));
    isInitializing = false;
    notifyListeners();
    startStatusPolling();
  }

  Future<void> checkConfig() async {
    final downloadPath = prefs.getString('download_path');
    final concurrency = prefs.getInt('concurrency') ?? 3;
    final isFirstRun = prefs.getBool('is_first_run') ?? true;

    if (!isFirstRun) {
      isConfigured = true;
      notifyListeners();
      
      // Retry setConfig until backend is ready
      bool success = false;
      int retries = 0;
      while (!success && retries < 15) {
        try {
          await api.setConfig(downloadPath: downloadPath, concurrency: concurrency);
          success = true;
          print("✅ Backend configured successfully after ${retries} retries");
        } catch (e) {
          retries++;
          print("⏳ Waiting for backend... ($retries/15)");
          await Future.delayed(const Duration(seconds: 2));
        }
      }
    } else {
      isConfigured = false;
      notifyListeners();
    }
  }

  Future<void> saveConfig({String? downloadPath, int? concurrency, int? minConfidence}) async {
    if (downloadPath != null) {
      await prefs.setString('download_path', downloadPath);
    }
    if (minConfidence != null) {
      await prefs.setInt('min_confidence', minConfidence);
    }
    await prefs.setInt('concurrency', concurrency ?? 3);
    await prefs.setBool('is_first_run', false);
    
    await api.setConfig(
      downloadPath: prefs.getString('download_path'), 
      concurrency: concurrency ?? prefs.getInt('concurrency'),
      minConfidence: minConfidence ?? prefs.getInt('min_confidence') ?? 70,
    );
    isConfigured = true;
    notifyListeners();
  }

  Future<void> fetchPlaylist(String url, {String? customName, int? minConfidence}) async {
    // 1. Ensure config is synced
    await saveConfig(minConfidence: minConfidence);
    
    statusMessage = "Analyzing...";
    notifyListeners();

    // 2. Start polling for scraper progress
    Timer? progressTimer = Timer.periodic(const Duration(milliseconds: 1000), (timer) async {
      try {
        final status = await api.getScrapeStatus();
        scrapeCount = status['count'] ?? 0;
        scrapeTarget = status['target'] ?? 0;
        
        if (scrapeCount > 0) {
          if (scrapeTarget > 0) {
            statusMessage = "Analyzing... Found $scrapeCount of $scrapeTarget songs";
          } else {
            statusMessage = "Analyzing... Found $scrapeCount songs";
          }
          notifyListeners();
        }
      } catch (e) {
        // Silent fail for polling
      }
    });

    try {
      scrapeCount = 0;
      scrapeTarget = 0;
      // 3. Perform the long fetch with 5-minute timeout
      tracks = await api.getPlaylistTracks(url, customName: customName);
    } catch (e) {
      statusMessage = "Error: $e";
      rethrow;
    } finally {
      scrapeCount = 0;
      scrapeTarget = 0;
      progressTimer.cancel();
    }
    
    notifyListeners();
  }

  void startStatusPolling() {
    _statusTimer = Timer.periodic(const Duration(seconds: 1), (timer) async {
      if (tracks.isEmpty || _isPolling) return;
      
      _isPolling = true;
      try {
        final status = await api.getStatus();
        bool changed = false;
        
        for (var track in tracks) {
          if (status.containsKey(track.id)) {
            final trackStatus = status[track.id];
            
            // Only flag change for meaningful visual updates
            final newProgress = (trackStatus['progress'] ?? 0.0).toDouble();
            final newStatus = trackStatus['status'];
            
            if (track.status != newStatus || (track.progress - newProgress).abs() > 0.5) {
              track.status = newStatus;
              track.progress = newProgress;
              track.speed = trackStatus['speed'];
              track.downloadedMb = trackStatus['downloadedMb'];
              track.totalMb = trackStatus['totalMb'];
              changed = true;
            }
          }
        }
        if (changed) notifyListeners();
      } catch (e) {
        print("Status poll skipped/error: $e");
      } finally {
        _isPolling = false;
      }
    });
  }

  @override
  void dispose() {
    _statusTimer?.cancel();
    super.dispose();
  }
}

class SpotifyDownloaderApp extends StatelessWidget {
  const SpotifyDownloaderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Spotify Smart Downloader',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1DB954), // Spotify Green
          brightness: Brightness.dark,
        ),
        textTheme: GoogleFonts.outfitTextTheme(ThemeData.dark().textTheme),
      ),
      home: Consumer<AppState>(
        builder: (context, state, child) {
          if (state.isInitializing) {
            return const SplashScreen();
          }
          return state.isConfigured ? const HomeScreen() : const SetupScreen();
        },
      ),
    );
  }
}
