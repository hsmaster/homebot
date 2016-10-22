#from __future__ import print_function
import os
import sys
import time
import warnings
from math import pi, tan, atan

from PIL import Image
from PIL import ImageFilter
from PIL.ImageChops import difference
import numpy as np
import yaml
from scipy import stats

from . import utils

TOP = 'top'
BOTTOM = 'bottom'

def percent_error(expected, actual):
    return (expected - actual)/float(actual)*100

def calibrate(conf_fn):

    conf = yaml.load(open(conf_fn))

    readings = conf['readings']

    distances = conf['distances'] # {position: distance}
    
    h = float(conf['h'])
    
    image_width = int(conf['image_width'])

    image_height = int(conf['image_height'])
    
    laser_position = conf['laser_position']
    
    measurements = []
    for col in sorted(distances.keys()):
        actual_d = distances[col]
        pix_dist = readings[col]
        if pix_dist < 0:
            warnings.warn('Ignoring reading for column %i that has a negative value.' % col)
            continue
        pfc = abs(pix_dist - image_height/2)
        #theta = atan(h/actual_d)
        measurements.append((actual_d, pfc))
        
    assert measurements, 'No measurements!'
    
    #print '\nmeasurements:', measurements
    
    x = [_pix_dist for _actual_d, _pix_dist in measurements]
    y = [atan(h/_actual_d) for _actual_d, _pix_dist in measurements]
        
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    #print '\nlinreg:', slope, intercept, r_value, p_value, std_err
    # y = m * x + b => theta = rpc * pfc + ro
    # slope = m = rpc
    # intercept = b = ro
    rpc = slope
    ro = intercept
    print('\n--rpc=%s --ro=%s\n' % (slope, intercept))
    return rpc, ro, h, laser_position

class LaserRangeFinder(object):
    
    def __init__(self, **kwargs):
        
        # Camera's verticial field-of-view in degrees.
        self.vert_fov_deg = float(kwargs.pop('vert_fov_deg', 41.41))
        
        # Camera's horizontal field-of-view in degrees.
        self.horz_fov_deg = float(kwargs.pop('horz_fov_deg', 53.50))
        
        # Radian per pixel pitch.
        self.rpc = float(kwargs.pop('rpc', 0.00103721750257))
        
        # Radian offset.
        self.ro = float(kwargs.pop('ro', -0.21))
        
        # Distance between camera center and laser.
        self.h = float(kwargs.pop('h', 22.5)) # mm
        
        # If true, laser pixels that are less bright than the mean brightness minus
        # a factor of the standard deviation will be considered noise and ignored.
        self.filter_outliers = bool(kwargs.pop('filter_outliers', True))
        
        # The number of standard deviations below the mean above which a laser pixel will
        # be considered valid.
        self.outlier_filter_threshold = float(kwargs.pop('outlier_filter_threshold', 1))
        
        self.blur_radius = int(kwargs.pop('blur_radius', 2))
        
        self.laser_position = kwargs.pop('laser_position', BOTTOM)
        
        self.normalize_brightness = kwargs.pop('normalize_brightness', False)
        
        self.track_progress_images = kwargs.pop('track_progress_images', False)
        
        self.out1 = None
        self.out2 = None
        self.out3 = None
        
    def get_distance(self, off_img, on_img, save_images_dir=None, **kwargs):
        """
        Calculates distance using two images.
        
        Keyword arguments:
        
            off_img := a stream or filename of an image assumed to have no laser projection
            on_img := a stream of filename of an image assumed to have a laser projection
            
        Returns tuple of the form:
        
            ([distances], [row per column containing laser])
        """
        
        out1 = None
        out2 = None
        out3 = None
        
        if save_images_dir:
            save_images_dir = os.path.expanduser(save_images_dir)
            assert os.path.isdir(save_images_dir), 'Invalid directory: %s' % save_images_dir
        
        if isinstance(off_img, basestring):
            off_img = Image.open(os.path.expanduser(off_img)).convert('RGB')
            
        if isinstance(on_img, basestring):
            on_img = Image.open(os.path.expanduser(on_img)).convert('RGB')
        
        # Normalize image brightness.
        t0 = time.time()
        if self.normalize_brightness:
            off_img = Image.fromarray(utils.normalize(np.array(off_img)).astype('uint8'), 'RGB')
            if save_images_dir:
                off_img.save(os.path.join(
                    save_images_dir, kwargs.pop('off_img_norm_fn', 'off_img_norm.jpg')))
            on_img = Image.fromarray(utils.normalize(np.array(on_img)).astype('uint8'), 'RGB')
            if save_images_dir:
                on_img.save(os.path.join(
                    save_images_dir, kwargs.pop('on_img_norm_fn', 'on_img_norm.jpg')))
#         print 'normalize brightness td:', time.time() - t0
        
        # Strip out non-red channels.
        t0 = time.time()
        off_img = utils.only_red(off_img)
        if save_images_dir:
            off_img.save(os.path.join(
                save_images_dir, kwargs.pop('off_img_norm_red_fn', 'off_img_norm_red.jpg')))
        on_img = utils.only_red(on_img)
        if save_images_dir:
            on_img.save(os.path.join(
                save_images_dir, kwargs.pop('on_img_norm_red_fn', 'on_img_norm_red.jpg')))
#         print 'red only td:', time.time() - t0
                
        # Calculate difference.
        # The laser line should now be the brightest pixels.
        t0 = time.time() 
        diff_img = difference(off_img, on_img)
        if save_images_dir:
            diff_img.save(os.path.join(
                save_images_dir, kwargs.pop('diff_img_fn', 'diff_img.jpg')))
#         print 'img difference td:', time.time() - t0
        
        if self.blur_radius:
            t0 = time.time()
            diff_img = diff_img.filter(ImageFilter.GaussianBlur(radius=self.blur_radius))
            if save_images_dir:
                diff_img.save(os.path.join(
                    save_images_dir, kwargs.pop('diff_blur_img_fn', 'diff2_img.jpg')))
#             print 'blurring td:', time.time() - t0
        
        # Estimate the pixels that are the laser by
        # finding the row in each column with maximum brightness.
        t0 = time.time()
        width, height = size = diff_img.size
        x = diff_img.convert('L')
        if save_images_dir or self.track_progress_images:
            # If saving a result image, create an empty black image which we'll later map
            # the laser line into.
            out1 = Image.new("L", x.size, "black")
            pix1 = out1.load()
            out2 = Image.new("L", x.size, "black")
            pix2 = out2.load()
            out3 = Image.new("L", x.size, "black")
            pix3 = out3.load()
        y = np.asarray(x.getdata(), dtype=np.float64).reshape((x.size[1], x.size[0]))
#         laser_measurements = [0]*width # [row]
#         laser_brightness = [0]*width # [brightness]
#         for col_i in xrange(y.shape[1]):
#             col_max = max([(y[row_i][col_i], row_i) for row_i in xrange(y.shape[0])])
#             col_max_brightness, col_max_row = col_max
#             laser_measurements[col_i] = col_max_row
#             laser_brightness[col_i] = col_max_brightness
        laser_measurements = np.argmax(y, axis=0)
        if self.filter_outliers:
            laser_brightness = np.amax(y, axis=0)
#         print 'pixel estimate td:', time.time() - t0
            
        # Ignore all columns with dim brightness outliers.
        # These usually indicate a region where the laser is absorbed or otherwise scattered
        # too much to see.
        t0 = time.time()
        if self.filter_outliers:
            brightness_std = np.std(laser_brightness)
            brightness_mean = np.mean(laser_brightness)
            outlier_level = brightness_mean - brightness_std * self.outlier_filter_threshold
        final_measurements = [-1]*width # [brightest row]
        for col_i, col_max_row in enumerate(laser_measurements):
        
            if save_images_dir or self.track_progress_images:
                pix1[col_i, col_max_row] = 255
                    
            if not self.filter_outliers \
            or (self.filter_outliers and laser_brightness[col_i] > outlier_level):
                if save_images_dir or self.track_progress_images:
                    pix2[col_i, col_max_row] = 255
                    
            # Assuming the laser is mounted below the camera,
            # we can assume all points above the centerline are noise.
            if self.laser_position == BOTTOM and col_max_row < height/2:
                continue
            elif self.laser_position == TOP and col_max_row > height/2:
                continue
                
            if not self.filter_outliers \
            or (self.filter_outliers and laser_brightness[col_i] > outlier_level):
                if save_images_dir or self.track_progress_images:
                    pix3[col_i, col_max_row] = 255
                final_measurements[col_i] = col_max_row
#         print 'final estimation td:', time.time() - t0
        
        self.out1 = out1
        self.out2 = out2
        self.out3 = out3
        if save_images_dir:
            out1.save(os.path.join(save_images_dir, kwargs.pop('line_img1_fn', 'line1.jpg')))
            out2.save(os.path.join(save_images_dir, kwargs.pop('line_img2_fn', 'line2.jpg')))
            out3.save(os.path.join(save_images_dir, kwargs.pop('line_img3_fn', 'line3.jpg')))
        
        # Convert the pixel measurements to distance.
        t0 = time.time()
        D_lst = pixels_to_distance(
            pixel_rows=final_measurements,
            rpc=self.rpc,
            ro=self.ro,
            h=self.h,
            max_height=height,
            max_width=width,
        )
#         print 'pixels to distance td:', time.time() - t0
            
        return D_lst, final_measurements

def pixels_to_distance(pixel_rows, rpc, ro, h, max_height, max_width):
    """
    Converts a list integers representing the row in each column where a laser line was detected
    into a list of real-world distances.
    
    Technique and code based on:
    
        https://sites.google.com/site/todddanko/home/webcam_laser_ranger
        https://shaneormonde.wordpress.com/2014/01/25/webcam-laser-rangefinder/
    
    Arguments:
    
        pixel_rows := list of integers
        
        rpc := radians per pixel pitch
        
        ro := radian offset (compensates for alignment errors)
            
        h := distance between laser and camera
        
        max_height := camera image height
        
        max_width := camera image width
        
    Math:
    
        for each pixel:
            pfc = number of pixels from center of focal plane
            theta = pfc*rpc + ro
            D = h/tan(theta)
        
    """
    D_lst = []
    for laser_row_i in pixel_rows:
        if laser_row_i < 0:
            # No laser could be detected in this column.
            D_lst.append(laser_row_i)
        else:
            pfc = abs(laser_row_i - max_height/2)
            theta = rpc * pfc + ro
            if theta:
                D = h/tan(theta)
            else:
                D = -1
            D_lst.append(D)
    return D_lst
