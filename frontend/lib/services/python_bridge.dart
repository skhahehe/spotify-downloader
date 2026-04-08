import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:serious_python/serious_python.dart';
import 'package:path/path.dart' as p;

class PythonBridge {
  static Future<void> startBackend() async {
    try {
      // serious_python automatically extracts assets/app.zip and runs the specified script.
      // We start FastAPI server from the entry point main.py inside the zip.
      SeriousPython.run(
        "app/backend/main.py", 
        appFileName: "app.zip",
        environmentVariables: {"PYTHONPATH": "."}
      );
      print("Python Backend Started via SeriousPython");
    } catch (e) {
      print("Failed to start Python Backend: $e");
    }
  }
}
