project(remotelegends LANGUAGES CXX)

cmake_minimum_required(VERSION 3.13)
if(COMMAND cmake_policy)
  cmake_policy(SET CMP0003 NEW)
endif(COMMAND cmake_policy)


#
# constants
#
set(FILTER        "df.*.xml")
set(XML_DIR       "${dfhack_SOURCE_DIR}/library/xml")
set(XML_PATCH_DIR "${CMAKE_CURRENT_SOURCE_DIR}/xml")

set(XML_BUILD_DIR     "${CMAKE_CURRENT_BINARY_DIR}/xml")
set(PROTO_BUILD_DIR   "${CMAKE_CURRENT_BINARY_DIR}/proto")
set(INCLUDE_BUILD_DIR "${CMAKE_CURRENT_BINARY_DIR}/include")
set(SOURCE_BUILD_DIR  "${CMAKE_CURRENT_BINARY_DIR}/src")


# target to generate all proto files and conversion code (needed since pb dependencies cannot be handled precisely)
add_custom_target(xml_all)
#add_custom_target(proto_all)
add_custom_target(convert_all)

# all cpp files
set(PROJECT_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/remotelegends.cpp")
set(all_libraries "")
set(PLUGIN_PROTO_SRCS "")

#
# identify global types dependencies
#
file(GLOB structures ${XML_PATCH_DIR}/${FILTER})
foreach (diff_file ${structures})

  get_filename_component(filter ${diff_file} NAME)
  if (NOT EXISTS "${XML_DIR}/${filter}")
	continue()
  endif()
  
  # patch dfhack structures with our filters
  set(xml_file "${XML_DIR}/${filter}")
  set(tmp_xml_file "${XML_BUILD_DIR}/${filter}.tmp")
  add_custom_command(
    OUTPUT ${tmp_xml_file}
	COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/protogen/merge.py
	${xml_file} "${XML_PATCH_DIR}/${filter}" > ${tmp_xml_file}
    MAIN_DEPENDENCY ${CMAKE_CURRENT_SOURCE_DIR}/protogen/merge.py
    COMMENT "Patching xml structure ${filter}"
    DEPENDS ${xml_file} "${XML_PATCH_DIR}/${filter}"
  )  

  # identify types in each xml file of df-structures  
  execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/protogen/list.py
	${XML_PATCH_DIR} ${PROTO_BUILD_DIR}
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
#  message(STATUS "${filter}: ${types} exported types")
  
  execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/protogen/list.py
	${XML_PATCH_DIR} ${INCLUDE_BUILD_DIR}
	--type h
	--separator ";"
	--filter ${filter}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE header_files
  )
  execute_process(COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/protogen/list.py
	${XML_PATCH_DIR} ${SOURCE_BUILD_DIR}
	--type cpp
	--separator ";"
	--filter ${filter}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE source_files
  )

  file(GLOB GENERATE_INPUT_SCRIPTS ${CMAKE_CURRENT_SOURCE_DIR}/protogen/*.py ${XML_DIR}/*.xslt)
  
  # generate code from the .xml
  add_custom_command(
    OUTPUT ${proto_files} ${header_files} ${source_files}
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/protogen/protogen.py
    --proto_out ${PROTO_BUILD_DIR}
    --cpp_out ${SOURCE_BUILD_DIR}
    --h_out ${INCLUDE_BUILD_DIR}
	--transform ${XML_DIR}/lower-1.xslt
	--transform ${XML_DIR}/lower-2.xslt
  	--quiet
	# TODO: no need for exceptions.conf ?
  	--exceptions=${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
    ${tmp_xml_file}
    MAIN_DEPENDENCY ${CMAKE_CURRENT_SOURCE_DIR}/protogen/protogen.py
    COMMENT "Generating protobuf messages and conversion code for ${filter}"
    DEPENDS ${tmp_xml_file} ${GENERATE_INPUT_SCRIPTS} ${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
  )

  # define target for all products of this xml file
  string(REGEX REPLACE "/" "_" struct_target ${filter})
  string(REGEX REPLACE "\\." "_" struct_target ${struct_target})
  add_custom_target(${struct_target} DEPENDS ${proto_files} ${header_files} ${source_files})
  add_dependencies(xml_all ${struct_target})
  
  list(APPEND PROJECT_SRCS ${source_files})
  list(APPEND PLUGIN_PROTOS ${proto_files} )
    
endforeach()

# protobuf code for generated .proto
string(REPLACE ".proto" ".pb.cc" proto_sources "${PLUGIN_PROTOS}")
string(REPLACE ".proto" ".pb.h" proto_headers "${PLUGIN_PROTOS}")
set_source_files_properties(${proto_sources} ${proto_headers} PROPERTIES GENERATED TRUE)
set_source_files_properties(${proto_headers} PROPERTIES HEADER_FILE_ONLY TRUE)
list(APPEND PLUGIN_PROTO_SRCS ${proto_sources})

# protobuf of service
list(APPEND PLUGIN_PROTOS "${CMAKE_CURRENT_SOURCE_DIR}/proto/RemoteLegends.proto")
list(APPEND PLUGIN_PROTO_SRCS "${PROTO_BUILD_DIR}/RemoteLegends.pb.cc")

add_custom_command(
  OUTPUT ${PLUGIN_PROTO_SRCS}
  COMMAND protoc-bin
  -I=${PROTO_BUILD_DIR}
  -I=${CMAKE_CURRENT_SOURCE_DIR}/proto
  --cpp_out=${PROTO_BUILD_DIR}
  ${PLUGIN_PROTOS}
  COMMENT "Generating protobuf code for ${PLUGIN_PROTOS}"
  DEPENDS protoc-bin ${PLUGIN_PROTOS}
)
add_custom_target(proto_all DEPENDS ${PLUGIN_PROTO_SRCS})


if(UNIX AND NOT APPLE)
    set(PROJECT_LIBS ${PROJECT_LIBS} SDL)
endif()

message(STATUS "RemoteLegends requires: ${PROJECT_SRCS} ${PLUGIN_PROTO_SRCS}")

#
# compile and link options
#
include_directories(${Protobuf_INCLUDE_DIRS})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${INCLUDE_BUILD_DIR})
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
  DEPENDS convert_all proto_all xml_all
)
