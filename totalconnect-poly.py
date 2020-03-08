#!/usr/bin/env python3

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import re
import schedule
from distutils.util import strtobool
from total_connect_client import TotalConnectClient
from security_panel_node import SecurityPanel
from zone_node import Zone

LOGGER = polyinterface.LOGGER
VALID_DEVICES = ['Security Panel',
                 'Security System',
                 'L5100-WiFi',
                 'Lynx Touch-WiFi',
                 'ILP5',
                 'LTE-XV',
                 'GSMX4G',
                 'GSMVLP5-4G',
                 '7874i',
                 'GSMV4G',
                 'VISTA-21IP4G'
                 ]


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
        self.include_non_bypassable_zones = "false"
        self.allow_disarming = "false"
        self.refresh_auth_interval = "120"
        self.tc = None
        self.filter_regex = r'[^a-zA-Z0-9_\- \t\n\r\f\v]+'

        # Don't enable in deployed node server. I use these so I can run/debug directly in IntelliJ.
        # LOGGER.debug("Profile Num: " + os.environ.get('PROFILE_NUM'))
        # LOGGER.debug("MQTT Host: " + os.environ.get('MQTT_HOST'))
        # LOGGER.debug("MQTT Port: " + os.environ.get('MQTT_PORT'))
        # LOGGER.debug("Token: " + os.environ.get('TOKEN'))

    def start(self):
        LOGGER.info('Started Total Connect Nodeserver')
        if self.check_params():
            self.discover()

            schedule.every(int(self.refresh_auth_interval)).minutes.do(self.authenticate)
            self.setDriver('ST', 1)

    def shortPoll(self):
        for node in self.nodes:
            if isinstance(self.nodes[node], SecurityPanel):
                self.nodes[node].query()
                self.nodes[node].reportDrivers()

    def longPoll(self):
        schedule.run_pending()
        for node in self.nodes:
            if isinstance(self.nodes[node], Zone):
                self.nodes[node].query()
                self.nodes[node].reportDrivers()

    def query(self):
        for node in self.nodes:
            if self.nodes[node] is not self:
                self.nodes[node].query()
                self.nodes[node].reportDrivers()
            else:
                self.reportDrivers()

    def authenticate(self):
        try:
            LOGGER.info("Re-authenticating")
            self.tc.authenticate()
        except Exception as ex:
            LOGGER.exception("Could not re-authenticate %s", ex)

    def discover(self, *args, **kwargs):
        try:
            LOGGER.debug("Starting discovery")
            # If this is a re-discover than update=True
            update = len(args) > 0

            self.tc = TotalConnectClient.TotalConnectClient(self.user, self.password)
            locations = self.tc.request("GetSessionDetails(self.token, self.applicationId, self.applicationVersion)")["Locations"]["LocationInfoBasic"]
            for location in locations:
                loc_id = location['LocationID']
                loc_name = re.sub(self.filter_regex, '', location['LocationName'])

                LOGGER.debug("Adding devices for location {} with name {}".format(loc_id, loc_name))

                devices = location['DeviceList']['DeviceInfoBasic']

                if devices is None:
                    raise Exception("No devices were found for location {} - {} \n{}".format(loc_name, loc_id, location))

                # Create devices in location
                for device in devices:
                    LOGGER.debug("Found device %s in location %s", device['DeviceName'], loc_name)

                    if device['DeviceName'].lower() == 'automation':
                        continue

                    # Add security devices.
                    # PanelType appears to only show up for security panels
                    if device['DeviceName'] in VALID_DEVICES or 'PanelType' in device['DeviceFlags']:
                        self.add_security_device(loc_id, loc_name, device, update)
                    else:
                        LOGGER.warn("Device {} in location {} is not a valid security device".format(device['DeviceName'], loc_name))

                    # If we wanted to support other device types it would go here
        except Exception as ex:
            self.addNotice({'discovery_failed': 'Discovery failed please check logs for a more detailed error.'})
            LOGGER.exception("Discovery failed with error %s", ex)

    def add_security_device(self, loc_id, loc_name, device, update):
        device_name = re.sub(self.filter_regex, '', device['DeviceName'])
        device_addr = "panel_" + str(device['DeviceID'])
        LOGGER.debug("Adding security device {} with name {} for location {}".format(device_addr, device_name, loc_name))

        self.addNode(SecurityPanel(self, device_addr, device_addr, loc_name + " - " + device_name, self.tc, loc_name, loc_id, bool(strtobool(self.allow_disarming))), update)

        # create zone nodes
        # We are using GetPanelMetaDataAndFullStatusEx_V1 because we want the extended zone info
        panel_data = self.tc.soapClient.service.GetPanelMetaDataAndFullStatusEx_V1(self.tc.token, loc_id, 0, 0, 1)
        if panel_data['ResultCode'] == 0:
            LOGGER.debug("Getting zones for panel {}".format(device_addr))
            zones = panel_data['PanelMetadataAndStatus']['Zones']['ZoneInfoEx']

            if zones is None:
                raise Exception("No zones were found for {} - {} \n{}".format(device_name, device_addr, panel_data))

            for zone in zones:
                if not bool(zone.CanBeBypassed) and not bool(strtobool(self.include_non_bypassable_zones)):
                    LOGGER.debug("Skipping zone {} with name {}".format(zone.ZoneID, zone.ZoneDescription))
                    continue

                self.add_zone(loc_id, loc_name, device_addr, device['DeviceID'], zone, update)
        else:
            LOGGER.warn("Unable to get extended panel information, code {} data {}".format(panel_data["ResultCode"], panel_data["ResultData"]))

    def add_zone(self, loc_id, loc_name, device_addr, device_id, zone, update):
        zone_name = re.sub(self.filter_regex, '', loc_name + " - " + zone.ZoneDescription)
        zone_addr = "z_{}_{}".format(device_id, str(zone.ZoneID))

        LOGGER.debug("Adding zone {} with name {} for location {}".format(zone_addr, zone_name, loc_name))
        self.addNode(Zone(self, device_addr, zone_addr, zone_name, zone.ZoneID, self.tc, loc_name, loc_id), update)

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

        if 'include_non_bypassable_zones' in self.polyConfig['customParams']:
            self.include_non_bypassable_zones = self.polyConfig['customParams']['include_non_bypassable_zones']

        if 'allow_disarming' in self.polyConfig['customParams']:
            self.allow_disarming = self.polyConfig['customParams']['allow_disarming']

        if 'refresh_auth_interval' in self.polyConfig['customParams']:
            self.refresh_auth_interval = self.polyConfig['customParams']['refresh_auth_interval']

        # Make sure they are in the params
        self.addCustomParam({'password': self.password, 'user': self.user, "include_non_bypassable_zones": self.include_non_bypassable_zones, "allow_disarming": self.allow_disarming, "refresh_auth_interval": self.refresh_auth_interval})

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
