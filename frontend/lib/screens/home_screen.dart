import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';

import '../main.dart';
import 'track_list_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _urlController = TextEditingController();
  final TextEditingController _folderNameController = TextEditingController();
  final TextEditingController _accuracyController = TextEditingController();
  bool _isSearching = false;
  String _format = 'mp3';
  String _mode = 'auto';

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final state = context.read<AppState>();
    setState(() {
      _accuracyController.text = (state.prefs.getInt('min_confidence') ?? 70).toString();
    });
  }

  void _onPaste() async {
    if (_urlController.text.trim().isEmpty) return;
    
    setState(() => _isSearching = true);
    final state = context.read<AppState>();
    state.statusMessage = "Initializing Scraper...";
    state.notifyListeners();
    
    try {
      // Update format and base config
      await state.saveConfig(
        minConfidence: int.tryParse(_accuracyController.text) ?? 70,
      );
      await state.api.setConfig(
        downloadPath: state.prefs.getString('download_path'),
        format: _format,
        concurrency: state.prefs.getInt('concurrency') ?? 3,
        minConfidence: int.tryParse(_accuracyController.text) ?? 70,
      );
      
      await state.fetchPlaylist(
        _urlController.text.trim(), 
        customName: _folderNameController.text.trim()
      );
      if (context.mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => TrackListScreen(mode: _mode)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error: $e"), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSearching = false);
      }
    }
  }

  void _pasteFromClipboard() async {
    final ClipboardData? data = await Clipboard.getData(Clipboard.kTextPlain);
    if (data != null && data.text != null) {
      if (mounted) {
        setState(() {
          _urlController.text = data.text!;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Spotify Downloader"),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) {
                  final state = context.read<AppState>();
                  return AlertDialog(
                    title: const Text("Settings"),
                    content: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ListTile(
                          title: const Text("Update Download Folder"),
                          subtitle: Text(state.prefs.getString('download_path') ?? "Using default folder"),
                          trailing: const Icon(Icons.edit),
                          onTap: () async {
                            String? selectedDir = await FilePicker.platform.getDirectoryPath();
                            if (selectedDir != null) {
                              await state.saveConfig(downloadPath: selectedDir);
                              if (context.mounted) Navigator.pop(context);
                            }
                          },
                        ),
                        const Divider(),
                        ListTile(
                          title: const Text("Match Accuracy Threshold (%)"),
                          subtitle: const Text("Songs below this match % will wait for manual review"),
                          trailing: SizedBox(
                            width: 60,
                            child: TextField(
                              controller: _accuracyController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(border: OutlineInputBorder()),
                            ),
                          ),
                        ),
                        const Divider(),
                        ListTile(
                          title: const Text("Reset App Data", style: TextStyle(color: Colors.red)),
                          leading: const Icon(Icons.refresh, color: Colors.red),
                          onTap: () async {
                            await state.prefs.clear();
                            state.isConfigured = false;
                            state.notifyListeners();
                            if (context.mounted) Navigator.pop(context);
                          },
                        ),
                      ],
                    ),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
                      FilledButton(
                        onPressed: () async {
                          await state.saveConfig(
                            downloadPath: state.prefs.getString('download_path'),
                          );
                          if (context.mounted) Navigator.pop(context);
                        },
                        child: const Text("Save"),
                      ),
                    ],
                  );
                },
              );
            },
          )
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.library_music, size: 100, color: Colors.green),
              const SizedBox(height: 32),
              const Text(
                "Enjoy Public Playlists",
                style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              const Text(
                "Paste any public Spotify link. No login required.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey, fontSize: 16),
              ),
              const SizedBox(height: 48),
              Container(
                constraints: const BoxConstraints(maxWidth: 600),
                child: Column(
                  children: [
                    TextField(
                      controller: _urlController,
                      enabled: !_isSearching,
                      decoration: InputDecoration(
                        hintText: "https://open.spotify.com/playlist/...",
                        labelText: "Playlist URL",
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.link),
                        suffixIcon: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (_urlController.text.isNotEmpty)
                              IconButton(
                                icon: const Icon(Icons.clear),
                                onPressed: () => setState(() => _urlController.clear()),
                              ),
                            IconButton(
                              icon: const Icon(Icons.content_paste_rounded),
                              onPressed: _pasteFromClipboard,
                              tooltip: "Paste",
                            ),
                          ],
                        ),
                      ),
                      onChanged: (val) => setState(() {}),
                      onSubmitted: (_) => _onPaste(),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _folderNameController,
                      enabled: !_isSearching,
                      decoration: InputDecoration(
                        hintText: "Leave blank for Spotify's auto name",
                        labelText: "Custom Folder Name",
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.create_new_folder),
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.clear),
                          onPressed: () => setState(() => _folderNameController.clear()),
                        ),
                      ),
                      onSubmitted: (_) => _onPaste(),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: _format,
                            decoration: const InputDecoration(labelText: "Format", border: OutlineInputBorder()),
                            items: const [
                              DropdownMenuItem(value: "mp3", child: Text("MP3 (320kbps)")),
                              DropdownMenuItem(value: "m4a", child: Text("AAC (m4a)")),
                              DropdownMenuItem(value: "original", child: Text("Keep Original")),
                            ],
                            onChanged: (val) => setState(() => _format = val!),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Row(
                            children: [
                              Expanded(
                                child: DropdownButtonFormField<String>(
                                  value: _mode,
                                  decoration: const InputDecoration(labelText: "Mode", border: OutlineInputBorder()),
                                  items: const [
                                    DropdownMenuItem(value: "auto", child: Text("Auto Search")),
                                    DropdownMenuItem(value: "hybrid", child: Text("Hybrid")),
                                    DropdownMenuItem(value: "manual", child: Text("Manual Selection")),
                                  ],
                                  onChanged: (val) => setState(() => _mode = val!),
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.info_outline, color: Colors.green),
                                onPressed: () {
                                  showDialog(
                                    context: context,
                                    builder: (context) => AlertDialog(
                                      title: const Text("Download Modes Explained"),
                                      content: const Column(
                                        mainAxisSize: MainAxisSize.min,
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text("• Auto Search:", style: TextStyle(fontWeight: FontWeight.bold)),
                                          Text("Completely automated. The app finds and downloads the best match instantly.\n"),
                                          Text("• Hybrid:", style: TextStyle(fontWeight: FontWeight.bold)),
                                          Text("Automated, but if a match's accuracy is lower than your threshold, it pauses for you to pick.\n"),
                                          Text("• Manual Selection:", style: TextStyle(fontWeight: FontWeight.bold)),
                                          Text("The app always shows you the list of candidates so you can choose exactly what to download."),
                                        ],
                                      ),
                                      actions: [
                                        TextButton(onPressed: () => Navigator.pop(context), child: const Text("Got it")),
                                      ],
                                    ),
                                  );
                                },
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),
                    Consumer<AppState>(
                      builder: (context, state, _) {
                        double progress = 0;
                        if (state.scrapeTarget > 0) {
                          progress = state.scrapeCount / state.scrapeTarget;
                        }
                        
                        return Column(
                          children: [
                            SizedBox(
                              width: double.infinity,
                              height: 60,
                              child: Stack(
                                children: [
                                  // 1. Background Fill Layer (Only when searching)
                                  if (_isSearching)
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(12),
                                      child: LinearProgressIndicator(
                                        value: progress > 0 ? progress : null, // Null = indeterminate until we have a target
                                        minHeight: 60,
                                        backgroundColor: Colors.green.withOpacity(0.1),
                                        color: Colors.green,
                                      ),
                                    ),
                                  
                                  // 2. Button Layer
                                  SizedBox.expand(
                                    child: ElevatedButton(
                                      onPressed: _isSearching ? null : _onPaste,
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: _isSearching ? Colors.transparent : Colors.green,
                                        foregroundColor: _isSearching ? Colors.white : Colors.white,
                                        elevation: _isSearching ? 0 : 2,
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                        disabledBackgroundColor: Colors.transparent,
                                        disabledForegroundColor: Colors.white,
                                      ),
                                      child: _isSearching 
                                        ? Text(
                                            state.scrapeTarget > 0 
                                              ? "Searching: ${state.scrapeCount} / ${state.scrapeTarget}"
                                              : "Initializing Scraper...",
                                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white, shadows: [Shadow(blurRadius: 2, color: Colors.black45)]),
                                          )
                                        : const Text("Analyze & Fetch", style: TextStyle(fontSize: 18)),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            if (_isSearching) ...[
                              const SizedBox(height: 12),
                              Text(
                                state.statusMessage,
                                style: const TextStyle(color: Colors.green, fontSize: 13, fontWeight: FontWeight.w500),
                              ),
                            ],
                          ],
                        );
                      }
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
