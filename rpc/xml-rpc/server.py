from xmlrpc.server import SimpleXMLRPCServer

# The actual function the server will run
def get_item_price(item_name):
    inventory = {"laptop": 1200, "phone": 800, "tablet": 400}
    return inventory.get(item_name.lower(), "Item not found")

# Initialize the server
server = SimpleXMLRPCServer(("localhost", 8000))
server.register_function(get_item_price, "check_price")

print("Inventory Server is online. Waiting for XML-RPC calls...")
server.serve_forever()