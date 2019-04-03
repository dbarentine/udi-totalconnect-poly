try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface

from total_connect_client import TotalConnectClient
from enum import Enum

LOGGER = polyinterface.LOGGER


class ZoneStatus(Enum):
    OK = 0
    BYPASSED = 1
    FAULTED = 2
    TROUBLED = 8
    TAMPERED = 16
    FAILED = 32
    ALARM = 256
    UNKNOWN = -1


zoneStatusMap = {
    ZoneStatus.OK: 1,
    ZoneStatus.BYPASSED: 2,
    ZoneStatus.FAULTED: 3,
    ZoneStatus.TROUBLED: 4,
    ZoneStatus.TAMPERED: 5,
    ZoneStatus.FAILED: 6,
    ZoneStatus.ALARM: 7,
    ZoneStatus.UNKNOWN: 8
}


class Zone(polyinterface.Node):

    def __init__(self, controller, primary, address, name, zone_id, tc, loc_name, loc_id):
        super(Zone, self).__init__(controller, primary, address, name)
        self.zone_id = zone_id
        self.tc = tc
        self.loc_name = loc_name
        self.loc_id = loc_id

    def start(self):
        self.query()

    def query(self):
        try:
            LOGGER.debug("Query zone {}".format(self.address))
            self.tc.keep_alive()

            # GetZonesListInStateEx seems to update quicker than GetPanelMetaData...
            # panel_data = self.tc.soapClient.service.GetPanelMetaDataAndFullStatusEx_V1(self.tc.token, self.loc_id, 0, 0, 1)
            # zones = panel_data['PanelMetadataAndStatus']['Zones']['ZoneInfoEx']
            zone_data = self.tc.soapClient.service.GetZonesListInStateEx(self.tc.token, self.loc_id, 1, 0)
            if zone_data.ResultCode != 0:
                LOGGER.warn("Unable to refresh zone, code {} message {}".format(str(zone_data.ResultCode), zone_data.ResultData))
                return

            zones = zone_data.ZoneStatus.Zones.ZoneStatusInfoEx
            filtered_zones = list(filter(lambda zone: zone['ZoneID'] == self.zone_id, zones))

            if len(filtered_zones) > 0:
                zone = filtered_zones[0]
                can_be_bypassed = zone['CanBeBypassed']
                zone_status = zone['ZoneStatus']

                # It might be interesting to display the alarm trigger time but I don't see a data type
                # that I can use for the editors to make that work.
                # Maybe convert to unix time and store as an int
                # if ZoneStatus(zone_status) == ZoneStatus.ALARM:
                #   panel_data = self.tc.soapClient.service.GetPanelMetaDataAndFullStatusEx_V1(self.tc.token, self.loc_id, 0, 0, 1)
                #   panel_zones = panel_data['PanelMetadataAndStatus']['Zones']['ZoneInfoEx']
                #   filtered_panel_zones = list(filter(lambda zone: zone['ZoneID'] == self.zone_id, panel_zones))
                #   panel_zone = filtered_panel_zones[0]
                #   alarm_trigger_time = panel_zone['AlarmTriggerTime']

                self.setDriver('GV0', zoneStatusMap[ZoneStatus(zone_status)])
                self.setDriver('GV1', int(can_be_bypassed))
            else:
                LOGGER.error("No zone was found matching zone id {} in location {}".format(self.zone_id, self.loc_name))
        except Exception as ex:
            LOGGER.error("Refreshing zone {0} failed {1}".format(self.address, ex))
            self.setDriver('GV0', zoneStatusMap[ZoneStatus.UNKNOWN])

        self.reportDrivers()

    drivers = [
        {'driver': 'GV0', 'value': zoneStatusMap[ZoneStatus.UNKNOWN], 'uom': 25},  # Zone Status
        {'driver': 'GV1', 'value': int(False), 'uom': 2},  # Can Be Bypassed
    ]

    id = 'tc_zone'
    commands = {}
