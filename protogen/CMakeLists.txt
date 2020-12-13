project(remotelegends LANGUAGES CXX)

cmake_minimum_required(VERSION 3.13)
if(COMMAND cmake_policy)
  cmake_policy(SET CMP0003 NEW)
endif(COMMAND cmake_policy)

#
# constants
#
set(FILTER        "df.*.xml")
set(dfhack_SOURCE_DIR "/home/francois/workspace/df/dfhack")
set(XML_DIR       "${dfhack_SOURCE_DIR}/library/xml")
set(XML_PATCH_DIR "${CMAKE_CURRENT_SOURCE_DIR}/xml")
set(XML_BUILD_DIR "${CMAKE_CURRENT_BINARY_DIR}/xml")

set(ANTLR4   "/usr/bin/antlr4")
set(DEPENDS  "${CMAKE_CURRENT_SOURCE_DIR}/dependencies.py")
set(DAG      "${CMAKE_CURRENT_SOURCE_DIR}/dag.py")
set(MERGE    "${CMAKE_CURRENT_SOURCE_DIR}/merge.py")

# target to generate all proto files and conversion code (needed since pb dependencies cannot be handled precisely)
add_custom_target(dag_all)

# types to be exported
#set(EXPORTED_TYPES world_landmass world_region world_mountain_peak world_river world_underground_region creature_raw)

# result of
# $ ./protogen/dependencies.py ../df-structures/df.*.xml  --type   world_landmass world_region world_mountain_peak world_river world_underground_region --separator=';'
# TODO: generate this list from EXPORTED_TYPES using dag.py --ancestors
# TODO: export proto files corresponding to theses types only
#set(TYPES "biome_type;coord2d;coord2d_path;feature;feature_alteration;feature_init;language_name;language_name_type;layer_type;part_of_speech;save_version;world_landmass;world_mountain_peak;world_population;world_population_type;world_region;world_region_type;world_river;world_underground_region;creature_raw")
set( TYPES "skill_rating;world_mountain_peak;job_skill;body_part_layer_raw;caste_body_info;world_region;world_river;coord2d_path;body_appearance_modifier;material_vec_ref;interaction_source_usage_hint;color_modifier_raw;tissue_style_raw;creature_interaction;world_population;tissue_style_type;caste_attack;creature_interaction_target_flags;coord2d;pronoun_type;gait_info;biome_type;caste_raw;tissue;world_underground_region;part_of_speech;breath_attack_type;world_region_type;item_type;bp_appearance_modifier;appearance_modifier_growth_interval;interaction_effect_location_hint;matter_state;creature_raw;material;world_landmass;body_part_raw;world_population_type;appearance_modifier_type")
# source files of the generated types
# TODO: generate this list from EXPORTED_TYPES using dag.py --sources
#set(XMLS "df.language.xml;df.map.xml;df.version.xml;df.world-data.xml")
set(XMLS "df.creature-raws.xml;df.interaction.xml;df.item-raws.xml;df.language.xml;df.map.xml;df.materials.xml;df.skills.xml;df.units.xml;df.world-data.xml")

#
# build grammar parser
#
set(PARSER_SRCS "DfLexer.interp;DfLexer.py;DfLexer.tokens;DfParser.interp;DfParser.py;DfParser.tokens;DfParserVisitor.py;__init__.py")
list(TRANSFORM PARSER_SRCS PREPEND "${CMAKE_CURRENT_SOURCE_DIR}/parser/")
set(GRAMMAR_SRCS "DfLexer.g4;DfParser.g4")
list(TRANSFORM GRAMMAR_SRCS PREPEND "${CMAKE_CURRENT_SOURCE_DIR}/")
add_custom_command(
  OUTPUT ${PARSER_SRCS}
  COMMAND mkdir -p parser
  COMMAND ${ANTLR4} -o parser -visitor -Dlanguage=Python3 DfLexer.g4 DfParser.g4
  COMMAND touch parser/__init__.py
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  MAIN_DEPENDENCY ${ANTLR4}
  COMMENT "Generating df-structures parser"
  DEPENDS ${GRAMMAR_SRCS}
)

#
# identify global types dependencies
#
file(GLOB structures ${XML_DIR}/${FILTER})
foreach (xml_file ${structures})

  get_filename_component(fname ${xml_file} NAME)

  # patch dfhack structures with our filters
  if (EXISTS "${XML_PATCH_DIR}/${fname}")
	set(tmp_xml_file "${XML_BUILD_DIR}/${fname}.tmp")
	add_custom_command(
	  OUTPUT ${tmp_xml_file}
	  COMMAND mkdir -p ${XML_BUILD_DIR}
  	  COMMAND ${PYTHON_EXECUTABLE} ${MERGE} ${xml_file} "${XML_PATCH_DIR}/${fname}" > ${tmp_xml_file}
  	  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
	  COMMENT "Patching ${fname}"
	  MAIN_DEPENDENCY ${MERGE}
	  DEPENDS ${xml_file} ${XML_PATCH_DIR}/${fname}
	)
  else()
    set(tmp_xml_file "${xml_file}")
  endif()

  # generate .dag file
  set(dag_file ${XML_BUILD_DIR}/${fname}.dag)
  add_custom_command(
	OUTPUT ${dag_file}
	COMMAND ${DEPENDS} ${tmp_xml_file} --plain --separator=';' > ${dag_file}
	COMMENT "Generating dependency graph for ${fname}"
	MAIN_DEPENDENCY ${DEPENDS}
	DEPENDS ${tmp_xml_file}
  )
  add_custom_target(${fname}.dag DEPENDS ${dag_file})
  set_source_files_properties(${dag_file} PROPERTIES GENERATED TRUE)
  add_dependencies(dag_all ${fname}.dag)
    
endforeach()

# generate global .dag file
set(dag_file ${XML_BUILD_DIR}/df-structures.dag)
add_custom_command(
  OUTPUT ${dag_file}
  COMMAND cat ${XML_BUILD_DIR}/df.*.xml.dag > ${dag_file}
  COMMENT "Generating global dependency graph"
  DEPENDS dag_all
)
add_custom_target(df-structures.dag ALL DEPENDS ${dag_file})
set_source_files_properties(${dag_file} PROPERTIES GENERATED TRUE)
