# Enode-for-HA
Enode vehicle custom integration for Homeassistant

Inspired by https://github.com/OldSmurf56/xpeng but I have chosen to make a custom integration instead of using nodered.

Still betaversion and hence still missing some features + translations and have bugs.
Versions before 0.8 were only tested in sandbox, so some issues showed up with production access.

The initial setup described by oldsmurf56 is basically the same, I have however made the linksession step easier, as described in step 3 in the enode setup..


Enode setup
1) Create an enode account.
2) Ask sales for production access (you can test the integration with the sandbox environment by changing the environment in const.py to "sandbox", until you get production access)
3) Have your enode credentials ready, and use either the instructions here https://developers.enode.com/docs/getting-started or use my simplified process here https://lauridsen.nl/enode/enodelink.php to get the link to the linksession between your vehicles app account and enode. The php file is also uploaded here, so that you can see the code, and can use it in your own webserver if you prefer for privacy concerns.
4) Use the generated url to link your vehicle to enode within 24 hours.

How to install the custom integration in homeassistant
1) Copy full repository directory enodeforha to your homeassistant custom_components folder
2) Restart homeassistant
3) Add integration "Enode" the same way you would add other buildin homeassistant integrations (so NOT via HACS)
4) It will ask for clientid and clientsecret for enode
5) It should then show you a list of the vehicles available with that clientid but you can only add one at a time (if you have more)
6) You can now select the sensors you want to add. All sensors offered by Enode are included,  but not all sensors contain data from all vehicles, eg Xpeng does not provide odometer. That's why the select sensors option is provided, so you can disable eg Odometer for Xpeng. Currently the select function is not available after configuration of the vehicle, so you will have to remove and then add the vehicle again, if you want to change sensor selection.
7) There is also an option to change the data refresh interval. This can also be changed for each vehicle after configuration, but the change will only be applied after reload of the integration. 
I have not seen documentation from enode about how often we can request data from the api, but have not experienced problems with both 30 and 60 seconds. However it seems that the connection between vehicle and enode does not necessarily refresh data very often, so also consider this before you choose 5 seconds..
8) The debug notifications options is only meant to be used if sensordata are not received or are incorrect. What it does is that it enables a notification in HomeAssistant, that provides the raw json response from the api request. The notification will only be sent every 10 minutes. This can also be activated/deactivated for each vehicle after configuration, but the activation/deactivation will only be applied after reload of the integration.

Please don't hesitate to give me feedback both on bugs and missing features.

Disclaimer 🙂 all code is built with AI
