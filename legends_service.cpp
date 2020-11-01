#include <iostream>
#include <memory>
#include <string>

#include <grpcpp/grpcpp.h>
#include <grpcpp/health_check_service_interface.h>
#include <grpcpp/ext/proto_server_reflection_plugin.h>
#include "legends_service.grpc.pb.h"
#include "world_landmass.h"
#include "df/world_landmass.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;
using legends::world_landmass_request;
using legends::world_landmass_response;
using legends::legends_service;

// remove this when converting service to df-plugin
std::vector<df::world_landmass*>& df::world_landmass::get_vector() {
	static std::vector<df::world_landmass*> v;
	return v;
}

// Logic and data behind the server's behavior.
class LegendsServiceImpl final : public legends::legends_service::Service {
	Status get_world_landmass(ServerContext* context,
							  const world_landmass_request* request,
							  world_landmass_response* response) {
		for (auto lm : df::world_landmass::get_vector()) {
			DFProto::describe_world_landmass(response->add_all(), lm);
		}
		return Status::OK;
	}
};

/*
  Test the service with client grpcc:
  $ npm install grpcc
  $ nodejs ./node_modules/.bin/grpcc -d proto/ -p legends_service.proto -a localhost:50051 -i
  $ legends_service@localhost:50051> client.getWorldLandmass({}, printReply)
*/

int main(int argc, char** argv) {

  std::string server_address("0.0.0.0:50051");
  LegendsServiceImpl service;

  grpc::EnableDefaultHealthCheckService(true);
  grpc::reflection::InitProtoReflectionServerBuilderPlugin();
  ServerBuilder builder;
  // Listen on the given address without any authentication mechanism.
  builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
  // Register "service" as the instance through which we'll communicate with
  // clients. In this case it corresponds to an *synchronous* service.
  builder.RegisterService(&service);
  // Finally assemble the server.
  std::unique_ptr<Server> server(builder.BuildAndStart());
  std::cout << "Server listening on " << server_address << std::endl;

  // Wait for the server to shutdown. Note that some other thread must be
  // responsible for shutting down the server for this call to ever return.
  server->Wait();

  return 0;
}
