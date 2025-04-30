# Enode-for-HA
A custom integration for Homeassistant, to access Enodes API for vehicles. Other devices/assets than vehicles, are not supported by the integration.

PLEASE NOTE that the integration requires production access from Enode to work with real-life vehicles. This is not something that is necessarily granted for single-users - the Enode api is primarily meant for paying enterprises.

Inspired by https://github.com/OldSmurf56/xpeng but I have chosen to make a custom integration instead of using nodered.

The initial setup described by oldsmurf56 is basically the same, I have however made the linksession step easier, as described in step 3 in the enode setup..

Still betaversion and hence still missing some features + translations and have bugs. One of the missing features is the Smart Charging function from the API.


Enode setup
1) Create an enode account.
2) Ask Enode sales if they will give you production access, you will not be able to connect to real devices without. If they accept, you will get access to a limited amount of assets/devices. As noted above - there is no guarantee that Enode will grant single users production access or to continue to offer it for free.
You can however test the integration with the sandbox environment by changing the environment in const.py to "sandbox".
4) Have your enode credentials ready, and use either the instructions here https://developers.enode.com/docs/getting-started or use my simplified process here https://lauridsen.nl/enode/enodelink.php to get the link to the linksession between your vehicles app account and enode. The php file is also uploaded here, so that you can see the code, and can use it in your own webserver if you prefer for privacy concerns.
5) Use the generated url to link your vehicle to enode within 24 hours.


Homeassistant setup
1) Copy full repository directory enodeforha to your homeassistant custom_components folder. If you only have sandbox access, change the environment in const.py.
2) Restart homeassistant
3) Add integration "Enode" the same way you would add other buildin homeassistant integrations (so NOT via HACS)
4) It will ask for clientid and clientsecret for enode
5) It should then show you a list of the vehicles available with that clientid but you can only add one at a time (if you have more)
6) You can now select the sensors you want to add. All sensors offered by Enode are included, but not all sensors contain data from all vehicles, eg Xpeng does not provide odometer. That's why the select sensors option is provided, so you can disable eg Odometer for Xpeng. Currently the select function is not available after configuration of the vehicle, so you will have to remove and then add the vehicle again, if you want to change sensor selection. For now the smart charge function is not working, and will throw an error if you use it, so simply deselect that sensor when installing.
7) There is also an option to change the data refresh interval. This can also be changed for each vehicle after configuration, but the change will only be applied after reload of the integration. 
Enode does not currently have a rate limit to their API, however it seems that the connection between vehicle and enode does not necessarily refresh data very often, so consider this before you choose 5 seconds, because it is unnecessary if the vehicle data are only updated every 10 minutes. 
8) The debug notifications options is only meant to be used if sensordata are not received or are incorrect. What it does is that it enables a notification in HomeAssistant, that provides the raw json response from the api request. The notification will only be sent every 10 minutes. This can also be activated/deactivated for each vehicle after configuration, but the activation/deactivation will only be applied after reload of the integration.

Please don't hesitate to give me feedback both on bugs and missing features.

Disclaimer 🙂 all code is built with AI
