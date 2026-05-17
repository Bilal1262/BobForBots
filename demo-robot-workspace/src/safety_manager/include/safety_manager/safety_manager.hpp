#ifndef SAFETY_MANAGER__SAFETY_MANAGER_HPP_
#define SAFETY_MANAGER__SAFETY_MANAGER_HPP_

#include <memory>
#include <string>

#include "diagnostic_msgs/msg/diagnostic_array.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"
#include "rclcpp_lifecycle/lifecycle_publisher.hpp"
#include "std_msgs/msg/bool.hpp"

namespace safety_manager
{

class SafetyManager : public rclcpp_lifecycle::LifecycleNode
{
public:
  explicit SafetyManager(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

  rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
  on_configure(const rclcpp_lifecycle::State & state) override;

  rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
  on_activate(const rclcpp_lifecycle::State & state) override;

  rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
  on_deactivate(const rclcpp_lifecycle::State & state) override;

  rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
  on_cleanup(const rclcpp_lifecycle::State & state) override;

  rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
  on_shutdown(const rclcpp_lifecycle::State & state) override;

private:
  void emergency_callback(const std_msgs::msg::Bool::SharedPtr msg);
  void diagnostics_callback(const diagnostic_msgs::msg::DiagnosticArray::SharedPtr msg);
  void timer_callback();

  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr emergency_stop_sub_;
  rclcpp::Subscription<diagnostic_msgs::msg::DiagnosticArray>::SharedPtr diagnostics_sub_;
  rclcpp_lifecycle::LifecyclePublisher<std_msgs::msg::Bool>::SharedPtr safety_status_pub_;
  rclcpp::TimerBase::SharedPtr safety_timer_;

  bool emergency_pressed_{false};
  double publish_rate_hz_{10.0};
};

}  // namespace safety_manager

#endif  // SAFETY_MANAGER__SAFETY_MANAGER_HPP_
