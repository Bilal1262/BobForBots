#ifndef MOTION_CONTROLLER__MOTION_CONTROLLER_HPP_
#define MOTION_CONTROLLER__MOTION_CONTROLLER_HPP_

#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp/rclcpp.hpp"

namespace motion_controller
{

class MotionController : public rclcpp::Node
{
public:
  explicit MotionController(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  geometry_msgs::msg::Twist clampVelocity(const geometry_msgs::msg::Twist & in);

  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr safe_cmd_vel_pub_;

  double max_linear_vel_{0.5};
  double max_angular_vel_{1.0};
};

}  // namespace motion_controller

#endif  // MOTION_CONTROLLER__MOTION_CONTROLLER_HPP_
