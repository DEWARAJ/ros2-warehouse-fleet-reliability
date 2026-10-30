cmake_minimum_required(VERSION 3.8)
project(warehouse_fleet_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/RobotHealth.msg"
  "msg/FleetIncident.msg"
  "action/ExecuteMission.action"
  DEPENDENCIES builtin_interfaces
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
