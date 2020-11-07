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
#include "df/world_landmass.h"

#include "include/world_landmass.h"

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
	*out = Translation::TranslateName(in, false);
}

command_result GetWorldLandmassList(color_ostream &stream, const RemoteLegends::MyListRequest *in, RemoteLegends::WorldLandmassList *out)
{
    if (!Core::getInstance().isWorldLoaded()) {
        stream.printerr("No world loaded\n");
        return CR_FAILURE;
    }
	if (!in) {
        stream.printerr("Missing parameters\n");
        return CR_WRONG_USAGE;		
	}
    df::world_data * data = df::global::world->world_data;
	int start = in->has_list_start() ? in->list_start() : 0;
	int end = in->has_list_end() ? in->list_end() : data->landmasses.size()-1;
	if (start<0 || end<start || end>data->landmasses.size()) {
        stream.printerr("Invalid param start=%d/end=%d\n", start, end);
		return CR_WRONG_USAGE;
	}
	auto sublist = std::vector<df::world_landmass*>(&data->landmasses[start], &data->landmasses[end+1]);
    for (auto lm : sublist) {
		DFProto::describe_world_landmass(out->add_landmass_list(), lm);
    }
	stream.print("%d landmasses found\n", sublist.size());
    return CR_OK;	
}

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
    svc->addFunction("GetWorldLandmassList", GetWorldLandmassList);
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
