project(remotelegends LANGUAGES CXX)

cmake_minimum_required(VERSION 3.13)
if(COMMAND cmake_policy)
  cmake_policy(SET CMP0003 NEW)
endif(COMMAND cmake_policy)


#
# constants
#
set(XML_DIR       "${dfhack_SOURCE_DIR}/library/xml")
set(XML_PATCH_DIR "${CMAKE_CURRENT_SOURCE_DIR}/protogen/xml")

set(XML_BUILD_DIR     "${CMAKE_CURRENT_BINARY_DIR}/protogen/xml")
set(PROTO_BUILD_DIR   "${CMAKE_CURRENT_BINARY_DIR}/proto")
set(HEADER_BUILD_DIR  "${CMAKE_CURRENT_BINARY_DIR}/include")
set(SOURCE_BUILD_DIR  "${CMAKE_CURRENT_BINARY_DIR}/src")

set(methods_inc   "${CMAKE_CURRENT_SOURCE_DIR}/methods.inc")
set(service_proto "${PROTO_BUILD_DIR}/RemoteLegends.proto")

set(DAG      "${CMAKE_CURRENT_SOURCE_DIR}/protogen/dag.py")
set(MERGE    "${CMAKE_CURRENT_SOURCE_DIR}/protogen/merge.py")
set(PROTOGEN "${CMAKE_CURRENT_SOURCE_DIR}/protogen.legacy/protogen.py")
set(LIST     "${CMAKE_CURRENT_SOURCE_DIR}/protogen.legacy/list.py")

# target to generate all proto files and conversion code
add_custom_target(convert_all)

add_subdirectory(protogen)

# types to be exported
# FIXME: missing: historical_entity 
set(EXPORTED_TYPES
	world_landmass world_mountain_peak world_region world_underground_region world_river
	creature_raw world_site world_construction artifact_record historical_figure identity
	entity_population history_event history_event_collection history_era
	written_content poetic_form musical_form dance_form
)
# generate list of types to convert
execute_process(
  COMMAND ${DAG} ${XML_PATCH_DIR}/df-structures.dag
  --ancestors ${EXPORTED_TYPES} --plain --exclude=.*df\..*\.xml[.tmp]* --separator=\;
  OUTPUT_VARIABLE TYPES
  RESULT_VARIABLE rc
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
if(NOT rc EQUAL 0)
    message(FATAL_ERROR "Failed to generate list of exported types")
endif()
# generate list of xml files the define the types to convert
execute_process(
  COMMAND ${DAG} ${XML_PATCH_DIR}/df-structures.dag
  --sources ${EXPORTED_TYPES} --plain --separator=\;
  OUTPUT_VARIABLE XMLS
  RESULT_VARIABLE rc
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
if(NOT rc EQUAL 0)
    message(FATAL_ERROR "Failed to generate list of DF structures")
endif()
message(STATUS "Exported types: ${TYPES}")
#message(STATUS "Compiled structures: ${XMLS}")

# build list of generated files
string(REGEX REPLACE "([^;]+)" "${PROTO_BUILD_DIR}/\\1.proto" PLUGIN_PROTOS "${TYPES}")
string(REGEX REPLACE "([^;]+)" "${SOURCE_BUILD_DIR}/\\1.cpp" PROJECT_SRCS "${TYPES}")
list(APPEND PROJECT_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/remotelegends.cpp")
add_custom_target(main_cpp DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/remotelegends.cpp" ${methods_inc})

#
# identify global types dependencies
#
foreach (xml_file ${XMLS})

  get_filename_component(fname ${xml_file} NAME)

  # identify types for this xml file
  # (use temporarly ":" instead of ";" for command to succeed)
  execute_process(
  	COMMAND ${DAG} ${XML_PATCH_DIR}/df-structures.dag
	--successors ${xml_file} --plain --separator=:
  	OUTPUT_VARIABLE prefixes
  	WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
	)
  string(REPLACE ":" "\;" prefixes ${prefixes})

  string(REGEX REPLACE "([^;]+)" "${PROTO_BUILD_DIR}/\\1.proto" proto_files ${prefixes})
  string(REGEX REPLACE "([^;]+)" "${HEADER_BUILD_DIR}/\\1.h" header_files ${prefixes})
  string(REGEX REPLACE "([^;]+)" "${SOURCE_BUILD_DIR}/\\1.cpp" source_files ${prefixes})
  set_source_files_properties(${proto_files} ${header_files} ${source_files} PROPERTIES GENERATED TRUE)
  set_source_files_properties(${header_files} PROPERTIES HEADER_FILE_ONLY TRUE)
  
  # generate code from the .xml
  file(GLOB GENERATE_INPUT_SCRIPTS ${CMAKE_CURRENT_SOURCE_DIR}/protogen.legacy/*.py ${XML_DIR}/*.xslt)
  set(macros_inc ${SOURCE_BUILD_DIR}/${fname}.inc)
  set(rpc_proto ${PROTO_BUILD_DIR}/${fname}.rpc.proto)
  add_custom_command(
    OUTPUT ${proto_files} ${header_files} ${source_files} ${rpc_proto} ${macros_inc}
    COMMAND ${PYTHON_EXECUTABLE} ${PROTOGEN}
    --proto_out ${PROTO_BUILD_DIR}
    --cpp_out ${SOURCE_BUILD_DIR}
    --h_out ${HEADER_BUILD_DIR}
	--methods ${macros_inc}
	--grpc ${rpc_proto}
	--transform ${XML_DIR}/lower-1.xslt
	--transform ${XML_DIR}/lower-2.xslt
  	--quiet
	# TODO: get rid of exceptions.conf ?
  	--exceptions=${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
    ${xml_file}
    MAIN_DEPENDENCY ${PROTOGEN}
    COMMENT "Generating protobuf messages and conversion code for ${fname}"
    DEPENDS ${xml_file} ${GENERATE_INPUT_SCRIPTS} ${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
	)
  list(APPEND list_methods ${SOURCE_BUILD_DIR}/${fname}.inc)
  list(APPEND list_rpc ${PROTO_BUILD_DIR}/${fname}.rpc.proto)

  # define target for all products of this xml file
  string(REGEX REPLACE "/" "_" struct_target ${fname})
  string(REGEX REPLACE "\\." "_" struct_target ${struct_target})
  add_custom_target(${struct_target} DEPENDS ${proto_files} ${header_files} ${source_files})
  add_dependencies(convert_all ${struct_target})
    
endforeach()

# protobuf code for generated .proto
string(REPLACE ".proto" ".pb.cc" proto_sources "${PLUGIN_PROTOS}")
string(REPLACE ".proto" ".pb.h" proto_headers "${PLUGIN_PROTOS}")
set_source_files_properties(${proto_sources} ${proto_headers} PROPERTIES GENERATED TRUE)
set_source_files_properties(${proto_headers} PROPERTIES HEADER_FILE_ONLY TRUE)
list(APPEND PLUGIN_PROTO_SRCS ${proto_sources})

# protobuf of service methods
add_custom_command(
  OUTPUT ${service_proto}
  COMMAND cat ${CMAKE_CURRENT_SOURCE_DIR}/RemoteLegends.proto.hdr ${list_rpc} > ${service_proto}
  COMMENT "Generating protobuf definition for RPC methods"
  DEPENDS ${list_rpc}
)
list(APPEND PLUGIN_PROTOS "${service_proto}")
list(APPEND PLUGIN_PROTO_SRCS "${PROTO_BUILD_DIR}/RemoteLegends.pb.cc")

# cpp methods macros
add_custom_command(
  OUTPUT ${methods_inc}
  COMMAND echo "/* THIS FILE WAS GENERATED. DO NOT EDIT. */" | cat - ${list_methods} > ${methods_inc}
  COMMENT "Generating macro definition for RPC methods"
  DEPENDS ${list_methods}
)

add_custom_command(
  OUTPUT ${PLUGIN_PROTO_SRCS}
  COMMAND protoc-bin
  -I=${PROTO_BUILD_DIR}
  --cpp_out=${PROTO_BUILD_DIR}
  ${PLUGIN_PROTOS}
  COMMENT "Generating protobuf code for ${PLUGIN_PROTOS}"
  DEPENDS protoc-bin ${PLUGIN_PROTOS}
)
add_custom_target(proto_all DEPENDS ${PLUGIN_PROTO_SRCS})


if(UNIX AND NOT APPLE)
    set(PROJECT_LIBS ${PROJECT_LIBS} SDL)
endif()

#message(STATUS "RemoteLegends requires: ${PROJECT_SRCS} ${PLUGIN_PROTO_SRCS}")

#
# compile and link options
#
include_directories(${Protobuf_INCLUDE_DIRS})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${HEADER_BUILD_DIR})
include_directories(${PROTO_BUILD_DIR})
include_directories(${dfhack_SOURCE_DIR}/library/include)

# fast-compilation & debugging
add_definitions(-DLINUX_BUILD)

dfhack_plugin(RemoteLegends
  ${PROJECT_SRCS}
  ${PLUGIN_PROTO_SRCS}
  LINK_LIBRARIES protobuf-lite ${PROJECT_LIBS}
  COMPILE_FLAGS_MSVC "/FI\"Export.h\""
  COMPILE_FLAGS_GCC "-include Export.h -Wno-misleading-indentation"
  DEPENDS convert_all proto_all df-structures.dag main_cpp
)
