project(grpc LANGUAGES CXX)

cmake_minimum_required(VERSION 3.13)
if(COMMAND cmake_policy)
  cmake_policy(SET CMP0003 NEW)
endif(COMMAND cmake_policy)


#
# Protobuf & gRPC
#
set(protobuf_MODULE_COMPATIBLE TRUE)
find_package(Protobuf CONFIG REQUIRED)
message(STATUS "Using protobuf ${Protobuf_VERSION}")
set(_PROTOBUF_LIBPROTOBUF protobuf::libprotobuf)
set(_REFLECTION gRPC::grpc++_reflection)
set(_PROTOBUF_PROTOC $<TARGET_FILE:protobuf::protoc>)

find_package(gRPC CONFIG REQUIRED)
message(STATUS "Using gRPC ${gRPC_VERSION}")
set(_GRPC_GRPCPP gRPC::grpc++)
set(_GRPC_CPP_PLUGIN_EXECUTABLE $<TARGET_FILE:gRPC::grpc_cpp_plugin>)


#
# constants
#
set(FILTER df.*.xml)
set(DFHACK_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../dfhack)
set(XML_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../df-structures)


#
# compile and link options
#
include_directories(${Protobuf_INCLUDE_DIRS})
#include_directories(${CMAKE_CURRENT_BINARY_DIR})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/proto)
include_directories(${DFHACK_DIR}/library/include)

# fast-compilation & debugging
add_compile_options("-O0")
add_definitions(-DLINUX_BUILD)

# target to generate all proto files and conversion code (needed since pb dependencies cannot be handled precisely)
add_custom_target(xml_all)
add_custom_target(proto_all)
add_custom_target(convert_all)

# all cpp files
set(all_source_files "")
set(all_libraries "")


#
# identify global types dependencies
#
file(GLOB structures ${XML_DIR}/${FILTER})
foreach (xml_file ${structures})
  get_filename_component(filter ${xml_file} NAME)

  # identify types in each xml file of df-structures  
  execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/list.py
	${XML_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/proto/
	--type proto
	--separator ";"
	--filter ${filter}
	WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
	OUTPUT_VARIABLE proto_files
  )
  if ("${proto_files}" STREQUAL "")
    continue()
  endif()
  list(LENGTH proto_files types)
  message(STATUS "${filter}: ${types} exported types")
  
  execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/list.py
	${XML_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/include
	--type h
	--separator ";"
	--filter ${filter}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE header_files
  )
  execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/list.py
	${XML_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/src
	--type cpp
	--separator ";"
	--filter ${filter}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE source_files
  )

  file(GLOB GENERATE_INPUT_SCRIPTS ${CMAKE_CURRENT_SOURCE_DIR}/*.py ${XML_DIR}/*.xslt)

  # generate code from the .xml
  add_custom_command(
    OUTPUT ${proto_files} ${header_files} ${source_files}
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/protogen.py
    --proto_out ${CMAKE_CURRENT_SOURCE_DIR}/proto
    --cpp_out ${CMAKE_CURRENT_SOURCE_DIR}/src
    --h_out ${CMAKE_CURRENT_SOURCE_DIR}/include
  	--quiet
  	--exceptions=${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
    ${xml_file}
    MAIN_DEPENDENCY ${CMAKE_CURRENT_SOURCE_DIR}/protogen.py
    COMMENT "Generating protobuf files and conversion code for ${filter}"
    DEPENDS ${xml_file} ${GENERATE_INPUT_SCRIPTS} ${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
  )

  # define target for all products of this xml file
  string(REGEX REPLACE "/" "_" struct_target ${filter})
  string(REGEX REPLACE "\\." "_" struct_target ${struct_target})
  add_custom_target(${struct_target} DEPENDS ${proto_files} ${header_files} ${source_files})
  add_dependencies(xml_all ${struct_target})

  # generate protobuf code from each .proto
  foreach(proto_file ${proto_files})
	string(REPLACE ".proto" ".pb.cc" proto_source "${proto_file}")
	string(REPLACE ".proto" ".pb.h" proto_header "${proto_file}")
	add_custom_command(
      OUTPUT ${proto_source} ${proto_header}
	  BYPRODUCTS ${proto_file}.d
      COMMAND ${_PROTOBUF_PROTOC} -I=${CMAKE_CURRENT_SOURCE_DIR}/proto/
      --cpp_out=${CMAKE_CURRENT_SOURCE_DIR}/proto/
	  --dependency_out=${proto_file}.tmp.d
      ${proto_file}
	  COMMAND tail -n +2 ${proto_file}.tmp.d > ${proto_file}.d && rm ${proto_file}.tmp.d
	  DEPFILE ${proto_file}.d
      COMMENT "Generating protobuf code for ${proto_file}"
      DEPENDS ${proto_file}
	)
    # define target for the protobuf code
	get_filename_component(proto_prefix ${proto_file} NAME_WE)
	add_custom_target(proto_${proto_prefix} DEPENDS ${proto_source} ${proto_header})
	add_dependencies(proto_${proto_prefix} ${struct_target})
	add_dependencies(proto_all proto_${proto_prefix} xml_all)
  endforeach()
  
  # define target for each convertible type
  foreach(cpp_file ${source_files})
	get_filename_component(my_target ${cpp_file} NAME)
	string(REGEX REPLACE ".cpp" "" my_target ${my_target})
	string(REGEX REPLACE "/" "_" my_target ${my_target})
	string(REGEX REPLACE "\\." "_" my_target ${my_target})
	
	# define target for the conversion code
	add_custom_target(convert_${my_target} DEPENDS ${cpp_file} proto_${my_target})
    add_dependencies(convert_all convert_${my_target})
	list(APPEND all_source_files ${cpp_file})

	string(REGEX REPLACE ".cpp" ".pb.cc" pb_cc_file ${cpp_file})
	string(REGEX REPLACE "src/" "proto/" pb_cc_file ${pb_cc_file})
    add_library(${my_target}
	  ${cpp_file}
	  ${pb_cc_file}
	)
    add_dependencies(${my_target} convert_${my_target})
    list(APPEND all_libraries ${my_target})
	target_link_libraries(${my_target} ${Protobuf_LIBRARIES})
  endforeach()
  
endforeach()


#
# gRPC service
#

# Service proto file
get_filename_component(hw_proto "${CMAKE_CURRENT_SOURCE_DIR}/legends_service.proto" ABSOLUTE)
get_filename_component(hw_proto_path "${hw_proto}" PATH)

# Generated sources
set(hw_proto_srcs "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.pb.cc")
set(hw_proto_hdrs "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.pb.h")
set(hw_grpc_srcs "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.grpc.pb.cc")
set(hw_grpc_hdrs "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.grpc.pb.h")

add_custom_command(
  OUTPUT "${hw_proto_srcs}" "${hw_proto_hdrs}" "${hw_grpc_srcs}" "${hw_grpc_hdrs}"
  COMMAND ${_PROTOBUF_PROTOC}
  -I=${CMAKE_CURRENT_SOURCE_DIR} -I=${CMAKE_CURRENT_SOURCE_DIR}/proto/
  --grpc_out=${CMAKE_CURRENT_SOURCE_DIR}/proto/
  --cpp_out=${CMAKE_CURRENT_SOURCE_DIR}/proto/
  --plugin=protoc-gen-grpc="${_GRPC_CPP_PLUGIN_EXECUTABLE}"
  "${hw_proto}"
  COMMENT "Generating grpc service"
  DEPENDS "${hw_proto}"
  )

message(STATUS "legends_service requires: ${all_libraries}")
add_executable(legends_service
  ${CMAKE_CURRENT_SOURCE_DIR}/legends_service.cpp
  ${hw_proto_srcs}
  ${hw_grpc_srcs}
)
target_link_libraries(legends_service
  world_landmass
  language_name
  part_of_speech
  ${_REFLECTION}
  ${_GRPC_GRPCPP}
)
add_dependencies(legends_service
  convert_all
  ${all_libraries}
)
