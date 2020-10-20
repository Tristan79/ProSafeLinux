#!/usr/bin/python
# -*- coding: utf-8 -*-

# MQTT For Netgear PowerSave Switches
# v1 20-10-2020 Tristan Crispijn

# Fill in macs here (sample macs)

mqtt_server = "localhost"
mqtt_port = "1883"
mqtt_username = ""
mqtt_password = ""
mqtt_connected = False
poll_time = 30 # in seconds
netgear_interface = "en0"
netgear_timeout = 3

netgear_query_once = ["model","number_of_ports","firmwarever","firmware2ver","firmware_active"]
netgear_query_monitor = ["speed_stat","port_stat"]

sw_data = {}

"""
netgear_query_unknown = ["fixme5400","fixme2","fixmeC","fixme7400"]
netgear_query_multi_not = "vlan_id","vlan_pvid","port_based_qos","vlan802_id","bandwidth_in","bandwidth_out"
"""

import paho.mqtt.client as mqtt
from psl_class import ProSafeLinux
import psl_typ
import time
 
def on_connect(client, userdata, flags, rc):
    if rc == 5:
        print("MQTT: Authentication Failure")
    elif rc == 0:
        print("MQTT: Connected")
        global mqtt_connected
        mqtt_connected = True
    else:
        print("MQTT: Connect: Result Code " + str(rc))

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    print("MQTT: Disconnected: Result Code " + str(rc))
   
client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect

if mqtt_username != "":
    client.username_pw_set(mqtt_username, mqtt_password)

try:
    client.connect(mqtt_server, mqtt_port, 60)
    client.loop_start()
except:
    print("MQTT: Connection Refused")
    exit();

switch = ProSafeLinux()
switch.set_timeout(netgear_timeout)
if not switch.bind(netgear_interface):
    print("Netgear: Interface has no addresses, cannot talk to switch")
else:
    pass

def query_once(mac):
    query_cmd = []
    for cmd in netgear_query_once:
        query_cmd.append(switch.get_cmd_by_name(cmd))
    switchdata = switch.query(query_cmd, mac)
    
    v1 = ""
    v2 = ""
    ports = 0
    active = 0
    model = "Unknown"
    firmware = "Unknown"
    
    if switchdata != False:
        if switchdata != {}:
            for key in list(switchdata.keys()):
                if isinstance(key, psl_typ.PslTyp):
                    cmd = key.get_name()
                    if cmd == "model":
                        model = switchdata[key]
                        ports = int(switchdata[key],16)
                        v1 = switchdata[key]
                        v2 = switchdata[key]
                        active = int(switchdata[key])
    if active > 0:
        if active == 1:
            firmware = v1
        else:
            firmware = v2
    
    if ports != 0 and firmware != "Unknown" and model != "Unkown":
        print("Netgear [" + mac + "] " + str(ports) + "x Switch Model " + model + " (" + firmware + ")")
        client.publish("netgear/" + mac + "/model/" + model)
        client.publish("netgear/" + mac + "/firmware/" + firmware)
        client.publish("netgear/" + mac + "/ports/" + str(ports))
        sw_data[mac] =  { "model" : model, "firmware" : firmware, "ports" : ports}
    
for mac in switches:
    query_once(mac)
    
stop = False
while not stop:
    
    if not mqtt_connected:
        try:
            client.reconnect()
        except:
            print("MQTT: Not Connected")
            continue
        
    for mac in sw_data.keys():
        print("Netgear [" + mac + "] " + str(sw_data[mac]["ports"]) + "x Switch Model " + sw_data[mac]["model"] + " (" + sw_data[mac]["firmware"] + ")")
        query_cmd = []
        for cmd in netgear_query_monitor:
            query_cmd.append(switch.get_cmd_by_name(cmd))
        switchdata = switch.query(query_cmd, mac)
        if switchdata != False:
            if switchdata != {}:
                for key in list(switchdata.keys()):
                    if isinstance(key, psl_typ.PslTyp):
                        cmd = key.get_name()
                        if cmd == "port_stat":
                            for i in range(1, len(switchdata[key]) + 1):
                                received = switchdata[key][i-1]["rec"]
                                send  = switchdata[key][i-1]["send"]
                                crcerror = switchdata[key][i-1]["error"]
                                multicastpackets = switchdata[key][i-1]["mcst"]
                                broadcastpackets = switchdata[key][i-1]["bcst"]
                                packets = switchdata[key][i-1]["pkt"]
                                if sw_data[mac].has_key(str(i)):
                                    if sw_data[mac][str(i)].has_key("Statistics"):
                                            sw_data[mac][str(i)]["CRCError"] = crcerror
                                            client.publish("netgear/" + mac + "/" + str(i) + "/statistics/crcerror/" + str(crcerror))
                                        if sw_data[mac][str(i)]["Send"] != send:
                                            sw_data[mac][str(i)]["Send"] = send
                                            client.publish("netgear/" + mac + "/" + str(i) + "/statistics/send/" + str(send))
                                        if sw_data[mac][str(i)]["Received"] != received:
                                            sw_data[mac][str(i)]["Received"] = received
                                            client.publish("netgear/" + mac + "/" + str(i) + "/statistics/received/" + str(received))
                                        if sw_data[mac][str(i)]["MulticastPackets"] != multicastpackets:
                                            sw_data[mac][str(i)]["MulticastPackets"] = multicastpackets
                                            client.publish("netgear/" + mac + "/" + str(i) + "/statistics/multicastpackets/" + str(multicastpackets))
                                        if sw_data[mac][str(i)]["BroadcastPackets"] != broadcastpackets:
                                            sw_data[mac][str(i)]["BroadcastPackets"] = broadcastpackets
                                            client.publish("netgear/" + mac + "/" + str(i) + "/statistics/broadcastpackets/" + str(broadcastpackets))
                                        if sw_data[mac][str(i)]["Packets"] != packets:
                                            sw_data[mac][str(i)]["Packets"] = packets
                                            client.publish("netgear/" + mac + "/" + str(i) + "/statistics/packets/" + str(packets))
                                        sw_data[mac][str(i)]["TimeStamp"] = time.time()
                                    else:
                                        sw_data[mac][str(i)].update({'Statistics' : {"TimeStamp" : time.time(), "Packets" : packets, "Send" : send, "Received" : received, "CRCError" : crcerror, "MulticastPackets" : multicastpackets, "BroadcastPackets" : broadcastpackets}})
                                        client.publish("netgear/" + mac + "/" + str(i) + "/statistics/crcerror/" + str(crcerror))
                                        client.publish("netgear/" + mac + "/" + str(i) + "/statistics/send/" + str(send))
                                        client.publish("netgear/" + mac + "/" + str(i) + "/statistics/received/" + str(received))
                                        client.publish("netgear/" + mac + "/" + str(i) + "/statistics/packets/" + str(packets))
                                        client.publish("netgear/" + mac + "/" + str(i) + "/statistics/broadcastpackets/" + str(broadcastpackets))
                                        client.publish("netgear/" + mac + "/" + str(i) + "/statistics/multicastpackets/" + str(multicastpackets))

                                else:
                                    sw_data[mac][str(i)] = {'Statistics' : {"TimeStamp" : time.time(), "Packets" : packets, "Send" : send, "Received" : received, "CRCError" : crcerror, "MulticastPackets" : multicastpackets, "BroadcastPackets" : broadcastpackets}}
                                    client.publish("netgear/" + mac + "/" + str(i) + "/statistics/crcerror/" + str(crcerror))
                                    client.publish("netgear/" + mac + "/" + str(i) + "/statistics/send/" + str(send))
                                    client.publish("netgear/" + mac + "/" + str(i) + "/statistics/received/" + str(received))
                                    client.publish("netgear/" + mac + "/" + str(i) + "/statistics/packets/" + str(packets))
                                    client.publish("netgear/" + mac + "/" + str(i) + "/statistics/broadcastpackets/" + str(broadcastpackets))
                                    client.publish("netgear/" + mac + "/" + str(i) + "/statistics/multicastpackets/" + str(multicastpackets))
                        elif cmd == "speed_stat":
                            for i in range(1, len(switchdata[key]) + 1):
                                speed = switchdata[key][i-1]["speed"]
                                connected = True
                                if speed == psl_typ.PslTypSpeedStat.SPEED_NONE:
                                    speed = "Not connected"
                                    connected = False
                                if speed == psl_typ.PslTypSpeedStat.SPEED_10MH:
                                    speed = "10 Mbit/s Half Duplex"
                                if speed == psl_typ.PslTypSpeedStat.SPEED_10ML:
                                    speed = "10 Mbit/s Full Duplex"
                                if speed == psl_typ.PslTypSpeedStat.SPEED_100MH:
                                    speed = "100 Mbit/s Half Duplex"
                                if speed == psl_typ.PslTypSpeedStat.SPEED_100ML:
                                    speed = "100 Mbit/s Full Duplex"
                                if speed == psl_typ.PslTypSpeedStat.SPEED_1G:
                                    speed = "1 Gbit/s"
                                if sw_data[mac].has_key(str(i)):
                                    if sw_data[mac][str(i)].has_key("Connection"):
                                        if sw_data[mac][str(i)]["Speed"] != speed:
                                            sw_data[mac][str(i)]["Speed"] = speed
                                            sw_data[mac][str(i)]["Connected"] = connected
                                            sw_data[mac][str(i)]["TimeStamp"] = time.time()
                                            client.publish("netgear/" + mac + "/" + str(i) + "/connection/speed/" + speed)
                                            client.publish("netgear/" + mac + "/" + str(i) + "/connection/connected/" + str(connected))
                                    else:
                                        sw_data[mac][str(i)].update({'Connection' : {"TimeStamp" : time.time(), "Speed" : speed, "Connected" : connected }})
                                        client.publish("netgear/" + mac + "/" + str(i) + "/connection/speed/" + speed)
                                        client.publish("netgear/" + mac + "/" + str(i) + "/connection/connected/" + str(connected))
                                else:
                                    sw_data[mac][str(i)] = {'Connection' : {"TimeStamp" : time.time(), "Speed" : speed, "Connected" : connected }}
                                    client.publish("netgear/" + mac + "/" + str(i) + "/connection/speed/" + speed)
                                    client.publish("netgear/" + mac + "/" + str(i) + "/connection/connected/" + str(connected))
    time.sleep(poll_time)
