""" Module defining a simple image based on a NumPy array. """

import  ctypes
import  math
import  threading

import  wx
import  numpy as np

from    koko.c.libfab       import libfab
from    koko.c.multithread  import multithread
from    koko.c.path         import Path as Path_

from    koko.fab.path       import Path


class Image(object):
    ''' @class Image
        @brief Wraps a numpy array (indexed by row, column) and various parameters
    '''

    def __init__(self, w, h, channels=1, depth=8):
        """ @brief Image constructor
            @param w Image width in pixels
            @param h Image height in pixels
            @param channels Number of channels (1 or 3)
            @param depth Image depth (8, 16, 32, or 'f' for floating-point)
        """

        if depth == 8:      dtype = np.uint8
        elif depth == 16:   dtype = np.uint16
        elif depth == 32:   dtype = np.uint32
        elif depth == 'f':  dtype = np.float32
        else:   raise ValueError("Invalid bit depth (must be 8, 16, or 'f')")

        ## @var array
        # NumPy array storing image pixels
        if channels == 1 or channels == 3:
            self.array = np.zeros( (h, w, channels), dtype=dtype )
        else:
            raise ValueError('Invalid number of channels (must be 1 or 3)')

        ## @var width
        # Width in pixels
        self.width      = w

        ## @var height
        # Height in pixels
        self.height     = h

        ## @var _channels
        # Number of image channels (1 or 3)
        self._channels  = channels

        ## @var _depth
        # Image bit depth (8, 16, 32, or 'f' for floating-point)
        self._depth     = depth

        ## @var color
        # Base image color (used when merging black-and-white images)
        self.color      = None

        for b in ['xmin','ymin','zmin','xmax','ymax','zmax']:
            setattr(self, b, None)

        ## @var _wx
        # wx.Image representation of this image
        self._wx = None

        ## @var filename
        # String representing filename or None
        self.filename = None

    def __eq__(self, other):
        eq = self.array == other.array
        if eq is False: return False
        else:           return eq.all()

    def copy(self, channels=None, depth=None):
        """ @brief Copies an image, optionally changing depth and channel count.
            @returns A copied Image
            @param channels Channel count
            @param depth Depth count
        """

        out = self.__class__(
            self.width, self.height,
            self.channels, self.depth
        )
        out.array = self.array.copy()
        for a in ['xmin','ymin','zmin',
                  'xmax','ymax','zmax']:
            setattr(out, a, getattr(self, a))
        out.color = [c for c in self.color] if self.color else None
        if channels is not None:    out.channels = channels
        if depth is not None:       out.depth = depth
        return out


    def colorize(self, r, g, b):
        """ @brief Creates a colorized image from a black-and-white image.
            @param r Red level (0-1)
            @param b Blue level (0-1)
            @param g Green level (0-1)
            @returns A three-channel 8-bit colorized Image
        """

        if self.channels != 1:
            raise ValueError('Invalid image type for colorizing cut ' +
                '(requires 1-channel image)')

        out = self.__class__(
            self.width, self.height, channels=3, depth=8,
        )

        out.array = np.dstack(
            np.ones((self.width, self.height), dtype=np.uint8)*r,
            np.ones((self.width, self.height), dtype=np.uint8)*g,
            np.ones((self.width, self.height), dtype=np.uint8)*b
        ) * self.copy(channels=3, depth=8).array

        return out


    def __getitem__(self, index):
        """ @brief Overloads image indexing to get pixels
        """
        return self.array[index]


    @property
    def wximg(self):
        """ @brief Returns (after constructing, if necessary) a wx.Image representation of this Image.
        """
        if self._wx is None:
            img = self.copy(channels=3, depth=8)
            self._wx = wx.ImageFromBuffer(img.width, img.height, img.array)
        return self._wx


    @property
    def channels(self): return self._channels
    @channels.setter
    def channels(self, c):
        """ @brief Sets the number of channels, convering as needed.
        """
        if c == self._channels: return
        elif c == 1 and self._channels == 3:
            self.array = np.array(np.sum(self.array, axis=2)/3,
                                  dtype=self.array.dtype)
        elif c == 3 and self._channels == 1:
            self.array = np.dstack((self.array,self.array,self.array))
        else:
            raise ValueError('Invalid channel count (must be 1 or 3)')
        self._channels = c


    @property
    def depth(self):    return self._depth
    @depth.setter
    def depth(self, d):
        """ @brief Sets the image depth, convering as needed.
        """
        if d == self._depth:    return
        elif d == 8:
            if self._depth == 16:
                self.array = np.array(self.array >> 8, dtype=np.uint8)
            elif self._depth == 32:
                self.array = np.array(self.array >> 24, dtype=np.uint8)
            elif self._depth == 'f':
                self.array = np.array(self.array*255, dtype=np.uint8)
        elif d == 16:
            if self._depth == 8:
                self.array = np.array(self.array << 8, dtype=np.uint16)
            elif self._depth == 32:
                self.array = np.array(self.array >> 16, dtype=np.uint16)
            elif self._depth == 'f':
                self.array = np.array(self.array*65535, dtype=np.uint16)
        elif d == 32:
            if self._depth == 8:
                self.array = np.array(self.array << 24, dtype=np.uint32)
            elif self._depth == 16:
                self.array = np.array(self.array << 16, dtype=np.uint32)
            elif self._depth == 'f':
                self.array = np.array(self.array*4294967295., dtype=np.uint32)
        elif d == 'f':
            if self._depth == 8:
                self.array = np.array(self.array/255., dtype=np.float32)
            elif self._depth == 16:
                self.array = np.array(self.array/65535., dtype=np.float32)
            elif self._depth == 32:
                self.array = np.array(self.array/4294967295., dtype=np.float32)
        else:
            raise ValueError("Invalid depth (must be 8, 16, 32, or 'f')")
        self._depth = d


    @property
    def dx(self):
        try:                return self.xmax - self.xmin
        except TypeError:   return None
    @property
    def dy(self):
        try:                return self.ymax - self.ymin
        except TypeError:   return None
    @property
    def dz(self):
        try:                return self.zmax - self.zmin
        except TypeError:   return None


    @property
    def pixels_per_mm(self):
        """ @brief Parameter to get image pixels/mm
        """
        if self.width > self.height and self.dx is not None:
            return self.width/self.dx
        elif self.dy is not None:
            return self.height/self.dy
        else:       return None
    @property
    def mm_per_pixel(self):
        """ @brief Parameter to get image mm/pixel
        """
        if self.width > self.height and self.dx is not None:
            return self.dx/self.width
        elif self.dy is not None:
            return self.dy/self.height
        else:       return None

    @property
    def bits_per_mm(self):
        if self.dz is None or self.depth is 'f': return None
        elif self.depth == 8:   return 255. / self.dz
        elif self.depth == 16:  return 65535. / self.dz
        elif self.depth == 32:  return 4294967295. / self.dz
    @property
    def mm_per_bit(self):
        if self.dz is None or self.depth is 'f': return None
        elif self.depth == 8:   return self.dz / 255.
        elif self.depth == 16:  return self.dz / 65535.
        elif self.depth == 32:  return self.dz / 4294967295.

    @property
    def dtype(self):
        """ @returns Pixel data type (from ctypes)
        """
        if self.array.dtype == np.uint8:        return ctypes.c_uint8
        elif self.array.dtype == np.uint16:     return ctypes.c_uint16
        elif self.array.dtype == np.uint32:     return ctypes.c_uint32
        elif self.array.dtype == np.float32:    return ctypes.c_float

    @property
    def row_ptype(self):
        """ @returns Row pointer type
        """
        if self.channels == 3:  return ctypes.POINTER(self.dtype*3)
        else:                   return ctypes.POINTER(self.dtype)

    @property
    def pixels(self):
        """ @brief Creates a ctypes pixel array that looks into the NumPy array.
            @returns Pointer of type **dtype if channels is 1, **dtype[3] if channels is 3
        """

        # Make sure that the array is contiguous in memory
        if not self.array.flags['C_CONTIGUOUS']:
            self.array = np.ascontiguousarray(self.array)

        pixels = (self.row_ptype*self.height)()

        start = self.array.ctypes.data
        stride = self.array.ctypes.strides[0]

        for j in range(self.height):
            pixels[self.height-j-1] = ctypes.cast(
                start + j*stride, self.row_ptype
            )

        return pixels


    @property
    def flipped_pixels(self):
        """ @brief Identical to self.pixels, but flipped on the y axis.
        """
        return (self.row_ptype*self.height)(*self.pixels[::-1])



    @classmethod
    def merge(cls, images):
        """ @brief Merges a set of greyscale images into an RGB image.
            @details The input images need to have the same z bounds and scale,
            otherwise the merge will produce something nonsensical.
            @param images List of Images
            @returns 8-bit 3-channel combined Image
        """

        if not images or not all(isinstance(i, Image) for i in images):
            raise TypeError('Invalid argument to merge')

        xmin = min(i.xmin for i in images)
        xmax = max(i.xmax for i in images)
        ymin = min(i.ymin for i in images)
        ymax = max(i.ymax for i in images)

        # Find the target resolution based on the largest image side
        # (to avoid discretization error if we have small and large images)
        largest = 0
        resolution = 0
        for i in images:
            if i.width > largest:
                resolution = i.width / i.dx
                largest = i.width
            elif i.height > largest:
                resolution = i.height / i.dy
                largest = i.height

        out = cls(
            int((xmax-xmin)*resolution),
            int((ymax-ymin)*resolution),
            channels=3, depth=8,
        )
        out.xmin, out.xmax = xmin, xmax
        out.ymin, out.ymax = ymin, ymax
        out.zmin, out.zmax = images[0].zmin, images[0].zmax

        depth = cls(out.width, out.height)

        for img in images:
            img = img.copy(depth=8)

            x  = max(0, int((img.xmin - out.xmin)*resolution))
            ni = min(out.width - x, img.width)
            y  = max(0, int((img.ymin - out.ymin)*resolution))
            nj = min(out.height - y, img.height)

            R, G, B = [c/255. for c in img.color] if img.color else [1, 1, 1]

            libfab.depth_blit(
                img.pixels, depth.pixels, out.pixels,
                x, y, ni, nj,
                R, G, B
            )

        return out


    @classmethod
    def load(cls, filename):
        """ @brief Loads a png from a file as a 16-bit heightmap.
            @param filename Name of target .png image
            @returns A 16-bit, 1-channel image.
        """

        # Get various png parameters so that we can allocate the
        # correct amount of storage space for the new image
        dx, dy, dz = ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
        ni, nj = ctypes.c_int(), ctypes.c_int()
        libfab.load_png_stats(filename, ni, nj, dx, dy, dz)

        # Create a python image data structure
        img = cls(ni.value, nj.value, channels=1, depth=16)

        # Add bounds to the image
        if math.isnan(dx.value):
            print 'Assuming 72 dpi for x resolution.'
            img.xmin, img.xmax = 0, 72*img.width/25.4
        else:   img.xmin, img.xmax = 0, dx.value

        if math.isnan(dy.value):
            print 'Assuming 72 dpi for y resolution.'
            img.ymin, img.ymax = 0, 72*img.height/25.4
        else:   img.ymin, img.ymax = 0, dy.value

        if not math.isnan(dz.value):    img.zmin, img.zmax = 0, dz.value

        # Load the image data from the file
        libfab.load_png(filename, img.pixels)
        img.filename = filename

        return img


    def save(self, filename):
        """ @brief Saves an image as a png
            @detail 3-channel images are saved as RGB images without metadata; 1-channel images are saved as 16-bit greyscale images with correct bounds and 'zmax', 'zmin' fields as text chunks.
        """
        if filename[-4:].lower() != '.png':
            raise ValueError('Image must be saved with .png extension')

        if self.channels == 3:
            self.wximg.SaveFile(filename, wx.BITMAP_TYPE_PNG)
        else:
            img = self.copy(channels=1, depth=16)
            bounds = (ctypes.c_float*6)(
                self.xmin, self.ymin, self.zmin if self.zmin else float('nan'),
                self.xmax, self.ymax, self.zmax if self.zmax else float('nan')
            )
            libfab.save_png16L(filename, self.width, self.height,
                                bounds, img.flipped_pixels)


    def threshold(self, z):
        """ @brief Thresholds a heightmap at a given depth.
            @brief Can only be called on an 8, 16, or 32-bit image.
            @param z Z depth (in image units)
            @returns Thresholded image (8-bit, single-channel)
        """

        out = self.__class__(self.width, self.height, channels=1, depth=8)
        for b in ['xmin','xmax','ymin','ymax']:
            setattr(out, b, getattr(self, b))
        out.zmin = out.zmax = z

        if self.depth == 8:     k = int(255*(z-self.zmin) / self.dz)
        elif self.depth == 16:  k = int(65535*(z-self.zmin) / self.dz)
        elif self.depth == 32:  k = int(4294967295*(z-self.zmin) / self.dz)
        elif self.depth == 'f':
            raise ValueError('Cannot take threshold of floating-point image')

        out.array = np.array(self.array >= k, dtype=np.uint8)

        return out


    def finish_cut(self, bit_diameter, overlap, bit_type):
        ''' Calculates xy and yz finish cuts on a 16-bit heightmap
        '''

        if self.depth != 16 or self.channels != 1:
            raise ValueError('Invalid image type for finish cut '+
                '(requires 16-bit, 1-channel image)')

        ptr = ctypes.POINTER(ctypes.POINTER(Path_))()
        path_count = libfab.finish_cut(
            self.width, self.height, self.pixels,
            self.mm_per_pixel, self.mm_per_bit,
            bit_diameter, overlap, bit_type, ptr)

        paths = [Path.from_ptr(ptr[i]) for i in range(path_count)]
        libfab.free_paths(ptr, path_count)

        return paths


    def contour(self, bit_diameter, count=1, overlap=0.5):
        """ @brief Finds a set of isolines on a distance field image.
            @param bit_diameter Tool diameter (in mm)
            @param count Number of offsets
            @param overlap Overlap between offsets
            @returns A list of Paths
        """
        if self.depth != 'f' or self.channels != 1:
            raise ValueError('Invalid image type for contour cut '+
                '(requires floating-point, 1-channel image)')

        max_distance = max(self.array.flatten())
        levels = [bit_diameter/2]
        step = bit_diameter * overlap
        if count == -1:
            while levels[-1] < max_distance:
                levels.append(levels[-1] + step)
            levels[-1] = max_distance
        else:
            for i in range(count-1):
                levels.append(levels[-1] + step)
        levels = (ctypes.c_float*len(levels))(*levels)

        ptr = ctypes.POINTER(ctypes.POINTER(Path_))()
        path_count = libfab.find_paths(
            self.width, self.height, self.pixels,
            1./self.pixels_per_mm, len(levels),
            levels, ptr)

        paths = [Path.from_ptr(ptr[i]) for i in range(path_count)]
        libfab.free_paths(ptr, path_count)

        return Path.sort(paths)


    def distance(self, threads=2):
        """ @brief Finds the distance transform of an input image.
            @param threads Number of threads to use
            @returns A one-channel floating-point image
        """
        input = self.copy(depth=8)

        # Temporary storage for G lattice
        g = self.__class__(
            self.width, self.height,
            channels=1, depth=32
        )
        ibounds = [int(t/float(threads)*self.width) for t in range(threads)]
        ibounds = zip(ibounds, ibounds[1:] + [self.width])

        args1 = [(i[0], i[1], self.width, self.height, input.pixels, g.pixels)
                 for i in ibounds]

        multithread(libfab.distance_transform1, args1)

        del input

        output = self.copy(depth='f')

        jbounds = [int(t/float(threads)*self.height) for t in range(threads)]
        jbounds = zip(jbounds, jbounds[1:] + [self.height])

        args2 = [(j[0], j[1], self.width, self.pixels_per_mm,
                 g.pixels, output.pixels) for j in jbounds]

        multithread(libfab.distance_transform2, args2)

        output.zmin = output.zmax = None

        return output


