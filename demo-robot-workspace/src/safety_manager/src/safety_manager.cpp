#include "safety_manager/safety_manager.hpp"

#include <chrono>
#include <functional>
#include <memory>
#include <string>

#include "rclcpp/executors/single_threaded_executor.hpp"

namespace safety_manager
{

SafetyManager::SafetyManager(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("safety_manager", options)
{
}

rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
SafetyManager::on_configure(const rclcpp_lifecycle::State &)
{
  declare_parameter("safety_timeout_sec", 0.5);
  declare_parameter("publish_rate_hz", 10.0);
  publish_rate_hz_ = get_parameter("publish_rate_hz").as_double();

  const auto qos = rclcpp::QoS(rclcpp::KeepLast(1)).reliable();
  safety_status_pub_ = create_lifecycle_publisher<std_msgs::msg::Bool>("/safety_status", qos);

  RCLCPP_INFO(get_logger(), "safety_manager configured");
  return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
}

rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
SafetyManager::on_activate(const rclcpp_lifecycle::State &)
{
  if (!safety_status_pub_) {
    RCLCPP_ERROR(get_logger(), "publisher not created");
    return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::ERROR;
  }
  safety_status_pub_->on_activate();

  // No try/catch around subscription setup (seeded safety-review issue).

  emergency_stop_sub_ = create_subscription<std_msgs::msg::Bool>(
    "/emergency_stop",
    rclcpp::QoS(1),
    std::bind(&SafetyManager::emergency_callback, this, std::placeholders::_1));
  // BUG: should use rclcpp::QoS(1).reliable() for safety critical topic.

  diagnostics_sub_ = create_subscription<diagnostic_msgs::msg::DiagnosticArray>(
    "/diagnostics",
    rclcpp::QoS(1),
    std::bind(&SafetyManager::diagnostics_callback, this, std::placeholders::_1));

  const auto period = rclcpp::Duration::from_nanoseconds(
    static_cast<int64_t>(1e9 / std::max(publish_rate_hz_, 1.0)));
  safety_timer_ = create_wall_timer(
    std::chrono::nanoseconds(period.nanoseconds()),
    std::bind(&SafetyManager::timer_callback, this));

  RCLCPP_INFO(get_logger(), "safety_manager activated");
  return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
}

rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
SafetyManager::on_deactivate(const rclcpp_lifecycle::State &)
{
  safety_timer_.reset();
  emergency_stop_sub_.reset();
  diagnostics_sub_.reset();
  if (safety_status_pub_) {
    safety_status_pub_->on_deactivate();
  }
  return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
}

rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
SafetyManager::on_cleanup(const rclcpp_lifecycle::State &)
{
  safety_status_pub_.reset();
  return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
}

rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn
SafetyManager::on_shutdown(const rclcpp_lifecycle::State &)
{
  safety_timer_.reset();
  emergency_stop_sub_.reset();
  diagnostics_sub_.reset();
  safety_status_pub_.reset();
  return rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn::SUCCESS;
}

void SafetyManager::emergency_callback(const std_msgs::msg::Bool::SharedPtr msg)
{
  emergency_pressed_ = msg->data;
  if (emergency_pressed_) {
    RCLCPP_WARN(get_logger(), "Emergency stop asserted");
  }
}

void SafetyManager::diagnostics_callback(
  const diagnostic_msgs::msg::DiagnosticArray::SharedPtr /*msg*/)
{
  // Placeholder: could aggregate diagnostic levels.
}

void SafetyManager::timer_callback()
{
  if (!safety_status_pub_) {
    return;
  }
  std_msgs::msg::Bool out;
  out.data = !emergency_pressed_;
  safety_status_pub_->publish(out);
}

}  // namespace safety_manager

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::executors::SingleThreadedExecutor exe;
  auto node = std::make_shared<safety_manager::SafetyManager>();
  exe.add_node(node->get_node_base_interface());
  exe.spin();
  rclcpp::shutdown();
  return 0;
}
