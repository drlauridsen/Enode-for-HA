# Enode-for-HA
Enode vehicle custom integration for Homeassistant

Still betaversion, and only tested with Enode sandbox environment, since I am awaiting production access.
Still missing some features, including working location sensor and translations. And might have bugs. But again - waiting until I have real-life vehicle access to continue work.
Inspired by https://github.com/OldSmurf56/xpeng but I have chosen to make a custom integration instead of using nodered.
The initial setup described by oldsmurf56 is basically the same, I have however made the linksession step easier, as described in step 3 in the enode setup..


Enode setup
1) Create an enode account.
2) Ask sales for production access (you can test the integration with the sandbox environment by changing the environment in const.py to "sandbox", until you get production access)
3) Have your enode credentials ready, and use either the instructions here https://developers.enode.com/docs/getting-started or use my simplified process here https://lauridsen.nl/enode/enodelink.php to get the link to the linksession between your vehicles app account and enode. The php file is also uploaded here, so that you see the code, and can use it in your own webserver if you prefer.
4) Use the generated url to link your vehicle to enode within 24 hours.

How to install the custom integration in homeassistant
1) Copy full repository directory enodeforha to your homeassistant custom_components folder
2) Restart homeassistant
3) Add integration "Enode" the same way you would add other buildin homeassistant integrations (so NOT via HACS)
4) It will ask for clientid and clientsecret for enode
5) It should then show you a list of the vehicles available with that clientid but you can only add one at a time (if you have more)
6) If it works it should add sensors and switches, however not the location and possibly some sensors that are not available for the vehicle in real-life,  but were available in the sandbox..

Please don't hesitate to give me feedback both on bugs, missing features and also what's working

Disclaimer 🙂 all code is built with AI
