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
  String _filter = 'all'; // all | active | failed | done

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
          final all = state.tracks;
          final done = all.where((t) => t.status == 'done').length;
          final failed = all.where((t) => t.isFailed).length;
          final active = all.where((t) => t.isActive).length;
          final shown = switch (_filter) {
            'active' => all.where((t) => t.isActive || t.status == 'pending').toList(),
            'failed' => all.where((t) => t.isFailed).toList(),
            'done' => all.where((t) => t.status == 'done').toList(),
            _ => all,
          };
          final scheme = Theme.of(context).colorScheme;

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text("$done of ${all.length} downloaded",
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                        const Spacer(),
                        if (active > 0) Text("$active in progress", style: TextStyle(color: scheme.primary, fontSize: 13)),
                        if (failed > 0) Padding(
                          padding: const EdgeInsets.only(left: 12),
                          child: Text("$failed failed", style: const TextStyle(color: Colors.redAccent, fontSize: 13)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: all.isEmpty ? 0 : done / all.length,
                        minHeight: 6,
                        backgroundColor: Colors.white10,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      children: [
                        for (final (key, label) in [
                          ('all', 'All ${all.length}'),
                          ('active', 'To do ${all.length - done - failed}'),
                          ('failed', 'Failed $failed'),
                          ('done', 'Done $done'),
                        ])
                          ChoiceChip(
                            label: Text(label),
                            selected: _filter == key,
                            onSelected: (_) => setState(() => _filter = key),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              Expanded(
                child: shown.isEmpty
                    ? Center(child: Text("Nothing here.", style: TextStyle(color: Colors.grey[500])))
                    : ListView.builder(
                        padding: const EdgeInsets.only(bottom: 32),
                        itemCount: shown.length,
                        itemBuilder: (context, index) => TrackCard(track: shown[index], mode: widget.mode),
                      ),
              ),
            ],
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
                      tileColor: i == 0 ? Colors.green.withValues(alpha: 0.08) : null,
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

  static String _statusLabel(String status) => switch (status) {
        'queued' => 'Waiting in queue',
        'searching' => 'Finding the best match on YouTube',
        'downloading' => 'Downloading',
        'processing' => 'Converting audio',
        'tagging' => 'Adding cover art & tags',
        _ => status,
      };

  @override
  Widget build(BuildContext context) {
    final statColor = _getStatusColor(track.status);
    final isDone = track.status == 'done';
    final isWorking = track.isActive;
    // No real percentage before the download starts or while converting: show a moving bar instead of a stuck 0%
    final indeterminate = track.status != 'downloading';

    return Card(
      elevation: 0,
      color: Colors.grey[900]!.withValues(alpha: 0.5),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: track.isFailed ? Colors.redAccent.withValues(alpha: 0.3) : Colors.white.withValues(alpha: 0.05))),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: track.imageUrl != null 
                  ? Image.network(track.imageUrl!, width: 50, height: 50, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(width: 50, height: 50, color: Colors.grey[800], child: const Icon(Icons.music_note)))
                  : Container(width: 50, height: 50, color: Colors.grey[800], child: const Icon(Icons.music_note)),
              ),
              title: Text(track.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15), maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: Text("${track.artist} • ${track.album}", maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, color: Colors.grey)),
              trailing: isDone 
                ? const Icon(Icons.check_circle_rounded, color: Colors.greenAccent)
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (mode != 'auto' && !track.isFailed)
                        IconButton(
                          icon: const Icon(Icons.manage_search_rounded, size: 20),
                          onPressed: () => _showMatchPicker(context),
                          tooltip: "Manual Search",
                        ),
                      IconButton(
                        icon: Icon(track.isFailed ? Icons.replay_rounded : Icons.download_rounded, size: 20),
                        onPressed: () => context.read<AppState>().api.startDownload(track.id),
                        tooltip: track.isFailed ? "Retry" : "Download",
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
                            "${_statusLabel(track.status)}${track.status == 'downloading' && track.totalMb != null ? ' • ${track.downloadedMb ?? '0.0MB'} / ${track.totalMb}' : ''}",
                            style: TextStyle(fontSize: 12, color: statColor, fontWeight: FontWeight.w600),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Row(
                          children: [
                            if (track.status == 'downloading' && track.speed != null && track.speed!.isNotEmpty)
                              Text("${track.speed}  ·  ", style: const TextStyle(fontSize: 12, color: Colors.grey)),
                            if (!indeterminate)
                              Text("${track.progress.toStringAsFixed(0)}%", style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                          ],
                        )
                      ],
                    ),
                    const SizedBox(height: 6),
                    if (indeterminate)
                      ClipRRect(
                        borderRadius: BorderRadius.circular(2),
                        child: LinearProgressIndicator(minHeight: 4, color: statColor, backgroundColor: Colors.white10),
                      )
                    else
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
            if (track.isFailed)
              Padding(
                padding: const EdgeInsets.only(top: 4.0),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline_rounded, color: Colors.redAccent, size: 16),
                    const SizedBox(width: 6),
                    const Expanded(
                      child: Text("No confident match, or the download failed.",
                          style: TextStyle(color: Colors.redAccent, fontSize: 12)),
                    ),
                    TextButton(onPressed: () => _showMatchPicker(context), child: const Text("Pick a match")),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
