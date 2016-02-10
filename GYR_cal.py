
import smbus
import time
import math
import sys
import numpy as np
import scipy.signal as signal
from LSM9DS0 import *

bus = smbus.SMBus(1)

LA_So = .000732 # g/LSB (16g)
M_GN = 0.48 # mgauss/LSB (12 gauss)
G_So = 0.00875 # dps/LSB (2000dps)
GYRx_bias = 0
GYRy_bias = 0
GYRz_bias = 0
timestart = time.time()

def writeACC(register,value):
        bus.write_byte_data(ACC_ADDRESS , register, value)
        return -1

def writeMAG(register,value):
        bus.write_byte_data(MAG_ADDRESS, register, value)
        return -1

def writeGRY(register,value):
        bus.write_byte_data(GYR_ADDRESS, register, value)
        return -1

def readACCx():
        acc_l = bus.read_byte_data(ACC_ADDRESS, OUT_X_L_A)
        acc_h = bus.read_byte_data(ACC_ADDRESS, OUT_X_H_A)
	acc_combined = (acc_l | acc_h <<8)

	return acc_combined  if acc_combined < 32768 else acc_combined - 65536

def readACCy():
        acc_l = bus.read_byte_data(ACC_ADDRESS, OUT_Y_L_A)
        acc_h = bus.read_byte_data(ACC_ADDRESS, OUT_Y_H_A)
	acc_combined = (acc_l | acc_h <<8)

	return acc_combined  if acc_combined < 32768 else acc_combined - 65536

def readACCz():
        acc_l = bus.read_byte_data(ACC_ADDRESS, OUT_Z_L_A)
        acc_h = bus.read_byte_data(ACC_ADDRESS, OUT_Z_H_A)
	acc_combined = (acc_l | acc_h <<8)

	return acc_combined  if acc_combined < 32768 else acc_combined - 65536

def readMAGx():
        mag_l = bus.read_byte_data(MAG_ADDRESS, OUT_X_L_M)
        mag_h = bus.read_byte_data(MAG_ADDRESS, OUT_X_H_M)
        mag_combined = (mag_l | mag_h <<8)

        return mag_combined  if mag_combined < 32768 else mag_combined - 65536

def readMAGy():
        mag_l = bus.read_byte_data(MAG_ADDRESS, OUT_Y_L_M)
        mag_h = bus.read_byte_data(MAG_ADDRESS, OUT_Y_H_M)
        mag_combined = (mag_l | mag_h <<8)

        return mag_combined  if mag_combined < 32768 else mag_combined - 65536


def readMAGz():
        mag_l = bus.read_byte_data(MAG_ADDRESS, OUT_Z_L_M)
        mag_h = bus.read_byte_data(MAG_ADDRESS, OUT_Z_H_M)
        mag_combined = (mag_l | mag_h <<8)

        return mag_combined  if mag_combined < 32768 else mag_combined - 65536

def readGYRx():
        gyr_l = bus.read_byte_data(GYR_ADDRESS, OUT_X_L_G)
        gyr_h = bus.read_byte_data(GYR_ADDRESS, OUT_X_H_G)
        gyr_combined = (gyr_l | gyr_h <<8)

        return gyr_combined  if gyr_combined < 32768 else gyr_combined - 65536
  
def readGYRy():
        gyr_l = bus.read_byte_data(GYR_ADDRESS, OUT_Y_L_G)
        gyr_h = bus.read_byte_data(GYR_ADDRESS, OUT_Y_H_G)
        gyr_combined = (gyr_l | gyr_h <<8)

        return gyr_combined  if gyr_combined < 32768 else gyr_combined - 65536

def readGYRz():
        gyr_l = bus.read_byte_data(GYR_ADDRESS, OUT_Z_L_G)
        gyr_h = bus.read_byte_data(GYR_ADDRESS, OUT_Z_H_G)
        gyr_combined = (gyr_l | gyr_h <<8)

        return gyr_combined  if gyr_combined < 32768 else gyr_combined - 65536

	
#initialise the accelerometer
writeACC(CTRL_REG1_XM, 0b01100111) #z,y,x axis enabled, continuos update,  100Hz data rate
writeACC(CTRL_REG2_XM, 0b00100000) #+/- 16G full scale

#initialise the magnetometer
writeMAG(CTRL_REG5_XM, 0b11110000) #Temp enable, M data rate = 50Hz
writeMAG(CTRL_REG6_XM, 0b01100000) #+/-12gauss
writeMAG(CTRL_REG7_XM, 0b00000000) #Continuous-conversion mode

#initialise the gyroscope
writeGRY(CTRL_REG1_G, 0b00001111) #Normal power mode, all axes enabled (95 Hz 12.5 cutoff)
writeGRY(CTRL_REG2_G, 0b00100001) #High-pass filter: Normal mode, 13.5 Hz
writeGRY(CTRL_REG4_G, 0b00000000) #Continuos update, 245 dps full scale
######################################################

def butter_lowpass(cutoff, fs, order):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def manual_filt_low(b,a,data_in,data_out):
	n = len(b)-1
	print n, data_in, b[0], a,a[0]
	out = b[0]*data_in[n]/a[0]
	n-=1
	for x in range(n+1):
		out += b[x+1]*data_in[n]/a[0]
		out -= a[x+1]*data_out[n]/a[0]
		print n,x+1, out, a[x+1], b[x+1]
		n-=1
	return out

def floating_array_filter(in_window,out_window,in_temp):
	in_window.append(in_temp)
	in_window.pop(0)
	out_n = manual_filt_low(b,a,in_temp,out_window)
	out_window.append(out_n)
	out_window.pop(0)
	return out_n, out_window, in_window

######################################################
order = 3
fs = 25       # sample rate, Hz
cutoff = 20    # desired cutoff frequency of the filter, Hz
b,a = butter_lowpass(cutoff, fs, order)
count=bias_totx=bias_toty=bias_totz=biasx=biasy=biasz=0
start=time.time()
timer=t_tot=0
in_x_window = [0.0]*(len(b))
out_x_window = [0.0]*(len(a))
in_y_window = [0.0]*(len(b))
out_y_window = [0.0]*(len(a))
in_z_window = [0.0]*(len(b))
out_z_window = [0.0]*(len(a))
while timer<15:
        a=time.time()
	GYRx, out_x_window, in_x_window = floating_array_filter(in_x_window,out_x_window,(readGYRx()- GYRx_bias))
	GYRy, out_y_window, in_y_window = floating_array_filter(in_y_window,out_y_window,(readGYRy()- GYRy_bias))
	GYRz, out_z_window, in_z_window = floating_array_filter(in_z_window,out_z_window,(readGYRz()- GYRz_bias))
	bias_totx += GYRx
	bias_toty += GYRy
	bias_totz += GYRz
	count+=1
	timer=time.time()-start
	b=time.time()
	t = b-a
	t_tot+=t
	print "GYRx: %2.1f, GYRy: %2.1f, GYRz: %2.1f, loop time: %2.4f" %(GYRx,GYRy,GYRz,t)
	
        
biasx = bias_totx/count
biasy = bias_toty/count
biasz = bias_totz/count
avg_t = t_tot/count
print "GYRx bias = %3.1f" % (biasx)
print "GYRy bias = %3.1f" % (biasy)
print "GYRz bias = %3.1f" % (biasz)
print "average lp time = %1.5f" % (avg_t)
