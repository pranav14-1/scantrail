import 'package:agrisense/screens/dashboard_screen.dart';
import 'package:flutter/material.dart';
import 'package:agrisense/screens/capture_screen.dart';
import 'package:agrisense/screens/rover_panel_screen.dart';
import 'package:agrisense/theme/app_theme.dart';
import 'package:animated_bottom_navigation_bar/animated_bottom_navigation_bar.dart';
import 'package:flutter/material.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _bottomNavIndex = 0;

  // List of widgets to display in the body
  final List<Widget> _screens = [
    const DashboardScreen(),
    const CaptureScreen(),
    const RoverPanelScreen(),
  ];

  final iconList = <IconData>[
    Icons.dashboard_outlined,
    Icons.camera_alt_outlined,
    Icons.smart_toy_outlined,
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _bottomNavIndex,
        children: _screens,
      ),
      bottomNavigationBar: AnimatedBottomNavigationBar(
        icons: iconList,
        activeIndex: _bottomNavIndex,
        gapLocation: GapLocation.none,
        notchSmoothness: NotchSmoothness.softEdge,
        onTap: (index) => setState(() => _bottomNavIndex = index),
        activeColor: AppTheme.primaryColor,
        inactiveColor: AppTheme.subTextColor,
        backgroundColor: Colors.white,
        elevation: 8,
        height: 65,
      ),
    );
  }
}
