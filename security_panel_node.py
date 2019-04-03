try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface

from total_connect_client import TotalConnectClient
from enum import Enum

LOGGER = polyinterface.LOGGER


class ArmStatus(Enum):
    DISARMED = 10200
    DISARMED_BYPASS = 10211
    ARMED_AWAY = 10201
    ARMED_AWAY_BYPASS = 10202
    ARMED_AWAY_INSTANT = 10205
    ARMED_AWAY_INSTANT_BYPASS = 10206
    ARMED_CUSTOM_BYPASS = 10223
    ARMED_STAY = 10203
    ARMED_STAY_BYPASS = 10204
    ARMED_STAY_INSTANT = 10209
    ARMED_STAY_INSTANT_BYPASS = 10210
    ARMED_STAY_NIGHT = 10218
    ARMING = 10307
    DISARMING = 10308
    ALARM = 10207
    ALARM_CANCELED = 10213
    UNKNOWN = 0


armStatusMap = {
    ArmStatus.DISARMED: 1,
    ArmStatus.DISARMED_BYPASS: 2,
    ArmStatus.ARMED_AWAY: 3,
    ArmStatus.ARMED_AWAY_BYPASS: 4,
    ArmStatus.ARMED_AWAY_INSTANT: 5,
    ArmStatus.ARMED_AWAY_INSTANT_BYPASS: 6,
    ArmStatus.ARMED_CUSTOM_BYPASS: 7,
    ArmStatus.ARMED_STAY: 8,
    ArmStatus.ARMED_STAY_BYPASS: 9,
    ArmStatus.ARMED_STAY_INSTANT: 10,
    ArmStatus.ARMED_STAY_INSTANT_BYPASS: 11,
    ArmStatus.ARMED_STAY_NIGHT: 12,
    ArmStatus.ARMING: 13,
    ArmStatus.DISARMING: 14,
    ArmStatus.ALARM: 15,
    ArmStatus.ALARM_CANCELED: 16,
    ArmStatus.UNKNOWN: 17
}


class SecurityPanel(polyinterface.Node):

    def __init__(self, controller, primary, address, name, tc, panel_location):
        super(SecurityPanel, self).__init__(controller, primary, address, name)
        self.tc = tc
        self.location = panel_location

    def start(self):
        self.query()

    def armStay(self, command):
        try:
            self.tc.keep_alive()
            self.tc.arm_stay(self.location)
        except Exception as ex:
            LOGGER.error("Arming panel {0} failed {1}".format(self.address, ex))

    def armStayNight(self, command):
        try:
            self.tc.keep_alive()
            self.tc.arm_stay_night(self.location)
        except Exception as ex:
            LOGGER.error("Arming panel {0} failed {1}".format(self.address, ex))

    def armAway(self, command):
        try:
            self.tc.keep_alive()
            self.tc.arm_away(self.location)
        except Exception as ex:
            LOGGER.error("Arming panel {0} failed {1}".format(self.address, ex))

    def query(self):
        try:
            LOGGER.debug("Query zone {}".format(self.address))
            self.tc.keep_alive()
            panel_meta_data = self.tc.get_panel_meta_data(self.location)
            alarm_code = panel_meta_data['PanelMetadataAndStatus']['Partitions']['PartitionInfo'][0]['ArmingState']
            low_battery = panel_meta_data['PanelMetadataAndStatus']['IsInLowBattery']
            ac_loss = panel_meta_data['PanelMetadataAndStatus']['IsInACLoss']

            self.setDriver('GV0', armStatusMap[ArmStatus(alarm_code)])
            self.setDriver('GV1', int(low_battery))
            self.setDriver('GV2', int(ac_loss))
        except Exception as ex:
            LOGGER.error("Refreshing panel {0} failed {1}".format(self.address, ex))
            self.setDriver('GV0', armStatusMap[ArmStatus.UNKNOWN])

        self.reportDrivers()

    drivers = [
        {'driver': 'GV0', 'value': armStatusMap[ArmStatus.UNKNOWN], 'uom': 25},
        {'driver': 'GV1', 'value': int(False), 'uom': 2},
        {'driver': 'GV2', 'value': int(False), 'uom': 2}
    ]

    id = 'tc_panel'
    commands = {
        'ARM_STAY': armStay, 'ARM_STAY_NIGHT': armStayNight, 'ARM_AWAY': armAway
    }
