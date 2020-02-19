# Polyglot v2 Total Connect v2

## Description
This project is a node server to integrate Honeywell Total Connect v2 security systems into the UDI ISY. It is designed to run in UDI's [Polyglot v2](https://github.com/UniversalDevicesInc/polyglot-v2) server.

## Requirements
* [Total Connect v2](https://totalconnect2.com/) Subscription and login.
* total-connect-client python library

## Installation
* Clone into your polyglot nodeservers directory.
* Run install.sh to install dependencies
* Update the user/password in the configuration and restart the node server

### Credentials
The credentials needed are the same ones you use to log into the TC2 website at https://totalconnect2.com.

The configuration parameters are:

| Parameter |Required?|Description|
| --------- | ------- | --------- |
| user      | yes     | TC2 Username |
| password  | yes     | TC2 Password |
| include_non_bypassable_zones  | no     | True/False - Specifies if non bypassable zones such as fire and police should be included |
| allow_disarming | no | True/False - Specifies if disarming is allowed from the ISY |
| refresh_auth_interval | no | Integer - Number of minutes between refreshing of the authentication token to the TotalConnect2 API |