import 'dart:async';
import 'package:agrisense/providers/farm_data_provider.dart';
import 'package:agrisense/screens/info_profile_screen.dart';
import 'package:agrisense/screens/main_screen.dart';
import 'package:agrisense/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _navigateToNextScreen();
  }

  Future<void> _navigateToNextScreen() async {
    // Wait for the splash animation to be visible
    await Future.delayed(const Duration(seconds: 3));

    if (mounted) {
      final farmDataProvider = context.read<FarmDataProvider>();

      // **THE FIX IS HERE:**
      // We will now wait until the provider's `isLoading` flag becomes false.
      // This guarantees that we don't check for onboarding status until
      // the data has been loaded from storage.
      while (farmDataProvider.isLoading) {
        await Future.delayed(const Duration(milliseconds: 100));
      }

      // Now that we are sure the data has been loaded, we can safely check the flag
      if (farmDataProvider.hasOnboarded) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => const MainScreen()),
        );
      } else {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (context) => const InfoProfileScreen()),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primaryColor,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.agriculture,
              size: 120,
              Icons.add_road,
              size: 110,
              color: Colors.white,
            ),
            const SizedBox(height: 24),
            const SizedBox(height: 20),
            Text(
              'AgriSense',
              'ScanTrail',
              style: TextStyle(
                fontSize: 36,
                fontWeight: FontWeight.bold,
                color: Colors.white,
                letterSpacing: 1.2,
                shadows: [
                  Shadow(
                    blurRadius: 10.0,
                    color: Colors.black.withOpacity(0.3),
                    offset: const Offset(2.0, 2.0),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Spatial-Temporal Road Infrastructure Monitoring',
              style: TextStyle(
                fontSize: 13,
                color: Colors.white70,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

