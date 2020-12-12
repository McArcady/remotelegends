/*
 * $ antlr4 DfLexer.g4 DfParser.g4  &&  javac -cp /usr/share/java/antlr4-runtime.jar  Df*.java
 * $ for f in  ../../df-structures/df.*.xml; do echo $f && cat $f | grun  Df datadef ; done
 */

parser grammar DfParser;

options { tokenVocab=DfLexer; }

/* data-definition */
datadef	    : '<' DATADEF '>' misc* TEXT? (gtype TEXT? misc*)* '</' DATADEF '>' misc* ;
gtype       : bitfield_type
            | class_type
            | struct_type
		    | enum_type
		    | other_type
		    | XML_COMMENT
		    ;

/* struct/class */
struct_type	: '<' STRUCT_TYPE (attribute misc*)* '>' misc* TEXT? (cfield TEXT? misc*)* '</' STRUCT_TYPE '>'
			| '<' STRUCT_TYPE (attribute misc*)* '/>'
			;
class_type	: '<' CLASS_TYPE (attribute misc*)* '>' misc* TEXT? (cfield TEXT? misc*)* '</' CLASS_TYPE '>'
			| '<' CLASS_TYPE (attribute misc*)* '/>'
			;
cfield		: field TEXT? | vmethods ;
vmethods	: '<' METHODS '>' misc* TEXT? (method TEXT? misc*)* '</' METHODS '>' ;
method		: '<' METHOD attribute* '>' misc* TEXT? (mfield TEXT? misc*)* '</' METHOD '>'
			| '<' METHOD attribute* '/>'
			;
mfield		: field TEXT? | rtype ;
rtype		: '<' RET_TYPE attribute* '>' misc* TEXT? (field TEXT? misc*)* '</' RET_TYPE '>'
			| '<' RET_TYPE attribute* '/>'
			;

/* enum */
enum_type	: '<' ENUM_TYPE attribute* '>' misc* TEXT? (item TEXT? misc*)* '</' ENUM_TYPE '>' ;
item		: '<' ENUM_ITEM attribute* '>' misc* TEXT? (item_attr TEXT? misc*)* '</' ENUM_ITEM '>'
			| '<' ENUM_ITEM attribute* '/>'
			| '<' ENUM_ATTR attribute* '>' misc* content '</' ENUM_ATTR '>'
			| '<' ENUM_ATTR attribute* '/>'
			| comment
			;
item_attr	: '<' ITEM_ATTR attribute* '/>' ;

/* bitfield */
bitfield_type: '<' BITFIELD_TYPE attribute* '>' misc* TEXT? (flag_bit TEXT? misc*)* '</' BITFIELD_TYPE '>' ;
flag_bit	: '<' FLAG_BIT attribute* '>' misc* (comment | TEXT)? misc* '</' FLAG_BIT '>'
			| '<' FLAG_BIT attribute* '/>'
		    | comment
			;

/* other types */
other	    : GLOBAL_TYPE | LINKED_LIST_TYPE | VECTORS_TYPE ;
other_type	: '<' other attribute* '>' misc* TEXT? (field TEXT? misc*)* '</' other '>'
			| '<' other attribute* '/>'
			;

/* field */
field	   : '<' (COMPOUND | CONTAINER | PRIMTAG) attribute* '>' misc* TEXT? (field TEXT? misc*)* '</' (COMPOUND | CONTAINER | PRIMTAG) '>'
		   | '<' (COMPOUND | CONTAINER | PRIMTAG) attribute* '/>'
		   | '<' BITFIELD attribute* '>' misc* TEXT? (flag_bit TEXT? misc*)* '</' BITFIELD '>'
		   | '<' BITFIELD attribute* '/>'
		   | '<' ENUM attribute* '>' misc* TEXT? (item TEXT? misc*)* '</' ENUM '>'
		   | '<' ENUM attribute* '/>'
		   | '<' CODE_HELPER attribute* '>' TEXT '</' CODE_HELPER '>'
		   | comment
		   | XML_COMMENT
		   ;
comment    : '<' COMMENT attribute* '>' TEXT '</' COMMENT '>' ;

/* attribute */
attribute  : (ATTRNAME | RET_TYPE | COMMENT | METHODS) '=' STRING ;

/* misc */
chardata   : TEXT | SEA_WS ;
content    : chardata* ;
misc       : XML_COMMENT | SEA_WS ;
