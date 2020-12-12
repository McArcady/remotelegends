lexer grammar DfLexer;

// Default "mode": Everything OUTSIDE of a tag
XML_COMMENT :   '<!--' .*? '-->' ;
SEA_WS      :   (' '|'\t'|'\r'? '\n')+ ;
OPEN        :   '<'                     -> pushMode(INSIDE) ;
OPEN_SLASH	:	'</'    				-> pushMode(INSIDE) ;
TEXT        :   ~[<]+ ;

// Everything INSIDE of a tag
mode INSIDE;

/* data-definition */
DATADEF		  	: 'data-definition' ;

/* struct/class */
STRUCT_TYPE		: 'struct-type' ;
CLASS_TYPE		: 'class-type' ;
METHODS			: 'virtual-methods' | 'custom-methods' ;
METHOD			: 'vmethod' | 'cmethod' ;
RET_TYPE		: 'ret-type' ;

/* enum */
ENUM_TYPE		: 'enum-type' ;
ENUM			: 'enum' ;
ENUM_ITEM		: 'enum-item' ;
ENUM_ATTR		: 'enum-attr' ;
ITEM_ATTR		: 'item-attr' ;

/* bitfield */
BITFIELD_TYPE	: 'bitfield-type' ;
BITFIELD		: 'bitfield' ;
FLAG_BIT		: 'flag-bit' ;

/* other types */
VECTORS_TYPE	: 'df-other-vectors-type' ;
GLOBAL_TYPE		: 'global-object' ;
LINKED_LIST_TYPE: 'df-linked-list-type' ;

/* field */
COMPOUND	: 'compound' ;
CONTAINER	: 'pointer'
			| 'static-array'
			| 'stl-deque'
			| 'stl-set'
			| 'stl-vector'
			;
PRIMTAG		: 'bool'
			| 'df-array'
			| 'df-flagarray'
			| 'df-linked-list'
			| 'extra-include'
			| 'int8_t'
			| 'int16_t'
			| 'int32_t'
			| 'int64_t'
			| 'long'
			| 'padding'
			| 'ptr-string'
			| 'static-string'
			| 'stl-bit-vector'
			| 'stl-string'
			| 'stl-fstream'
			| 's-float'
			| 'uint8_t'
			| 'uint16_t'
			| 'uint32_t'
			| 'uint64_t'
			;
COMMENT		: 'comment' ;
CODE_HELPER	: 'code-helper' ;

/* attribute */
ATTRNAME	: ~[ \t\r\n/<>"'=]+ ;

/* misc */
CLOSE       :   '>'                     -> popMode ;
SLASH_CLOSE :   '/>'                    -> popMode ;
SLASH       :   '/' ;
EQUALS      :   '=' ;
STRING      :   '"' ~[<"]* '"'
            |   '\'' ~[<']* '\''
            ;
S           :   [ \t\r\n]               -> skip ;
