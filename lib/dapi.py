from websocket import create_connection
import json
from random import randint

# Let's do some dep checking and handle missing ones gracefully
try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    from PyQt4.Qt import Qt
    import PyQt4.QtCore as QtCore

except ImportError:
    print "You need to have PyQT installed to run Electrum-DASH in graphical mode."
    print "If you have pip installed try 'sudo pip install pyqt' if you are on Debian/Ubuntu try 'sudo apt-get install python-qt4'."
    sys.exit(0)


from electrum_dash.i18n import _
import websocket
import threading
from time import sleep
from electrum_dash.plugins import run_hook

dapi = None

def on_message(ws, message):
    global dapi

    dapi.on_message(message)

def on_close(ws):
    print "### closed ###"

class DAPIWebSocket(object):    
    def start(self):
        websocket.enableTrace(True)
        self._ws = websocket.WebSocketApp("ws://www.dash.org:5000/", on_message = on_message, on_close = on_close)
        self._wst = threading.Thread(target=self._ws.run_forever)
        self._wst.daemon = True
        self._wst.start()
        self._messages = []
        self._main_window = None

    def set_main_window(self, window):
        self._main_window = window

    def on_message(self, message):
        obj = json.loads(message)
        if(obj["object"] == "dapi_message"):
            dapi.process_message(obj)

        self._messages.append(message)

    def send(self, json):
        try:
            self._ws.send(json)
        except:
            print "DAPI connection was closed, restarting"
            self.start()
            sleep(5)
            self._ws.send(json)

    def receive(self):
        if len(self._messages) > 0: return self._messages.pop()
        return False

    def close(self):
        self._ws.close()

    def process_message(self, message):
        # { 
        #     "object" : "dapi_command",
        #     "data" : {
        #         "command" = "send_message",
        #         "sub_command" = "(One of these: addr,addr-request,tx-desc,payment-request)",
        #         "from_uid" = UID,
        #         "to_uid" = UID, 
        #         "signature" = "",
        #         "payload" = ENCRYPTED
        #     }
        # }

        print "dapi, process new message", message

        #####################################################################################       
        # all messages are broadcast to all users currently, this filters only the ones to us
        username = self._main_window.wallet.storage.get('username', None)
        if(message["data"]["to_uid"] != username):
            print "Skipping message to", message["data"]["to_uid"]
            return False

        #####################################################################################
        # we only want to filter pms here
        if(message["object"] != "dapi_message"):
            return False
        if(message["data"]["command"] != "send_message"):
            return False
        #####################################################################################

        #####################################################################################
        # Address-Request : A friend is asking for us to top-off their address list
        if(message["data"]["sub_command"] == "addr-request"):
            username = self._main_window.wallet.storage.get('username', None)
            username2 = message["data"]["from_uid"]

            #in the demo all users can send all other users messages (friends can only send messages)
            #TODO: We need to keep track of these
            dapi.send_private_message(username, username2, "addr", self._main_window.wallet.get_unused_address(self._main_window.current_account, 0))
            dapi.send_private_message(username, username2, "addr", self._main_window.wallet.get_unused_address(self._main_window.current_account, 1))
            dapi.send_private_message(username, username2, "addr", self._main_window.wallet.get_unused_address(self._main_window.current_account, 2))
            dapi.send_private_message(username, username2, "addr", self._main_window.wallet.get_unused_address(self._main_window.current_account, 3))
            dapi.send_private_message(username, username2, "addr", self._main_window.wallet.get_unused_address(self._main_window.current_account, 4))

        #####################################################################################
        # Addr : A friend sent us a new address that can be used for payment to them
        if(message["data"]["sub_command"] == "addr"):
            username2 = message["data"]["from_uid"] 
            addr = message["data"]["payload"] 

            if username2 in self._main_window.contacts:
                _type, obj = self._main_window.contacts[username2]

                if addr not in obj["addresses"]:
                    obj["addresses"].append(addr)

                self._main_window.contacts[username2] = ('friend', obj)
                #self._main_window.update_contacts_tab()     
                #run_hook('contacts_tab_update')
                #run_hook('contacts_tab_update', self._main_window.contacts)       

                # l = self._main_window.contacts_list
                # item = l.currentItem()
                # current_key = item.data(0, Qt.UserRole).toString() if item else None
                # l.clear()
                
                # items = []
                # for key in sorted(self._main_window.contacts.keys()):
                #     _type, obj = self._main_window.contacts[key]
                #     if "stars" in obj and "addresses" in obj:
                #         if key == current_key:
                #             obj['current'] = True
                #         else:
                #             obj['current'] = False    

                #         items.append(obj)

                # self._main_window.contacts_list.update(items)

                # run_hook('update_contacts_tab', l)


        #####################################################################################
        # Tx-Desc : A friend sent us a transaction description, this will be displayed in the UI
        if(message["data"]["sub_command"] == "tx-desc"):
            username2 = message["data"]["from_uid"] 
            tx_desc = json.loads(message["data"]["payload"]) 

            if "tx" not in tx_desc or "desc" not in tx_desc:
                print "Invalid tx description", tx_desc
                return

            if username2 in self._main_window.contacts:
                _type, obj = self._main_window.contacts[username2]

                if "txes" not in obj:
                    obj["txes"] = []

                if tx_desc['tx'] not in obj["txes"]:
                    obj["txes"].append(tx_desc)
                else:
                    print "failed to append"

                self._main_window.contacts[username2] = ('friend', obj)
                run_hook('history_tab_update')
                run_hook('set_label', tx_desc["tx"], tx_desc["desc"], True)
            else:
                print "missing user", username2

        #####################################################################################
        # Payment-Request : A contact is asking for payment for something, this will ask the user if it's OK
        if(message["data"]["sub_command"] == "payment-request"):
            username2 = message["data"]["from_uid"] 
            tx_desc = json.loads(message["data"]["payload"]) 

            """
                ["data"]["payload"] : {
                    "command" : "payment-request,
                    "username_merchant" : UID,
                    "username_client" : UID,
                    "requested_amount" : AMOUNT,
                    "description" : DESCRIPTION,
                    "callback_url" : CALLBACK_URL, 
                    "signature" : ""
                }
            """

            print username2
            print tx_desc
            print self._main_window

            # QMessageBox.warning(self._main_window, _('Error'),
            #     _('Invalid Dash Address') + ':\n' + tx_desc['description'], _('OK'))
            # return False

            print "append"
            self._main_window._payment_requests.append([username2, tx_desc])
            run_hook('timer_actions')
            
        return True
    
    def send_invitation(self, myusername, target_email):        
        ex = {   
            "object" : "dapi_command",
            "data" : {
                "id" : str(randint(1000000,9000000)),
                "command" : "send_invitaiton",
                "from_uid" : myusername,
                "target_email" : target_email
            }
        }

        # send a message to DAPI
        s = json.dumps(ex)
        self.send(s)

        # wait for the result
        count = 0
        result = False
        while True:
            result = self.receive()
            if result:
                if(result.find('"dapi_result"') > 0):
                    obj = json.loads(result)
                    return obj["data"]["data"]
            
            sleep(.1)
            count += 1

            if count > 30:
                print "dapi.send_invitaiton timeout"
                return None

        print "dapi.send_invitaiton error"
        return None

    def get_profile(self, myusername, target_username):        
        ex = {   
            "object" : "dapi_command",
            "data" : {
                "id" : str(randint(1000000,9000000)),
                "command" : "get_profile",
                "from_uid" : myusername,
                "to_uid" : target_username, 
                "slot" : 1
            }
        }

        # send a message to DAPI
        s = json.dumps(ex)
        self.send(s)

        # wait for the result
        count = 0
        result = False
        while True:
            result = self.receive()
            if result:
                try:
                    obj = json.loads(result)
                    if obj["object"] == "dapi_result" and obj["data"]["data"]["username"] == target_username:
                        print "obj", obj
                        return obj["data"]["data"]
                except:
                    pass
            
            sleep(.1)
            count += 1

            if count > 30:
                print "dapi.get_profile timeout"
                return None

        print "dapi.get_profile error"
        return None

    def send_private_message(self, myusername, target_username, sub_command, payload):
        ex = {   
            "object" : "dapi_command",
            "data" : {
                "id" : str(randint(1000000,9000000)),
                "command" : "send_message",
                "sub_command" : sub_command,
                "from_uid" : myusername,
                "to_uid" : target_username,
                "payload" : payload
            }
        }

        s = json.dumps(ex)
        print "Send:", s
        self.send(s)

        count = 0
        result = False
        while True:
            result = self.receive()
            if result:
                print "Recieve:", result
                if(result.find('"dapi_message"') > 0):
                    return result

            sleep(.1)
            count += 1

            if count > 30:
                print "dapi.get_profile timeout"
                return None

        print "dapi.get_profile error"
        return None


dapi = DAPIWebSocket()

try:
    dapi.start()
except:
    raise
    #print "DAPI is not running"

