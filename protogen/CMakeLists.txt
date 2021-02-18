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

# target to generate all graphs of dependencies
add_custom_target(dag_all)

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
  string(REGEX REPLACE "df\.(.+)\.xml" "\\1" sname ${fname})
#  message(STATUS ${sname})

  # patch dfhack structures with our filters
  set(export_file "${XML_PATCH_DIR}/${sname}.export")
  if (EXISTS ${export_file})
	set(tmp_xml_file "${XML_BUILD_DIR}/${fname}")
	add_custom_command(
	  OUTPUT ${tmp_xml_file}
	  COMMAND mkdir -p ${XML_BUILD_DIR}
  	  COMMAND ${PYTHON_EXECUTABLE} ${MERGE} ${xml_file} ${export_file} > ${tmp_xml_file}
  	  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
	  COMMENT "Patching ${fname}"
	  MAIN_DEPENDENCY ${MERGE}
	  DEPENDS ${xml_file} ${export_file}
	)
    set_source_files_properties(${tmp_xml_file} PROPERTIES GENERATED TRUE)
  else()
    set(tmp_xml_file "${xml_file}")
  endif()

  # generate .dag file
  set(dag_file ${XML_BUILD_DIR}/${fname}.dag)
  add_custom_command(
	OUTPUT ${dag_file}
	COMMAND ${DEPENDS} ${tmp_xml_file} --plain --separator=';' > ${dag_file}
	COMMENT "Generating dependency graph for ${fname}"
	MAIN_DEPENDENCY ${DEPENDS} ${PARSER_SRCS}
	DEPENDS ${tmp_xml_file}  ${DEPENDS} ${PARSER_SRCS}
  )
  add_custom_target(${fname}.dag DEPENDS ${dag_file})
  set_source_files_properties(${dag_file} PROPERTIES GENERATED TRUE)
  add_dependencies(dag_all ${fname}.dag)
    
endforeach()

# generate global .dag file
set(dag_file ${XML_PATCH_DIR}/df-structures.dag)
add_custom_target(
  df-structures.dag
  COMMAND cat ${XML_BUILD_DIR}/df.*.xml.dag > ${dag_file}
  COMMENT "Generating global dependency graph"
  DEPENDS dag_all
)
