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
set(XML_DIR ${DFHACK_DIR}/library/xml)


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
add_custom_target(df_all_xml)
add_custom_target(proto_all)
add_custom_target(convert_all)


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

  # how to generate code from the .xml
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
  add_dependencies(df_all_xml ${struct_target})

  # how to generate protobuf code from each .proto
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
	add_dependencies(proto_all proto_${proto_prefix} df_all_xml)
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

	string(REGEX REPLACE ".cpp" ".pb.cc" pb_cc_file ${cpp_file})
	string(REGEX REPLACE "src/" "proto/" pb_cc_file ${pb_cc_file})
    add_library(${my_target}
	  ${cpp_file}
	  ${pb_cc_file}
	)
	add_dependencies(${my_target} convert_${my_target})
	target_link_libraries(${my_target} ${Protobuf_LIBRARIES})
  endforeach()
  
endforeach()


#
# grpc service
#

# Service proto file
get_filename_component(hw_proto "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.proto" ABSOLUTE)
get_filename_component(hw_proto_path "${hw_proto}" PATH)

# Generated sources
set(hw_proto_srcs "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.pb.cc")
set(hw_proto_hdrs "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.pb.h")
set(hw_grpc_srcs "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.grpc.pb.cc")
set(hw_grpc_hdrs "${CMAKE_CURRENT_SOURCE_DIR}/proto/legends_service.grpc.pb.h")

add_custom_command(
  OUTPUT "${hw_proto_srcs}" "${hw_proto_hdrs}" "${hw_grpc_srcs}" "${hw_grpc_hdrs}"
  COMMAND ${_PROTOBUF_PROTOC}
  -I=${CMAKE_CURRENT_SOURCE_DIR}/proto/
  --grpc_out=${CMAKE_CURRENT_SOURCE_DIR}/proto/
  --cpp_out=${CMAKE_CURRENT_SOURCE_DIR}/proto/
  --plugin=protoc-gen-grpc="${_GRPC_CPP_PLUGIN_EXECUTABLE}"
  "${hw_proto}"
  COMMENT "Generating grpc service"
  DEPENDS "${hw_proto}"
  )

#
# A list of dependent cc files can be generated by filtering link-time errors with:
# cat ../COMPILE |grep undefined|grep "dfproto::"|sed 's/^.*dfproto::\([^(:> ]*\).*$/\1/g'|sed 's/_IsValid//g'|sed 's/_default_instance_//g'|grep -v "^_.*"|sort -h|uniq | sed 's/\(.*\)/${CMAKE_CURRENT_SOURCE_DIR}\/proto\/\1.pb.cc/g'
#

add_executable(legends_service
  ${CMAKE_CURRENT_SOURCE_DIR}/src/legends_service.cpp
  ${hw_proto_srcs}
  ${hw_grpc_srcs}
  
  ${CMAKE_CURRENT_SOURCE_DIR}/src/artifact_record.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/entity_event.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/histfig_entity_link.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/histfig_hf_link.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/histfig_site_link.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/historical_figure.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/historical_figure_info.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/historical_kills.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_add_syndromest.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_animatest.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_change_item_qualityst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_change_weatherst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_cleanst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_contactst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_create_itemst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_hidest.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_material_emissionst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_propel_unitst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_resurrectst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_effect_summon_unitst.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/language_name.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/plot_agreement.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/unit_personality.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/world_region.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/world_site.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/world_underground_region.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/abstract_building.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/agreement.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/agreement_details.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/agreement_party.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/coord.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/coord2d.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/coord2d_path.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/creature_interaction_effect.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/cultural_identity.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/entity_site_link.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/feature_alteration.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/feature_init.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_source.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/interaction_target.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/item.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/location_scribe_jobs.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/nemesis_record.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/occupation.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/occupation_sub1.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/property_ownership.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/site_reputation_info.cpp
#${CMAKE_CURRENT_SOURCE_DIR}/src/specific_ref.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/syndrome.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/unit_emotion_memory.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/world_population.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/world_site_inhabitant.cpp
${CMAKE_CURRENT_SOURCE_DIR}/src/world_site_unk130.cpp

  ${CMAKE_CURRENT_SOURCE_DIR}/proto/agreement.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/agreement_details.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/agreement_details_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/agreement_party.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/artifact_record.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/coord.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/coord2d.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/coord2d_path.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/death_condition_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/emotion_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/entity_event.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/entity_event_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/feature_alteration.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/feature_init.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/goal_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/histfig_entity_link.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/histfig_hf_link.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/histfig_site_link.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/historical_figure.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/historical_figure_info.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/historical_kills.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/interaction.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/interaction_effect.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/interaction_effect_location_hint.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/interaction_source.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/interaction_target.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/interaction_target_location_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/item.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/item_flags.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/item_flags2.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/job_skill.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_0.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_1.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_10.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_11.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_12.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_13.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_2.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_3.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_4.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_5.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_6.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_7.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_8.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/knowledge_scholar_flags_9.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/language_name.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/layer_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/need_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/orientation_flags.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/part_of_speech.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/personality_facet_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/plot_agreement.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/plot_role_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/plot_strategy_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/profession.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/reputation_type.pb.cc
  # ${CMAKE_CURRENT_SOURCE_DIR}/proto/specific_ref.pb.cc
  # ${CMAKE_CURRENT_SOURCE_DIR}/proto/specific_ref_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/sphere_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/unit_emotion_memory.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/unit_item_wrestle.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/unit_personality.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/unit_thought_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/vague_relationship_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/value_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/whereabouts_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/world_population.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/world_population_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/world_region.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/world_region_type.pb.cc
  ${CMAKE_CURRENT_SOURCE_DIR}/proto/world_underground_region.pb.cc
)
target_link_libraries(legends_service
  ${_REFLECTION}
  ${_GRPC_GRPCPP}
)
add_dependencies(legends_service
  df_all_xml
  proto_all  
  agreement
  artifact_record
  entity_event
  histfig_entity_link
  histfig_hf_link
  histfig_site_link
  historical_figure
  historical_figure_info
  historical_kills
  interaction
  interaction_effect
  interaction_effect_add_syndromest
  interaction_effect_animatest
  interaction_effect_change_item_qualityst
  interaction_effect_change_weatherst
  interaction_effect_cleanst
  interaction_effect_contactst
  interaction_effect_create_itemst
  interaction_effect_hidest
  interaction_effect_material_emissionst
  interaction_effect_propel_unitst
  interaction_effect_resurrectst
  interaction_effect_summon_unitst
  language_name
  plot_agreement
  unit_personality
  world_region
  world_site
  world_underground_region
)
