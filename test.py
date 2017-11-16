"""
This script reads Cherenkov and fluorescence photon bunches
from all events in the CORSIKA output.

Usage: It takes CERnnnnnn and DATACARD files as input arguments:

    python test.py CERnnnnnn all

Variables in capital letters corespond to datacard input arguments
"""

import histogram
import DataCard
import sys
from itertools import compress
import numpy as np
from scipy.io import FortranFile

data_card = DataCard.read(sys.argv[2])

# Definition of the histogram depending on the detection area
bunches = np.array([]).reshape(0, 7)
binsize = 10  # meters

if data_card['XCERARY'] > data_card['YCERARY']:
    # print("Histogram along x-axis...")
    type_of_hist = 'x'
    maxlen = 1e-2 * data_card['XCERARY'] / 2
    numbins = int(maxlen / binsize)
    breaks = numbins + 1
    distances = np.linspace(0, maxlen, breaks)
    mids = ((distances[1] - distances[0]) / 2) + distances
    mids = mids[0:numbins]

elif data_card['XCERARY'] < data_card['YCERARY']:
    # print("Histogram along y-axis...")
    type_of_hist = 'y'
    maxlen = 1e-2 * data_card['YCERARY'] / 2
    numbins = int(maxlen / binsize)
    breaks = numbins + 1
    distances = np.linspace(0, maxlen, breaks)
    mids = ((distances[1] - distances[0]) / 2) + distances
    mids = mids[0:numbins]

else:
    # print("Histogram radially...")
    type_of_hist = 'r'
    maxlen = 1e-2 * data_card['XCERARY'] / 2
    numbins = int(maxlen / binsize)
    breaks = numbins + 1
    radius = np.linspace(0, maxlen, breaks)
    mids = ((radius[1] - radius[0]) / 2) + radius
    mids = mids[0:numbins]

hist_c = np.zeros((2, numbins))
hist_f = np.zeros((2, numbins))

# Define telescope pointing angle
onaxis = input("On-axis pointing (y/n)? ")
if onaxis == 'y':
    pointing_angle = data_card['THETAP']
    pointing = 'onaxis'
else:
    pointing_angle = input("Off-axis angle? ")
    pointing = 'offaxis'

# Open binary CORSIKA output file
file = FortranFile(sys.argv[1], 'r')

# Control and debugging counters:
count = 0
lines = 0
photons = 0

while True:
    count = count + 1
    # Sort data in 21 sub-blocks of 39 lines each (and 7 columns)
    data = np.split(file.read_reals(dtype=np.float32).reshape(-1, 7), 21)
    # It should be:
    # indices_boolean = [np.abs(i[0][0])<max(cersize, fluorsize) for i in data]
    # select only sub-blocks of bunches
    indices_boolean = [np.abs(i[0][0]) < 100 for i in data]
    # store 1st element of each sub-block
    indices = [i[0][0] for i in data]
    bunches = np.vstack([bunches, np.vstack(compress(data, indices_boolean))])
    # drop those lines containing only zeros
    bunches = bunches[np.all(bunches != 0, axis=1)]

    # Not store sub-blocks to bunches array every time to speed the process up
    if count == 10:
        h_c = histogram.PhotonBunches(bunches[bunches[:, 0] > 0],
                                      data_card['XCERARY'],
                                      data_card['YCERARY'],
                                      pointing_angle,
                                      data_card['NSHOW']
                                      )
        h_f = histogram.PhotonBunches(bunches[bunches[:, 0] < 0],
                                      data_card['XCERARY'],
                                      data_card['YCERARY'],
                                      pointing_angle,
                                      data_card['NSHOW']
                                      )
        hist_c = hist_c + h_c
        hist_f = hist_f + h_f
        count = 0  # reset counter
        bunches = np.array([]).reshape(0, 7)  # reset array

    if any(3300 < i < 3303. for i in indices):  # Flag indicating RUN END sub-block
        if count < 10:
            h_c = histogram.PhotonBunches(bunches[bunches[:, 0] > 0],
                                          data_card['XCERARY'],
                                          data_card['YCERARY'],
                                          pointing_angle,
                                          data_card['NSHOW']
                                          )
            h_f = histogram.PhotonBunches(bunches[bunches[:, 0] < 0],
                                          data_card['XCERARY'],
                                          data_card['YCERARY'],
                                          pointing_angle,
                                          data_card['NSHOW']
                                          )
            hist_c = hist_c + h_c
            hist_f = hist_f + h_f
        file.close()
        break


np.savetxt('%iGeV_%ish_%ideg_%i%s_hist_%s.dat' % (data_card['ERANGE'],
                                                  data_card['NSHOW'],
                                                  data_card['THETAP'],
                                                  pointing_angle,
                                                  pointing,
                                                  type_of_hist),
           np.transpose([mids, hist_c[0], hist_c[1], hist_f[0], hist_f[1]]),
           newline='\n',
           fmt="%7.2f %1.6e %1.6e %1.6e %1.6e",
           header=(' Num_showers:%i \n E_primary (GeV): %i \n ID_prim_particle: %s \n Seeds: %i, %i \n'
                   % (data_card['NSHOW'],
                      data_card['ERANGE'],
                      data_card['PRMPAR'],
                      data_card['SEED1'],
                      data_card['SEED2'])
                   +
                   ' Theta prim. part. incidence: %i deg \n Obs level (m): %i \n Atmosp model: %i'
                   % (data_card['THETAP'],
                      data_card['OBSLEV'],
                      data_card['ATMOD'])
                   +
                   '\n Cerenk_bunch_size: %i \n Fluor_bunch_size: %i'
                   % (data_card['CERSIZ'], data_card['FLSIZE'])
                   +
                   '\n Distance to shower axis (m) | Phot_density_Cher/fluor (1/m2)'
                   )
           )
print('Histogram stored into: %iGeV_%ish_%ideg_%i%s_hist_%s.dat' %
      (data_card['ERANGE'], data_card['NSHOW'], data_card['THETAP'],
       pointing_angle, pointing, type_of_hist)
      )
