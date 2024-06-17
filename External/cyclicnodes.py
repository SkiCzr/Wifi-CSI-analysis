from scapy.all import *
import numpy as np
import json
import time
import psutil
import subprocess as sp
import atexit
from datetime import datetime

VERSION = "050823-1613"

IP_BROADCAST = "ff:ff:ff:ff:ff:ff"
IP_INTELMAGIC = "00:16:ea:12:34:56"

NETWORKED_CLIENTS = 139
ASSO_ID = 140
TRANSMISSION_PARAMS = 141
CSI_PACKET = 150
RESET_REQUEST = 160

SWEEPING_PARAMS = []

SWEEPING_DURATION = []

SWEEPING_RATE = []

TX_PARAM = {
	'rate': 100,
	'duration': 1
	}

ROTATION = 0

wlan_iface = next(iface for iface in psutil.net_if_addrs().keys() if 'mon' in iface)
my_addr = psutil.net_if_addrs()[wlan_iface][0].address
known_clients = {"bc:6e:e2:d0:02:05": "Node10",
				 "84:7b:57:62:0a:48": "Node11",
				 "84:7b:57:61:d8:5c": "Node12",
				 "84:7b:57:60:cc:1e": "Node13",
				 "84:7b:57:62:d9:28": "Node14",
				 "84:7b:57:60:d0:6f": "Node15",
				 "84:7b:57:60:25:fc": "Node16",
				 "84:7b:57:62:d8:fb": "Node17",
				 "84:7b:57:62:d8:ec": "Node18",
				 "84:7b:57:61:c2:b3": "Node19"}
verbal_clients = []
client_uptimes = []

last_received_ns = None

Asso_IDs = []
AssoRes_expected = None

last_ns = time.time_ns()

weights = np.random.rand(4,13)

@atexit.register
def stopping_cyclicnodes():
	print("Cancelling 'cyclicnodes.py', resetting other devices...")
	send_reset_request()


def check_known_clients(mac_address):
	if mac_address == my_addr:
		return "Self"
	elif mac_address in known_clients.keys():
		return known_clients[mac_address]
	else:
		return mac_address

def get_picoscenes_runtime():
	#runtime = sp.check_output('$$(( $(date +%%s) - $$(date -d "$$(systemctl show --property=ActiveEnterTimestamp picoscenes | cut -d= -f2)" +%%s)))',shell=True)
	systemdate = str(sp.check_output("systemctl show --property=ActiveEnterTimestamp picoscenes",shell=True).decode("utf-8"))
	systemdate = systemdate[systemdate.index(" ")+1:systemdate.index(" CEST")]
	dt_started = datetime.strptime(systemdate,'%Y-%m-%d %H:%M:%S')
	picoscenes_runtime = datetime.now() - dt_started
	return picoscenes_runtime.total_seconds()

def gen_sc(frag: int, seq: int) -> int:
	return (seq << 4) + frag

def scan_clients(timeout:int):
	def handle_probe_response(packet):
		if packet.haslayer(Dot11ProbeResp) and packet.addr3 not in verbal_clients:
			verbal_clients.append(packet.addr3)
			if packet.getlayer(Dot11Elt, ID=99):
				client_uptimes.append(packet.getlayer(Dot11Elt, ID=99).info.decode('utf-8'))
			else:
				client_uptimes.append(-1)
			#print(f"Received response from {packet.addr3}")

	radiotap = RadioTap()
	probe_req = Dot11(
		type=0,
		subtype=4,
		addr1=IP_BROADCAST,
		addr2=IP_INTELMAGIC,
		addr3=my_addr
	) / \
	Dot11ProbeReq() / \
	Dot11Elt(ID="SSID", info="Cyclic Nodes")
	sendp(radiotap / probe_req, iface=wlan_iface, count=5, inter=0.01, verbose=False)
	sniff(filter = f"ether src {IP_INTELMAGIC}", prn=handle_probe_response, iface=wlan_iface, timeout=timeout)
	#sniff(prn=handle_probe_response, lfilter=lambda pkt: pkt.haslayer(Dot11ProbeResp), timeout=timeout)

def load_settings(clients):
	print(f"File to load (empty to load 'default.txt')")
	file_name = input()
	file_name = "default.txt" if len(file_name) == 0 else file_name
	with open(file_name, 'r') as load_file:
		loaded_settings = load_file.read()
		settings = [setting for setting in loaded_settings.split("\n") if len(setting) > 0]
		sort = settings[0]
		if sort in ["asc", "desc"]:
			named_clients = [known_clients[client] for client in clients]
			reverse = True if sort == "desc" else False
			named_clients.sort(reverse=reverse)
			clients = [list(known_clients.keys())[list(known_clients.values()).index(client)] for client in named_clients]
		else:
			raise ValueError

		sweeping_params_input = [(float(params.split(" ")[0]), float(params.split(" ")[1]), int(params.split(" ")[2]))  for params in settings[1].split(", ")]
		global SWEEPING_PARAMS
		for sweeping_param in sweeping_params_input:
			SWEEPING_PARAMS += [[sweeping_param[0], sweeping_param[1]]]*sweeping_param[2]

		auto_start = bool(settings[2])
		print(f"Loaded the following settings:\n\tClients ordered as: {named_clients}\n\tSweeping Tx parameters: {sweeping_params_input}\n\tAutostart: {auto_start}")
		return clients, auto_start

def advanced_options(clients):
	clients = np.asarray(clients)
	print(f"Current rotation: {', '.join([f'{idx}: {check_known_clients(mac)}' for idx, mac in enumerate(clients)])}")
	print(f"Please enter new sequence, seperated by spaces (e.g., '0 4 1 Individual test'), or choose ASC(ending) or DESC(ending):")
	#print("Note that the entered sequence is from the POV of this node; you may choose another starting node later*")
	sort = input().lower()
	if sort in ["asc", "desc"]:
		named_clients = [known_clients[client] for client in clients]
		reverse = True if sort == "desc" else False
		named_clients.sort(reverse=reverse)
		clients = [list(known_clients.keys())[list(known_clients.values()).index(client)] for client in named_clients]
	else:
		try:
			new_order = [int(idx) for idx in sort.split(" ")]
			#if len(new_order) != len(clients):
			#	print("Not enough elements, make sure every client has a position!")
			#	return clients.tolist()
			clients = np.asarray(verbal_clients)[new_order]
		except Exception as e:
			print(f"Something went wrong, maintaining old sequence...\n\t{e}")
		clients = clients.tolist()
	print("Setting option for transmission sweeping, leave empty for none.")
	print("Provide the duration, rate, and repeats (space seperated) per element (comma seperated) as follow:")
	print("0.1 100 10, 0.Individual test 100 5, 1 5 1")
	sweeping_params_input = [(float(params.split(" ")[0]), float(params.split(" ")[1]), int(params.split(" ")[2]))  for params in input().split(", ")]
	global SWEEPING_PARAMS
	for sweeping_param in sweeping_params_input:
		SWEEPING_PARAMS += [[sweeping_param[0], sweeping_param[1]]]*sweeping_param[2]
	'''
	print(f"If sweeping duration, enter sequence seperated by spaces (e.g. '0.1 1 10') or leave empty for none:")
	sweeping_dur = input()
	if len(sweeping_dur) > 0:
		global SWEEPING_DURATION
		try:
			 SWEEPING_DURATION = [float(dur) for dur in sweeping_dur.split(" ")]
		except Exception as e:
			print(f"Something went wrong, no sweeping duration set...")
		print(SWEEPING_DURATION)
	'''
	return clients

def manual_init():
	scan_clients(timeout=1)
	global verbal_clients
	global client_uptimes
	while True:
		print(f"Found clients [{len(verbal_clients)}]:")
		for client, uptime in zip(verbal_clients, client_uptimes):
			print(f"\t{known_clients[client]} ({uptime}s)")
		print(f"Type 'start' to start, 'scan' to scan for clients again, 'abort' to abort, or 'adv' for advanced setup (e.g.custom list, sweeping rates)")
		select = input().lower()
		if select == 'start':
			break;
		elif select == 'scan':
			verbal_clients = []
			client_uptimes = []
			print('Scanning for clients again...')
			scan_clients(timeout=1)
		elif select in ['abort', 'exit']:
			return False
		elif select in ['adv', 'advance', 'advanced']:
			verbal_clients = advanced_options(verbal_clients)
		elif select in ['l', 'load']:
			verbal_clients, auto_start = load_settings(verbal_clients)
			if auto_start:
				break
		else:
			print("Please select a valid option.")

	if len(SWEEPING_PARAMS) > 0:
		#print(SWEEPING_PARAMS)
		tx_duration = SWEEPING_PARAMS[0][0]
		tx_rate = SWEEPING_PARAMS[0][1]
	else:
		valid_tx_duration = False
		print(f"Set transmission duration per device in seconds (> 0, e.g. 0.1 or 10):")
		while not valid_tx_duration:
			try:
				tx_duration = float(input())
				if tx_duration <= 0:
					raise ValueError
				valid_tx_duration = True
			except Exception as e:
				print(f"Invalid transmission duration ({tx_duration}); please enter a valid transmission duration (e.g. 0.1 or 10)")

		valid_tx_rate = False
		print(f"Set transmission rate for all devices per second (whole number > 0, in packets per second/in Hz))")
		while not valid_tx_rate:
			try:
				tx_rate = int(input())
				if tx_rate <= 0:
					raise ValueError
				valid_tx_rate = True
			except Exception as e:
				print(f"Invalid transmission duration ({tx_rate}); please enter a valid transmission rate (e.g. 1 or 100) per second (in Hz)")

	global TX_PARAM
	TX_PARAM['rate'] = tx_rate
	TX_PARAM['duration'] = tx_duration

	verbal_clients.insert(0, my_addr)
	print(f"Starting with clients [{len(verbal_clients)}]: {', '.join([check_known_clients(client) for client in verbal_clients])}; announcing to others")
	update_transmission_params(IP_BROADCAST,IP_INTELMAGIC,my_addr,TX_PARAM)
	init_beacon = RadioTap() / Dot11(
		type=0,
		subtype=8,
		addr1=IP_BROADCAST,
		addr2=IP_INTELMAGIC,
		addr3=my_addr) / \
		Dot11Beacon(cap="ESS") / \
		Dot11Elt(ID=NETWORKED_CLIENTS, info=json.dumps(verbal_clients))
	sendp(init_beacon, iface=wlan_iface,inter=0.01,count=1,verbose=False)
	return True

def send_reset_request():
	init_beacon = RadioTap() / Dot11(
		type=0,
		subtype=8,
		addr1=IP_BROADCAST,
		addr2=IP_INTELMAGIC,
		addr3=my_addr) / \
		Dot11Beacon(cap="ESS") / \
		Dot11Elt(ID=RESET_REQUEST, info="")

	sendp(init_beacon, iface=wlan_iface,inter=0.1,count=20,verbose=False)

def update_transmission_params(addr1,addr2,addr3,TX_PARAM):
	init_beacon = RadioTap() / Dot11(
		type=0,
		subtype=8,
		addr1=addr1,
		addr2=addr2,
		addr3=addr3) / \
		Dot11Beacon(cap="ESS") / \
		Dot11Elt(ID=TRANSMISSION_PARAMS, info=json.dumps(TX_PARAM))
	sendp(init_beacon, iface=wlan_iface,inter=0.01,count=1,verbose=False)

def send_probe_rspn(packet):
	probe_rspn = RadioTap() / Dot11(
		type=0,
		subtype=5,
		addr1=packet.addr3,
		addr2="00:16:ea:12:34:56",
		addr3=my_addr) / \
	Dot11ProbeResp() / \
	Dot11Elt(ID=99, info=f"{int(get_picoscenes_runtime())}") / \
	Dot11Elt(ID="SSID", info="Cyclic Nodes")

	sendp(probe_rspn, iface=wlan_iface, count=5, inter=0.01, verbose=False)

def get_next_client():
	return verbal_clients[(verbal_clients.index(my_addr)+1) % len(verbal_clients)]

def send_csi_packets():
	global last_ns
	global AssoRes_expected
	global Asso_IDs

	def handle_asso_response(packet):
		global AssoRes_expected
		global Asso_IDs
		if packet.type == 0 and packet.subtype == 4: # This is a new scan - we should reset our current state and listen again
			print("Resetting")
			AssoRes_expected = None # Should have def reset_state()
			send_probe_rspn(packet)
			return True
		elif packet.addr1 == my_addr:
			if packet.haslayer(Dot11AssoResp) and packet.addr3 == AssoRes_expected:
				Asso_ID_info = packet.getlayer(Dot11Elt, ID=ASSO_ID).info[2:].decode("utf-8")
				#print(Asso_ID_info, Asso_IDs)
				if Asso_ID_info in Asso_IDs:
					Asso_IDs.remove(Asso_ID_info)
					AssoRes_expected = None
					return True
			if packet.haslayer(Dot11AssoReq):
				print("[!] Full circle -- continuing...")
				AssoRes_expected = None
				return True
		elif packet.addr1 == IP_BROADCAST and packet.addr3 == AssoRes_expected:
			print("[!] No AssoReq received, but CSI collecting -- continuing...")
			AssoRes_expected = None
			return True
		return False

	#start_csi = time.perf_counter()
	present = "TSFT+Flags+Rate+Channel+dBm_AntSignal+RXFlags+timestamp+RadiotapNS+Ext"
	radiotap = RadioTap(present=present)
	packet = Dot11(
			type=2,
			subtype=0,
			addr1=IP_BROADCAST,
			addr2=IP_INTELMAGIC,
			addr3=my_addr,
			SC=gen_sc(0,1),
			FCfield=0x0001,
			ID=CSI_PACKET)  / \
			Raw(json.dumps(weights.tolist()))
		#json.dumps({'CSI': True, 'Weights': weights.tolist()})
		# Used to have Dot11QoS() / \
	pkt_interval = 1/TX_PARAM['rate']
	pkt_count = int(TX_PARAM['duration']/pkt_interval)
	#print(f"count={pkt_count} | interval = {pkt_interval}")
	sendp(radiotap/packet, iface=wlan_iface,count=pkt_count,inter=pkt_interval,verbose=False)
	#ack = srp1(packet, iface="mon5", timeout=5)
	#time.sleep(1)
	#end_csi = time.perf_counter()

	#start_asso_req = time.perf_counter()
	global verbal_clients
	AssoRes_expected = get_next_client()
	
	retries = 0
	timeout = 0.05
	Asso_ID_info = str(time.time_ns())
	Asso_IDs.append(Asso_ID_info)
	while AssoRes_expected is not None:
		next_addr = AssoRes_expected
		asso_req = RadioTap() / Dot11(type=0,
				subtype=0,
				addr1=next_addr,
				addr2=IP_INTELMAGIC,
				addr3=my_addr,
				SC=gen_sc(0,101)) / \
				Dot11AssoReq(listen_interval=0) / \
				Dot11Elt(ID=ASSO_ID, info=Asso_ID_info)
		print(f"[{round((time.time_ns()-last_ns)/1e9,2)}s] AssoReq>>{check_known_clients(verbal_clients[(verbal_clients.index(my_addr)+1) % len(verbal_clients)])}[CSI sent={pkt_count}@{pkt_interval}s]")
		last_ns = time.time_ns()
		sendp(asso_req, iface=wlan_iface,inter=0.001,count=1,verbose=False)
		sniff(filter = f"ether src {IP_INTELMAGIC}", stop_filter=handle_asso_response, iface=wlan_iface, timeout=timeout, count=10)
		timeout += random.uniform(0,1)
		retries += 1
		if retries > 100:
			AssoRes_expected = None
	if retries > 1:
		print(f"[!]\tRetries: {retries-1} [Timeout: {timeout}s]")
	#end_asso_req = time.perf_counter()
	#print(f"\t Performance counter: csi={end_csi-start_csi}; association={end_asso_req-start_asso_req}")

handled_packets = []
received_csi = 0
def handle_packet(packet):
	global last_ns
	global received_csi
	global AssoRes_expected
	global TX_PARAM
	if packet.haslayer(Dot11):
		packet = packet[Dot11]
		if packet.type == 0 and packet.subtype == 0 and packet.haslayer(Dot11AssoReq) and packet.addr1 == my_addr and int(packet[Dot11Elt].info) not in handled_packets:
			handled_packets.append(int(packet[Dot11Elt].info))
			print(f"[{round((time.time_ns()-last_ns)/1e9,2)}s] AssoReq<<{check_known_clients(packet.addr3)} [CSI counted={received_csi}]")
			last_ns = time.time_ns()
			received_csi = 0
			asso_rspn = RadioTap() / Dot11(
				type=0,
				subtype=1,
				addr1=packet.addr3,
				addr2=IP_INTELMAGIC,
				addr3=my_addr,
				SC=packet.SC) / \
			Dot11AssoResp() / \
			Dot11Elt(ID=ASSO_ID, info=packet.getlayer(Dot11Elt, ID=ASSO_ID)) / \
			Dot11Elt(ID="SSID", info="Cyclic Nodes")
			sendp(asso_rspn, iface=wlan_iface, count=1, inter=0.001, verbose=False)
			#print(packet.SC)

			if len(SWEEPING_PARAMS) > 0 and list(known_clients.keys()).index(my_addr) == 0:
				global ROTATION
				TX_PARAM['duration'] = SWEEPING_PARAMS[ROTATION % len(SWEEPING_PARAMS)][0]
				TX_PARAM['rate'] = SWEEPING_PARAMS[ROTATION % len(SWEEPING_PARAMS)][1]
				update_transmission_params(get_next_client(),IP_INTELMAGIC,my_addr,TX_PARAM)
				ROTATION += 1
			send_csi_packets()
		if packet.type == 2 and packet.subtype == 0:
			# This is a packet to measure CSI from :)
			if packet.addr1 == IP_BROADCAST and packet.addr2 == IP_INTELMAGIC:
				sc = packet.SC
				seq = sc >> 4
				frag = sc & 0b1111
				if packet.ID != CSI_PACKET: # for some reason this is reversed?
					received_csi = received_csi + 1
		if packet.type == 0 and packet.subtype == 8:
				if packet.getlayer(Dot11Elt, ID=RESET_REQUEST):
					print("[!] Reset request received, restarting PicoScenes...")
					sp.call(["systemctl", "restart", "picoscenes"])
					print("[v] Restarting PicoScenes done!")
				if packet.getlayer(Dot11Elt, ID=NETWORKED_CLIENTS): # Participating nodes information
					global verbal_clients
					verbal_clients = json.loads(packet.getlayer(Dot11Elt, ID=NETWORKED_CLIENTS).info)
					print(f"Participating with clients [{len(verbal_clients)}]: {', '.join([check_known_clients(client) for client in verbal_clients])}")
				if packet.getlayer(Dot11Elt, ID=TRANSMISSION_PARAMS): # Transmission parameters
					tx_update = json.loads(packet.getlayer(Dot11Elt, ID=TRANSMISSION_PARAMS).info)
					updated = False
					for key in tx_update.keys():
						if tx_update[key] != TX_PARAM[key]:
							TX_PARAM[key] = tx_update[key]
							updated = True
					if updated:
						print(f"Transmission rate set to {TX_PARAM['rate']} for {TX_PARAM['duration']}s per cycle (total cycle: {len(verbal_clients)*TX_PARAM['duration']}s)")
		if packet.type == 0 and packet.subtype == 4:
			#print(f"Received probe request from {packet.addr3}")
			send_probe_rspn(packet)

def main():
	print(f"Started with addr={my_addr} on iface={wlan_iface} [Version: {VERSION}] | PicoScenes running since: {int(get_picoscenes_runtime())}s")
	last_ns = time.time_ns()
	success = True
	known_macs = list(known_clients.keys())
	if my_addr in known_macs and known_macs.index(my_addr) == 0:
		success = manual_init()
		if success:
			#time.sleep(5)
			send_csi_packets()
	if success:
		sniff(filter = "ether src 00:16:ea:12:34:56", iface=wlan_iface,prn=handle_packet)
	else:
		print("Aborted.")

if __name__ == "__main__":
	main()
