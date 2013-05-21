#ifndef TOOLPATH_H
#define TOOLPATH_H

struct Path_;

/** @brief Extracts a set of contours from a distance image
    @param ni Image width
    @param nj Image height
    @param distance Distance field (with distances in mm)
    @param mm_per_pixel Lattice scale factor
    @param num_contours Number of contours to extract
    @param contour_levels List of contour levels
    @param paths Pointer to an array of path pointers
    @details paths can be dereferenced to get an array of path pointers.
    It may be reallocated to increase storage size.
    @returns The number of paths stored.
*/
int find_paths(const int ni, const int nj,
               float const*const*const distances,
               const float mm_per_pixel, const int num_contours,
               const float* const contour_levels,
               struct Path_*** const paths);

#endif
