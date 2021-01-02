#define RL_VERSION "0.0.1"

#include <vector>

#include "Core.h"
#include "DataDefs.h"
#include "Export.h"
#include "Hooks.h"
#include "MiscUtils.h"
#include "PluginManager.h"
#include "RemoteServer.h"

#include "modules/Translation.h"

#include "RemoteLegends.pb.h"

#include "df/world.h"
#include "df/world_data.h"

using namespace DFHack;
using namespace df::enums;
using std::vector;
using std::string;

DFHACK_PLUGIN("RemoteLegends");
REQUIRE_GLOBAL(world);


/* commands processing */

command_result RemoteLegends_version(color_ostream &out, vector<string> &parameters)
{
    out.print(RL_VERSION);
    return CR_OK;
}

void convert_language_name_to_string(const df::language_name* in, string* out) {
	*out = DF2UTF(Translation::TranslateName(in));
}

command_result check_list_request(color_ostream &stream, const RemoteLegends::MyListRequest *in, int max_end, int* startp, int* endp) {
    if (!Core::getInstance().isWorldLoaded()) {
        stream.printerr("No world loaded\n");
        return CR_FAILURE;
    }
	if (!in) {
        stream.printerr("Missing parameters\n");
        return CR_WRONG_USAGE;
	}
	int start = in->has_list_start() ? in->list_start() : 0;
	int end = in->has_list_end() ? in->list_end() : max_end-1;
	if (start<0 || end<start || end>max_end) {
        stream.printerr("Invalid param start=%d/end=%d\n", start, end);
		return CR_WRONG_USAGE;
	}
	*startp = start;
	*endp = end;
	return CR_OK;
}
#define METHOD_GET_LIST(UTYPE, TYPE, VNAME)								\
command_result Get##UTYPE##List(color_ostream &stream, const RemoteLegends::MyListRequest *in, RemoteLegends::UTYPE##List *out) { \
	int start, end;														\
	command_result rc = check_list_request(stream, in, VNAME.size(), &start, &end); \
	if (rc)	{ return rc; }												\
    for (auto elt : std::vector<df::TYPE*>(&VNAME[start], &VNAME[end+1])) {	\
		DFProto::describe_##TYPE(out->add_list(), elt);					\
    }																	\
    return CR_OK;														\
}

#include "methods.inc"

#undef METHOD_GET_LIST
#define DFPROTO_INCLUDED 1


/* plugin control */

DFHACK_PLUGIN_IS_ENABLED(enableUpdates);

DFhackCExport command_result plugin_init (color_ostream &out, std::vector <PluginCommand> &commands)
{
    commands.push_back(PluginCommand("RemoteLegends_version", "List the loaded RemoteLegends version",
									 RemoteLegends_version, false,
									 "This is used for plugin version checking.")
					   );
    enableUpdates = true;
    return CR_OK;
}


DFhackCExport RPCService *plugin_rpcconnect(color_ostream &)
{
    RPCService *svc = new RPCService();

#define METHOD_GET_LIST(UTYPE, TYPE, VNAME) svc->addFunction("Get" #UTYPE "List", Get##UTYPE##List);
#include "methods.inc"
#undef METHOD_GET_LIST

    return svc;
}

DFhackCExport command_result plugin_shutdown (color_ostream &out)
{
    return CR_OK;
}

DFhackCExport command_result plugin_onupdate(color_ostream &out)
{
    return CR_OK;
}
