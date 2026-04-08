import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:percent_indicator/linear_percent_indicator.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../main.dart';
import '../models/track.dart';

class TrackListScreen extends StatefulWidget {
  final String mode;
  const TrackListScreen({super.key, this.mode = 'auto'});

  @override
  State<TrackListScreen> createState() => _TrackListScreenState();
}

class _TrackListScreenState extends State<TrackListScreen> {
  final TextEditingController _pathController = TextEditingController();
  bool _isSearching = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkResumeAndAuto();
    });
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _pathController.text = prefs.getString('download_path') ?? '';
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('download_path', _pathController.text);

    final state = context.read<AppState>();
    await state.saveConfig(
      downloadPath: _pathController.text,
    );

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Settings saved.")),
      );
    }
  }

  void _showSettingsDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Settings"),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _pathController,
                decoration: const InputDecoration(labelText: "Download Path", hintText: "/Users/name/Downloads"),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
          FilledButton(
            onPressed: () {
              _saveSettings();
              Navigator.pop(context);
            },
            child: const Text("Save"),
          ),
        ],
      ),
    );
  }

  void _checkResumeAndAuto() {
    // Issue 6: UI no longer re-triggers processing as the
    // Backend Orchestrator handles auto-saturation now.
    if (!mounted) return;
    final state = context.read<AppState>();
    
    int completedCount = state.tracks.where((t) => t.status == 'done').length;
    
    if (completedCount > 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Resumed playlist: $completedCount / ${state.tracks.length} already done"),
          backgroundColor: Colors.green.withOpacity(0.8),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  void _startAllPending() {
    final state = context.read<AppState>();
    for (var track in state.tracks) {
      if (track.status == 'pending' || track.status == 'failed') {
        state.api.startDownload(track.id).catchError((e) => print("Queue error: $e"));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Download Queue"),
        actions: [
          Consumer<AppState>(
            builder: (context, state, child) {
              int failedCount = state.tracks.where((t) => t.status == 'failed' || t.status == 'error').length;
              if (failedCount > 0) {
                return TextButton.icon(
                  onPressed: () => state.api.retryFailed(),
                  icon: const Icon(Icons.replay_rounded, color: Colors.orangeAccent),
                  label: const Text("Retry Failed", style: TextStyle(color: Colors.orangeAccent)),
                );
              }
              return const SizedBox();
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: _showSettingsDialog,
          ),
          const SizedBox(width: 8),
          Padding(
            padding: const EdgeInsets.only(right: 8.0),
            child: FilledButton.tonalIcon(
              onPressed: _startAllPending,
              icon: const Icon(Icons.play_arrow_rounded),
              label: const Text("Start All"),
            ),
          ),
        ],
      ),
      body: Consumer<AppState>(
        builder: (context, state, child) {
          if (state.tracks.isEmpty) {
            return const Center(child: Text("No tracks found in this playlist."));
          }
          return ListView.builder(
            padding: const EdgeInsets.only(bottom: 32),
            itemCount: state.tracks.length,
            itemBuilder: (context, index) {
              final track = state.tracks[index];
              return TrackCard(track: track, mode: widget.mode);
            },
          );
        },
      ),
    );
  }
}

class TrackCard extends StatelessWidget {
  final Track track;
  final String mode;
  const TrackCard({super.key, required this.track, required this.mode});

  void _showMatchPicker(BuildContext context) async {
    final state = context.read<AppState>();
    try {
      List<YouTubeMatch> matches = await state.api.searchTrack(track.id);
      if (!context.mounted) return;

      showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.grey[900],
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        builder: (context) => DraggableScrollableSheet(
          initialChildSize: 0.6,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          expand: false,
          builder: (context, scrollController) => Column(
            children: [
              Container(
                width: 40, height: 4, 
                margin: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(2)),
              ),
              const Text("Manual Selection", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              Expanded(
                child: ListView.builder(
                  controller: scrollController,
                  itemCount: matches.length,
                  itemBuilder: (context, i) {
                    final m = matches[i];
                    return ListTile(
                      leading: const Icon(Icons.video_library_rounded, color: Colors.redAccent),
                      title: Text(m.title, maxLines: 1, overflow: TextOverflow.ellipsis),
                      subtitle: Text("${m.channel} • ${m.confidence}% match"),
                      trailing: const Icon(Icons.download_rounded),
                      onTap: () {
                        track.youtubeUrl = m.url;
                        state.api.startDownload(track.id, youtubeUrl: m.url);
                        Navigator.pop(context);
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      );
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Search failed: $e")));
      }
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'done': return Colors.greenAccent;
      case 'failed':
      case 'error': return Colors.redAccent;
      case 'downloading':
      case 'processing':
      case 'tagging': return Colors.blueAccent;
      default: return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final statColor = _getStatusColor(track.status);
    final isDone = track.status == 'done';
    final isWorking = !isDone && track.status != 'pending' && track.status != 'failed';

    return Card(
      elevation: 0,
      color: Colors.grey[900]!.withOpacity(0.5),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: Colors.white.withOpacity(0.05))),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: track.imageUrl != null 
                  ? Image.network(track.imageUrl!, width: 50, height: 50, fit: BoxFit.cover)
                  : Container(width: 50, height: 50, color: Colors.grey[800], child: const Icon(Icons.music_note)),
              ),
              title: Text(track.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15), maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: Text("${track.artist} • ${track.album}", maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, color: Colors.grey)),
              trailing: isDone 
                ? const Icon(Icons.check_circle_rounded, color: Colors.greenAccent)
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (mode != 'auto') 
                        IconButton(
                          icon: const Icon(Icons.manage_search_rounded, size: 20),
                          onPressed: () => _showMatchPicker(context),
                          tooltip: "Manual Search",
                        ),
                      IconButton(
                        icon: Icon(track.status == 'failed' ? Icons.replay_rounded : Icons.download_rounded, size: 20),
                        onPressed: () => context.read<AppState>().api.startDownload(track.id),
                        tooltip: "Download",
                      ),
                    ],
                  ),
            ),
            if (isWorking)
              Padding(
                padding: const EdgeInsets.only(top: 8.0),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            "${track.status.toUpperCase()} ${track.status == 'downloading' && track.totalMb != null ? ' • ${track.downloadedMb ?? '0.0MB'} / ${track.totalMb}' : ''}", 
                            style: TextStyle(fontSize: 10, color: statColor, fontWeight: FontWeight.bold, letterSpacing: 1.2),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Row(
                          children: [
                            if (track.status == 'downloading' && track.speed != null && track.speed!.isNotEmpty)
                              Text("${track.speed}  |  ", style: const TextStyle(fontSize: 10, color: Colors.grey, fontWeight: FontWeight.bold)),
                            Text("${track.progress.toStringAsFixed(0)}%", style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                          ],
                        )
                      ],
                    ),
                    const SizedBox(height: 6),
                    LinearPercentIndicator(
                      padding: EdgeInsets.zero,
                      percent: (track.progress / 100.0).clamp(0.0, 1.0),
                      backgroundColor: Colors.white10,
                      progressColor: statColor,
                      lineHeight: 4,
                      barRadius: const Radius.circular(2),
                      animation: true,
                      animateFromLastPercent: true,
                      animationDuration: 300,
                    ),
                  ],
                ),
              ),
            if (track.status == 'failed')
               const Padding(
                 padding: EdgeInsets.only(top: 4.0),
                 child: Text("Download failed. Duration mismatch or network error.", style: TextStyle(color: Colors.redAccent, fontSize: 11)),
               ),
          ],
        ),
      ),
    );
  }
}
