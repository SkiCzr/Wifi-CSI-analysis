import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import os
import time
import csiread
import sys, getopt

fig, [ax0, ax1] = plt.subplots(nrows=2,ncols=1)
node_dict = {    "bc:6e:e2:d0:2:5": {'Color': np.asarray([103,0,31])/255, 'Name': "Node 10"},
				 "84:7b:57:62:a:48": {'Color': np.asarray([253,219,199])/255, 'Name': "Node11"},
				 "84:7b:57:61:d8:5c": {'Color': np.asarray([67,147,195])/255, 'Name': "Node12"},
				 "84:7b:57:60:cc:1e": {'Color': np.asarray([178,24,43])/255, 'Name': "Node13"},
				 "84:7b:57:62:d9:28": {'Color': np.asarray([209,229,240])/255, 'Name': "Node14"},
				 "84:7b:57:60:d0:6f": {'Color': np.asarray([33,102,172])/255, 'Name': "Node15"},
				 "84:7b:57:60:25:fc": {'Color': np.asarray([214,96,77])/255, 'Name': "Node16"},
				 "84:7b:57:62:d8:fb": {'Color': np.asarray([146,197,222])/255, 'Name': "Node17"},
				 "84:7b:57:62:d8:ec": {'Color': np.asarray([5,48,97])/255, 'Name': "Node18"},
                 "84:7b:57:61:c2:b3": {'Color': np.asarray([244,165,130])/255, 'Name': "Node 19"}
}
node_id = int(os.environ['NODE_ID'])
show_duration = 5 # In seconds
sampling_rate = 100 # In Hz
total_frames = show_duration*sampling_rate

def get_latest_csi(csifile):
    if os.path.isfile(csifile):
        try:
            csi = csiread.Picoscenes(csifile, {'CSI': [52, 2, 1], 'MPDU': 1522})
            csi.read()
        except IndexError as e:
            pass
        return csi.raw['CSI']['CSI'][-total_frames:,...], list(map(get_mac_address, csi.raw['StandardHeader']['Addr3'][-total_frames:]))


def get_mac_address(int_list):
    return ':'.join([hex(elem) for elem in int_list]).replace('0x','')

def get_mac_color(mac_address):
    return node_dict[mac_address]['Color']

def get_mac_name(mac_address):
    return node_dict[mac_address]['Name'] if 'Name' in node_dict[mac_address].keys() else mac_address


def create_csi_img(csi, macs, csitype='Mag', nodatafrom=None):
    '''
    Create mac color depth
        1st = 2D array of color values for every frame (frame x 3)
        2nd = third empty axis to repeat over (0 x frame x 3)
        3rd = repeat array over frame (104 x frame x 3)
    '''
    mac_color_depth = np.asarray(list(map(get_mac_color, macs)))
    mac_color_depth = mac_color_depth[np.newaxis,...]
    mac_color_depth = np.repeat(mac_color_depth,repeats=104,axis=0)

    img = np.zeros((total_frames, 104))
    divide_by = 255 if csitype == 'Mag' else 3.15
    img[:,0:52] = csi[:,:,0,0]/divide_by
    img[:,52:] = csi[:,:,1,0]/divide_by

    mac_color_intensity = img.T[...,np.newaxis]
    mac_color_intensity = np.repeat(mac_color_intensity,repeats=3,axis=-1)
    #print(nodatafrom)
    #img[300-nodatafrom:,:] = 0

    return (mac_color_depth*mac_color_intensity).astype(np.float32), get_mac_name(macs[-1])
    

def livecsi(i):
    global CSI_FILE
    csi, macs = get_latest_csi(csifile=CSI_FILE)
    #print(csi)
    # Below an attempt to add time but doesn't really work well..
    '''
    current_time = time.time_ns()
    plot_start = current_time-int(total_frames*(10e9/(sampling_rate*10)))
    
    data_end = os.stat(f"data/{node_id}.csi").st_mtime_ns
    data_start = data_end-int(total_frames*(10e9/(sampling_rate*10)))
    data_xs = np.linspace(data_start,data_end,total_frames)
    #data_xs = np.linspace(last_mtime-total_frames,current_time,total_frames)
    data_in_plot = np.where(data_xs > plot_start)
    empty_idx = 0 if np.sum(data_in_plot) < 1 else list(data_in_plot)[0][0]
    print(empty_idx)
    #hm = np.swapaxes(hm, 0, 1)
    #ys = csi[:,:,0,0]
    
    csi_img, title = create_csi_img(csi=csi,macs=macs,nodatafrom=empty_idx)
    '''
    csi_img_mag, title = create_csi_img(csi=np.abs(csi), csitype='Mag', macs=macs)   
    csi_img_phase, _ = create_csi_img(csi=np.angle(csi), csitype='Phase', macs=macs)     
    ax0.clear()
    ax1.clear()
    
    ax0.set_title(f"Currently receiving from: {title}")

    ax0.imshow(csi_img_mag)
    ax1.imshow(csi_img_phase)

CSI_FILE = ""

def main(argv):

    opts, args = getopt.getopt(argv,"i:",["ifile="])
    for opt, arg in opts:
       if opt in ("-i", "--ifile"):
          global CSI_FILE
          CSI_FILE = arg
    print(CSI_FILE)
    if True:
        ani = animation.FuncAnimation(fig, livecsi, interval=0.1)

        plt.show()

if __name__=="__main__":
    main(sys.argv[1:])
