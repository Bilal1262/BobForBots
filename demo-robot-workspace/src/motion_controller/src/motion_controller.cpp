#include "motion_controller/motion_controller.hpp"

#include <algorithm>
#include <functional>
#include <memory>
#include <string>

namespace motion_controller
{

MotionController::MotionController(const rclcpp::NodeOptions & options)
: rclcpp::Node("motion_controller", options)
{
  declare_parameter("max_linear_vel", 0.5);
  declare_parameter("max_angular_vel", 1.0);
  max_linear_vel_ = get_parameter("max_linear_vel").as_double();
  max_angular_vel_ = get_parameter("max_angular_vel").as_double();

  safe_cmd_vel_pub_ = create_publisher<geometry_msgs::msg::Twist>("/safe_cmd_vel", 10);
  cmd_vel_sub_ = create_subscription<geometry_msgs::msg::Twist>(
    "/cmd_vel",
    10,
    [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
      auto out = clampVelocity(*msg);
      safe_cmd_vel_pub_->publish(out);
    });
}

geometry_msgs::msg::Twist MotionController::clampVelocity(const geometry_msgs::msg::Twist & in)
{
  geometry_msgs::msg::Twist out = in;

  // BUG: should use max_linear_vel_ parameter, not hardcoded 0.8
  const double lim_lin = 0.8;
  out.linear.x = std::clamp(in.linear.x, -lim_lin, lim_lin);
  out.linear.y = std::clamp(in.linear.y, -lim_lin, lim_lin);
  out.linear.z = std::clamp(in.linear.z, -lim_lin, lim_lin);

  out.angular.x = std::clamp(in.angular.x, -max_angular_vel_, max_angular_vel_);
  out.angular.y = std::clamp(in.angular.y, -max_angular_vel_, max_angular_vel_);
  out.angular.z = std::clamp(in.angular.z, -max_angular_vel_, max_angular_vel_);

  return out;
}

}  // namespace motion_controller

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<motion_controller::MotionController>());
  rclcpp::shutdown();
  return 0;
}
