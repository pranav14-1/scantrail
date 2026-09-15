import 'package:agrisense/models/scan_record.dart';
import 'package:agrisense/providers/farm_data_provider.dart';
import 'package:agrisense/providers/language_provider.dart';
import 'package:agrisense/screens/splash_screen.dart';
import 'package:agrisense/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:isar/isar.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'l10n/app_localizations.dart';

// --- 1. IMPORT flutter_dotenv ---
import 'package:flutter_dotenv/flutter_dotenv.dart';

// --- 2. IMPORT THE NEW MQTT SERVICE ---
import 'package:agrisense/services/mqtt_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // --- 3. LOAD the .env file ---
  await dotenv.load(fileName: ".env");

  // --- Your existing code ---
  final dir = await getApplicationDocumentsDirectory();
  await Isar.open(
    [ScanRecordSchema],
    directory: dir.path,
  );

  final prefs = await SharedPreferences.getInstance();
  final String? languageCode = prefs.getString('language_code');

  // --- 4. MODIFY THE MultiProvider BLOCK ---
  runApp(
    MultiProvider(
      providers: [
        // Your existing LanguageProvider
        ChangeNotifierProvider(
            create: (context) => LanguageProvider(languageCode)),

        // Your existing FarmDataProvider
        ChangeNotifierProvider(create: (context) => FarmDataProvider()),

        // --- THIS IS THE FIX ---
        // We create the MQTTService ONCE using 'Provider' instead of 'ProxyProvider'.
        // We use 'context.read' to get the FarmDataProvider that was just
        // created above and pass it to the service.
        Provider<MQTTService>(
          create: (context) => MQTTService(context.read<FarmDataProvider>()),
        ),
      ],
      child: const AgriSenseApp(),
    ),
  );
}

// --- NO CHANGES NEEDED TO THIS CLASS ---
class AgriSenseApp extends StatelessWidget {
  const AgriSenseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<LanguageProvider>(
      builder: (context, languageProvider, child) {
        return MaterialApp(
          title: 'AgriSense',
          title: 'ScanTrail',
          theme: AppTheme.lightTheme,
          debugShowCheckedModeBanner: false,
          locale: languageProvider.appLocale,
          supportedLocales: const [
            Locale('en', ''),
            Locale('hi', ''),
            Locale('ta', ''),
            Locale('bn', ''),
            Locale('te', ''),
            Locale('mr', ''),
            Locale('ur', ''),
            Locale('gu', ''),
            Locale('kn', ''),
            Locale('or', ''),
            Locale('ml', ''),
            Locale('pa', ''),
            Locale('as', ''),
          ],
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: const SplashScreen(),
        );
      },
    );
  }
}