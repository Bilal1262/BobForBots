"""Test that odometry watchdog detects loss from startup and during operation."""

import unittest
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from nav_msgs.msg import Odometry

from odometry_health_monitor.odometry_health_monitor_node import OdometryHealthMonitorNode


class TestOdomLossDetection(unittest.TestCase):
    """Test odometry loss detection scenarios."""

    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        """Create test node and monitor node for each test."""
        self.test_node = Node("test_odom_loss_detection")
        self.monitor_node = OdometryHealthMonitorNode()
        
        # Override parameters for faster testing
        self.monitor_node.set_parameters([
            Parameter("odom_timeout_sec", Parameter.Type.DOUBLE, 0.5),
            Parameter("stop_on_timeout", Parameter.Type.BOOL, True),
        ])
        
        self.received_diagnostics = []
        self.diag_sub = self.test_node.create_subscription(
            DiagnosticArray,
            "/diagnostics",
            self._on_diagnostic,
            10,
        )

    def tearDown(self):
        """Clean up nodes."""
        self.test_node.destroy_node()
        self.monitor_node.destroy_node()

    def _on_diagnostic(self, msg: DiagnosticArray) -> None:
        """Store received diagnostic messages."""
        self.received_diagnostics.append(msg)

    def _spin_for(self, duration_sec: float) -> None:
        """Spin both nodes for specified duration."""
        start = time.time()
        while time.time() - start < duration_sec:
            rclpy.spin_once(self.monitor_node, timeout_sec=0.01)
            rclpy.spin_once(self.test_node, timeout_sec=0.01)

    def test_detects_no_odometry_from_startup(self):
        """Test that watchdog reports ERROR when no odometry is ever received."""
        # Arrange: monitor node is running, no odometry published
        
        # Act: wait for watchdog timer to tick (1.0s timer + 0.5s timeout)
        self._spin_for(1.5)
        
        # Assert: should have received at least one ERROR diagnostic
        self.assertGreater(len(self.received_diagnostics), 0, 
                          "No diagnostics received")
        
        error_diagnostics = [
            diag for diag in self.received_diagnostics
            if any(s.level == DiagnosticStatus.ERROR for s in diag.status)
        ]
        
        self.assertGreater(len(error_diagnostics), 0,
                          "Watchdog failed to detect missing odometry from startup")
        
        # Verify the error message
        error_status = error_diagnostics[0].status[0]
        self.assertEqual(error_status.name, "odometry_health")
        self.assertEqual(error_status.message, "odometry stale")

    def test_detects_odometry_loss_after_initial_messages(self):
        """Test that watchdog detects when odometry stops after initial messages."""
        # Arrange: publish some odometry messages
        odom_pub = self.test_node.create_publisher(Odometry, "/odom", 10)
        
        # Publish 3 odometry messages
        for _ in range(3):
            odom_pub.publish(Odometry())
            self._spin_for(0.1)
        
        # Clear any diagnostics received so far
        self.received_diagnostics.clear()
        
        # Act: stop publishing odometry and wait for timeout
        self._spin_for(1.5)
        
        # Assert: should detect the loss
        error_diagnostics = [
            diag for diag in self.received_diagnostics
            if any(s.level == DiagnosticStatus.ERROR for s in diag.status)
        ]
        
        self.assertGreater(len(error_diagnostics), 0,
                          "Watchdog failed to detect odometry loss after initial messages")

    def test_recovers_when_odometry_resumes(self):
        """Test that watchdog returns to OK when odometry resumes."""
        # Arrange: start with no odometry (ERROR state)
        self._spin_for(1.5)
        self.received_diagnostics.clear()
        
        # Act: start publishing odometry
        odom_pub = self.test_node.create_publisher(Odometry, "/odom", 10)
        for _ in range(5):
            odom_pub.publish(Odometry())
            self._spin_for(0.2)
        
        # Assert: should receive OK diagnostics
        ok_diagnostics = [
            diag for diag in self.received_diagnostics
            if any(s.level == DiagnosticStatus.OK for s in diag.status)
        ]
        
        self.assertGreater(len(ok_diagnostics), 0,
                          "Watchdog failed to recover when odometry resumed")


if __name__ == "__main__":
    unittest.main()

# Made with Bob
