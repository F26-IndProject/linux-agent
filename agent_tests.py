#!/usr/bin/env python3
"""
User Tests for Linux Activity Agent
Tests cover plugin system, heartbeat functionality, and core agent behavior
"""

import unittest
import json
import os
import sys
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_agent_heartbeat import (
    HeartbeatManager, 
    ConfigManager, 
    ActivityUtils,
    EnhancedActivityAgent,
    DEFAULT_USER_CONFIG,
    HEARTBEAT_CONFIG
)
from plugin_manager import PluginManager, ApplicationPlugin


class TestPluginManager(unittest.TestCase):
    """Tests for the Plugin Manager functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_manager = PluginManager(self.temp_dir)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_plugin_directory_creation(self):
        """Test that plugin directories are created correctly"""
        self.assertTrue(os.path.exists(self.temp_dir))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "configs")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "scripts")))
    
    def test_load_plugin_from_json(self):
        """Test loading a plugin from JSON configuration"""
        config = {
            "app_info": {
                "name": "TestApp",
                "display_name": "Test Application"
            },
            "execution": {
                "open_command": "test_app",
                "close_command": "pkill test_app"
            },
            "activities": [{
                "id": "test_activity",
                "name": "Test Activity",
                "commands": [{"type": "wait", "time": 1}]
            }]
        }
        
        config_file = os.path.join(self.temp_dir, "configs", "test_app.json")
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        plugin = self.plugin_manager.load_plugin_from_json(config_file)
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.get_name(), "TestApp")
        self.assertEqual(plugin.get_display_name(), "Test Application")
    
    def test_scan_and_load_plugins(self):
        """Test scanning directory and loading all plugins"""
        # Create multiple test plugins
        for i in range(3):
            config = {
                "app_info": {"name": f"App{i}"},
                "execution": {"open_command": f"app{i}"}
            }
            config_file = os.path.join(self.temp_dir, "configs", f"app{i}.json")
            with open(config_file, 'w') as f:
                json.dump(config, f)
        
        self.plugin_manager.scan_and_load_plugins()
        plugins = self.plugin_manager.get_all_plugins()
        
        self.assertEqual(len(plugins), 3)
        self.assertIn("App0", plugins)
        self.assertIn("App1", plugins)
        self.assertIn("App2", plugins)
    
    def test_create_plugin_template(self):
        """Test creating a new plugin template"""
        template_path = self.plugin_manager.create_plugin_template("NewApp")
        self.assertTrue(os.path.exists(template_path))
        
        with open(template_path, 'r') as f:
            template = json.load(f)
        
        self.assertEqual(template["app_info"]["name"], "NewApp")
        self.assertIn("activities", template)
        self.assertIn("execution", template)
    
    def test_validate_plugin_config(self):
        """Test plugin configuration validation"""
        # Valid config
        valid_config = os.path.join(self.temp_dir, "valid.json")
        with open(valid_config, 'w') as f:
            json.dump({
                "app_info": {"name": "ValidApp"},
                "execution": {"open_command": "valid"},
                "activities": [{"commands": []}]
            }, f)
        
        errors = self.plugin_manager.validate_plugin_config(valid_config)
        self.assertEqual(len(errors), 0)
        
        # Invalid config - missing required fields
        invalid_config = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_config, 'w') as f:
            json.dump({"app_info": {}}, f)
        
        errors = self.plugin_manager.validate_plugin_config(invalid_config)
        self.assertGreater(len(errors), 0)


class TestHeartbeatManager(unittest.TestCase):
    """Tests for Heartbeat functionality"""
    
    def setUp(self):
        self.user_config = DEFAULT_USER_CONFIG.copy()
        self.mock_agent = Mock()
        self.heartbeat_manager = HeartbeatManager(self.user_config, self.mock_agent)
    
    def test_heartbeat_data_preparation(self):
        """Test that heartbeat data is prepared correctly"""
        data = self.heartbeat_manager._prepare_heartbeat_data()
        
        # Check required fields
        self.assertIn('timestamp', data)
        self.assertIn('agent_id', data)
        self.assertIn('username', data)
        self.assertIn('role', data)
        self.assertIn('department', data)
        self.assertIn('location', data)
        self.assertIn('system_info', data)
        self.assertIn('status', data)
        
        # Verify data values
        self.assertEqual(data['agent_id'], 'USR0012345')
        self.assertEqual(data['username'], 'john_doe')
        self.assertEqual(data['role'], 'Junior Developer')
        self.assertEqual(data['status'], 'active')
    
    def test_system_info_collection(self):
        """Test system information collection"""
        system_info = self.heartbeat_manager._collect_system_info()
        
        self.assertIn('hostname', system_info)
        self.assertIn('platform', system_info)
        self.assertIn('python_version', system_info)
        self.assertIn('cpu_count', system_info)
        self.assertIn('agent_version', system_info)
        
        self.assertEqual(system_info['agent_version'], '1.0.0')
        self.assertIsInstance(system_info['cpu_count'], int)
    
    @patch('urllib.request.urlopen')
    def test_heartbeat_sending(self, mock_urlopen):
        """Test sending heartbeat to backend"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = self.heartbeat_manager._send_heartbeat()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.heartbeat_manager.last_heartbeat_time)
        
        # Verify the request was made correctly
        mock_urlopen.assert_called_once()
        call_args = mock_urlopen.call_args[0][0]
        
        self.assertEqual(call_args.get_method(), 'POST')
        self.assertEqual(call_args.get_full_url(), 'http://localhost:8000/api/agents/heartbeat')
        self.assertIn('Authorization', call_args.headers)
        self.assertEqual(call_args.headers['Authorization'], 'Bearer sk-agent-heartbeat-key-2024')
    
    @patch('urllib.request.urlopen')
    def test_heartbeat_retry_mechanism(self, mock_urlopen):
        """Test that heartbeat retries on failure"""
        # Mock failed responses
        mock_urlopen.side_effect = Exception("Connection error")
        
        result = self.heartbeat_manager._send_heartbeat()
        
        self.assertFalse(result)
        # Should have tried 3 times (retry_count)
        self.assertEqual(mock_urlopen.call_count, 3)


class TestApplicationPlugin(unittest.TestCase):
    """Tests for Application Plugin base class"""
    
    def setUp(self):
        self.config = {
            "app_info": {"name": "TestApp", "display_name": "Test Application"},
            "installation": {
                "check_command": "which test_app",
                "install_commands": ["echo 'Installing test_app'"]
            },
            "execution": {
                "open_command": "test_app",
                "close_command": "pkill test_app",
                "startup_delay": 2
            },
            "activities": [{
                "id": "test_activity",
                "name": "Test Activity",
                "weight": 10,
                "commands": [
                    {"type": "wait", "time": 1},
                    {"type": "key", "key": "Return"}
                ]
            }],
            "settings": {
                "session_duration": {"min": 60, "max": 120},
                "usage_probability": 0.7
            }
        }
        self.plugin = ApplicationPlugin(self.config)
    
    def test_plugin_initialization(self):
        """Test plugin is initialized correctly"""
        self.assertEqual(self.plugin.get_name(), "TestApp")
        self.assertEqual(self.plugin.get_display_name(), "Test Application")
        self.assertFalse(self.plugin.is_running)
        self.assertIsNone(self.plugin.current_activity)
    
    @patch('subprocess.run')
    def test_is_installed_check(self, mock_run):
        """Test checking if application is installed"""
        mock_run.return_value.returncode = 0
        self.assertTrue(self.plugin.is_installed())
        
        mock_run.return_value.returncode = 1
        self.assertFalse(self.plugin.is_installed())
    
    @patch('subprocess.run')
    def test_execute_activity_command(self, mock_run):
        """Test executing different activity command types"""
        mock_run.return_value.returncode = 0
        
        # Test key combination
        self.plugin.execute_activity_command({
            "type": "key_combination",
            "keys": "ctrl+c"
        })
        mock_run.assert_called_with("xdotool key ctrl+c", shell=True, capture_output=True, text=True)
        
        # Test typing text
        self.plugin.execute_activity_command({
            "type": "type_text",
            "text": "Hello World"
        })
        mock_run.assert_called_with("xdotool type 'Hello World'", shell=True, capture_output=True, text=True)
    
    def test_get_weighted_activity(self):
        """Test activity selection based on weights"""
        # Add more activities with different weights
        self.plugin.activities.append({
            "id": "heavy_activity",
            "name": "Heavy Activity",
            "weight": 90,  # Much higher weight
            "commands": []
        })
        
        # Run multiple times and check distribution
        activities = []
        for _ in range(100):
            activity = self.plugin.get_weighted_activity()
            activities.append(activity['name'])
        
        # Heavy activity should appear more often
        heavy_count = activities.count("Heavy Activity")
        test_count = activities.count("Test Activity")
        
        self.assertGreater(heavy_count, test_count)


class TestEnhancedActivityAgent(unittest.TestCase):
    """Tests for the main Enhanced Activity Agent"""
    
    def setUp(self):
        self.config = DEFAULT_USER_CONFIG.copy()
        self.agent = EnhancedActivityAgent(self.config)
    
    def test_agent_initialization(self):
        """Test agent is initialized correctly"""
        self.assertIsNone(self.agent.current_app)
        self.assertIsNone(self.agent.current_plugin)
        self.assertIsNotNone(self.agent.plugin_manager)
        self.assertIsNotNone(self.agent.heartbeat_manager)
    
    def test_get_available_applications(self):
        """Test getting list of available applications"""
        apps = self.agent.get_available_applications()
        
        # Should include at least the default applications
        self.assertIn("Visual Studio Code", apps)
        self.assertIn("leafpad", apps)
    
    @patch('subprocess.run')
    def test_open_close_application(self, mock_run):
        """Test opening and closing applications"""
        mock_run.return_value.returncode = 0
        
        # Test opening
        result = self.agent.open_application("leafpad")
        self.assertTrue(result)
        self.assertEqual(self.agent.current_app, "leafpad")
        
        # Test closing
        self.agent.close_application("leafpad")
        self.assertIsNone(self.agent.current_app)
    
    def test_should_switch_app(self):
        """Test logic for switching applications"""
        # Initially should switch (no current app)
        self.assertTrue(self.agent.should_switch_app())
        
        # Set current app
        self.agent.current_app = "TestApp"
        self.agent.app_start_time = time.time()
        self.agent.session_duration = 60  # 1 minute
        
        # Should not switch immediately
        self.assertFalse(self.agent.should_switch_app())
        
        # Simulate time passing
        self.agent.app_start_time = time.time() - 120  # 2 minutes ago
        self.assertTrue(self.agent.should_switch_app())
    
    def test_get_system_statistics(self):
        """Test system statistics collection"""
        stats = self.agent.get_system_statistics()
        
        self.assertIn('agent_uptime', stats)
        self.assertIn('current_app', stats)
        self.assertIn('plugin_mode', stats)
        self.assertIn('total_plugins', stats)
        self.assertIn('available_apps', stats)


class TestActivityUtils(unittest.TestCase):
    """Tests for Activity Utilities"""
    
    def test_is_work_time(self):
        """Test work time detection"""
        work_schedule = {
            "start_time": "09:00",
            "end_time": "17:00",
            "breaks": []
        }
        
        # Test during work hours
        work_time = datetime.strptime("2024-01-15 10:00", "%Y-%m-%d %H:%M")
        self.assertTrue(ActivityUtils.is_work_time(work_time, work_schedule))
        
        # Test outside work hours
        off_time = datetime.strptime("2024-01-15 20:00", "%Y-%m-%d %H:%M")
        self.assertFalse(ActivityUtils.is_work_time(off_time, work_schedule))
    
    def test_is_break_time(self):
        """Test break time detection"""
        work_schedule = {
            "start_time": "09:00",
            "end_time": "17:00",
            "breaks": [{
                "start": "12:00",
                "duration_minutes": 60
            }]
        }
        
        # Test during break
        break_time = datetime.strptime("2024-01-15 12:30", "%Y-%m-%d %H:%M")
        self.assertTrue(ActivityUtils.is_break_time(break_time, work_schedule))
        
        # Test outside break
        work_time = datetime.strptime("2024-01-15 10:00", "%Y-%m-%d %H:%M")
        self.assertFalse(ActivityUtils.is_break_time(work_time, work_schedule))


class TestConfigManager(unittest.TestCase):
    """Tests for Configuration Manager"""
    
    def setUp(self):
        self.config_manager = ConfigManager()
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager.config_paths = [self.temp_dir]
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_config_from_file(self):
        """Test loading configuration from file"""
        test_config = {
            "username": "test_user",
            "work_schedule": {
                "start_time": "08:00",
                "end_time": "16:00"
            },
            "applications_used": ["TestApp"]
        }
        
        config_file = os.path.join(self.temp_dir, "test_config.json")
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        loaded_config = self.config_manager.load_config("test")
        
        self.assertEqual(loaded_config['username'], "test_user")
        self.assertEqual(loaded_config['work_schedule']['start_time'], "08:00")
    
    def test_validate_config(self):
        """Test configuration validation"""
        # Incomplete config
        incomplete_config = {"username": "test"}
        validated = self.config_manager.validate_config(incomplete_config)
        
        # Should have default values filled in
        self.assertIn('work_schedule', validated)
        self.assertIn('applications_used', validated)
        self.assertEqual(validated['username'], "test")


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    @patch('subprocess.run')
    @patch('urllib.request.urlopen')
    def test_agent_with_plugin_and_heartbeat(self, mock_urlopen, mock_run):
        """Test agent running with plugin system and heartbeat"""
        # Setup mocks
        mock_run.return_value.returncode = 0
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Create agent
        config = DEFAULT_USER_CONFIG.copy()
        agent = EnhancedActivityAgent(config)
        
        # Start heartbeat
        agent.heartbeat_manager.start()
        time.sleep(0.1)  # Give heartbeat time to send
        
        # Verify heartbeat was sent
        mock_urlopen.assert_called()
        
        # Test opening application
        result = agent.open_application("leafpad")
        self.assertTrue(result)
        
        # Get statistics
        stats = agent.get_system_statistics()
        self.assertEqual(stats['current_app'], "leafpad")
        
        # Stop heartbeat
        agent.heartbeat_manager.stop()


# Test runner
if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPluginManager))
    suite.addTests(loader.loadTestsFromTestCase(TestHeartbeatManager))
    suite.addTests(loader.loadTestsFromTestCase(TestApplicationPlugin))
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedActivityAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestActivityUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("="*70)
    