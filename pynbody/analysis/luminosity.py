"""

luminosity
==========

Calculates luminosities -- NEEDS DOCUMENTATION

"""

import numpy as np
try :
    import scipy, scipy.weave
    from scipy.weave import inline
except ImportError :
    pass

import os
from ..array import SimArray

def calc_mags(simstars, band='v') :
    """

    calc mags -- documentation placeholder

    """

    # find data file in PYTHONPATH
    # data is from http://stev.oapd.inaf.it/cgi-bin/cmd
    # Padova group stellar populations Marigo et al (2008), Girardi et al (2010)
    lumfile = os.path.join(os.path.dirname(__file__),"cmdlum.npz")
    if os.path.exists(lumfile) :
        # import data
        # print "Loading luminosity data"
        lums=np.load(lumfile)
    else :
        raise IOError, "cmdlum.npz (magnitude table) not found"

    #calculate star age
    #import pdb; pdb.set_trace()
    age_star=(simstars.properties['time'].in_units('yr', **simstars.conversion_context())-simstars['tform'].in_units('yr'))
    # allocate temporary metals that we can play with
    metals = simstars['metals']
    # get values off grid to minmax
    age_star[np.where(age_star < np.min(lums['ages']))] = np.min(lums['ages'])
    age_star[np.where(age_star > np.max(lums['ages']))] = np.max(lums['ages'])
    metals[np.where(metals < np.min(lums['mets']))] = np.min(lums['mets'])
    metals[np.where(metals > np.max(lums['mets']))] = np.max(lums['mets'])
    #interpolate
    code = file(os.path.join(os.path.dirname(__file__),'interpolate.c')).read()
    age_grid = np.log10(lums['ages'])
    n_age_grid = len(age_grid)
    met_grid = lums['mets']
    n_met_grid = len(met_grid)
    mag_grid = lums[band]
    n_stars = len(metals)
    output_mags = np.zeros(n_stars)
    # before inlining, the views on the arrays must be standard np.ndarray
    # otherwise the normal numpy macros are not generated
    age_star,metals,age_grid,met_grid = [q.view(np.ndarray) for q in 
                                         np.log10(age_star),
                                         metals,age_grid,met_grid]
    #print "Calculating magnitudes"
    inline(code,['met_grid','n_met_grid','age_grid','n_age_grid',
                 'age_star','metals','n_stars','mag_grid','output_mags'])
    try :
        return output_mags - 2.5*np.log10(simstars['massform'].in_units('Msol'))
    except KeyError, ValueError:
        return output_mags - 2.5*np.log10(simstars['mass'].in_units('Msol'))


def halo_mag(sim,band='v') :
    return -2.5*np.log10(np.sum(10.0**(-0.4*sim.star[band+'_mag'])))

def halo_lum(sim,band='v') :
    return np.sum(10.0**((5.8-sim.star[band+'_mag'])/2.5))

def half_light_r(sim,band='v'):
    import pynbody, pynbody.filt as f
    half_l = halo_lum(sim,band=band) * 0.5
    #print "half_l: %g"%half_l
    max_high_r = np.max(sim.star['r'])
    test_r = 0.5*max_high_r
    testrf = f.LowPass('r',test_r)
    min_low_r = 0.0
    test_l = halo_lum(sim[testrf],band=band)
    it=0
    while ((np.abs(test_l - half_l)/half_l) > 0.01):
        it = it+1
        if (it > 20):
            break
        #error = np.abs(test_l - half_l)/half_l
        #print "iteration: %d error: %6.2g test_l: %g test_r: %g"%(it,error,test_l,test_r)
        if (test_l > half_l):
            test_r = 0.5*(min_low_r + test_r)
        else :
            test_r = (test_r + max_high_r)*0.5
        testrf = f.LowPass('r',test_r)
        test_l = halo_lum(sim[testrf],band=band)

        if (test_l > half_l):
            max_high_r = test_r
        else :
            min_low_r = test_r
        
    return test_r*sim.star['r'].units
