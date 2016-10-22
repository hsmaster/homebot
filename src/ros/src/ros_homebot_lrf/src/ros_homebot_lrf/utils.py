try:
    from PIL import Image
    import numpy as np
except ImportError:
    pass

def compress_list(lst, bins=10, as_int=0, ignore_negative=True):
    """
    Averages a list of numbers into smaller bins.
    """
    new_lst = []
    chunk_size = int(round(len(lst)/float(bins)))
    for bin_part in xrange(bins):
        samples = lst[bin_part*chunk_size:bin_part*chunk_size+chunk_size]
        if ignore_negative:
            samples = [_ for _ in samples if _ >= 0]
            if not samples:
                samples = [-1]
        new_lst.append(sum(samples)/float(len(samples)))
    if as_int:
        new_lst = [int(round(_)) for _ in new_lst]
    return new_lst

def list_to_str(lst, decimals=2, digits=7):
    return ', '.join(('%+0'+str(digits)+'.'+str(decimals)+'f') % v for v in lst)

def only_red(im):
    """
    Strips out everything except red.
    """
    im = im.convert('RGBA')
    data = np.array(im)
    red, green, blue, alpha = data.T
    im2 = Image.fromarray(red.T)
    return im2

def normalize(arr):
    """
    Linear normalization
    http://en.wikipedia.org/wiki/Normalization_%28image_processing%29
    """
    arr = arr.astype('float')
    # Do not touch the alpha channel
    for i in range(3):
        minval = arr[..., i].min()
        maxval = arr[..., i].max()
        if minval != maxval:
            arr[..., i] -= minval
            arr[..., i] *= (255.0/(maxval-minval))
    return arr
