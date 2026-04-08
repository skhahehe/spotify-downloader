import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import '../main.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final TextEditingController _pathController = TextEditingController();
  final TextEditingController _concurrencyController = TextEditingController(text: "3");
  bool _isLoading = false;

  void _pickDirectory() async {
    String? selectedDirectory = await FilePicker.platform.getDirectoryPath();
    if (selectedDirectory != null) {
      setState(() {
        _pathController.text = selectedDirectory;
      });
    }
  }

  void _showInfo() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("How to Use"),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Text("1. Set your Download Directory below."),
              Text("2. Adjust Parallel Workers (3-5 recommended) if needed."),
              Text("3. Click Continue to enter the app."),
              SizedBox(height: 10),
              Text("💡 Now using hidden Selenium for zero-auth scraping!", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green)),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("Got it!"))
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.info_outline),
          onPressed: _showInfo,
          tooltip: "Help Guide",
        ),
        title: const Text("App Preferences"),
        centerTitle: true,
      ),
      body: Center(
        child: SingleChildScrollView(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 500),
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.download_done_rounded, size: 80, color: Colors.green),
                const SizedBox(height: 24),
                const Text(
                  "Welcome!",
                  style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                const Text(
                  "Configure your download settings. Parallel workers help download multiple songs at once.",
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey),
                ),
                const SizedBox(height: 32),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _pathController,
                        readOnly: true,
                        decoration: const InputDecoration(
                          labelText: "Download Directory",
                          hintText: "Select folder...",
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.folder_open),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filledTonal(
                      onPressed: _pickDirectory,
                      icon: const Icon(Icons.add_home_work_outlined),
                      tooltip: "Pick Directory",
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _concurrencyController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: "Parallel Workers (3-5 recommended)",
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.speed),
                    hintText: "3",
                  ),
                ),
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 16),
                const Text("App Configuration", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 12),
                const SizedBox(height: 16),
                // Removed Spotify Login Button as it is no longer required
                const SizedBox(height: 16),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : () async {
                      setState(() => _isLoading = true);
                      try {
                        final concurrency = int.tryParse(_concurrencyController.text) ?? 3;
                        await context.read<AppState>().saveConfig(
                          downloadPath: _pathController.text.isEmpty ? null : _pathController.text.trim(),
                          concurrency: concurrency,
                        );
                      } catch (e) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text("Error: $e"), backgroundColor: Colors.red),
                        );
                      } finally {
                        setState(() => _isLoading = false);
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                    ),
                    child: _isLoading 
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text("2. Continue", style: TextStyle(fontSize: 18)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
