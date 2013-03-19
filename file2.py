# -*- coding: utf-8 -*-
"""
Created on Mon Mar 18 12:01:16 2013

@author: FlorianFetzer
"""

import numpy as np
from PIL import Image

path = 'C:\Users\FlorianFetzer\Desktop\Sample Data\Cubert\Settings\Dark.jpg'

di = Image.open(path)

im1arr = np.asarray(di)

print im1arr