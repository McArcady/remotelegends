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

set(PROTOGEN "${CMAKE_CURRENT_SOURCE_DIR}/protogen.legacy/protogen.py")
set(MERGE    "${CMAKE_CURRENT_SOURCE_DIR}/protogen.legacy/merge.py")
set(LIST     "${CMAKE_CURRENT_SOURCE_DIR}/protogen.legacy/list.py")

# target to generate all proto files and conversion code (needed since pb dependencies cannot be handled precisely)
add_custom_target(xml_all)
#add_custom_target(proto_all)
add_custom_target(convert_all)

# types to be exported
#set(EXPORTED_TYPES world_landmass world_region world_mountain_peak world_river world_underground_region)

# result of
# $ ./protogen/dependencies.py ../df-structures/df.*.xml  --type   world_landmass world_region world_mountain_peak world_river world_underground_region --separator=';'
# TODO: generate this list from EXPORTED_TYPES using dag.py --ancestors
# TODO: export proto files corresponding to theses types only
set(TYPES "biome_type;coord2d;coord2d_path;feature;feature_alteration;feature_init;language_name;language_name_type;layer_type;part_of_speech;save_version;world_landmass;world_mountain_peak;world_population;world_population_type;world_region;world_region_type;world_river;world_underground_region")

# source files of the generated types
# TODO: generate this list from EXPORTED_TYPES using dag.py --sources
set(XMLS "df.language.xml;df.map.xml;df.version.xml;df.viewscreen.xml;df.world-data.xml")

# build list of generated files
string(REGEX REPLACE "([^;]+)" "${PROTO_BUILD_DIR}/\\1.proto" PLUGIN_PROTOS "${TYPES}")
string(REGEX REPLACE "([^;]+)" "${SOURCE_BUILD_DIR}/\\1.cpp" PROJECT_SRCS "${TYPES}")
list(APPEND PROJECT_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/remotelegends.cpp")


#
# identify global types dependencies
#
file(GLOB structures ${XML_DIR}/${FILTER})
foreach (diff_file ${structures})

  get_filename_component(fname ${diff_file} NAME)
  if (NOT ${fname} IN_LIST XMLS)
	continue()
  endif()
  set(xml_file "${XML_DIR}/${fname}")

  # patch dfhack structures with our filters
  if (EXISTS "${XML_PATCH_DIR}/${fname}")
 	message(STATUS "Patching xml structure ${fname}")
	execute_process(COMMAND mkdir -p ${XML_BUILD_DIR}) 
	set(tmp_xml_file "${XML_BUILD_DIR}/${fname}.tmp")
	execute_process(
  	  COMMAND ${PYTHON_EXECUTABLE} ${MERGE}
  	  ${xml_file} "${XML_PATCH_DIR}/${fname}"
	  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  	  OUTPUT_FILE ${tmp_xml_file}
    )
  else()
    set(tmp_xml_file "${xml_file}")
  endif()

  # identify types in each xml file of df-structures  
  execute_process(
  	COMMAND mkdir -p ${PROTO_BUILD_DIR}
  	COMMAND ${PYTHON_EXECUTABLE} ${LIST}
  	${tmp_xml_file} ${PROTO_BUILD_DIR}
  	--type proto
  	--separator ";"
  	WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  	OUTPUT_VARIABLE proto_files
  )
  if ("${proto_files}" STREQUAL "")
    continue()
  endif()
  list(LENGTH proto_files types)
  message(STATUS "${fname}: ${types} exported types")
  
  execute_process(COMMAND ${PYTHON_EXECUTABLE} ${LIST}
  	${tmp_xml_file} ${INCLUDE_BUILD_DIR}
  	--type h
  	--separator ";"
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE header_files
  )
  execute_process(COMMAND ${PYTHON_EXECUTABLE} ${LIST}
  	${tmp_xml_file} ${SOURCE_BUILD_DIR}
  	--type cpp
  	--separator ";"
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    OUTPUT_VARIABLE source_files
  )

  file(GLOB GENERATE_INPUT_SCRIPTS ${CMAKE_CURRENT_SOURCE_DIR}/protogen.legacy/*.py ${XML_DIR}/*.xslt)
  
  # generate code from the .xml
  add_custom_command(
    OUTPUT ${proto_files} ${header_files} ${source_files}
    COMMAND ${PYTHON_EXECUTABLE} ${PROTOGEN}
    --proto_out ${PROTO_BUILD_DIR}
    --cpp_out ${SOURCE_BUILD_DIR}
    --h_out ${INCLUDE_BUILD_DIR}
	--transform ${XML_DIR}/lower-1.xslt
	--transform ${XML_DIR}/lower-2.xslt
  	--quiet
	# TODO: no need for exceptions.conf ?
  	--exceptions=${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
    ${tmp_xml_file}
    MAIN_DEPENDENCY ${PROTOGEN}
    COMMENT "Generating protobuf messages and conversion code for ${fname}"
    DEPENDS ${GENERATE_INPUT_SCRIPTS} ${CMAKE_CURRENT_SOURCE_DIR}/exceptions.conf
  )

  # define target for all products of this xml file
  string(REGEX REPLACE "/" "_" struct_target ${fname})
  string(REGEX REPLACE "\\." "_" struct_target ${struct_target})
  add_custom_target(${struct_target} DEPENDS ${proto_files} ${header_files} ${source_files})
  add_dependencies(xml_all ${struct_target})
    
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

#message(STATUS "RemoteLegends requires: ${PROJECT_SRCS} ${PLUGIN_PROTO_SRCS}")

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
