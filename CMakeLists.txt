project(grpc LANGUAGES CXX)

cmake_minimum_required(VERSION 3.13)
if(COMMAND cmake_policy)
  cmake_policy(SET CMP0003 NEW)
endif(COMMAND cmake_policy)

find_package(Protobuf REQUIRED)


set(FILTER df.*.xml)
set(DFHACK_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../dfhack)
set(XML_DIR ${DFHACK_DIR}/library/xml)


#
# compile and link
#
include_directories(${Protobuf_INCLUDE_DIRS})
#include_directories(${CMAKE_CURRENT_BINARY_DIR})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/proto)
include_directories(${DFHACK_DIR}/library/include)

# fast-compilation & debugging
add_compile_options("-O0")
add_definitions(-DLINUX_BUILD)


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

  # code generation
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

  # generate protobuf code
  string(REPLACE ".proto" ".pb.cc" proto_sources "${proto_files}")
  string(REPLACE ".proto" ".pb.h" proto_headers "${proto_files}")
  add_custom_command(
    OUTPUT ${proto_sources} ${proto_headers}
    COMMAND protoc -I=${CMAKE_CURRENT_SOURCE_DIR}/proto/
    --cpp_out=${CMAKE_CURRENT_SOURCE_DIR}/proto/
    ${proto_files}
    COMMENT "Generating core protobufs"
    DEPENDS ${proto_files}
  )

  # define target for the protobuf code
  add_custom_target(proto_${struct_target} DEPENDS ${proto_sources} ${proto_headers})

  # define target for each convertible type
  foreach(cpp_file ${source_files})
	get_filename_component(my_target ${cpp_file} NAME)
	string(REGEX REPLACE ".cpp" "" my_target ${my_target})
	string(REGEX REPLACE "/" "_" my_target ${my_target})
	string(REGEX REPLACE "\\." "_" my_target ${my_target})
	add_custom_target(convert_${my_target}
	  DEPENDS ${cpp_file} proto_${struct_target}
	)

    add_library(${my_target} ${cpp_file})
	add_dependencies(${my_target} convert_${my_target})
	target_link_libraries(${my_target} ${Protobuf_LIBRARIES})
  endforeach()
  
endforeach()
