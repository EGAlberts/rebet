#include <cstdio>
#include <chrono>
#include <functional>
#include <memory>
#include <string>

#include "behaviortree_ros2/bt_action_node.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rebet_msgs/action/reactive.hpp"


using namespace BT;




using Reactive = rebet_msgs::action::Reactive;

class ReactiveAction: public RosActionNode<Reactive>
{
public:

  ReactiveAction(const std::string& name,
                  const NodeConfig& conf,
                  const RosNodeParams& params)
    : RosActionNode<Reactive>(name, conf, params)
  {
    std::cout << "Someone made me (a Reactive Action Node) \n\n\n\n\n\n" << std::endl;


  }

  // The specific ports of this Derived class
  // should be merged with the ports of the base class,
  // using RosActionNode::providedBasicPorts()
  static PortsList providedPorts()
  {
    return providedBasicPorts({InputPort<bool>("mission_ongoing", "whether we should cancel our goal.")})
    ;
  }

  // This is called when the TreeNode is ticked and it should
  // send the request to the action server
  bool setGoal(RosActionNode::Goal& goal) override 
  {
    RCLCPP_INFO(node_->get_logger(), "setGoal in ReactiveClient Called");

    return true;
  }
  
  // Callback executed when the reply is received.
  // Based on the reply you may decide to return SUCCESS or FAILURE.
  NodeStatus onResultReceived(const WrappedResult& wr) override
  {
    RCLCPP_INFO(node_->get_logger(), "onResultReceived in ReactiveClient Called");

    return NodeStatus::SUCCESS;
  }

  // Callback invoked when there was an error at the level
  // of the communication between client and server.
  // This will set the status of the TreeNode to either SUCCESS or FAILURE,
  // based on the return value.
  // If not overridden, it will return FAILURE by default.
  virtual NodeStatus onFailure(ActionNodeErrorCode error) override
  {
    RCLCPP_INFO(node_->get_logger(), "onFailure in ReactiveClient Called");

    RCLCPP_ERROR(node_->get_logger(), "Error: %d", error);
    return NodeStatus::FAILURE;
  }

  // we also support a callback for the feedback, as in
  // the original tutorial.
  // Usually, this callback should return RUNNING, but you
  // might decide, based on the value of the feedback, to abort
  // the action, and consider the TreeNode completed.
  // In that case, return SUCCESS or FAILURE.
  // The Cancel request will be send automatically to the server.
  NodeStatus onFeedback(const std::shared_ptr<const Feedback> feedback)
  {
    RCLCPP_INFO(node_->get_logger(), "onFeedback in ReactiveClient Called");
    bool miss_status;
    std::string some_text;
    std::stringstream ss;
    ss << "Feedback received: ";

    ss << feedback->chosen_adaptation;
    // }
    //RCLCPP_INFO(node_->get_logger(), ss.str().c_str());

    getInput("mission_ongoing", miss_status);

    if(!miss_status)
    {
      RCLCPP_INFO(node_->get_logger(), "mission done in reactive action node");

      return NodeStatus::SUCCESS;
    }
    std::stringstream sstwo;

    sstwo << "Port info received: ";
    // for (auto number : feedback->left_time) {
    sstwo << some_text;
    // }
    //RCLCPP_INFO(node_->get_logger(), sstwo.str().c_str());


    return NodeStatus::RUNNING;
  }
};
