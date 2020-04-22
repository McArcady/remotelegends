project(grpc)

cmake_minimum_required(VERSION 3.13)
if(COMMAND cmake_policy)
  cmake_policy(SET CMP0003 NEW)
endif(COMMAND cmake_policy)

find_package(Protobuf REQUIRED)


set(FILTER df.*.xml)
set(XML_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../dfhack/library/xml)

#
# identify generated files
#
message("Identifying generated proto files...")
execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/list.py
  ${XML_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/proto
  --type proto
  --separator ";"
  --filter ${FILTER}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE GENERATED_PROTOS
)
message("Identifying generated source files...")
execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/list.py
  ${XML_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/include
  --type h
  --separator ";"
  --filter ${FILTER}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE GENERATED_HDRS
)
message("Identifying generated header files...")
execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/list.py
  ${XML_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/src
  --type cpp
  --separator ";"
  --filter ${FILTER}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE GENERATED_SRCS
)

#
# generate proto files
#
file(GLOB GENERATE_INPUT_SCRIPTS *.py ${XML_DIR}/*.xslt)
file(GLOB GENERATE_INPUT_XMLS ${XML_DIR}/${FILTER})

set(PROTOGEN_OUT proto/protogen.out.xml)
if(NOT("${CMAKE_GENERATOR}" STREQUAL Ninja))
    # use BYPRODUCTS instead under Ninja to avoid rebuilds
    list(APPEND PROTOGEN_OUT ${GENERATED_HDRS})
endif()

add_custom_command(
    OUTPUT ${GENERATED_PROTOS} ${GENERATED_SRCS} ${GENERATED_HDRS}
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/protogen.py
        --proto_out ${CMAKE_CURRENT_SOURCE_DIR}/proto
        --cpp_out ${CMAKE_CURRENT_SOURCE_DIR}/src
        --h_out ${CMAKE_CURRENT_SOURCE_DIR}/include
		--quiet
		--exceptions=${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
        ${XML_DIR}
    MAIN_DEPENDENCY ${CMAKE_CURRENT_SOURCE_DIR}/protogen.py
    COMMENT "Generating protobuf files and conversion code"
    DEPENDS ${GENERATE_INPUT_XMLS} ${GENERATE_INPUT_SCRIPTS}
)

#
# generate protobuf code
#
#protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS ${GENERATED_PROTOS})

string(REPLACE ".proto" ".pb.cc" PROJECT_PROTO_SRCS "${GENERATED_PROTOS}")
string(REPLACE ".proto" ".pb.h" PROJECT_PROTO_HDRS "${GENERATED_PROTOS}")
set(PROJECT_PROTO_TMP_FILES "${PROJECT_PROTO_SRCS};${PROJECT_PROTO_HDRS}")
add_custom_command(
    OUTPUT ${PROJECT_PROTO_TMP_FILES}
    COMMAND protoc -I=${CMAKE_CURRENT_SOURCE_DIR}/proto/
        --cpp_out=${CMAKE_CURRENT_SOURCE_DIR}/proto/
        ${GENERATED_PROTOS}
    COMMENT "Generating core protobufs"
    DEPENDS ${GENERATED_PROTOS}
)

#
# compile and link
#
include_directories(${Protobuf_INCLUDE_DIRS})
include_directories(${CMAKE_CURRENT_BINARY_DIR})

# fast-compilation & debugging
add_compile_options("-O0")

add_library(grpc ${PROTO_SRCS} ${PROTO_HDRS} ${PROJECT_PROTO_TMP_FILES})
target_link_libraries(grpc ${Protobuf_LIBRARIES})
