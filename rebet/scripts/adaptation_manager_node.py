#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rebet_msgs.srv import GetQR, GetVariableParams, SetBlackboard
from rcl_interfaces.msg import Parameter
from std_msgs.msg import Float64
from rebet_msgs.msg import AdaptationState, Configuration, QRValue
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from itertools import product
import numpy as np
import sys

ADAP_PERIOD_PARAM = "adaptation_period"




class AdaptationManager(Node):

    def __init__(self):
        super().__init__('adaptation_manager')
        self.publisher_ = self.create_publisher(AdaptationState, 'system_adaptation_state', 10)
     
        self.i = 0
        exclusive_group = MutuallyExclusiveCallbackGroup()
        self.declare_parameter(ADAP_PERIOD_PARAM, 8)
        self.adaptation_period = self.get_parameter(ADAP_PERIOD_PARAM).get_parameter_value().integer_value

        self.timer = self.create_timer(self.adaptation_period, self.timer_callback)
        
        self.cli_qr = self.create_client(GetQR, '/get_qr', callback_group=exclusive_group)
        self.cli_var = self.create_client(GetVariableParams, '/get_variable_params', callback_group=exclusive_group)

        self.cli_sbb = self.create_client(SetBlackboard, '/set_blackboard', callback_group=exclusive_group)

        self.req_sbb = SetBlackboard.Request()
        self.req_sbb.script_code = "average_utility:='"
        self.req_qr = GetQR.Request()
        self.req_var = GetVariableParams.Request()

        self.reporting = [0,0]

        self.bounds_dict = {}


    def dynamic_bounding(self, utility, bounds):
        lower_bound, upper_bound = bounds


        if(utility > upper_bound): upper_bound = utility


        elif(utility < lower_bound): lower_bound = utility

        new_range = upper_bound - lower_bound

        
        # self.get_logger().info("new_range " + str(new_range))
        # self.get_logger().info("new bounds " + str((lower_bound,upper_bound)))
        # self.get_logger().info("bounds " + str(bounds))
        # self.get_logger().info("utility " + str(utility))

        

        result = float((utility - lower_bound)/new_range)

        bounds[0:2] = [lower_bound,upper_bound]

        return result


    def get_system_utility(self):
        self.get_logger().info("Calling QR service client...")
        
        while not self.cli_qr.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        
        response = self.cli_qr.call(self.req_qr)

        self.get_logger().info('Result of QRS in tree ' + str(response.qrs_in_tree))


        weight_sum = sum([qr.weight for qr in response.qrs_in_tree])


        all_the_qrs = []

        for qr in response.qrs_in_tree:
            if qr.qr_name not in self.bounds_dict: self.bounds_dict[qr.qr_name] = [0,0.000000000001]

            normalized_value = self.dynamic_bounding(qr.metric, self.bounds_dict[qr.qr_name])
            self.get_logger().info("Bounds dict: " + str(self.bounds_dict))
            self.get_logger().info("Metric value vs. normalized value " + str(qr.metric) + " vs. " + str(normalized_value))

            qr_val = QRValue()
            qr_val.name = qr.qr_name
            qr_val.qr_fulfilment = (qr.weight/weight_sum) * normalized_value
            all_the_qrs.append(qr_val)

            
        self.reporting[0]+=(np.product([qr.qr_fulfilment for qr in all_the_qrs]))
        self.reporting[1]+=1
        self.req_sbb.script_code+=str(self.reporting[0]/self.reporting[1]) + "'"

        self.get_logger().info(self.req_sbb.script_code)

        res = self.cli_sbb.call(self.req_sbb)
        self.get_logger().info("Put this in the whiteboard for average utility " + str(self.reporting[0]/self.reporting[1]) + " with res " + str(res.success))

        self.req_sbb.script_code = "average_utility:='"
        return all_the_qrs
    
    def get_system_vars(self):
        param_to_node = {}
        self.get_logger().info("Calling VariableParams service client...")
        
        while not self.cli_var.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        
        response = self.cli_var.call(self.req_var)

        self.get_logger().info('get vars Result of it ' + str(response.variables_in_tree))

        possible_configurations = []

        possible_configurations = []
        list_of_list_param = []
        for knob in response.variables_in_tree.variable_parameters:
            decomposed = []
            #knob is a msg of type VariableParameter is name-potential_values pair representing a thing that can change about the current state of the system.
            for pos_val in knob.possible_values:
                param = Parameter()
                param.name = knob.name
                param.value = pos_val
                param_to_node[str((param.name, param.value))] = knob.node_name
                decomposed.append(param)
            list_of_list_param.append(decomposed)
        
        self.get_logger().info('list of list param ' + str(list_of_list_param))
        possible_configurations = list(product(*list_of_list_param))
        #here's where you'd apply constraints to remove invalid configurations
        print(len(possible_configurations))
        print(possible_configurations)
        config_list = []
        for possible_config in possible_configurations:
            if(len(possible_config) != 0):
                possible_config_list = list(possible_config)
                config_msg = Configuration()
                config_msg.node_names = [param_to_node[str((param.name, param.value))] for param in possible_config_list]
                config_msg.configuration_parameters = possible_config
                config_list.append(config_msg)
        #The arms should consists of a list of Parameter, name value pairs of each parameter given.
        return config_list




    def timer_callback(self):        
        #I should probably make functions like these into utilities, like as members of a subclass of Node..




        
        msg = AdaptationState()
        msg.qr_values = self.get_system_utility()
        msg.system_possible_configurations = self.get_system_vars()
        self.publisher_.publish(msg)
        self.get_logger().info('\n\n\nPublishing: "%s"\n\n\n\n\n' % msg)
        self.i += 1

    


    

def main(args=None):
    rclpy.init()

    adapt_manage_node = AdaptationManager()

    mt_executor = MultiThreadedExecutor()
    mt_executor.add_node(adapt_manage_node)
    
    mt_executor.spin()
   

    
    
    adapt_manage_node.destroy_node()
    rclpy.shutdown()



if __name__ == '__main__':
    main()