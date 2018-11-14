#!/usr/bin/env python3

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import os
from total_connect_client import TotalConnectClient
from security_panel_node import SecurityPanel

LOGGER = polyinterface.LOGGER


class Controller(polyinterface.Controller):
    """
    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot for the controller Node
    self.added: Boolean Confirmed added to ISY as primary node
    self.config: Dictionary, this node's Config

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node, update = False): Adds Node to self.nodes and polyglot/ISY. This is called
        for you on the controller itself. Update = True overwrites the existing Node data.
    updateNode(polyinterface.Node): Overwrites the existing node data here and on Polyglot.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    getDriver('ST'): gets the current value from Polyglot for driver 'ST' returns a STRING, cast as needed
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = "Total Connect Controller"
        self.user = ""
        self.password = ""
        self.tc = None

        # Don't enable in deployed node server. I use these so I can run/debug directly in IntelliJ.
        # LOGGER.debug("Profile Num: " + os.environ.get('PROFILE_NUM'))
        # LOGGER.debug("MQTT Host: " + os.environ.get('MQTT_HOST'))
        # LOGGER.debug("MQTT Port: " + os.environ.get('MQTT_PORT'))
        # LOGGER.debug("Token: " + os.environ.get('TOKEN'))

    def start(self):
        LOGGER.info('Started Total Connect Nodeserver')
        if self.check_params():
            self.discover()
            self.setDriver('ST', 1)

    def shortPoll(self):
        self.query()

    def longPoll(self):
        pass

    def query(self):
        for node in self.nodes:
            if self.nodes[node] is not self:
                self.nodes[node].query()

            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        try:
            # If this is a re-discover than update=True
            update = len(args) > 0

            self.tc = TotalConnectClient.TotalConnectClient(self.user, self.password)
            self.tc.get_zone_status()
            for location in self.tc.locations:
                for device in location['DeviceList']['DeviceInfoBasic']:
                    name = device['DeviceName']
                    if name in TotalConnectClient.VALID_DEVICES:
                        loc = location['LocationName']
                        device_addr = "panel_" + str(device['DeviceID'])
                        self.addNode(SecurityPanel(self, device_addr, device_addr, loc + " - " + name, self.tc, loc), update)
        except Exception as ex:
            self.addNotice({'discovery_failed': 'Discovery failed please check logs for a more detailed error.'})
            LOGGER.error("Discovery failed with error {0}".format(ex))

    def delete(self):
        LOGGER.info('Total Connect NS Deleted')

    def stop(self):
        LOGGER.debug('Total Connect NS stopped.')

    def check_params(self):
        if 'user' in self.polyConfig['customParams']:
            self.user = self.polyConfig['customParams']['user']
        else:
            LOGGER.error('check_params: user not defined in customParams, please add it.  Using {}'.format(self.user))

        if 'password' in self.polyConfig['customParams']:
            self.password = self.polyConfig['customParams']['password']
        else:
            LOGGER.error('check_params: password not defined in customParams, please add it.  Using {}'.format(self.password))

        # Make sure they are in the params
        self.addCustomParam({'password': self.password, 'user': self.user})

        # Remove all existing notices
        self.removeNoticesAll()
        # Add a notice if they need to change the user/password from the default.
        if self.user == "" or self.password == "":
            self.addNotice({'mynotice': 'Please set proper user and password in configuration page, and restart this nodeserver'})
            return False
        else:
            return True

    def remove_notices_all(self,command):
        LOGGER.info('remove_notices_all:')
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile(self,command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st

    id = 'controller'
    commands = {
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all
    }

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('TotalConnect')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
