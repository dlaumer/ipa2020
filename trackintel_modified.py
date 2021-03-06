#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Trackintel
    This file is mostly refered to the trackintel package of MIE lab except
    1 - a maximum time threshold is added to detect stay points in extract_staypoints_ipa
    2 - the final stay point is treated as the stay point if it meets the minimum time threshold in extract_staypoints_ipa
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString

from shapely.geometry import Point
from sklearn.cluster import DBSCAN

from trackintel.geogr.distances import haversine_dist


def extract_staypoints_ipa(positionfixes, method='sliding',
                       dist_threshold=50, time_threshold=5 * 60, timemax_threshold=12 * 3600,
                       epsilon=100, dist_func=haversine_dist, eps=None, num_samples=None):
    """Extract staypoints from positionfixes.
    This function modifies the positionfixes and adds staypoint_ids.
    Parameters
    ----------
    num_samples
    eps
    positionfixes : GeoDataFrame
        The positionfixes have to follow the standard definition for positionfixes DataFrames.
    method : {'sliding' or 'dbscan'}
        The following methods are available to extract staypoints from positionfixes:
        'sliding' : Applies a sliding window over the data.
        'dbscan' : Uses the DBSCAN algorithm to find clusters of staypoints.
    dist_threshold : float
        The distance threshold for the 'sliding' method, i.e., how far someone has to travel to
        generate a new staypoint.
    time_threshold : float
        The time threshold for the 'sliding' method in seconds, i.e., how long someone has to 
        stay within an area to consider it as a staypoint.
    epsilon : float
        The epsilon for the 'dbscan' method.
    dist_func : function
        A function that expects (lon_1, lat_1, lon_2, lat_2) and computes a distance in meters.
    Returns
    -------
    GeoDataFrame
        A new GeoDataFrame containing points where a person spent some time.
    Examples
    --------
    >>> psfs.as_positionfixes.extract_staypoints('sliding', dist_threshold=100)
    References
    ----------
    Zheng, Y. (2015). Trajectory data mining: an overview. ACM Transactions on Intelligent Systems 
    and Technology (TIST), 6(3), 29.
    Li, Q., Zheng, Y., Xie, X., Chen, Y., Liu, W., & Ma, W. Y. (2008, November). Mining user 
    similarity based on location history. In Proceedings of the 16th ACM SIGSPATIAL international 
    conference on Advances in geographic information systems (p. 34). ACM.
    """
    if 'id' not in positionfixes.columns:
        positionfixes['id'] = positionfixes.index

    ret_staypoints = pd.DataFrame(columns=['started_at', 'finished_at', 'geom', 'id'])

    if method == 'sliding':
        # Algorithm from Li et al. (2008). For details, please refer to the paper.
        staypoint_id_counter = 0
        positionfixes['staypoint_id'] = -1  # this marks all that are not part of a SP

        for user_id_this in positionfixes['user_id'].unique():

            positionfixes_user_this = positionfixes.loc[
                positionfixes['user_id'] == user_id_this]  # this is no copy

            pfs = positionfixes_user_this.sort_values('tracked_at').to_dict('records')
            num_pfs = len(pfs)

            posfix_staypoint_matching = {}

            i = 0
            j = 0  # is zero because it gets incremented in the beginning
            while i < num_pfs:
                if j == num_pfs:
                    # We're at the end, this can happen if in the last "bin", 
                    # the dist_threshold is never crossed anymore.
                    break
                else:
                    j = i + 1
                while j < num_pfs:
                    
                    dist = haversine_dist(pfs[i]['geom'].x, pfs[i]['geom'].y,
                                      pfs[j]['geom'].x, pfs[j]['geom'].y)
                    
                    if (dist > dist_threshold):
                        delta_t = (pfs[j]['tracked_at'] - pfs[i]['tracked_at']).total_seconds()
                        
                        # Compare with the maximum time threshold
                        if (delta_t > time_threshold):                                                   
                            if (delta_t > timemax_threshold):
                                hrdiff = []
                                hrsum = 0
                                for x in range(i,j): 
                                    hrdiff.append((pfs[x+1]['tracked_at']-pfs[x]['tracked_at']).total_seconds())  
                                i0 = i
                                for mid in range(0,j-i0):
                                    hrsum += hrdiff[mid]                                   
                                    if(hrsum > timemax_threshold or mid == j-i0-1):
                                        staypoint = {}
                                        staypoint['user_id'] = pfs[i]['user_id']
                                        staypoint['geom'] = Point(np.mean([pfs[k]['geom'].x for k in range(i, i0+mid+1)]),
                                                                  np.mean([pfs[k]['geom'].y for k in range(i, i0+mid+1)]))
                                        if 'elevation' in pfs[i].keys():
                                            staypoint['elevation'] = np.mean([pfs[k]['elevation'] for k in range(i, i0+mid+1)])
                                        if 'velocity' in pfs[i].keys():
                                            staypoint['velocity'] = np.mean([pfs[k]['velocity'] for k in range(i, i0+mid+1)])
                                        staypoint['started_at'] = pfs[i]['tracked_at']
                                        staypoint['finished_at'] = pfs[i0+mid+1]['tracked_at']  # TODO: should this not be j-1? because j is not part of the staypoint. DB: Changed                   
                                        staypoint['id'] = staypoint_id_counter
                                        # store matching 
                                        posfix_staypoint_matching[staypoint_id_counter] = [pfs[k]['id'] for k in range(i, i0+mid+1)]
                                        staypoint_id_counter += 1
                                        # add staypoint
                                        ret_staypoints = ret_staypoints.append(staypoint, ignore_index=True)
                                                                               
                                        i = i0+mid+1
                                        hrsum = 0
                            else:                                  
                                staypoint = {}
                                staypoint['user_id'] = pfs[i]['user_id']
                                staypoint['geom'] = Point(np.mean([pfs[k]['geom'].x for k in range(i, j)]),
                                                          np.mean([pfs[k]['geom'].y for k in range(i, j)]))
                                if 'elevation' in pfs[i].keys():
                                    staypoint['elevation'] = np.mean([pfs[k]['elevation'] for k in range(i, j)])
                                if 'velocity' in pfs[i].keys():
                                    staypoint['velocity'] = np.mean([pfs[k]['velocity'] for k in range(i, j)])
                                staypoint['started_at'] = pfs[i]['tracked_at']
                                staypoint['finished_at'] = pfs[j]['tracked_at']  # TODO: should this not be j-1? because j is not part of the staypoint. DB: Changed                   
                                staypoint['id'] = staypoint_id_counter
                                # store matching 
                                posfix_staypoint_matching[staypoint_id_counter] = [pfs[k]['id'] for k in range(i, j)]
                                staypoint_id_counter += 1
                                # add staypoint
                                ret_staypoints = ret_staypoints.append(staypoint, ignore_index=True)

                            # TODO Discussion: Is this last point really a staypoint? As we don't know if the
                            #      person "moves on" afterwards...
                        i = j
                        break
                    
                    # If the last point meets the minimum time threshold, then it is added to the stay point
                    if (j == num_pfs - 1):

                        delta_t = (pfs[j]['tracked_at'] - pfs[i]['tracked_at']).total_seconds()
                        if (delta_t > time_threshold):                                                
                            if (delta_t > timemax_threshold):
                                hrdiff = []
                                hrsum = 0
                                for x in range(i,j):
                                    hrdiff.append((pfs[x+1]['tracked_at']-pfs[x]['tracked_at']).total_seconds())
                                    
                                i0 = i       
                                for mid in range(0,j-i0):
                                    hrsum += hrdiff[mid]
                                    
                                    if(hrsum > timemax_threshold or mid == j-i0-1):
                                        staypoint = {}
                                        staypoint['user_id'] = pfs[i]['user_id']
                                        staypoint['geom'] = Point(np.mean([pfs[k]['geom'].x for k in range(i, i0+mid+1)]),
                                                                  np.mean([pfs[k]['geom'].y for k in range(i, i0+mid+1)]))
                                        if 'elevation' in pfs[i].keys():
                                            staypoint['elevation'] = np.mean([pfs[k]['elevation'] for k in range(i, i0+mid+1)])
                                        if 'velocity' in pfs[i].keys():
                                            staypoint['velocity'] = np.mean([pfs[k]['velocity'] for k in range(i, i0+mid+1)])
                                        staypoint['started_at'] = pfs[i]['tracked_at']
                                        staypoint['finished_at'] = pfs[i0+mid+1]['tracked_at']  # TODO: should this not be j-1? because j is not part of the staypoint. DB: Changed                   
                                        staypoint['id'] = staypoint_id_counter
                                        # store matching 
                                        posfix_staypoint_matching[staypoint_id_counter] = [pfs[k]['id'] for k in range(i, i0+mid+1)]
                                        staypoint_id_counter += 1
                                        # add staypoint
                                        ret_staypoints = ret_staypoints.append(staypoint, ignore_index=True)
                                                                               
                                        i = i0+mid+1
                                        hrsum = 0
                            else:                       
                                staypoint = {}
                                staypoint['user_id'] = pfs[i]['user_id']
                                staypoint['geom'] = Point(np.mean([pfs[k]['geom'].x for k in range(i, j+1)]),
                                                          np.mean([pfs[k]['geom'].y for k in range(i, j+1)]))
                                if 'elevation' in pfs[i].keys():
                                    staypoint['elevation'] = np.mean([pfs[k]['elevation'] for k in range(i, j+1)])
                                if 'velocity' in pfs[i].keys():
                                    staypoint['velocity'] = np.mean([pfs[k]['velocity'] for k in range(i, j+1)])
                                staypoint['started_at'] = pfs[i]['tracked_at']
                                staypoint['finished_at'] = pfs[j]['tracked_at']  # TODO: should this not be j-1? because j is not part of the staypoint. DB: Changed.
                                staypoint['id'] = staypoint_id_counter

                                # store matching
                                posfix_staypoint_matching[staypoint_id_counter] = [pfs[k]['id'] for k in range(i, j+1)]
        
                                    # posfix_staypoint_matching[staypoint_id_counter] = [
                                    #     j]  # rather [k for k in range(i, j)]?
                            
                                staypoint_id_counter += 1
                                ret_staypoints = ret_staypoints.append(staypoint, ignore_index=True)

                    j = j + 1

            # add matching to original positionfixes (for every user)

            for staypoints_id, posfix_idlist in posfix_staypoint_matching.items():
                # note that we use .loc because above we have saved the id 
                # of the positionfixes not thier absolut position
                positionfixes.loc[posfix_idlist, 'staypoint_id'] = staypoints_id


    elif method == 'dbscan':
        # TODO: Make sure time information is included in the clustering!
        # time information is in the column 'started at', however the user should be able to
        # adjust the distance metric e.g. chebychev

        db = DBSCAN(eps=epsilon, min_samples=num_samples)
        for user_id_this in positionfixes['user_id'].unique():

            user_positionfixes = positionfixes[positionfixes['user_id'] == user_id_this]  # this is not a copy!

            # TODO: enable transformations to temporary (metric) system
            transform_crs = None
            if transform_crs is not None:
                pass

            # get staypoint matching
            coordinates = np.array([[g.x, g.y] for g in user_positionfixes['geom']])
            labels = db.fit_predict(coordinates)

            # add positionfixes - staypoint matching to original positionfixes
            positionfixes.loc[user_positionfixes.index, 'staypoint_id'] = labels

        # create staypoints as the center of the grouped positionfixes
        grouped_df = positionfixes.groupby(['user_id', 'staypoint_id'])
        for combined_id, group in grouped_df:
            user_id, staypoint_id = combined_id

            if int(staypoint_id) != -1:
                staypoint = {}
                staypoint['user_id'] = user_id
                staypoint['id'] = staypoint_id

                # point geometry of staypoint
                staypoint['geom'] = Point(group.geometry.x.mean(),
                                          group.geometry.y.mean())

                ret_staypoints = ret_staypoints.append(staypoint, ignore_index=True)

    ret_staypoints = gpd.GeoDataFrame(ret_staypoints, geometry='geom',
                                      crs=positionfixes.crs)
    ret_staypoints['id'] = ret_staypoints['id'].astype('int')
    
    return ret_staypoints


def extract_triplegs_ipa(positionfixes, staypoints=None, *args, **kwargs):
    """Extract triplegs from positionfixes. A tripleg is (for now) defined as anything
    that happens between two consecutive staypoints.
    **Attention**: This function requires either a column ``staypoint_id`` on the 
    positionfixes or passing some staypoints that correspond to the positionfixes! 
    This means you usually should call ``extract_staypoints()`` first.
    This function modifies the positionfixes and adds a ``tripleg_id``.
    Parameters
    ----------
    positionfixes : GeoDataFrame
        The positionfixes have to follow the standard definition for positionfixes DataFrames.
    staypoints : GeoDataFrame, optional
        The staypoints (corresponding to the positionfixes). If this is not passed, the 
        positionfixes need staypoint_ids associated with them.
    Returns
    -------
    GeoDataFrame
        A new GeoDataFrame containing triplegs.
    Examples
    --------
    >>> psfs.as_positionfixes.extract_triplegs(staypoints)
    """
    # Check that data adheres to contract.
    if staypoints is None and len(positionfixes['staypoint_id'].unique()) < 2:
        raise ValueError("If staypoints is not defined, positionfixes must have more than 1 staypoint_id.")

    # if staypoints is not None:
    #     raise NotImplementedError("Splitting up positionfixes by timestamp is not available yet. " + \
    #         "Use extract_staypoints and the thus generated staypoint_ids.")

    ret_triplegs = pd.DataFrame(columns=['id', 'user_id', 'started_at', 'finished_at', 'geom'])
    curr_tripleg_id = 0
    # Do this for each user.
    for user_id_this in positionfixes['user_id'].unique():

        positionfixes_user_this = positionfixes.loc[
            positionfixes['user_id'] == user_id_this]  # this is no copy
        pfs = positionfixes_user_this.sort_values('tracked_at')
        generated_triplegs = []

        # Case 1: Staypoints exist and are connected to positionfixes by user id
        if staypoints is not None and "staypoint_id" in pfs:
            stps = staypoints.loc[staypoints['user_id'] == user_id_this].sort_values('started_at')
            stps = stps.to_dict('records')
            for stp1, stp2 in zip(list(stps), list(stps)[1:]):
                # Get all positionfixes that lie between these two staypoints.

                # get the last posfix of the first staypoint
                index_first_posfix_tl = pfs[pfs.staypoint_id == stp1['id']].index[-1]
                position_first_posfix_tl = pfs.index.get_loc(index_first_posfix_tl)
                # get first posfix of the second staypoint
                index_last_posfix_tl = pfs[pfs.staypoint_id == stp2['id']].index[0]
                position_last_posfix_tl = pfs.index.get_loc(index_last_posfix_tl)

                pfs_tripleg = pfs.iloc[position_first_posfix_tl:position_last_posfix_tl + 1]

                # include every positionfix that brings you closer to the center 
                # of the staypoint

                posfix_before, started_at = propagate_tripleg(pfs, stp1, position_first_posfix_tl, direction=-1)
                posfix_before = posfix_before[::-1]
                # add geometry of staypoint and correct the direction

                posfix_after, finished_at = propagate_tripleg(pfs, stp2, position_last_posfix_tl, direction=1)

                coords = list(pfs_tripleg['geom'].apply(lambda r: (r.x, r.y)))
                coords = posfix_before + coords + posfix_after

                if len(coords) > 1:
                    generated_triplegs.append({
                        'id': curr_tripleg_id,
                        'user_id': user_id_this,
                        'started_at': started_at,  # pfs_tripleg['tracked_at'].iloc[0],
                        'finished_at': finished_at,  # pfs_tripleg['tracked_at'].iloc[-1],
                        'geom': LineString(coords),
                        'start_stp': stp1['id'],
                        'end_stp': stp2['id']
                    })
                    curr_tripleg_id += 1

        # Case 2: Staypoints exist but there is no user_id given
        # TODO Not so efficient, always matching on the time (as things are sorted anyways).
        elif staypoints is not None:
            stps = staypoints.loc[staypoints['user_id'] == user_id_this].sort_values('started_at')
            stps = stps.to_dict('records')
            for stp1, stp2 in zip(list(stps), list(stps)[1:]):
                # Get all positionfixes that lie between these two staypoints.
                pfs_tripleg = pfs[(stp1['finished_at'] <= pfs['tracked_at']) & \
                                  (pfs['tracked_at'] <= stp2['started_at'])].sort_values('tracked_at')

                coords = list(pfs_tripleg['geom'].apply(lambda r: (r.x, r.y)))
                if len(coords) > 1:
                    generated_triplegs.append({
                        'id': curr_tripleg_id,
                        'user_id': user_id_this,
                        'started_at': pfs_tripleg['tracked_at'].iloc[0],
                        'finished_at': pfs_tripleg['tracked_at'].iloc[-1],
                        'geom': LineString(list(pfs_tripleg['geom'].apply(lambda r: (r.x, r.y))))
                    })
                    curr_tripleg_id += 1

        # case 3: Only positionfixes with staypoint id for tripleg generation
        else:
            prev_pf = None
            curr_tripleg = {
                'id': curr_tripleg_id,
                'user_id': user_id_this,
                'started_at': pfs['tracked_at'].iloc[0],
                'finished_at': None,
                'coords': []
            }
            for idx, pf in pfs.iterrows():
                if prev_pf is not None and prev_pf['staypoint_id'] == -1 and pf['staypoint_id'] != -1:
                    # This tripleg ends. 
                    pfs.loc[idx, 'tripleg_id'] = curr_tripleg_id
                    curr_tripleg['finished_at'] = pf['tracked_at']
                    curr_tripleg['coords'].append((pf['geom'].x, pf['geom'].y))

                elif (prev_pf is not None and prev_pf['staypoint_id'] != -1 and pf['staypoint_id'] == -1):
                    # A new tripleg starts (due to a staypoint_id switch from -1 to x).
                    if len(curr_tripleg['coords']) > 1:
                        curr_tripleg['geom'] = LineString(curr_tripleg['coords'])
                        del curr_tripleg['coords']
                        generated_triplegs.append(curr_tripleg)
                        curr_tripleg_id += 1

                    curr_tripleg = {'id': curr_tripleg_id, 'user_id': user_id_this, 'started_at': None,
                                    'finished_at': None, 'coords': []}
                    prev_pf['tripleg_id'] = curr_tripleg_id
                    pfs.loc[idx, 'tripleg_id'] = curr_tripleg_id
                    curr_tripleg['started_at'] = pf['tracked_at']
                    curr_tripleg['coords'].append((pf['geom'].x, pf['geom'].y))

                elif prev_pf is not None and prev_pf['staypoint_id'] != -1 and \
                        pf['staypoint_id'] != -1 and prev_pf['staypoint_id'] != pf['staypoint_id']:
                    # A new tripleg starts (due to a staypoint_id switch from x to y).
                    pfs.loc[idx, 'tripleg_id'] = curr_tripleg_id
                    curr_tripleg['finished_at'] = pf['tracked_at']
                    curr_tripleg['coords'].append((pf['geom'].x, pf['geom'].y))

                    if len(curr_tripleg['coords']) > 1:
                        curr_tripleg['geom'] = LineString(curr_tripleg['coords'])
                        del curr_tripleg['coords']
                        generated_triplegs.append(curr_tripleg)
                        curr_tripleg_id += 1

                    curr_tripleg = {
                        'id': curr_tripleg_id,
                        'user_id': user_id_this,
                        'started_at': None,
                        'finished_at': None,
                        'coords': []
                    }
                    prev_pf['tripleg_id'] = curr_tripleg_id
                    pfs.loc[idx, 'tripleg_id'] = curr_tripleg_id
                    curr_tripleg['started_at'] = pf['tracked_at']
                    curr_tripleg['coords'].append((pf['geom'].x, pf['geom'].y))

                elif prev_pf is not None and prev_pf['staypoint_id'] != -1 and \
                        prev_pf['staypoint_id'] == pf['staypoint_id']:
                    # This is still "at the same staypoint". Do nothing.
                    pass

                else:
                    pfs.loc[idx, 'tripleg_id'] = curr_tripleg_id
                    curr_tripleg['coords'].append((pf['geom'].x, pf['geom'].y))

                prev_pf = pf
        ret_triplegs = ret_triplegs.append(generated_triplegs)

    ret_triplegs = gpd.GeoDataFrame(ret_triplegs, geometry='geom', crs=positionfixes.crs)
    ret_triplegs['id'] = ret_triplegs['id'].astype('int')

    return ret_triplegs


def propagate_tripleg(pfs, stp, position_edge_posfix_tl, direction=1):
    # propagate backwards at start
    posfix_to_add = []
    i = direction

    if (position_edge_posfix_tl + i) >= len(pfs) or (position_edge_posfix_tl + i)  < 0:
        return posfix_to_add, pfs.iloc[position_edge_posfix_tl].tracked_at

    geom_stp = stp['geom']

    geom_edge_posfix_tl = pfs.iloc[position_edge_posfix_tl].geom
    geom_candidate_posfix = pfs.iloc[position_edge_posfix_tl + i].geom

    dist_edge_psf_stp = geom_stp.distance(geom_edge_posfix_tl)

    # new posfix must be closer to the center of the staypoint then the current one
    cond1 = (geom_stp.distance(geom_candidate_posfix) < dist_edge_psf_stp)

    # new posfix must be closer then the center of the staypoint to qualify
    cond2 = (geom_edge_posfix_tl.distance(geom_candidate_posfix) < dist_edge_psf_stp)

    closer = cond1 and cond2

    while (closer):
        if (position_edge_posfix_tl + i + direction) > len(pfs) or (position_edge_posfix_tl + i + direction)  < 0:
            break

        # insert new posfix
        posfix_to_add.append((geom_candidate_posfix.x, geom_candidate_posfix.y))

        # update variables
        geom_edge_posfix_tl = pfs.iloc[position_edge_posfix_tl + i,:].geom
        i = i + direction
        geom_candidate_posfix = pfs.iloc[position_edge_posfix_tl + i,:].geom

        # update closer
        dist_edge_psf_stp = geom_stp.distance(geom_edge_posfix_tl)
        cond1 = (geom_stp.distance(geom_candidate_posfix) < dist_edge_psf_stp)
        cond2 = (geom_edge_posfix_tl.distance(geom_candidate_posfix) < dist_edge_psf_stp)
        closer = cond1 and cond2

    tracked_at = pfs.iloc[position_edge_posfix_tl + i].tracked_at
    # posfix_to_add.append((geom_stp.x, geom_stp.y))
    return posfix_to_add, tracked_at
